"""Client for the MrSteam iSteamX cloud (Cognito + API Gateway + AWS IoT).

Design note — two different IoT client ids, because the fixed policy scopes
access to the caller's own thing:
  * READS use ``client_id == thingName`` (only that id may subscribe to the
    thing's shadow). The wall unit also uses that id, so a read briefly bumps it
    off the cloud — hence short bursts, not a persistent connection.
  * COMMANDS use a unique ``app-*-dev`` client id (like the vendor app). That id
    can PUBLISH shadow updates but not subscribe, and — crucially — it does NOT
    collide with the wall unit, so the device stays connected and receives the
    command. Publishing as thingName would kick the device offline and the
    command would never arrive.
Every operation is a short connect -> do one thing -> disconnect burst.
"""

from __future__ import annotations

import json
import logging
import threading
import time
import urllib.error
import urllib.request
import uuid
from dataclasses import dataclass, field
from typing import Any

import boto3
from botocore.config import Config as BotoConfig

from .const import (
    APP_CLIENT_ID,
    IDENTITY_POOL_ID,
    IOT_ENDPOINT,
    KEY_APP_PROGRAM,
    KEY_APP_STEAM_STATUS,
    LOGIN_PROVIDER,
    REGION,
    REST_BASE,
    USER_POOL_ID,
)

_LOGGER = logging.getLogger(__name__)

# Lazily imported awscrt/awsiot so import failures surface clearly.
_CRED_SKEW = 300  # refresh AWS creds this many seconds before expiry


class MrSteamAuthError(Exception):
    """Raised when authentication fails."""


class MrSteamError(Exception):
    """Generic MrSteam API error."""


@dataclass
class MrSteamDevice:
    """A discovered generator."""

    thing_name: str
    device_id: str
    name: str
    connected: bool = False


@dataclass
class _Creds:
    access_key: str
    secret_key: str
    session_token: str
    expiration: float = 0.0


