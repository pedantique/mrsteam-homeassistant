"""Config flow for MrSteam iSteamX."""

from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol
from homeassistant.config_entries import (
    ConfigEntry,
    ConfigFlow,
    ConfigFlowResult,
    OptionsFlow,
)
from homeassistant.core import callback
from homeassistant.helpers import config_validation as cv

from .api import MrSteamAuthError, MrSteamClient, MrSteamDevice, MrSteamError
from .const import (
    CONF_EMAIL,
    CONF_MODEL_NUMBER,
    CONF_PASSWORD,
    CONF_SCAN_INTERVAL,
    DEFAULT_MODEL_NUMBER,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
    MIN_SCAN_INTERVAL,
)

_LOGGER = logging.getLogger(__name__)


async def _validate(hass, email, password, model) -> list[MrSteamDevice]:
    client = MrSteamClient(email=email, password=password, model_number=model)
    await hass.async_add_executor_job(client.authenticate)
    return await hass.async_add_executor_job(client.get_devices)


class MrSteamConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle the config flow."""

    VERSION = 1

    def __init__(self) -> None:
        self._data: dict[str, Any] = {}
        self._devices: list[MrSteamDevice] = []

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        errors: dict[str, str] = {}
        if user_input is not None:
            model = user_input.get(CONF_MODEL_NUMBER, DEFAULT_MODEL_NUMBER)
            try:
                devices = await _validate(
                    self.hass,
                    user_input[CONF_EMAIL],
                    user_input[CONF_PASSWORD],
                    model,
                )
            except MrSteamAuthError:
                errors["base"] = "invalid_auth"
            except MrSteamError:
                errors["base"] = "cannot_connect"
            except Exception:  # noqa: BLE001
                _LOGGER.exception("Unexpected error during setup")
                errors["base"] = "unknown"
            else:
                if not devices:
                    errors["base"] = "no_devices"
                else:
                    self._data = {
                        CONF_EMAIL: user_input[CONF_EMAIL],
                        CONF_PASSWORD: user_input[CONF_PASSWORD],
                        CONF_MODEL_NUMBER: model,
                    }
                    self._devices = devices
                    if len(devices) == 1:
                        return await self._create(devices[0])
                    return await self.async_step_device()

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_EMAIL): str,
                    vol.Required(CONF_PASSWORD): str,
                    vol.Optional(
                        CONF_MODEL_NUMBER, default=DEFAULT_MODEL_NUMBER
                    ): str,
                }
            ),
            errors=errors,
        )

    async def async_step_device(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        if user_input is not None:
            device = next(
                d for d in self._devices if d.thing_name == user_input["thing_name"]
            )
            return await self._create(device)
        return self.async_show_form(
            step_id="device",
            data_schema=vol.Schema(
                {
                    vol.Required("thing_name"): vol.In(
                        {d.thing_name: d.name for d in self._devices}
                    )
                }
            ),
        )

    async def _create(self, device: MrSteamDevice) -> ConfigFlowResult:
        await self.async_set_unique_id(
            f"{self._data[CONF_EMAIL].lower()}:{device.thing_name}"
        )
        self._abort_if_unique_id_configured()
        return self.async_create_entry(
            title=device.name,
            data={**self._data, "thing_name": device.thing_name},
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> OptionsFlow:
        return MrSteamOptionsFlow()


class MrSteamOptionsFlow(OptionsFlow):
    """Handle options (poll interval)."""

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)
        current = self.config_entry.options.get(
            CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL
        )
        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                {
                    vol.Optional(CONF_SCAN_INTERVAL, default=current): vol.All(
                        cv.positive_int, vol.Clamp(min=MIN_SCAN_INTERVAL)
                    )
                }
            ),
        )
