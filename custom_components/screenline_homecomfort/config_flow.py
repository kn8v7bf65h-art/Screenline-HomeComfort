"""Config flow for ScreenLine HomeComfort."""

from __future__ import annotations

from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.core import callback
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import PelliniCloudClient, ScreenLineAuthError, ScreenLineConnectionError, WiseHubClient
from .const import (
    CONF_EMAIL,
    CONF_HOST,
    CONF_HUB_NAME,
    CONF_PASSWORD,
    CONF_VERIFY_SSL,
    DEFAULT_VERIFY_SSL,
    DOMAIN,
)


class ScreenLineConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a ScreenLine HomeComfort config flow."""

    VERSION = 2

    def __init__(self) -> None:
        self._email = ""
        self._password = ""
        self._hubs: dict[str, str] = {}

    async def async_step_user(self, user_input: dict[str, Any] | None = None):
        errors: dict[str, str] = {}
        if user_input is not None:
            self._email = user_input[CONF_EMAIL]
            self._password = user_input[CONF_PASSWORD]
            try:
                cloud = PelliniCloudClient(async_get_clientsession(self.hass))
                _token, hubs, _is_test = await cloud.login(self._email, self._password)
            except ScreenLineAuthError:
                errors["base"] = "invalid_auth"
            except ScreenLineConnectionError:
                errors["base"] = "cannot_connect"
            else:
                self._hubs = {
                    hub.hub_name: f"{hub.plant_name} ({hub.hub_name})" for hub in hubs
                }
                if not self._hubs:
                    errors["base"] = "no_hubs"
                else:
                    return await self.async_step_hub()

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_EMAIL, default=self._email): str,
                    vol.Required(CONF_PASSWORD): str,
                }
            ),
            errors=errors,
        )

    async def async_step_hub(self, user_input: dict[str, Any] | None = None):
        errors: dict[str, str] = {}
        if user_input is not None:
            hub_name = user_input[CONF_HUB_NAME]
            host = user_input[CONF_HOST]
            verify_ssl = user_input[CONF_VERIFY_SSL]
            await self.async_set_unique_id(hub_name)
            self._abort_if_unique_id_configured()
            try:
                cloud = PelliniCloudClient(async_get_clientsession(self.hass))
                token, _hubs, _is_test = await cloud.login(self._email, self._password)
                hub = WiseHubClient(async_get_clientsession(self.hass), host, token, verify_ssl)
                await hub.get_rooms()
            except ScreenLineAuthError:
                errors["base"] = "invalid_auth"
            except ScreenLineConnectionError:
                errors["base"] = "cannot_connect_hub"
            else:
                return self.async_create_entry(
                    title=self._hubs.get(hub_name, hub_name),
                    data={
                        CONF_EMAIL: self._email,
                        CONF_PASSWORD: self._password,
                        CONF_HUB_NAME: hub_name,
                        CONF_HOST: host,
                        CONF_VERIFY_SSL: verify_ssl,
                    },
                )

        default_hub = next(iter(self._hubs), "")
        return self.async_show_form(
            step_id="hub",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_HUB_NAME, default=default_hub): vol.In(self._hubs),
                    vol.Required(CONF_HOST, default=default_hub): str,
                    vol.Required(CONF_VERIFY_SSL, default=DEFAULT_VERIFY_SSL): bool,
                }
            ),
            errors=errors,
            description_placeholders={
                "note": "Vul het lokale IP-adres of de lokale hostnaam van de gekozen WISE Hub in."
            },
        )

    async def async_step_reauth(self, entry_data: dict[str, Any]):
        self._reauth_entry = self.hass.config_entries.async_get_entry(self.context["entry_id"])
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(self, user_input: dict[str, Any] | None = None):
        errors: dict[str, str] = {}
        if user_input is not None:
            try:
                cloud = PelliniCloudClient(async_get_clientsession(self.hass))
                await cloud.login(user_input[CONF_EMAIL], user_input[CONF_PASSWORD])
            except ScreenLineAuthError:
                errors["base"] = "invalid_auth"
            except ScreenLineConnectionError:
                errors["base"] = "cannot_connect"
            else:
                assert self._reauth_entry is not None
                return self.async_update_reload_and_abort(
                    self._reauth_entry,
                    data_updates={
                        CONF_EMAIL: user_input[CONF_EMAIL],
                        CONF_PASSWORD: user_input[CONF_PASSWORD],
                    },
                )

        assert self._reauth_entry is not None
        return self.async_show_form(
            step_id="reauth_confirm",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        CONF_EMAIL, default=self._reauth_entry.data[CONF_EMAIL]
                    ): str,
                    vol.Required(CONF_PASSWORD): str,
                }
            ),
            errors=errors,
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: config_entries.ConfigEntry):
        return ScreenLineOptionsFlow(config_entry)


class ScreenLineOptionsFlow(config_entries.OptionsFlow):
    """Options flow."""

    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        self.config_entry = config_entry

    async def async_step_init(self, user_input: dict[str, Any] | None = None):
        if user_input is not None:
            new_data = {**self.config_entry.data, **user_input}
            self.hass.config_entries.async_update_entry(self.config_entry, data=new_data)
            return self.async_create_entry(title="", data={})
        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        CONF_HOST, default=self.config_entry.data[CONF_HOST]
                    ): str,
                    vol.Required(
                        CONF_VERIFY_SSL,
                        default=self.config_entry.data.get(CONF_VERIFY_SSL, False),
                    ): bool,
                }
            ),
        )
