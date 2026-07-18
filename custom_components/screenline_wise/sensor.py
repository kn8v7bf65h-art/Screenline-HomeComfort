"""Sensor platform for ScreenLine WISE."""

from __future__ import annotations

from homeassistant.components.sensor import SensorDeviceClass, SensorEntity
from homeassistant.const import PERCENTAGE
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import ScreenLineConfigEntry
from .entity import ScreenLineEntity


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ScreenLineConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator = entry.runtime_data.coordinator
    async_add_entities(
        ScreenLineBatterySensor(coordinator, blind["id"])
        for _, blind in coordinator.blinds()
    )


class ScreenLineBatterySensor(ScreenLineEntity, SensorEntity):
    """Battery sensor for one ScreenLine blind."""

    _attr_device_class = SensorDeviceClass.BATTERY
    _attr_native_unit_of_measurement = PERCENTAGE
    _attr_name = "Battery"

    def __init__(self, coordinator, blind_id: int) -> None:
        super().__init__(coordinator, blind_id)
        self._attr_unique_id = f"{coordinator.client.host}_{blind_id}_battery"

    @property
    def native_value(self) -> int | None:
        value = (self.blind.get("status") or {}).get("batteryReceived")
        return int(value) if value is not None else None
