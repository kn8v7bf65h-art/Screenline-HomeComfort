"""Data coordinator for ScreenLine WISE."""

from __future__ import annotations

from datetime import timedelta
import logging
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import (
    ScreenLineApiClient,
    ScreenLineAuthError,
    ScreenLineConnectionError,
    ScreenLineError,
)
from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)


class ScreenLineCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Coordinate polling of a ScreenLine WISE hub."""

    def __init__(
        self,
        hass: HomeAssistant,
        entry: ConfigEntry,
        client: ScreenLineApiClient,
        scan_interval: int,
    ) -> None:
        super().__init__(
            hass,
            _LOGGER,
            config_entry=entry,
            name=DOMAIN,
            update_interval=timedelta(seconds=scan_interval),
            always_update=False,
        )
        self.client = client

    async def _async_update_data(self) -> dict[str, Any]:
        try:
            return await self.client.async_get_plant()
        except ScreenLineAuthError as err:
            raise ConfigEntryAuthFailed("ScreenLine Bearer token is invalid") from err
        except ScreenLineConnectionError as err:
            raise UpdateFailed(str(err)) from err
        except ScreenLineError as err:
            raise UpdateFailed(f"ScreenLine API error: {err}") from err

    def blinds(self) -> list[tuple[dict[str, Any], dict[str, Any]]]:
        """Return all (room, blind) pairs in coordinator data."""
        output: list[tuple[dict[str, Any], dict[str, Any]]] = []
        for room in self.data.get("rooms", []):
            for blind in room.get("blinds") or []:
                output.append((room, blind))
        return output

    def get_blind(self, blind_id: int) -> tuple[dict[str, Any], dict[str, Any]] | None:
        """Return room and blind by blind ID."""
        for room, blind in self.blinds():
            if blind.get("id") == blind_id:
                return room, blind
        return None
