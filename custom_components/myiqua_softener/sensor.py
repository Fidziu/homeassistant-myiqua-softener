"""Sensors for the MyIqua water softener."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    PERCENTAGE,
    SIGNAL_STRENGTH_DECIBELS_MILLIWATT,
    EntityCategory,
    UnitOfTime,
    UnitOfVolume,
    UnitOfVolumeFlowRate,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.util import dt as dt_util

from .const import DOMAIN
from .entity import MyIquaEntity


@dataclass(frozen=True)
class IquaSensor:
    key: str
    name: str
    converted: bool = False
    factor: float | None = None
    precision: int | None = None
    unit: str | None = None
    device_class: SensorDeviceClass | None = None
    state_class: SensorStateClass | None = None
    icon: str | None = None
    category: EntityCategory | None = None


SENSORS: tuple[IquaSensor, ...] = (
    IquaSensor("gallons_used_today", "Water used today", converted=True, precision=0,
               unit=UnitOfVolume.LITERS, device_class=SensorDeviceClass.WATER,
               state_class=SensorStateClass.TOTAL_INCREASING, icon="mdi:water"),
    IquaSensor("avg_daily_use_gals", "Average daily water use", converted=True, precision=0,
               unit=UnitOfVolume.LITERS, state_class=SensorStateClass.MEASUREMENT,
               icon="mdi:water-outline"),
    IquaSensor("treated_water_avail_gals", "Treated water available", converted=True, precision=0,
               unit=UnitOfVolume.LITERS, state_class=SensorStateClass.MEASUREMENT,
               icon="mdi:water-check"),
    IquaSensor("total_outlet_water_gals", "Total water used", converted=True, precision=0,
               unit=UnitOfVolume.LITERS, device_class=SensorDeviceClass.WATER,
               state_class=SensorStateClass.TOTAL_INCREASING, icon="mdi:counter"),
    IquaSensor("current_water_flow_gpm", "Current water flow", converted=True, precision=1,
               unit=UnitOfVolumeFlowRate.LITERS_PER_MINUTE,
               device_class=SensorDeviceClass.VOLUME_FLOW_RATE,
               state_class=SensorStateClass.MEASUREMENT, icon="mdi:water-pump"),
    IquaSensor("salt_level_tenths", "Salt level", factor=0.1, precision=0,
               unit=PERCENTAGE, state_class=SensorStateClass.MEASUREMENT, icon="mdi:cup"),
    IquaSensor("out_of_salt_estimate_days", "Out of salt in", unit=UnitOfTime.DAYS,
               icon="mdi:calendar-alert"),
    IquaSensor("days_since_last_regen", "Days since last regeneration", unit=UnitOfTime.DAYS,
               icon="mdi:calendar-refresh"),
    IquaSensor("total_regens", "Total regenerations",
               state_class=SensorStateClass.TOTAL_INCREASING, icon="mdi:refresh"),
    IquaSensor("hardness_grains", "Water hardness", unit="gpg", icon="mdi:water-percent"),
    IquaSensor("days_in_operation", "Days in operation", unit=UnitOfTime.DAYS,
               icon="mdi:clock-outline", category=EntityCategory.DIAGNOSTIC),
    IquaSensor("rf_signal_strength_dbm", "WiFi signal",
               unit=SIGNAL_STRENGTH_DECIBELS_MILLIWATT,
               device_class=SensorDeviceClass.SIGNAL_STRENGTH,
               state_class=SensorStateClass.MEASUREMENT,
               category=EntityCategory.DIAGNOSTIC),
)


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    coordinator = hass.data[DOMAIN][entry.entry_id]
    entities: list[SensorEntity] = [
        MyIquaSensor(coordinator, entry, spec) for spec in SENSORS
    ]
    entities.append(
        MyIquaDateSensor(coordinator, entry, "last_regeneration",
                         "Last regeneration", "days_since_last_regen", -1)
    )
    entities.append(
        MyIquaDateSensor(coordinator, entry, "out_of_salt_date",
                         "Out of salt date", "out_of_salt_estimate_days", 1)
    )
    async_add_entities(entities)


class MyIquaSensor(MyIquaEntity, SensorEntity):
    def __init__(self, coordinator, entry, spec: IquaSensor) -> None:
        super().__init__(coordinator, entry, spec.key)
        self._spec = spec
        self._attr_name = spec.name
        self._attr_native_unit_of_measurement = spec.unit
        self._attr_device_class = spec.device_class
        self._attr_state_class = spec.state_class
        self._attr_icon = spec.icon
        self._attr_entity_category = spec.category

    @property
    def native_value(self):
        prop = self._raw(self._spec.key)
        if not prop:
            return None
        raw = prop.get("converted_value") if self._spec.converted else None
        if raw is None:
            raw = prop.get("value")
        if raw is None:
            return None
        # No conversion requested: keep the API's native int/float/str.
        if not self._spec.converted and self._spec.factor is None and self._spec.precision is None:
            return raw
        try:
            raw = float(raw)
        except (TypeError, ValueError):
            return raw
        if self._spec.factor is not None:
            raw *= self._spec.factor
        if self._spec.precision is not None:
            raw = round(raw, self._spec.precision)
            if self._spec.precision == 0:
                raw = int(raw)
        return raw


class MyIquaDateSensor(MyIquaEntity, SensorEntity):
    """Derives a date from a 'number of days' property."""

    _attr_device_class = SensorDeviceClass.TIMESTAMP

    def __init__(self, coordinator, entry, key, name, source_key, sign) -> None:
        super().__init__(coordinator, entry, key)
        self._attr_name = name
        self._source_key = source_key
        self._sign = sign

    @property
    def native_value(self):
        days = self._value(self._source_key)
        if days is None:
            return None
        try:
            days = int(days)
        except (TypeError, ValueError):
            return None
        midnight = dt_util.now().replace(hour=0, minute=0, second=0, microsecond=0)
        return midnight + timedelta(days=self._sign * days)
