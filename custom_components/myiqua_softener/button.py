"""Button to trigger an immediate regeneration (recharge)."""
from __future__ import annotations

import logging

from homeassistant.components.button import ButtonEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .entity import MyIquaEntity

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    coordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([MyIquaRegenerateButton(coordinator, entry)])


class MyIquaRegenerateButton(MyIquaEntity, ButtonEntity):
    _attr_icon = "mdi:refresh"

    def __init__(self, coordinator, entry) -> None:
        super().__init__(coordinator, entry, "regenerate")
        self._attr_name = "Start regeneration"

    async def async_press(self) -> None:
        _LOGGER.info("MyIqua: requesting immediate regeneration")
        await self.coordinator.api.async_command("regenerate", "regenerate")
        await self.coordinator.async_request_refresh()
