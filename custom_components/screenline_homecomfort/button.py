"""Button platform for incremental ScreenLine slat control."""

from __future__ import annotations

import asyncio
from typing import Any

from homeassistant.components.button import ButtonEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import ScreenLineCoordinator
from .cover import _blind_list, _display_name


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up one-step tilt buttons for every blind."""
    coordinator: ScreenLineCoordinator = hass.data[DOMAIN][entry.entry_id]
    entities: list[ScreenLineTiltStepButton] = []

    for room in coordinator.data:
        room_id = room.get("id")
        room_name = _display_name(
            room.get("realName") or room.get("name"), f"Room {room_id}"
        )
        for blind in _blind_list(room):
            entities.extend(
                (
                    ScreenLineTiltStepButton(
                        coordinator, room_id, room_name, blind, "INCREMENT"
                    ),
                    ScreenLineTiltStepButton(
                        coordinator, room_id, room_name, blind, "DECREMENT"
                    ),
                )
            )

    async_add_entities(entities)


class ScreenLineTiltStepButton(
    CoordinatorEntity[ScreenLineCoordinator], ButtonEntity
):
    """Move the slats by one native ScreenLine step."""

    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: ScreenLineCoordinator,
        room_id: int | str,
        room_name: str,
        blind: dict[str, Any],
        tilt_type: str,
    ) -> None:
        super().__init__(coordinator)
        self._room_id = room_id
        self._blind_id = int(blind["id"])
        self._blind = blind
        self._tilt_type = tilt_type
        self._refresh_task: asyncio.Task[None] | None = None

        blind_name = _display_name(
            blind.get("realName") or blind.get("name"), f"Blind {self._blind_id}"
        )
        self._device_name = f"{room_name} {blind_name}"
        suffix = "tilt_increment" if tilt_type == "INCREMENT" else "tilt_decrement"
        self._attr_unique_id = (
            f"{coordinator.entry.unique_id}_{self._blind_id}_{suffix}"
        )
        self._attr_translation_key = suffix
        self._attr_icon = (
            "mdi:angle-acute" if tilt_type == "INCREMENT" else "mdi:angle-obtuse"
        )

    @property
    def device_info(self):
        model = self._blind.get("model") or {}
        model_name = model.get("name") if isinstance(model, dict) else None
        return {
            "identifiers": {
                (DOMAIN, f"{self.coordinator.entry.unique_id}_{self._blind_id}")
            },
            "name": self._device_name,
            "manufacturer": "Pellini ScreenLine",
            "model": model_name or "WISE blind",
            "via_device": (
                DOMAIN,
                self.coordinator.entry.unique_id or self.coordinator.entry.entry_id,
            ),
        }

    async def async_will_remove_from_hass(self) -> None:
        if self._refresh_task is not None:
            self._refresh_task.cancel()
            self._refresh_task = None
        await super().async_will_remove_from_hass()

    async def _delayed_refresh(self) -> None:
        try:
            # One status refresh is enough for a single 15-degree step.
            await asyncio.sleep(3)
            await self.coordinator.async_request_refresh()
        finally:
            self._refresh_task = None

    async def async_press(self) -> None:
        """Send the exact incremental command used by the official app."""
        await self.coordinator.hub.tilt(
            self._room_id, self._blind_id, self._tilt_type
        )
        if self._refresh_task is not None:
            self._refresh_task.cancel()
        self._refresh_task = self.hass.async_create_task(self._delayed_refresh())
