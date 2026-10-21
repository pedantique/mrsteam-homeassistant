"""Config flow and reauth flow tests."""

from unittest.mock import patch

from homeassistant import config_entries
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.mrsteam.api import MrSteamAuthError, MrSteamDevice, MrSteamError
from custom_components.mrsteam.const import DOMAIN

DEVICE = MrSteamDevice(thing_name="su-1", device_id="su-1", name="Spa", connected=True)
USER_INPUT = {"email": "e@example.com", "password": "pw"}


async def _start_user_flow(hass: HomeAssistant):
    return await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )


async def test_user_flow_success(hass: HomeAssistant) -> None:
    result = await _start_user_flow(hass)
    assert result["type"] is FlowResultType.FORM
    with patch(
        "custom_components.mrsteam.config_flow._validate", return_value=[DEVICE]
    ):
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], USER_INPUT
        )
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == "Spa"
    assert result["data"]["thing_name"] == "su-1"


async def test_user_flow_invalid_auth(hass: HomeAssistant) -> None:
    result = await _start_user_flow(hass)
    with patch(
        "custom_components.mrsteam.config_flow._validate",
        side_effect=MrSteamAuthError("bad password"),
    ):
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], USER_INPUT
        )
    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"base": "invalid_auth"}


async def test_user_flow_cannot_connect(hass: HomeAssistant) -> None:
    # A transient MrSteamError must surface as cannot_connect, not invalid_auth.
    result = await _start_user_flow(hass)
    with patch(
        "custom_components.mrsteam.config_flow._validate",
        side_effect=MrSteamError("network down"),
    ):
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], USER_INPUT
        )
    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"base": "cannot_connect"}


async def test_reauth_flow_updates_password(hass: HomeAssistant) -> None:
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={
            "email": "e@example.com",
            "password": "old",
            "model_number": "SU-70",
            "thing_name": "su-1",
        },
        unique_id="e@example.com:su-1",
    )
    entry.add_to_hass(hass)

    result = await entry.start_reauth_flow(hass)
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "reauth_confirm"

    with (
        patch(
            "custom_components.mrsteam.config_flow._validate", return_value=[DEVICE]
        ),
        patch("custom_components.mrsteam.async_setup_entry", return_value=True),
    ):
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], {"password": "new"}
        )
        await hass.async_block_till_done()

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "reauth_successful"
    assert entry.data["password"] == "new"
