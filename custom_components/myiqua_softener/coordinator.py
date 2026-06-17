import logging
from datetime import timedelta

from aiohttp import ClientResponseError
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import IquaApiAsync, IquaAuthError
from .const import UPDATE_INTERVAL_MINUTES

_LOGGER = logging.getLogger(__name__)


class MyIquaSoftenerDataUpdateCoordinator(DataUpdateCoordinator):
    def __init__(self, hass: HomeAssistant, entry: ConfigEntry, api: IquaApiAsync):
        self.api = api
        super().__init__(
            hass,
            _LOGGER,
            name="MyIqua Softener",
            config_entry=entry,
            update_interval=timedelta(minutes=UPDATE_INTERVAL_MINUTES),
        )

    async def _async_update_data(self) -> dict:
        try:
            return await self.api.async_get_device()
        except IquaAuthError as err:
            raise ConfigEntryAuthFailed(str(err)) from err
        except ClientResponseError as err:
            if err.status in (401, 403):
                raise ConfigEntryAuthFailed from err
            raise UpdateFailed(f"MyIqua API HTTP error {err.status}") from err
        except Exception as err:
            raise UpdateFailed(f"MyIqua communication error: {err}") from err
