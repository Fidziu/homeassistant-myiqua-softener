import logging

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


class MyIquaSoftenerConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    async def async_step_user(self, user_input=None):
        errors = {}

        if user_input is not None:
            session = async_get_clientsession(self.hass)
            api = IquaApiAsync(session, user_input[CONF_EMAIL], user_input[CONF_PASSWORD])
            try:
                devices = await api.async_list_devices()
            except IquaAuthError:
                errors["base"] = "invalid_auth"
            except Exception:  # noqa: BLE001
                _LOGGER.exception("MyIqua: unexpected error during setup")
                errors["base"] = "cannot_connect"
            else:
                if not devices:
                    errors["base"] = "no_devices"
                else:
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

        schema = vol.Schema(
            {
                vol.Required(CONF_EMAIL): str,
                vol.Required(CONF_PASSWORD): str,
            }
        )
        return self.async_show_form(step_id="user", data_schema=schema, errors=errors)
