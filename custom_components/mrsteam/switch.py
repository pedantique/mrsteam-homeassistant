"""Steam on/off switch for MrSteam iSteamX."""

from __future__ import annotations

from typing import Any

from homeassistant.components.switch import SwitchEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import MrSteamConfigEntry
from .const import R_STEAM_STATUS, STEAM_ON
from .entity import MrSteamEntity


async def async_setup_entry(
    hass: HomeAssistant,
    entry: MrSteamConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    async_add_entities([MrSteamSteamSwitch(entry.runtime_data)])


class MrSteamSteamSwitch(MrSteamEntity, SwitchEntity):
    """Turns the steam session on or off."""

    _attr_name = "Steam"
    _attr_icon = "mdi:hot-tub"

    def __init__(self, coordinator) -> None:  # noqa: ANN001
        super().__init__(coordinator, "steam")

    @property
    def is_on(self) -> bool:
        return self.coordinator.reported.get(R_STEAM_STATUS) == STEAM_ON

    async def async_turn_on(self, **kwargs: Any) -> None:
        await self.coordinator.async_set_steam(True)

    async def async_turn_off(self, **kwargs: Any) -> None:
        await self.coordinator.async_set_steam(False)
