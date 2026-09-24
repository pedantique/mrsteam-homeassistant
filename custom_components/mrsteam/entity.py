"""Base entity for MrSteam iSteamX."""

from __future__ import annotations

from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, R_HUB_VERSION
from .coordinator import MrSteamCoordinator


class MrSteamEntity(CoordinatorEntity[MrSteamCoordinator]):
    """Common base wiring device info + availability."""

    _attr_has_entity_name = True

    def __init__(self, coordinator: MrSteamCoordinator, key: str) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{coordinator.device.thing_name}_{key}"

    @property
    def device_info(self) -> DeviceInfo:
        dev = self.coordinator.device
        return DeviceInfo(
            identifiers={(DOMAIN, dev.thing_name)},
            name=dev.name,
            manufacturer="MrSteam",
            model=self.coordinator.client.model_number,
            sw_version=str(self.coordinator.reported.get(R_HUB_VERSION, "")) or None,
        )
