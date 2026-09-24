"""The MrSteam iSteamX integration."""

from __future__ import annotations

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed, ConfigEntryNotReady

from .api import MrSteamAuthError, MrSteamClient, MrSteamError
from .const import (
    CONF_EMAIL,
    CONF_MODEL_NUMBER,
    CONF_PASSWORD,
    CONF_SCAN_INTERVAL,
    DEFAULT_MODEL_NUMBER,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
)
from .coordinator import MrSteamCoordinator

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [
    Platform.SWITCH,
    Platform.SELECT,
    Platform.SENSOR,
    Platform.BINARY_SENSOR,
]

MrSteamConfigEntry = ConfigEntry[MrSteamCoordinator]


async def async_setup_entry(hass: HomeAssistant, entry: MrSteamConfigEntry) -> bool:
    """Set up MrSteam from a config entry."""
    client = MrSteamClient(
        email=entry.data[CONF_EMAIL],
        password=entry.data[CONF_PASSWORD],
        model_number=entry.data.get(CONF_MODEL_NUMBER, DEFAULT_MODEL_NUMBER),
    )
    try:
        await hass.async_add_executor_job(client.authenticate)
        devices = await hass.async_add_executor_job(client.get_devices)
    except MrSteamAuthError as err:
        raise ConfigEntryAuthFailed(str(err)) from err
    except MrSteamError as err:
        raise ConfigEntryNotReady(str(err)) from err

    thing_name = entry.data.get("thing_name")
    device = next((d for d in devices if d.thing_name == thing_name), None)
    if device is None:
        if not devices:
            raise ConfigEntryNotReady("No devices returned for this account")
        device = devices[0]

    scan_interval = entry.options.get(
        CONF_SCAN_INTERVAL, entry.data.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL)
    )
    coordinator = MrSteamCoordinator(hass, entry, client, device, scan_interval)
    await coordinator.async_config_entry_first_refresh()

    entry.runtime_data = coordinator
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    entry.async_on_unload(entry.add_update_listener(_async_reload_entry))
    return True


async def async_unload_entry(hass: HomeAssistant, entry: MrSteamConfigEntry) -> bool:
    """Unload a config entry."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)


async def _async_reload_entry(hass: HomeAssistant, entry: MrSteamConfigEntry) -> None:
    await hass.config_entries.async_reload(entry.entry_id)
