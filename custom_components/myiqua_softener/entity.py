from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import CONF_NICKNAME, CONF_SERIAL, DOMAIN
from .coordinator import MyIquaSoftenerDataUpdateCoordinator


class MyIquaEntity(CoordinatorEntity[MyIquaSoftenerDataUpdateCoordinator]):
    """Base entity: shares the device + a property reader."""

    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: MyIquaSoftenerDataUpdateCoordinator,
        entry: ConfigEntry,
        key: str,
    ) -> None:
        super().__init__(coordinator)
        self._entry = entry
        self._key = key
        self._attr_unique_id = f"{entry.unique_id}_{key}"

    def _raw(self, name: str):
        """Return the property dict for `name`, or None."""
        data = self.coordinator.data or {}
        props = data.get("properties") or {}
        return props.get(name)

    def _value(self, name: str):
        prop = self._raw(name)
        return prop.get("value") if prop else None

    @property
    def device_info(self) -> DeviceInfo:
        serial = self._entry.data.get(CONF_SERIAL) or self._entry.unique_id
        return DeviceInfo(
            identifiers={(DOMAIN, serial)},
            name=self._entry.data.get(CONF_NICKNAME) or "Water Softener",
            manufacturer="EcoWater / Viessmann",
            model=self._value("model_description"),
            sw_version=self._value("base_software_version"),
            serial_number=serial,
        )
