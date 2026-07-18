"""ScreenLine WISE integration."""

from __future__ import annotations

from dataclasses import dataclass

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers import device_registry as dr

from .api import ScreenLineApiClient
from .const import (
    CONF_SCAN_INTERVAL,
    CONF_TOKEN,
    CONF_VERIFY_SSL,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
    PLATFORMS,
)
from .coordinator import ScreenLineCoordinator


@dataclass
class ScreenLineRuntimeData:
    """Runtime data for a ScreenLine config entry."""

    client: ScreenLineApiClient
    coordinator: ScreenLineCoordinator


type ScreenLineConfigEntry = ConfigEntry[ScreenLineRuntimeData]


async def async_setup_entry(hass: HomeAssistant, entry: ScreenLineConfigEntry) -> bool:
    """Set up ScreenLine WISE from a config entry."""
    client = ScreenLineApiClient(
        async_get_clientsession(hass),
        entry.data[CONF_HOST],
        entry.data[CONF_TOKEN],
        verify_ssl=entry.data.get(CONF_VERIFY_SSL, False),
    )
    scan_interval = int(
        entry.options.get(
            CONF_SCAN_INTERVAL,
            entry.data.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL),
        )
    )
    coordinator = ScreenLineCoordinator(hass, entry, client, scan_interval)
    await coordinator.async_config_entry_first_refresh()

    entry.runtime_data = ScreenLineRuntimeData(client, coordinator)

    device_registry = dr.async_get(hass)
    plant_name = coordinator.data.get("name")
    device_registry.async_get_or_create(
        config_entry_id=entry.entry_id,
        identifiers={(DOMAIN, f"hub_{client.host}")},
        name=(
            plant_name
            if plant_name and not str(plant_name).startswith("@")
            else "ScreenLine WISE Hub"
        ),
        manufacturer="Pellini ScreenLine",
        model="WISE Hub",
        configuration_url=client.base_url,
    )
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    entry.async_on_unload(entry.add_update_listener(_async_update_listener))
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ScreenLineConfigEntry) -> bool:
    """Unload a ScreenLine config entry."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)


async def _async_update_listener(
    hass: HomeAssistant, entry: ScreenLineConfigEntry
) -> None:
    """Reload after options or credentials change."""
    await hass.config_entries.async_reload(entry.entry_id)
