"""Sensors for MrSteam iSteamX (parsed from the reported shadow)."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.const import UnitOfTemperature, UnitOfTime
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import MrSteamConfigEntry
from .const import (
    R_AROMA,
    R_ROOM_TEMP,
    R_SHOWER_CONNECTED,
    R_SHOWER_CURRENT_TEMP,
    R_SHOWER_TEMP,
    R_SHOWER_TIME,
    R_STEAM_MAX_TEMP,
    R_STEAM_REMAIN,
    R_STEAM_TEMP,
    R_STEAM_TIME,
)
from .entity import MrSteamEntity


def _hex_min(val: Any) -> int | None:
    """Decode a hex-string minutes field ("0014" -> 20)."""
    if val in (None, ""):
        return None
    try:
        return int(str(val), 16)
    except (ValueError, TypeError):
        return None


def _steam_c(val: Any) -> float | None:
    """deviceSteamTemp: DECIMAL tenths of a degree C — the steam-HEAD/vapour
    temperature (~78 C idle, ~98-100 C while steaming), not the room.
    Confirmed live: it holds ~98 C regardless of the room's target.
    """
    if val in (None, ""):
        return None
    try:
        return round(int(val) / 10, 1)
    except (ValueError, TypeError):
        return None


def _room_c(val: Any) -> float | None:
    """deviceRoomTemp: HEX, encoded as (deg F - 32) x 10, i.e. degC = hex / 18.

    CONFIRMED against the wall unit at two points during a live session:
    0x01B0=432 -> 24.0 C (wall showed 24) and 0x0276=630 -> 35.0 C (wall showed
    35). This is the steam-ROOM air temperature the wall unit displays.
    """
    if val in (None, ""):
        return None
    try:
        return round(int(str(val), 16) / 18, 1)
    except (ValueError, TypeError):
        return None


def _hex_whole(val: Any) -> int | None:
    """A hex whole-number field (e.g. steamMaxTemp "005D" -> 93)."""
    if val in (None, ""):
        return None
    try:
        return int(str(val), 16)
    except (ValueError, TypeError):
        return None


def _shower_min(val: Any) -> float | None:
    """deviceShowerTime appears to be seconds (1200 -> 20 min). Best-effort."""
    if val in (None, ""):
        return None
    try:
        return round(int(val) / 60, 1)
    except (ValueError, TypeError):
        return None


@dataclass(frozen=True, kw_only=True)
class MrSteamSensorDescription(SensorEntityDescription):
    """Sensor description with a value extractor over the reported dict."""

    value_fn: Callable[[dict[str, Any]], Any]


SENSORS: tuple[MrSteamSensorDescription, ...] = (
    MrSteamSensorDescription(
        key="remaining_time",
        translation_key="remaining_time",
        name="Remaining time",
        icon="mdi:timer-sand",
        native_unit_of_measurement=UnitOfTime.MINUTES,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda r: _hex_min(r.get(R_STEAM_REMAIN)),
    ),
    MrSteamSensorDescription(
        key="session_length",
        name="Session length",
        icon="mdi:timer",
        native_unit_of_measurement=UnitOfTime.MINUTES,
        value_fn=lambda r: _hex_min(r.get(R_STEAM_TIME)),
    ),
    # Decoders emit Celsius; HA converts to the user's display unit.
    MrSteamSensorDescription(
        key="steam_temperature",
        name="Steam head temperature",
        device_class=SensorDeviceClass.TEMPERATURE,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda r: _steam_c(r.get(R_STEAM_TEMP)),
    ),
    MrSteamSensorDescription(
        key="room_temperature",
        name="Room temperature",
        device_class=SensorDeviceClass.TEMPERATURE,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda r: _room_c(r.get(R_ROOM_TEMP)),
    ),
    # steamMaxTemp encoding isn't confidently known; expose as a raw diagnostic.
    MrSteamSensorDescription(
        key="max_temp_raw",
        name="Max temp (raw)",
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda r: _hex_whole(r.get(R_STEAM_MAX_TEMP)),
    ),
    # Aroma has no "connected" flag in the shadow, so it can't be auto-hidden;
    # it reads 0 when no aromatherapy unit is fitted (users can disable it).
    MrSteamSensorDescription(
        key="aroma",
        name="Aroma level",
        icon="mdi:flower",
        entity_category=EntityCategory.DIAGNOSTIC,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda r: r.get(R_AROMA),
    ),
)

# Only added when deviceShowerConnected is true. Read-only, best-effort decode;
# untested (developer has no shower accessory) — a shower owner should validate.
SHOWER_SENSORS: tuple[MrSteamSensorDescription, ...] = (
    MrSteamSensorDescription(
        key="shower_temperature",
        name="Shower target temperature",
        device_class=SensorDeviceClass.TEMPERATURE,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        value_fn=lambda r: _steam_c(r.get(R_SHOWER_TEMP)),
    ),
    MrSteamSensorDescription(
        key="shower_current_temperature",
        name="Shower current temperature",
        device_class=SensorDeviceClass.TEMPERATURE,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda r: _steam_c(r.get(R_SHOWER_CURRENT_TEMP)),
    ),
    MrSteamSensorDescription(
        key="shower_time",
        name="Shower time",
        icon="mdi:timer",
        native_unit_of_measurement=UnitOfTime.MINUTES,
        value_fn=lambda r: _shower_min(r.get(R_SHOWER_TIME)),
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: MrSteamConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator = entry.runtime_data
    entities = [MrSteamSensor(coordinator, desc) for desc in SENSORS]
    if coordinator.reported.get(R_SHOWER_CONNECTED):
        entities += [MrSteamSensor(coordinator, desc) for desc in SHOWER_SENSORS]
    async_add_entities(entities)


class MrSteamSensor(MrSteamEntity, SensorEntity):
    """A single reported-shadow value."""

    entity_description: MrSteamSensorDescription

    def __init__(self, coordinator, description: MrSteamSensorDescription) -> None:  # noqa: ANN001
        super().__init__(coordinator, description.key)
        self.entity_description = description

    @property
    def native_value(self) -> Any:
        return self.entity_description.value_fn(self.coordinator.reported)
