"""Async client for the MyIqua cloud API (api.myiquaapp.com).

Used by Viessmann / EcoWater "iQua" smart water softeners (EU backend).
Auth is a custom JWT: POST /auth/login returns an access_token (~24h) that we
send as a Bearer token. On a 401 we simply log in again.
"""
from __future__ import annotations

import logging

import aiohttp
import async_timeout

_LOGGER = logging.getLogger(__name__)

BASE_URL = "https://api.myiquaapp.com/v1"
WS_BASE = "wss://api.myiquaapp.com"
USER_AGENT = "home-assistant-myiqua/0.2.1"
TIMEOUT = 15


class IquaAuthError(Exception):
    """Raised when login is rejected (bad e-mail/password)."""


class IquaApiAsync:
    def __init__(self, session, email: str, passw: str, dev_id: str | None = None):
        self._session = session
        self._email = email
        self._password = passw
        self._device_id = dev_id
        self._token: str | None = None

    @property
    def device_id(self) -> str | None:
        return self._device_id

    async def _login(self) -> None:
        async with async_timeout.timeout(TIMEOUT):
            async with self._session.post(
                f"{BASE_URL}/auth/login",
                json={"email": self._email, "password": self._password},
            ) as resp:
                if resp.status in (400, 401, 403):
                    raise IquaAuthError(f"login rejected ({resp.status})")
                resp.raise_for_status()
                data = await resp.json()
                self._token = data["access_token"]
                _LOGGER.debug("MyIqua login successful")

    async def _get(self, path: str) -> dict:
        headers = {
            "Authorization": f"Bearer {self._token}",
            "User-Agent": USER_AGENT,
        }
        async with async_timeout.timeout(TIMEOUT):
            async with self._session.get(BASE_URL + path, headers=headers) as resp:
                resp.raise_for_status()
                return await resp.json()

    async def _request(self, path: str) -> dict:
        """GET with one transparent re-login on 401."""
        for attempt in range(2):
            if self._token is None:
                await self._login()
            try:
                return await self._get(path)
            except aiohttp.ClientResponseError as err:
                if err.status == 401 and attempt == 0:
                    self._token = None
                    continue
                raise

    async def async_list_devices(self) -> list[dict]:
        """Return all softeners on the account (used for discovery)."""
        data = await self._request("/devices")
        return data.get("data", [])

    async def async_get_device(self) -> dict:
        """Return the `device` object (incl. its `properties` map)."""
        data = await self._request(f"/devices/{self._device_id}/detail-or-summary")
        return data["device"]

    async def async_get_live_ws_url(self) -> str:
        """Return the full wss:// URL for the live property stream."""
        data = await self._request(f"/devices/{self._device_id}/live")
        return WS_BASE + data["websocket_uri"]

    async def async_command(self, function: str, action: str) -> dict:
        """Send a device command (e.g. function='regenerate', action='regenerate')."""
        for attempt in range(2):
            if self._token is None:
                await self._login()
            headers = {
                "Authorization": f"Bearer {self._token}",
                "User-Agent": USER_AGENT,
            }
            try:
                async with async_timeout.timeout(TIMEOUT):
                    async with self._session.put(
                        f"{BASE_URL}/devices/{self._device_id}/command",
                        json={"function": function, "action": action},
                        headers=headers,
                    ) as resp:
                        resp.raise_for_status()
                        return await resp.json()
            except aiohttp.ClientResponseError as err:
                if err.status == 401 and attempt == 0:
                    self._token = None
                    continue
                raise
