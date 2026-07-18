"""Cover platform for ScreenLine HomeComfort."""

from __future__ import annotations

import asyncio
from typing import Any

from homeassistant.components.cover import (
    ATTR_POSITION,
    ATTR_TILT_POSITION,
    CoverDeviceClass,
    CoverEntity,
    CoverEntityFeature,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import ScreenLineCoordinator

TILT_MIN = -75
TILT_MAX = 75


def _blind_list(room: dict[str, Any]) -> list[dict[str, Any]]:
    for key in ("blinds", "blindList", "blindItems"):
        value = room.get(key)
        if isinstance(value, list):
            return value
    return []


def _status(blind: dict[str, Any]) -> dict[str, Any]:
    """Return the nested physical status, with top-level fallback."""
    value = blind.get("status")
    return value if isinstance(value, dict) else blind


def _display_name(value: Any, fallback: str) -> str:
    if not value:
        return fallback
    text = str(value)
    if text.startswith("@"):
        return text[1:].replace("_", " ").title()
    return text


def coverage_to_ha(value: int | float | None) -> int | None:
    """Convert WISE coverage (0 open, 100 covered) to HA position."""
    if value is None:
        return None
    return max(0, min(100, 100 - round(float(value))))


def inclination_to_ha(value: int | float | None) -> int | None:
    """Convert WISE inclination (-75..75 degrees) to HA tilt (0..100)."""
    if value is None:
        return None
    result = (float(value) - TILT_MIN) / (TILT_MAX - TILT_MIN) * 100
    return max(0, min(100, round(result)))


def ha_to_inclination(value: int | float) -> int:
    """Convert HA tilt to a supported WISE 15-degree step."""
    result = TILT_MIN + float(value) / 100 * (TILT_MAX - TILT_MIN)
    return max(TILT_MIN, min(TILT_MAX, round(result / 15) * 15))


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator: ScreenLineCoordinator = hass.data[DOMAIN][entry.entry_id]
    entities: list[ScreenLineCover] = []
    for room in coordinator.data:
        room_id = room.get("id")
        room_name = _display_name(
            room.get("realName") or room.get("name"), f"Room {room_id}"
        )
        for blind in _blind_list(room):
            entities.append(ScreenLineCover(coordinator, room_id, room_name, blind))
    async_add_entities(entities)


class ScreenLineCover(CoordinatorEntity[ScreenLineCoordinator], CoverEntity):
    """Representation of one ScreenLine Venetian blind."""

    _attr_device_class = CoverDeviceClass.BLIND
    _attr_supported_features = (
        CoverEntityFeature.OPEN
        | CoverEntityFeature.CLOSE
        | CoverEntityFeature.STOP
        | CoverEntityFeature.SET_POSITION
        | CoverEntityFeature.OPEN_TILT
        | CoverEntityFeature.CLOSE_TILT
        | CoverEntityFeature.SET_TILT_POSITION
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
        self._attr_unique_id = f"{coordinator.entry.unique_id}_{self._blind_id}_cover"
        blind_name = _display_name(
            blind.get("realName") or blind.get("name"), f"Blind {self._blind_id}"
        )
        self._attr_name = f"{room_name} {blind_name}"

    @property
    def device_info(self):
        model = self._blind.get("model") or {}
        model_name = model.get("name") if isinstance(model, dict) else None
        return {
            "identifiers": {(DOMAIN, f"{self.coordinator.entry.unique_id}_{self._blind_id}")},
            "name": self._attr_name,
            "manufacturer": "Pellini ScreenLine",
            "model": model_name or "WISE blind",
            "via_device": (DOMAIN, self.coordinator.entry.unique_id or self.coordinator.entry.entry_id),
        }

    def _refresh_blind_reference(self) -> None:
        for room in self.coordinator.data:
            if str(room.get("id")) != str(self._room_id):
                continue
            for blind in _blind_list(room):
                if int(blind.get("id")) == self._blind_id:
                    self._blind = blind
                    return

    def _reported_status_value(
        self, current_key: str, received_key: str, confirmed_key: str
    ) -> int | float | None:
        self._refresh_blind_reference()
        status = _status(self._blind)
        current = status.get(current_key)
        received = status.get(received_key)
        confirmed = status.get(confirmed_key)
        # The hub may set the requested target immediately. Until the motor confirms
        # it, the last received physical position is the more accurate value.
        if confirmed is False and received is not None:
            return received
        return current if current is not None else received

    @property
    def current_cover_position(self) -> int | None:
        return coverage_to_ha(
            self._reported_status_value(
                "currentCoverage", "coverageReceived", "currentCoverageNotified"
            )
        )

    @property
    def current_cover_tilt_position(self) -> int | None:
        return inclination_to_ha(
            self._reported_status_value(
                "currentInclination",
                "inclinationReceived",
                "currentInclinationNotified",
            )
        )

    @property
    def is_closed(self) -> bool | None:
        position = self.current_cover_position
        return None if position is None else position == 0

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        self._refresh_blind_reference()
        status = _status(self._blind)
        return {
            "screenline_coverage": status.get("currentCoverage"),
            "screenline_inclination_degrees": status.get("currentInclination"),
            "coverage_received": status.get("coverageReceived"),
            "inclination_received_degrees": status.get("inclinationReceived"),
            "coverage_confirmed": status.get("currentCoverageNotified"),
            "inclination_confirmed": status.get("currentInclinationNotified"),
            "hub_counter_misaligned": status.get("hubCounterMisaligned"),
            "room": self._room_name,
        }

    async def _refresh_after_command(self) -> None:
        await self.coordinator.async_request_refresh()

        async def delayed_refresh(delay: int) -> None:
            await asyncio.sleep(delay)
            await self.coordinator.async_request_refresh()

        for delay in (2, 5, 10, 20, 40):
            self.hass.async_create_task(delayed_refresh(delay))

    async def async_open_cover(self, **kwargs: Any) -> None:
        await self.coordinator.hub.move(self._room_id, self._blind_id, "UP")
        await self._refresh_after_command()

    async def async_close_cover(self, **kwargs: Any) -> None:
        await self.coordinator.hub.move(self._room_id, self._blind_id, "DOWN")
        await self._refresh_after_command()

    async def async_stop_cover(self, **kwargs: Any) -> None:
        await self.coordinator.hub.move(self._room_id, self._blind_id, "STOP")
        await self._refresh_after_command()

    async def async_set_cover_position(self, **kwargs: Any) -> None:
        position = int(kwargs[ATTR_POSITION])
        inclination = self._reported_status_value(
            "currentInclination", "inclinationReceived", "currentInclinationNotified"
        )
        await self.coordinator.hub.set_position(
            self._room_id,
            self._blind_id,
            100 - position,
            0 if inclination is None else int(inclination),
        )
        await self._refresh_after_command()

    async def async_open_cover_tilt(self, **kwargs: Any) -> None:
        await self.coordinator.hub.tilt(self._room_id, self._blind_id, "INCREMENT")
        await self._refresh_after_command()

    async def async_close_cover_tilt(self, **kwargs: Any) -> None:
        await self.coordinator.hub.tilt(self._room_id, self._blind_id, "DECREMENT")
        await self._refresh_after_command()

    async def async_set_cover_tilt_position(self, **kwargs: Any) -> None:
        tilt_position = int(kwargs[ATTR_TILT_POSITION])
        coverage = self._reported_status_value(
            "currentCoverage", "coverageReceived", "currentCoverageNotified"
        )
        await self.coordinator.hub.set_position(
            self._room_id,
            self._blind_id,
            100 if coverage is None else int(coverage),
            ha_to_inclination(tilt_position),
        )
        await self._refresh_after_command()
