"""Program selector for MrSteam iSteamX."""

from __future__ import annotations

from homeassistant.components.select import SelectEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import MrSteamConfigEntry
from .entity import MrSteamEntity


async def async_setup_entry(
    hass: HomeAssistant,
    entry: MrSteamConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    async_add_entities([MrSteamProgramSelect(entry.runtime_data)])


class MrSteamProgramSelect(MrSteamEntity, SelectEntity):
    """Selects the steam program written to the shadow's desired state."""

    _attr_name = "Program"
    _attr_icon = "mdi:playlist-play"

    def __init__(self, coordinator) -> None:  # noqa: ANN001
        super().__init__(coordinator, "program")

    @property
    def options(self) -> list[str]:
        return [p["program_name"] for p in self.coordinator.programs]

    @property
    def current_option(self) -> str | None:
        return self.coordinator.current_program_name

    async def async_select_option(self, option: str) -> None:
        await self.coordinator.async_set_program(option)
