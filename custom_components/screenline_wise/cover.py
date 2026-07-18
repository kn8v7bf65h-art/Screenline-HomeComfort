"""Cover platform for ScreenLine WISE blinds."""

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
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import ScreenLineConfigEntry
from .const import (
    ATTR_COVERAGE_CONFIRMED,
    ATTR_COVERAGE_RECEIVED,
    ATTR_HUB_COUNTER_MISALIGNED,
    ATTR_INCLINATION_CONFIRMED,
    ATTR_INCLINATION_RECEIVED,
    ATTR_SCREENLINE_COVERAGE,
    ATTR_SCREENLINE_INCLINATION,
    TILT_MAX,
    TILT_MIN,
)
from .entity import ScreenLineEntity, display_name


def coverage_to_ha(coverage: int | float | None) -> int | None:
    """Convert ScreenLine coverage (0 up, 100 down) to HA position."""
    if coverage is None:
        return None
    return max(0, min(100, 100 - round(float(coverage))))


def ha_to_coverage(position: int | float) -> int:
    return max(0, min(100, 100 - round(float(position))))


def inclination_to_ha(inclination: int | float | None) -> int | None:
    """Convert -75..75 degrees to Home Assistant 0..100 tilt."""
    if inclination is None:
        return None
    value = (float(inclination) - TILT_MIN) / (TILT_MAX - TILT_MIN) * 100
    return max(0, min(100, round(value)))


def ha_to_inclination(position: int | float) -> int:
    value = TILT_MIN + (float(position) / 100) * (TILT_MAX - TILT_MIN)
    # WISE Venetian blinds generally move in 15 degree increments.
    return max(TILT_MIN, min(TILT_MAX, round(value / 15) * 15))


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ScreenLineConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator = entry.runtime_data.coordinator
    async_add_entities(
        ScreenLineCover(coordinator, blind["id"]) for _, blind in coordinator.blinds()
    )


class ScreenLineCover(ScreenLineEntity, CoverEntity):
    """A ScreenLine Venetian blind."""

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

    def __init__(self, coordinator, blind_id: int) -> None:
        super().__init__(coordinator, blind_id)
        self._attr_unique_id = f"{coordinator.client.host}_{blind_id}_cover"
        self._attr_name = None

    def _reported_status_value(
        self, current_key: str, received_key: str, confirmed_key: str
    ) -> int | float | None:
        """Prefer the last physical report while a target is not yet confirmed."""
        status = self.blind.get("status") or {}
        current = status.get(current_key)
        received = status.get(received_key)
        confirmed = status.get(confirmed_key)

        # The WISE hub updates current* immediately to the requested target. Until the
        # motor reports completion, *Received is a better representation of reality.
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
        status = self.blind.get("status") or {}
        return {
            ATTR_SCREENLINE_COVERAGE: status.get("currentCoverage"),
            ATTR_SCREENLINE_INCLINATION: status.get("currentInclination"),
            ATTR_COVERAGE_RECEIVED: status.get("coverageReceived"),
            ATTR_INCLINATION_RECEIVED: status.get("inclinationReceived"),
            ATTR_COVERAGE_CONFIRMED: status.get("currentCoverageNotified"),
            ATTR_INCLINATION_CONFIRMED: status.get("currentInclinationNotified"),
            ATTR_HUB_COUNTER_MISALIGNED: status.get("hubCounterMisaligned"),
            "room": display_name(self.room.get("name"), f"Room {self.room.get('id')}"),
        }

    async def _refresh_after_command(self) -> None:
        """Refresh now and several times while the battery blind is moving."""
        await self.coordinator.async_request_refresh()

        async def _delayed_refresh(delay: int) -> None:
            await asyncio.sleep(delay)
            await self.coordinator.async_request_refresh()

        for delay in (2, 5, 10, 20, 40):
            self.hass.async_create_task(_delayed_refresh(delay))

    async def async_open_cover(self, **kwargs: Any) -> None:
        await self.coordinator.client.async_move(
            self.room["id"], [self.blind_id], "UP"
        )
        await self._refresh_after_command()

    async def async_close_cover(self, **kwargs: Any) -> None:
        await self.coordinator.client.async_move(
            self.room["id"], [self.blind_id], "DOWN"
        )
        await self._refresh_after_command()

    async def async_stop_cover(self, **kwargs: Any) -> None:
        await self.coordinator.client.async_move(
            self.room["id"], [self.blind_id], "STOP"
        )
        await self._refresh_after_command()

    async def async_set_cover_position(self, **kwargs: Any) -> None:
        position = kwargs[ATTR_POSITION]
        status = self.blind.get("status") or {}
        inclination = int(status.get("currentInclination", 0))
        await self.coordinator.client.async_set_position(
            self.room["id"],
            [self.blind_id],
            ha_to_coverage(position),
            inclination,
        )
        await self._refresh_after_command()

    async def async_open_cover_tilt(self, **kwargs: Any) -> None:
        # The official app maps its tilt-up button to one INCREMENT command.
        # This changes only the slat angle and does not alter blind coverage.
        await self.coordinator.client.async_tilt_step(
            self.room["id"], [self.blind_id], "INCREMENT"
        )
        await self._refresh_after_command()

    async def async_close_cover_tilt(self, **kwargs: Any) -> None:
        # The official app maps its tilt-down button to one DECREMENT command.
        await self.coordinator.client.async_tilt_step(
            self.room["id"], [self.blind_id], "DECREMENT"
        )
        await self._refresh_after_command()

    async def async_set_cover_tilt_position(self, **kwargs: Any) -> None:
        tilt_position = kwargs[ATTR_TILT_POSITION]
        status = self.blind.get("status") or {}
        coverage = int(status.get("currentCoverage", 100))
        await self.coordinator.client.async_set_position(
            self.room["id"],
            [self.blind_id],
            coverage,
            ha_to_inclination(tilt_position),
        )
        await self._refresh_after_command()
