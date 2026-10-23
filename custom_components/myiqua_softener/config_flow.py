import logging
from collections.abc import Mapping
from typing import Any

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import IquaApiAsync, IquaAuthError
from .const import (
    CONF_DEVICE_ID,
    CONF_EMAIL,
    CONF_NICKNAME,
    CONF_PASSWORD,
    CONF_SERIAL,
    DOMAIN,
)

_LOGGER = logging.getLogger(__name__)

CREDENTIALS_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_EMAIL): str,
        vol.Required(CONF_PASSWORD): str,
    }
)


class MyIquaSoftenerConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    async def _async_fetch_devices(
        self, email: str, password: str, errors: dict[str, str]
    ) -> list[dict] | None:
        """Log in and list devices; on failure fill `errors` and return None."""
        session = async_get_clientsession(self.hass)
        api = IquaApiAsync(session, email, password)
        try:
            devices = await api.async_list_devices()
        except IquaAuthError:
            errors["base"] = "invalid_auth"
        except Exception:  # noqa: BLE001
            _LOGGER.exception("MyIqua: unexpected error while signing in")
            errors["base"] = "cannot_connect"
        else:
            if devices:
                return devices
            errors["base"] = "no_devices"
        return None

    async def async_step_user(self, user_input=None):
        errors = {}

        if user_input is not None:
            devices = await self._async_fetch_devices(
                user_input[CONF_EMAIL], user_input[CONF_PASSWORD], errors
            )
            if devices:
                device = devices[0]
                await self.async_set_unique_id(device["id"])
                self._abort_if_unique_id_configured()
                return self.async_create_entry(
                    title=device.get("nickname")
                    or device.get("serial_number")
                    or "MyIqua Softener",
                    data={
                        CONF_EMAIL: user_input[CONF_EMAIL],
                        CONF_PASSWORD: user_input[CONF_PASSWORD],
                        CONF_DEVICE_ID: device["id"],
                        CONF_SERIAL: device.get("serial_number"),
                        CONF_NICKNAME: device.get("nickname"),
                    },
                )

        return self.async_show_form(
            step_id="user", data_schema=CREDENTIALS_SCHEMA, errors=errors
        )

    async def _async_update_credentials(self, entry, step_id: str, user_input):
        """Shared body of reauth_confirm / reconfigure: verify, save, reload."""
        errors: dict[str, str] = {}

        if user_input is not None:
            devices = await self._async_fetch_devices(
                user_input[CONF_EMAIL], user_input[CONF_PASSWORD], errors
            )
            if devices:
                if not any(d.get("id") == entry.unique_id for d in devices):
                    errors["base"] = "wrong_account"
                else:
                    return self.async_update_reload_and_abort(
                        entry,
                        data_updates={
                            CONF_EMAIL: user_input[CONF_EMAIL],
                            CONF_PASSWORD: user_input[CONF_PASSWORD],
                        },
                    )

        return self.async_show_form(
            step_id=step_id,
            data_schema=self.add_suggested_values_to_schema(
                CREDENTIALS_SCHEMA, {CONF_EMAIL: entry.data.get(CONF_EMAIL)}
            ),
            errors=errors,
            description_placeholders={"name": entry.title},
        )

    async def async_step_reauth(self, entry_data: Mapping[str, Any]):
        """Started by HA after repeated login rejections.

        The iQua cloud occasionally rejects a correct password for a while, so
        first retry the stored credentials: if they work again, just reload the
        entry and finish without bothering the user.
        """
        entry = self._get_reauth_entry()
        errors: dict[str, str] = {}
        devices = await self._async_fetch_devices(
            entry_data[CONF_EMAIL], entry_data[CONF_PASSWORD], errors
        )
        if devices and any(d.get("id") == entry.unique_id for d in devices):
            _LOGGER.info("MyIqua: stored credentials work again, reloading entry")
            return self.async_update_reload_and_abort(entry)
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(self, user_input=None):
        return await self._async_update_credentials(
            self._get_reauth_entry(), "reauth_confirm", user_input
        )

    async def async_step_reconfigure(self, user_input=None):
        return await self._async_update_credentials(
            self._get_reconfigure_entry(), "reconfigure", user_input
        )
