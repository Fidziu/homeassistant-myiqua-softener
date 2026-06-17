"""Binary sensors (alerts) for the MyIqua water softener.

The softener exposes its alert flags as 0/1 properties. `flow_monitor_alert`
is the device's built-in continuous-flow / leak alarm.
"""
from __future__ import annotations

from dataclasses import dataclass

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .entity import MyIquaEntity


@dataclass(frozen=True)
class IquaBinary:
    key: str
    name: str
    device_class: BinarySensorDeviceClass | None = None
    icon: str | None = None
    category: EntityCategory | None = None
    invert: bool = False  # if True, is_on = (value == 0)


ALERTS: tuple[IquaBinary, ...] = (
    IquaBinary("flow_monitor_alert", "Leak / continuous flow alert",
               BinarySensorDeviceClass.PROBLEM, icon="mdi:water-alert"),
    IquaBinary("low_salt_alert", "Low salt alert",
               BinarySensorDeviceClass.PROBLEM, icon="mdi:cup-off"),
    IquaBinary("excessive_water_use_alert", "Excessive water use alert",
               BinarySensorDeviceClass.PROBLEM, icon="mdi:water-alert"),
    IquaBinary("water_shutoff_valve_alert", "Shutoff valve alert",
               BinarySensorDeviceClass.PROBLEM, icon="mdi:valve"),
    IquaBinary("resin_alert", "Resin alert",
               BinarySensorDeviceClass.PROBLEM, icon="mdi:dots-hexagon"),
    IquaBinary("error_code_alert", "Error alert",
               BinarySensorDeviceClass.PROBLEM, icon="mdi:alert-circle"),
    IquaBinary("_internal_is_online", "Online",
               BinarySensorDeviceClass.CONNECTIVITY,
               category=EntityCategory.DIAGNOSTIC),
)


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    coordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(MyIquaBinarySensor(coordinator, entry, spec) for spec in ALERTS)


class MyIquaBinarySensor(MyIquaEntity, BinarySensorEntity):
    def __init__(self, coordinator, entry, spec: IquaBinary) -> None:
        super().__init__(coordinator, entry, spec.key)
        self._spec = spec
        self._attr_name = spec.name
        self._attr_device_class = spec.device_class
        self._attr_icon = spec.icon
        self._attr_entity_category = spec.category

    @property
    def is_on(self) -> bool | None:
        value = self._value(self._spec.key)
        if value is None:
            return None
        if isinstance(value, bool):
            state = value
        else:
            try:
                state = float(value) != 0
            except (TypeError, ValueError):
                return None
        return (not state) if self._spec.invert else state
