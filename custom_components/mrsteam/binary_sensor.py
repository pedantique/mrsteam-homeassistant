"""Binary sensors for MrSteam iSteamX."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
    BinarySensorEntityDescription,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import MrSteamConfigEntry
from .const import (
    R_CHROMA_CONNECTED,
    R_LIGHT_STATUS,
    R_RELAY_CONNECTED,
    R_RELAY_STATUS,
    R_SHOWER_CONNECTED,
    R_SHOWER_STATUS,
    R_STEAM_H20,
    R_STEAM_STATUS,
    SHOWER_OFF,
    STEAM_ON,
)
from .entity import MrSteamEntity


@dataclass(frozen=True, kw_only=True)
class MrSteamBinaryDescription(BinarySensorEntityDescription):
    value_fn: Callable[[dict[str, Any]], bool]


BINARY_SENSORS: tuple[MrSteamBinaryDescription, ...] = (
    MrSteamBinaryDescription(
        key="running",
        name="Steaming",
        device_class=BinarySensorDeviceClass.RUNNING,
        value_fn=lambda r: r.get(R_STEAM_STATUS) == STEAM_ON,
    ),
    MrSteamBinaryDescription(
        key="water",
        name="Generator water",
        icon="mdi:water",
        # deviceSteamH20 (bool) reflects water in the generator's own tank, not a
        # room sensor. Exact polarity (present vs low-water) unconfirmed, so we
        # expose it directly rather than guessing an inversion.
        value_fn=lambda r: bool(r.get(R_STEAM_H20)),
    ),
)

# Added only when the matching accessory is connected. Read-only, untested.
SHOWER_BINARY = MrSteamBinaryDescription(
    key="shower_running",
    name="Shower running",
    device_class=BinarySensorDeviceClass.RUNNING,
    value_fn=lambda r: r.get(R_SHOWER_STATUS, SHOWER_OFF) != SHOWER_OFF,
)
LIGHT_BINARY = MrSteamBinaryDescription(
    key="light",
    name="Light",
    icon="mdi:lightbulb",
    value_fn=lambda r: bool(r.get(R_LIGHT_STATUS)),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: MrSteamConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator = entry.runtime_data
    entities: list[BinarySensorEntity] = [
        MrSteamBinarySensor(coordinator, desc) for desc in BINARY_SENSORS
    ]
    if coordinator.reported.get(R_SHOWER_CONNECTED):
        entities.append(MrSteamBinarySensor(coordinator, SHOWER_BINARY))
    if coordinator.reported.get(R_CHROMA_CONNECTED):
        entities.append(MrSteamBinarySensor(coordinator, LIGHT_BINARY))
    if coordinator.reported.get(R_RELAY_CONNECTED):
        for i, output in enumerate(coordinator.reported.get(R_RELAY_STATUS, [])):
            entities.append(MrSteamRelayBinary(coordinator, i, output.get("name")))
    async_add_entities(entities)


class MrSteamRelayBinary(MrSteamEntity, BinarySensorEntity):
    """One relay-box output (read-only)."""

    def __init__(self, coordinator, index: int, name: str | None) -> None:  # noqa: ANN001
        super().__init__(coordinator, f"relay_{index}")
        self._index = index
        self._attr_name = name or f"Relay output {index + 1}"

    @property
    def is_on(self) -> bool:
        outputs = self.coordinator.reported.get(R_RELAY_STATUS, [])
        if self._index < len(outputs):
            return bool(outputs[self._index].get("isOpen"))
        return False


class MrSteamBinarySensor(MrSteamEntity, BinarySensorEntity):
    entity_description: MrSteamBinaryDescription

    def __init__(self, coordinator, description: MrSteamBinaryDescription) -> None:  # noqa: ANN001
        super().__init__(coordinator, description.key)
        self.entity_description = description

    @property
    def is_on(self) -> bool:
        return self.entity_description.value_fn(self.coordinator.reported)
