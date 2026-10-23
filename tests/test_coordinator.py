"""A single rejected login must not put the entry into reauth."""
from datetime import timedelta
from unittest.mock import AsyncMock, patch

import pytest
from homeassistant.config_entries import SOURCE_REAUTH, ConfigEntryState
from homeassistant.util import dt as dt_util
from pytest_homeassistant_custom_component.common import (
    MockConfigEntry,
    async_fire_time_changed,
)

from custom_components.myiqua_softener.api import IquaAuthError
from custom_components.myiqua_softener.const import DOMAIN

DEVICE = {"id": "dev1", "properties": {}}
DATA = {"email": "a@b.c", "password": "pw", "device_id": "dev1"}
API = "custom_components.myiqua_softener.api.IquaApiAsync"


@pytest.fixture
def entry(hass):
    e = MockConfigEntry(domain=DOMAIN, unique_id="dev1", data=DATA, title="Zmiekczacz")
    e.add_to_hass(hass)
    return e


async def _tick(hass, minutes=5):
    async_fire_time_changed(hass, dt_util.utcnow() + timedelta(minutes=minutes))
    await hass.async_block_till_done()


def _reauth_flows(hass):
    return [
        f for f in hass.config_entries.flow.async_progress()
        if f["context"]["source"] == SOURCE_REAUTH
    ]


async def test_single_rejection_is_retried(hass, entry, freezer):
    get = AsyncMock(return_value=DEVICE)
    with patch(f"{API}.async_get_device", get), patch(
        f"{API}.async_list_devices", AsyncMock(return_value=[DEVICE])
    ):
        assert await hass.config_entries.async_setup(entry.entry_id)
        coordinator = hass.data[DOMAIN][entry.entry_id]

        get.side_effect = IquaAuthError("login rejected (401)")
        freezer.tick(timedelta(minutes=5))
        await _tick(hass, 0)
        assert not coordinator.last_update_success
        assert entry.state is ConfigEntryState.LOADED
        assert not _reauth_flows(hass)

        # Next cycle the cloud accepts the login again -> back to normal.
        get.side_effect = None
        freezer.tick(timedelta(minutes=5))
        await _tick(hass, 0)
        assert coordinator.last_update_success
        assert coordinator._auth_streak == {"count": 0, "since": None}


async def test_persistent_rejection_escalates_to_reauth(hass, entry, freezer):
    get = AsyncMock(return_value=DEVICE)
    # Stored credentials keep failing in the reauth flow too.
    with patch(f"{API}.async_get_device", get), patch(
        f"{API}.async_list_devices",
        AsyncMock(side_effect=IquaAuthError("login rejected (401)")),
    ):
        assert await hass.config_entries.async_setup(entry.entry_id)
        get.side_effect = IquaAuthError("login rejected (401)")
        # 3 rejections within 10 min: not yet.
        for _ in range(3):
            freezer.tick(timedelta(minutes=5))
            await _tick(hass, 0)
        assert not _reauth_flows(hass)
        # Keep failing past the 30 min window -> reauth.
        for _ in range(5):
            freezer.tick(timedelta(minutes=5))
            await _tick(hass, 0)
        flows = _reauth_flows(hass)
        assert len(flows) == 1
        assert flows[0]["step_id"] == "reauth_confirm"