@dataclass
class MrSteamClient:
    """Synchronous client. Call from an executor thread in Home Assistant."""

    email: str
    password: str | None = None
    model_number: str = "SU-70"

    _cognito: Any = field(default=None, init=False, repr=False)
    _id_token: str | None = field(default=None, init=False, repr=False)
    _creds: _Creds | None = field(default=None, init=False, repr=False)
    _lock: threading.Lock = field(default_factory=threading.Lock, init=False, repr=False)

    # -- construction helpers ------------------------------------------------
    @classmethod
    def from_id_token(cls, email: str, id_token: str, model_number: str = "SU-70") -> "MrSteamClient":
        """Build a client from an existing IdToken (used for testing/read-only)."""
        c = cls(email=email, password=None, model_number=model_number)
        c._id_token = id_token
        return c

    # -- authentication ------------------------------------------------------
    def authenticate(self) -> None:
        """Perform Cognito SRP login and cache tokens."""
        if self.password is None:
            if self._id_token:
                return  # token-injected client
            raise MrSteamAuthError("No password provided")
        from pycognito import Cognito  # noqa: PLC0415

        try:
            u = Cognito(
                USER_POOL_ID,
                APP_CLIENT_ID,
                username=self.email,
                user_pool_region=REGION,
            )
            u.authenticate(password=self.password)
        except Exception as err:  # noqa: BLE001
            raise MrSteamAuthError(f"Cognito login failed: {err}") from err
        self._cognito = u
        self._id_token = u.id_token

    def _valid_id_token(self) -> str:
        if not self._id_token:
            self.authenticate()
        elif self._cognito is not None:
            try:
                self._cognito.check_token()  # renews if within refresh window
                self._id_token = self._cognito.id_token
            except Exception as err:  # noqa: BLE001
                _LOGGER.debug("Token renew failed, re-authenticating: %s", err)
                self.authenticate()
        return self._id_token  # type: ignore[return-value]

    def _aws_creds(self) -> _Creds:
        """Mint (or reuse) temporary AWS credentials for IoT signing."""
        now = time.time()
        if self._creds and self._creds.expiration - _CRED_SKEW > now:
            return self._creds
        id_token = self._valid_id_token()
        ci = boto3.client(
            "cognito-identity", region_name=REGION, config=BotoConfig(proxies={})
        )
        logins = {LOGIN_PROVIDER: id_token}
        iid = ci.get_id(IdentityPoolId=IDENTITY_POOL_ID, Logins=logins)["IdentityId"]
        c = ci.get_credentials_for_identity(IdentityId=iid, Logins=logins)["Credentials"]
        self._creds = _Creds(
            access_key=c["AccessKeyId"],
            secret_key=c["SecretKey"],
            session_token=c["SessionToken"],
            expiration=float(c["Expiration"].timestamp())
            if hasattr(c["Expiration"], "timestamp")
            else float(c["Expiration"]),
        )
        return self._creds

    # -- device discovery (REST) --------------------------------------------
    def get_devices(self) -> list[MrSteamDevice]:
        id_token = self._valid_id_token()
        body = json.dumps(
            {"model_number": self.model_number, "user_id": self.email}
        ).encode()
        req = urllib.request.Request(
            f"{REST_BASE}/user/get-user-devices",
            data=body,
            headers={"Authorization": id_token, "Content-Type": "application/json"},
            method="POST",
        )
        # Never route this through a system proxy.
        opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
        try:
            with opener.open(req, timeout=15) as resp:
                data = json.loads(resp.read().decode())
        except urllib.error.URLError as err:
            raise MrSteamError(f"Device discovery failed: {err}") from err
        out: list[MrSteamDevice] = []
        for d in data.get("data", []) or []:
            out.append(
                MrSteamDevice(
                    thing_name=d["thingName"],
                    device_id=d.get("device_id", d["thingName"]),
                    name=d.get("device_custom_name") or d["thingName"],
                    connected=bool(d.get("connected")),
                )
            )
        return out

    # -- IoT shadow (burst) --------------------------------------------------
    def _connect(self, client_id: str):
        from awscrt import auth, mqtt  # noqa: PLC0415
        from awsiot import mqtt_connection_builder  # noqa: PLC0415

        creds = self._aws_creds()
        provider = auth.AwsCredentialsProvider.new_static(
            creds.access_key, creds.secret_key, creds.session_token
        )
        conn = mqtt_connection_builder.websockets_with_default_aws_signing(
            endpoint=IOT_ENDPOINT,
            region=REGION,
            credentials_provider=provider,
            client_id=client_id,
            clean_session=True,
            keep_alive_secs=30,
        )
        conn.connect().result()
        return conn, mqtt

    @staticmethod
    def _command_client_id() -> str:
        """A unique app-*-dev client id for command publishes (coexists with the
        wall unit, unlike thingName)."""
        return f"app-ha{uuid.uuid4().hex[:10]}-dev"

    def get_shadow(self, thing_name: str, timeout: float = 8.0) -> dict[str, Any]:
        """Fetch the full shadow document in a short burst."""
        with self._lock:
            conn, mqtt = self._connect(thing_name)
            try:
                box: dict[str, Any] = {}
                ev = threading.Event()

                def _cb(topic, payload, **_):  # noqa: ANN001
                    try:
                        box["doc"] = json.loads(payload)
                    finally:
                        ev.set()

                base = f"$aws/things/{thing_name}/shadow"
                conn.subscribe(
                    topic=f"{base}/get/accepted",
                    qos=mqtt.QoS.AT_LEAST_ONCE,
                    callback=_cb,
                )[0].result()
                conn.publish(
                    topic=f"{base}/get", payload=b"", qos=mqtt.QoS.AT_LEAST_ONCE
                )
                if not ev.wait(timeout):
                    raise MrSteamError("Timed out reading shadow")
                return box["doc"]
            finally:
                try:
                    conn.disconnect().result()
                except Exception:  # noqa: BLE001
                    pass

    def update_desired(
        self,
        thing_name: str,
        *,
        steam_status: bool | None = None,
        program: dict[str, Any] | str | None = None,
        timeout: float = 8.0,
    ) -> None:
        """Write desired steam state in a short burst (start/stop/program).

        ``program`` may be the string ``"default"`` or a full program object
        from ``reported.devices.deviceProgramList``; both are accepted when the
        command is published from an app-*-dev client (see class docstring).
        """
        steam: dict[str, Any] = {}
        if steam_status is not None:
            steam[KEY_APP_STEAM_STATUS] = steam_status
        if program is not None:
            steam[KEY_APP_PROGRAM] = program
        # The device only acts on desired changes that carry this clientToken
        # (it marks the write as an app command rather than its own echo).
        payload = json.dumps(
            {
                "state": {"desired": {"steam": steam}},
                "clientToken": f"app-{thing_name}",
            }
        ).encode()

        with self._lock:
            # Commands go out from a unique app-*-dev client: it may publish (but
            # not subscribe), and it does NOT collide with the wall unit, so the
            # device stays online and receives the delta. The QoS1 publish ack is
            # our confirmation (we can't subscribe to update/accepted here).
            conn, mqtt = self._connect(self._command_client_id())
            try:
                fut, _ = conn.publish(
                    topic=f"$aws/things/{thing_name}/shadow/update",
                    payload=payload,
                    qos=mqtt.QoS.AT_LEAST_ONCE,
                )
                fut.result(timeout=timeout)
            except Exception as err:  # noqa: BLE001
                raise MrSteamError(f"Command publish failed: {err}") from err
            finally:
                try:
                    conn.disconnect().result()
                except Exception:  # noqa: BLE001
                    pass
