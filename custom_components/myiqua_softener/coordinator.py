import logging
from datetime import datetime, timedelta

from aiohttp import ClientResponseError
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.util import dt as dt_util

from .api import IquaApiAsync, IquaAuthError
from .const import (
    AUTH_FAILURE_MIN_COUNT,
    AUTH_FAILURE_MIN_DURATION,
    DOMAIN,
    UPDATE_INTERVAL_MINUTES,
)

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
        # Streak of rejected logins, kept in hass.data so it survives the
        # coordinator being rebuilt on setup retries / reloads.
        self._auth_streak: dict = hass.data.setdefault(
            f"{DOMAIN}_auth_streak", {}
        ).setdefault(entry.entry_id, {"count": 0, "since": None})

    def _auth_rejected(self, err: Exception) -> Exception:
        """Decide whether a login rejection is a blip or a real auth problem.

        The iQua cloud has been seen to reject a correct password once
        (2026-10-21); escalating straight to ConfigEntryAuthFailed stops
        polling until the user acts. So only give up after several rejections
        in a row spread over a while; before that just retry next cycle.
        """
        now = dt_util.utcnow()
        streak = self._auth_streak
        streak["count"] += 1
        if streak["since"] is None:
            streak["since"] = now
        since: datetime = streak["since"]
        if (
            streak["count"] >= AUTH_FAILURE_MIN_COUNT
            and now - since >= AUTH_FAILURE_MIN_DURATION
        ):
            _LOGGER.error(
                "MyIqua: login rejected %d times in a row since %s, asking to re-authenticate",
                streak["count"],
                since.isoformat(),
            )
            return ConfigEntryAuthFailed(str(err))
        _LOGGER.warning(
            "MyIqua: login rejected (%s), attempt %d in a row; will retry",
            err,
            streak["count"],
        )
        return UpdateFailed(f"MyIqua login rejected, will retry: {err}")

    async def _async_update_data(self) -> dict:
        try:
            data = await self.api.async_get_device()
        except IquaAuthError as err:
            raise self._auth_rejected(err) from err
        except ClientResponseError as err:
            if err.status in (401, 403):
                raise self._auth_rejected(err) from err
            raise UpdateFailed(f"MyIqua API HTTP error {err.status}") from err
        except Exception as err:
            raise UpdateFailed(f"MyIqua communication error: {err}") from err
        self._auth_streak.update(count=0, since=None)
        return data
