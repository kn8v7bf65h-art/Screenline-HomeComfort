"""Base entity for ScreenLine WISE."""

from __future__ import annotations

from typing import Any

from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import ScreenLineCoordinator

_NAME_MAP = {
    "@HOME": "Home",
    "@LIVING_ROOM": "Living room",
    "@BLIND_RIGHT": "Blind right",
    "@BLIND_LEFT": "Blind left",
}


def display_name(value: str | None, fallback: str) -> str:
    """Turn app translation keys into readable names."""
    if not value:
        return fallback
    if value in _NAME_MAP:
        return _NAME_MAP[value]
    if value.startswith("@"):
        return value[1:].replace("_", " ").title()
    return value


class ScreenLineEntity(CoordinatorEntity[ScreenLineCoordinator]):
    """Base entity representing one ScreenLine blind."""

    _attr_has_entity_name = True

    def __init__(self, coordinator: ScreenLineCoordinator, blind_id: int) -> None:
        super().__init__(coordinator)
        self.blind_id = blind_id

    @property
    def blind_data(self) -> tuple[dict[str, Any], dict[str, Any]] | None:
        return self.coordinator.get_blind(self.blind_id)

    @property
    def blind(self) -> dict[str, Any]:
        data = self.blind_data
        return data[1] if data else {}

    @property
    def room(self) -> dict[str, Any]:
        data = self.blind_data
        return data[0] if data else {}

    @property
    def device_info(self) -> DeviceInfo:
        model = self.blind.get("model") or {}
        return DeviceInfo(
            identifiers={(DOMAIN, str(self.blind_id))},
            name=display_name(self.blind.get("name"), f"Blind {self.blind_id}"),
            manufacturer="Pellini ScreenLine",
            model=model.get("name", "WISE blind"),
            via_device=(DOMAIN, f"hub_{self.coordinator.client.host}"),
        )
