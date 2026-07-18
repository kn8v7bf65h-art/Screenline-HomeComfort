"""Sensor platform for ScreenLine HomeComfort."""

from __future__ import annotations

from typing import Any

from homeassistant.components.sensor import SensorDeviceClass, SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import PERCENTAGE
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import ScreenLineCoordinator


def _blind_list(room: dict[str, Any]) -> list[dict[str, Any]]:
    for key in ("blinds", "blindList", "blindItems"):
        value = room.get(key)
        if isinstance(value, list):
            return value
    return []


def _status(blind: dict[str, Any]) -> dict[str, Any]:
    value = blind.get("status")
    return value if isinstance(value, dict) else blind


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator: ScreenLineCoordinator = hass.data[DOMAIN][entry.entry_id]
    entities: list[ScreenLineBatterySensor] = []
    for room in coordinator.data:
        room_id = room.get("id")
        for blind in _blind_list(room):
            entities.append(ScreenLineBatterySensor(coordinator, room_id, blind))
    async_add_entities(entities)


class ScreenLineBatterySensor(
    CoordinatorEntity[ScreenLineCoordinator], SensorEntity
):
    """Battery sensor for one ScreenLine blind."""

    _attr_device_class = SensorDeviceClass.BATTERY
    _attr_native_unit_of_measurement = PERCENTAGE
    _attr_has_entity_name = True
    _attr_name = "Battery"

    def __init__(
        self,
        coordinator: ScreenLineCoordinator,
        room_id: int | str,
        blind: dict[str, Any],
    ) -> None:
        super().__init__(coordinator)
        self._room_id = room_id
        self._blind_id = int(blind["id"])
        self._blind = blind
        self._attr_unique_id = f"{coordinator.entry.unique_id}_{self._blind_id}_battery"

    def _refresh_blind_reference(self) -> None:
        for room in self.coordinator.data:
            if str(room.get("id")) != str(self._room_id):
                continue
            for blind in _blind_list(room):
                if int(blind.get("id")) == self._blind_id:
                    self._blind = blind
                    return

    @property
    def native_value(self) -> int | None:
        self._refresh_blind_reference()
        status = _status(self._blind)
        value = status.get("batteryReceived", status.get("battery"))
        if value is None:
            return None
        return max(0, min(100, round(float(value))))

    @property
    def device_info(self):
        model = self._blind.get("model") or {}
        model_name = model.get("name") if isinstance(model, dict) else None
        name = self._blind.get("realName") or self._blind.get("name") or f"Blind {self._blind_id}"
        if isinstance(name, str) and name.startswith("@"):
            name = name[1:].replace("_", " ").title()
        return {
            "identifiers": {(DOMAIN, f"{self.coordinator.entry.unique_id}_{self._blind_id}")},
            "name": str(name),
            "manufacturer": "Pellini ScreenLine",
            "model": model_name or "WISE blind",
            "via_device": (DOMAIN, self.coordinator.entry.unique_id or self.coordinator.entry.entry_id),
        }
