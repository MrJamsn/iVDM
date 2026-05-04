from __future__ import annotations

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, OBIS_META
from .coordinator import IstaVdmCoordinator

DEVICE_CLASS_MAP = {
    "energy": SensorDeviceClass.ENERGY,
    "water": SensorDeviceClass.WATER,
    "gas": SensorDeviceClass.GAS,
}

UNIT_MAP = {
    "kWh": "kWh",
    "m3": "m\u00b3",
}


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator: IstaVdmCoordinator = hass.data[DOMAIN][entry.entry_id]

    entities = []
    for obis_code, (name, unit, device_class) in OBIS_META.items():
        entities.append(
            IstaVdmSensor(coordinator, obis_code, name, unit, device_class, "current")
        )
        entities.append(
            IstaVdmSensor(coordinator, obis_code, name, unit, device_class, "previous")
        )

    async_add_entities(entities)


class IstaVdmSensor(CoordinatorEntity, SensorEntity):
    """Sensor fuer einen ista VDM Verbrauchswert."""

    _attr_state_class = SensorStateClass.TOTAL

    def __init__(
        self,
        coordinator: IstaVdmCoordinator,
        obis_code: str,
        name: str,
        unit: str,
        device_class: str,
        period: str,
    ) -> None:
        super().__init__(coordinator)
        self._obis_code = obis_code
        self._period = period
        period_label = "Aktuell" if period == "current" else "Vormonat"
        self._attr_name = f"ista VDM {name} {period_label}"
        self._attr_unique_id = (
            f"ivdm_{coordinator.flat_id}_{obis_code}_{period}"
        )
        self._attr_native_unit_of_measurement = UNIT_MAP.get(unit, unit)
        self._attr_device_class = DEVICE_CLASS_MAP.get(device_class)
        self._attr_device_info = {
            "identifiers": {(DOMAIN, coordinator.flat_id)},
            "name": "ista VDM",
            "manufacturer": "ista",
            "model": "Verbrauchsdatenmonitoring",
        }

    @property
    def native_value(self):
        if not self.coordinator.data:
            return None
        return self.coordinator.data.get(self._period, {}).get(self._obis_code)

    @property
    def extra_state_attributes(self):
        if not self.coordinator.data:
            return {}
        return {"monat": self.coordinator.data.get("month", "")}
