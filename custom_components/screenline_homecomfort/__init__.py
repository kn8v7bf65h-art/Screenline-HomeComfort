"""ScreenLine HomeComfort integration."""

from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import PelliniCloudClient, WiseHubClient
from .const import CONF_EMAIL, CONF_HOST, CONF_PASSWORD, CONF_VERIFY_SSL, DOMAIN
from .coordinator import ScreenLineCoordinator

PLATFORMS = [Platform.COVER, Platform.SENSOR, Platform.BUTTON]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    session = async_get_clientsession(hass)
    cloud = PelliniCloudClient(session)
    token, _hubs, _is_test = await cloud.login(
        entry.data[CONF_EMAIL], entry.data[CONF_PASSWORD]
    )
    hub = WiseHubClient(
        session,
        entry.data[CONF_HOST],
        token,
        entry.data.get(CONF_VERIFY_SSL, False),
    )
    coordinator = ScreenLineCoordinator(hass, entry, cloud, hub)
    await coordinator.async_config_entry_first_refresh()

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    unloaded = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unloaded:
        hass.data[DOMAIN].pop(entry.entry_id)
    return unloaded
