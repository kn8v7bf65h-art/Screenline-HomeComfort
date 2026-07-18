"""Cover platform for ScreenLine HomeComfort."""

from __future__ import annotations

from typing import Any

from homeassistant.components.cover import CoverEntity, CoverEntityFeature
from homeassistant.config_entries import ConfigEntry
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


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator: ScreenLineCoordinator = hass.data[DOMAIN][entry.entry_id]
    entities: list[ScreenLineCover] = []
    for room in coordinator.data:
        room_id = room.get("id")
        room_name = room.get("realName") or room.get("name") or f"Room {room_id}"
        for blind in _blind_list(room):
            entities.append(ScreenLineCover(coordinator, room_id, room_name, blind))
    async_add_entities(entities)


class ScreenLineCover(CoordinatorEntity[ScreenLineCoordinator], CoverEntity):
    """Representation of one ScreenLine blind."""

    _attr_supported_features = (
        CoverEntityFeature.OPEN
        | CoverEntityFeature.CLOSE
        | CoverEntityFeature.STOP
        | CoverEntityFeature.SET_POSITION
        | CoverEntityFeature.OPEN_TILT
        | CoverEntityFeature.CLOSE_TILT
    )

    def __init__(
        self,
        coordinator: ScreenLineCoordinator,
        room_id: int | str,
        room_name: str,
        blind: dict[str, Any],
    ) -> None:
        super().__init__(coordinator)
        self._room_id = room_id
        self._room_name = room_name
        self._blind_id = int(blind["id"])
        self._blind = blind
        self._attr_unique_id = f"{coordinator.entry.unique_id}_{self._blind_id}"
        blind_name = blind.get("realName") or blind.get("name") or f"Blind {self._blind_id}"
        self._attr_name = f"{room_name} {blind_name}"

    @property
    def device_info(self):
        return {
            "identifiers": {(DOMAIN, self.coordinator.entry.unique_id or self.coordinator.entry.entry_id)},
            "name": self.coordinator.entry.title,
            "manufacturer": "Pellini",
            "model": "ScreenLine WISE Hub",
        }

    def _refresh_blind_reference(self) -> None:
        for room in self.coordinator.data:
            if str(room.get("id")) != str(self._room_id):
                continue
            for blind in _blind_list(room):
                if int(blind.get("id")) == self._blind_id:
                    self._blind = blind
                    return

    @property
    def current_cover_position(self) -> int | None:
        self._refresh_blind_reference()
        coverage = self._blind.get("coverageReceived", self._blind.get("coverage"))
        if coverage is None:
            return None
        # WISE Hub coverage is percentage covered; Home Assistant position is percentage open.
        return max(0, min(100, 100 - int(coverage)))

    @property
    def current_cover_tilt_position(self) -> int | None:
        self._refresh_blind_reference()
        inclination = self._blind.get(
            "inclinationReceived", self._blind.get("inclination")
        )
        if inclination is None:
            return None
        return max(0, min(100, round(int(inclination) / 90 * 100)))

    @property
    def is_closed(self) -> bool | None:
        position = self.current_cover_position
        return None if position is None else position == 0

    async def async_open_cover(self, **kwargs: Any) -> None:
        await self.coordinator.hub.move(self._room_id, self._blind_id, "UP")
        await self.coordinator.async_request_refresh()

    async def async_close_cover(self, **kwargs: Any) -> None:
        await self.coordinator.hub.move(self._room_id, self._blind_id, "DOWN")
        await self.coordinator.async_request_refresh()

    async def async_stop_cover(self, **kwargs: Any) -> None:
        await self.coordinator.hub.move(self._room_id, self._blind_id, "STOP")
        await self.coordinator.async_request_refresh()

    async def async_set_cover_position(self, **kwargs: Any) -> None:
        position = int(kwargs["position"])
        tilt = self.current_cover_tilt_position
        inclination = 45 if tilt is None else round(tilt / 100 * 90)
        await self.coordinator.hub.set_position(
            self._room_id,
            self._blind_id,
            100 - position,
            inclination,
        )
        await self.coordinator.async_request_refresh()

    async def async_open_cover_tilt(self, **kwargs: Any) -> None:
        await self.coordinator.hub.tilt(self._room_id, self._blind_id, "INCREMENT")
        await self.coordinator.async_request_refresh()

    async def async_close_cover_tilt(self, **kwargs: Any) -> None:
        await self.coordinator.hub.tilt(self._room_id, self._blind_id, "DECREMENT")
        await self.coordinator.async_request_refresh()
