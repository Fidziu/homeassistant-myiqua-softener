"""On-demand 'Live view' switch.

When turned on, opens the MyIqua WebSocket so the device streams properties in
real time (flow, usage, ...). The incoming frames patch the coordinator data so
the existing sensors update live. Auto-closes after LIVE_SECONDS to avoid
holding a 24/7 connection.
"""
from __future__ import annotations

import asyncio
import json
import logging

from aiohttp import WSMsgType
from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.event import async_call_later

from .const import DOMAIN, LIVE_SECONDS
from .entity import MyIquaEntity

_LOGGER = logging.getLogger(__name__)

# Properties we forward from the live stream into our sensors.
LIVE_PROPS = {
    "current_water_flow_gpm",
    "gallons_used_today",
    "total_outlet_water_gals",
    "treated_water_avail_gals",
    "salt_level_tenths",
    "rf_signal_strength_dbm",
}


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    coordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([MyIquaLiveSwitch(coordinator, entry)])


class MyIquaLiveSwitch(MyIquaEntity, SwitchEntity):
    _attr_icon = "mdi:pulse"

    def __init__(self, coordinator, entry) -> None:
        super().__init__(coordinator, entry, "live_view")
        self._attr_name = "Podgląd live"
        self._attr_is_on = False
        self._task: asyncio.Task | None = None
        self._cancel_timer = None

    async def async_turn_on(self, **kwargs) -> None:
        if self._task and not self._task.done():
            return
        self._attr_is_on = True
        self.async_write_ha_state()
        self._task = self.hass.async_create_task(self._run())
        self._cancel_timer = async_call_later(self.hass, LIVE_SECONDS, self._auto_off)

    @callback
    def _auto_off(self, _now) -> None:
        self.hass.async_create_task(self.async_turn_off())

    async def async_turn_off(self, **kwargs) -> None:
        self._attr_is_on = False
        if self._cancel_timer is not None:
            self._cancel_timer()
            self._cancel_timer = None
        if self._task is not None:
            self._task.cancel()
            self._task = None
        self.async_write_ha_state()

    async def async_will_remove_from_hass(self) -> None:
        await self.async_turn_off()

    async def _run(self) -> None:
        session = async_get_clientsession(self.hass)
        try:
            url = await self.coordinator.api.async_get_live_ws_url()
            async with session.ws_connect(url, heartbeat=30) as ws:
                _LOGGER.debug("MyIqua live stream opened")
                async for msg in ws:
                    if msg.type != WSMsgType.TEXT:
                        continue
                    try:
                        frame = json.loads(msg.data)
                    except ValueError:
                        continue
                    self._apply(frame)
        except asyncio.CancelledError:
            raise
        except Exception as err:  # noqa: BLE001
            _LOGGER.warning("MyIqua live stream ended: %s", err)
        finally:
            if self._attr_is_on:
                self._attr_is_on = False
                self.async_write_ha_state()

    @callback
    def _apply(self, frame: dict) -> None:
        if frame.get("type") != "property":
            return
        name = frame.get("name")
        if name not in LIVE_PROPS or not self.coordinator.data:
            return
        props = self.coordinator.data.setdefault("properties", {})
        prop = props.setdefault(name, {"name": name})
        prop["value"] = frame.get("value")
        converted = frame.get("converted_property")
        if converted and converted.get("value") is not None:
            prop["converted_value"] = converted["value"]
        if frame.get("timestamp"):
            prop["updated_at"] = frame["timestamp"]
        self.coordinator.async_update_listeners()
