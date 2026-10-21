"""Unit tests for the API error mapping.

These lock in the distinction HACS review kept flagging: only a genuine Cognito
credential rejection is an auth failure (-> reauth); every transport, service or
parse error is a transient MrSteamError (-> retry), never a spurious reauth.
"""

import io
import sys
import types

import pytest
from botocore.exceptions import ClientError

from custom_components.mrsteam.api import (
    MrSteamAuthError,
    MrSteamClient,
    MrSteamError,
)


def _client_error(code: str) -> ClientError:
    return ClientError({"Error": {"Code": code, "Message": "m"}}, "InitiateAuth")


def _stub_pycognito(monkeypatch, exc: Exception) -> None:
    """Replace the lazily imported pycognito so Cognito.authenticate raises exc."""
    mod = types.ModuleType("pycognito")

    class Cognito:
        def __init__(self, *args, **kwargs):
            pass

        def authenticate(self, password):
            raise exc

    mod.Cognito = Cognito
    monkeypatch.setitem(sys.modules, "pycognito", mod)


# -- authenticate() ----------------------------------------------------------
@pytest.mark.parametrize(
    "code",
    [
        "NotAuthorizedException",
        "UserNotFoundException",
        "PasswordResetRequiredException",
        "UserNotConfirmedException",
    ],
)
def test_authenticate_rejected_credentials_raise_auth_error(monkeypatch, code):
    _stub_pycognito(monkeypatch, _client_error(code))
    client = MrSteamClient(email="e@example.com", password="pw")
    with pytest.raises(MrSteamAuthError):
        client.authenticate()


@pytest.mark.parametrize(
    "exc",
    [
        _client_error("TooManyRequestsException"),
        _client_error("InternalErrorException"),
        ConnectionError("dns failure"),
        TimeoutError("slow"),
    ],
)
def test_authenticate_transient_errors_raise_api_error(monkeypatch, exc):
    # MrSteamAuthError does NOT inherit MrSteamError, so this also asserts the
    # transient path never produces an auth error.
    _stub_pycognito(monkeypatch, exc)
    client = MrSteamClient(email="e@example.com", password="pw")
    with pytest.raises(MrSteamError):
        client.authenticate()


# -- get_devices() -----------------------------------------------------------
class _FakeResp(io.BytesIO):
    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False


def _client_with_opener(monkeypatch, open_impl):
    client = MrSteamClient(email="e@example.com", password=None)
    client._id_token = "tok"  # skip the auth path
    opener = types.SimpleNamespace(open=open_impl)
    monkeypatch.setattr(
        "custom_components.mrsteam.api.urllib.request.build_opener",
        lambda *a, **k: opener,
    )
    return client


@pytest.mark.parametrize("exc", [TimeoutError("read"), OSError("refused")])
def test_get_devices_transport_errors_raise_api_error(monkeypatch, exc):
    def _open(req, timeout=0):
        raise exc

    client = _client_with_opener(monkeypatch, _open)
    with pytest.raises(MrSteamError):
        client.get_devices()


@pytest.mark.parametrize(
    "body",
    [b"<html>502 Bad Gateway</html>", b'{"data":[{"no_thing_name":1}]}'],
)
def test_get_devices_bad_body_raises_api_error(monkeypatch, body):
    def _open(req, timeout=0):
        return _FakeResp(body)

    client = _client_with_opener(monkeypatch, _open)
    with pytest.raises(MrSteamError):
        client.get_devices()


def test_get_devices_valid_body_returns_device(monkeypatch):
    body = b'{"data":[{"thingName":"su-1","device_custom_name":"Spa"}]}'

    def _open(req, timeout=0):
        return _FakeResp(body)

    client = _client_with_opener(monkeypatch, _open)
    devices = client.get_devices()
    assert len(devices) == 1
    assert devices[0].thing_name == "su-1"
    assert devices[0].name == "Spa"
