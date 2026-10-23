"""Diagnostics: device data plus the cloud's settings list (no credentials)."""
from __future__ import annotations

from homeassistant.components.diagnostics import async_redact_data
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import CONF_EMAIL, CONF_PASSWORD, DOMAIN

TO_REDACT = {CONF_EMAIL, CONF_PASSWORD, "email", "phone", "address", "user", "users"}


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry: ConfigEntry
) -> dict:
    coordinator = hass.data[DOMAIN][entry.entry_id]
    api = coordinator.api
    extra: dict = {}
    for key, path in (
        ("settings", f"/devices/{api.device_id}/settings"),
        ("enriched_data", f"/devices/{api.device_id}/enriched-data"),
    ):
        try:
            extra[key] = await api._request(path)
        except Exception as err:  # noqa: BLE001
            extra[key] = {"error": repr(err)}
    return async_redact_data(
        {
            "entry": dict(entry.data),
            "device": coordinator.data,
            **extra,
        },
        TO_REDACT,
    )
