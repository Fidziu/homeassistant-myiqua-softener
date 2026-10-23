from unittest.mock import AsyncMock, patch

from homeassistant import config_entries
from homeassistant.data_entry_flow import FlowResultType
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.myiqua_softener.api import IquaAuthError
from custom_components.myiqua_softener.const import DOMAIN

DEVICE = {"id": "dev1", "serial_number": "S1", "nickname": "Zmiekczacz"}
DATA = {"email": "a@b.c", "password": "old", "device_id": "dev1"}
LIST = "custom_components.myiqua_softener.api.IquaApiAsync.async_list_devices"
SETUP = "custom_components.myiqua_softener.async_setup_entry"


def _entry(hass):
    e = MockConfigEntry(domain=DOMAIN, unique_id="dev1", data=DATA, title="Zmiekczacz")
    e.add_to_hass(hass)
    return e


async def test_user_flow(hass):
    with patch(LIST, AsyncMock(return_value=[DEVICE])), patch(SETUP, return_value=True):
        result = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": config_entries.SOURCE_USER}
        )
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], {"email": "a@b.c", "password": "pw"}
        )
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["result"].unique_id == "dev1"


async def test_reauth_recovers_silently_with_stored_password(hass):
    entry = _entry(hass)
    with patch(LIST, AsyncMock(return_value=[DEVICE])), patch(SETUP, return_value=True):
        result = await entry.start_reauth_flow(hass)
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "reauth_successful"
    assert entry.data["password"] == "old"


async def test_reauth_asks_user_and_saves_new_password(hass):
    entry = _entry(hass)
    with patch(LIST, AsyncMock(side_effect=IquaAuthError("x"))):
        result = await entry.start_reauth_flow(hass)
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "reauth_confirm"

    with patch(LIST, AsyncMock(side_effect=IquaAuthError("x"))):
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], {"email": "a@b.c", "password": "bad"}
        )
    assert result["errors"] == {"base": "invalid_auth"}

    with patch(LIST, AsyncMock(return_value=[DEVICE])), patch(SETUP, return_value=True):
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], {"email": "a@b.c", "password": "new"}
        )
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "reauth_successful"
    assert entry.data["password"] == "new"


async def test_reconfigure_rejects_other_account(hass):
    entry = _entry(hass)
    result = await entry.start_reconfigure_flow(hass)
    assert result["step_id"] == "reconfigure"
    with patch(LIST, AsyncMock(return_value=[{"id": "other"}])):
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], {"email": "x@y.z", "password": "pw"}
        )
    assert result["errors"] == {"base": "wrong_account"}

    with patch(LIST, AsyncMock(return_value=[DEVICE])), patch(SETUP, return_value=True):
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], {"email": "a@b.c", "password": "new"}
        )
    assert result["reason"] == "reconfigure_successful"
    assert entry.data["password"] == "new"
