"""Data update coordinator for MrSteam iSteamX."""

from __future__ import annotations

import logging
from datetime import timedelta
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.event import async_call_later
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import MrSteamClient, MrSteamDevice, MrSteamError
from .const import (
    DOMAIN,
    KEY_APP_PROGRAM,
    R_PROGRAM_LIST,
    R_STEAM_STATUS,
    STEAM_OFF,
    STEAM_ON,
)

_LOGGER = logging.getLogger(__name__)

# After a command we must NOT immediately poll: a status read connects as
# thingName, which briefly kicks the device offline and would interrupt it
# processing the command. Give it an uninterrupted window, then confirm.
_POST_COMMAND_DELAY = 15


class MrSteamCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Polls one generator's shadow in short bursts and dispatches commands."""

    def __init__(
        self,
        hass: HomeAssistant,
        entry: ConfigEntry,
        client: MrSteamClient,
        device: MrSteamDevice,
        scan_interval: int,
    ) -> None:
        super().__init__(
            hass,
            _LOGGER,
            name=f"{DOMAIN} {device.name}",
            update_interval=timedelta(seconds=scan_interval),
            config_entry=entry,
        )
        self.client = client
        self.device = device

    async def _async_update_data(self) -> dict[str, Any]:
        try:
            doc = await self.hass.async_add_executor_job(
                self.client.get_shadow, self.device.thing_name
            )
        except MrSteamError as err:
            raise UpdateFailed(str(err)) from err
        state = doc.get("state", {})
        reported = (state.get("reported") or {}).get("devices") or {}
        desired = (state.get("desired") or {}).get("steam") or {}
        return {"reported": reported, "desired": desired, "version": doc.get("version")}

    @property
    def reported(self) -> dict[str, Any]:
        return (self.data or {}).get("reported", {})

    @property
    def desired(self) -> dict[str, Any]:
        return (self.data or {}).get("desired", {})

    @property
    def programs(self) -> list[dict[str, Any]]:
        """Available program objects, e.g. {id, program_name, add_time, profiles_id}."""
        return [
            p
            for p in self.reported.get(R_PROGRAM_LIST, [])
            if isinstance(p, dict) and p.get("program_name")
        ]

    def program_by_name(self, name: str) -> dict[str, Any] | None:
        return next((p for p in self.programs if p.get("program_name") == name), None)

    @property
    def selected_program(self) -> dict[str, Any] | None:
        """The program object to start with.

        The device requires a FULL program object in desired.steam.appProgram
        (a bare "default" string is ignored). Prefer whatever the shadow's
        desired already holds; otherwise fall back to the first program.
        """
        cur = self.desired.get(KEY_APP_PROGRAM)
        if isinstance(cur, dict) and cur.get("program_name"):
            return cur
        return self.programs[0] if self.programs else None

    @property
    def current_program_name(self) -> str | None:
        cur = self.desired.get(KEY_APP_PROGRAM)
        if isinstance(cur, dict):
            return cur.get("program_name")
        sel = self.selected_program
        return sel.get("program_name") if sel else None

    # -- commands ------------------------------------------------------------
    def _optimistic_status(self, status: str) -> None:
        """Reflect a command in the UI immediately (the real poll is delayed)."""
        data = dict(self.data or {})
        reported = dict(data.get("reported", {}))
        reported[R_STEAM_STATUS] = status
        data["reported"] = reported
        self.async_set_updated_data(data)

    def _refresh_after_settle(self) -> None:
        async def _do(_now) -> None:
            await self.async_request_refresh()

        async_call_later(self.hass, _POST_COMMAND_DELAY, _do)

    async def async_set_steam(self, on: bool) -> None:
        """Start or stop steam (command via a unique app-*-dev client)."""
        if on:
            program = self.selected_program
            if program is None:
                raise MrSteamError(
                    "No steam programs available to start; create one in the app first"
                )
            await self.hass.async_add_executor_job(
                lambda: self.client.update_desired(
                    self.device.thing_name, steam_status=True, program=program
                )
            )
        else:
            await self.hass.async_add_executor_job(
                lambda: self.client.update_desired(
                    self.device.thing_name, steam_status=False
                )
            )
        self._optimistic_status(STEAM_ON if on else STEAM_OFF)
        self._refresh_after_settle()

    async def async_set_program(self, name: str) -> None:
        program = self.program_by_name(name)
        if program is None:
            raise MrSteamError(f"Unknown program: {name}")
        await self.hass.async_add_executor_job(
            lambda: self.client.update_desired(
                self.device.thing_name, program=program
            )
        )
        self._refresh_after_settle()
