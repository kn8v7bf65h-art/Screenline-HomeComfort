"""Data coordinator for ScreenLine HomeComfort."""

from __future__ import annotations

from datetime import timedelta
import logging
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import PelliniCloudClient, ScreenLineAuthError, ScreenLineConnectionError, WiseHubClient
from .const import CONF_EMAIL, CONF_PASSWORD, DEFAULT_SCAN_INTERVAL, DOMAIN

_LOGGER = logging.getLogger(__name__)


class ScreenLineCoordinator(DataUpdateCoordinator[list[dict[str, Any]]]):
    """Coordinate data updates and refresh expired cloud tokens."""

    def __init__(
        self,
        hass: HomeAssistant,
        entry: ConfigEntry,
        cloud: PelliniCloudClient,
        hub: WiseHubClient,
    ) -> None:
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=DEFAULT_SCAN_INTERVAL),
        )
        self.entry = entry
        self.cloud = cloud
        self.hub = hub

    async def _async_update_data(self) -> list[dict[str, Any]]:
        try:
            return await self.hub.get_rooms()
        except ScreenLineAuthError:
            try:
                token, _hubs, _is_test = await self.cloud.login(
                    self.entry.data[CONF_EMAIL], self.entry.data[CONF_PASSWORD]
                )
                self.hub.set_token(token)
                return await self.hub.get_rooms()
            except ScreenLineAuthError as err:
                self.entry.async_start_reauth(self.hass)
                raise UpdateFailed("Authentication failed; reauthentication required") from err
            except ScreenLineConnectionError as err:
                raise UpdateFailed(str(err)) from err
        except ScreenLineConnectionError as err:
            raise UpdateFailed(str(err)) from err
