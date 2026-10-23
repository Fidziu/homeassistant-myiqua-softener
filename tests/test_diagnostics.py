from unittest.mock import AsyncMock, patch

from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.myiqua_softener.const import DOMAIN
from custom_components.myiqua_softener.diagnostics import (
    async_get_config_entry_diagnostics,
)

API = "custom_components.myiqua_softener.api.IquaApiAsync"


async def test_diagnostics_redacts_credentials(hass):
    entry = MockConfigEntry(
        domain=DOMAIN, unique_id="dev1", title="Zmiekczacz",
        data={"email": "a@b.c", "password": "pw", "device_id": "dev1"},
    )
    entry.add_to_hass(hass)
    with patch(f"{API}.async_get_device", AsyncMock(return_value={"properties": {}})):
        assert await hass.config_entries.async_setup(entry.entry_id)
    with patch(f"{API}._request", AsyncMock(return_value={"settings": []})):
        diag = await async_get_config_entry_diagnostics(hass, entry)
    assert diag["entry"]["password"] == "**REDACTED**"
    assert diag["entry"]["email"] == "**REDACTED**"
    assert diag["settings"] == {"settings": []}
