"""Config flow for ScreenLine WISE."""

from __future__ import annotations

from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.const import CONF_HOST
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import (
    ScreenLineApiClient,
    ScreenLineAuthError,
    ScreenLineConnectionError,
    ScreenLineError,
)
from .const import (
    CONF_SCAN_INTERVAL,
    CONF_TOKEN,
    CONF_VERIFY_SSL,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
    MAX_SCAN_INTERVAL,
    MIN_SCAN_INTERVAL,
)


async def _validate_input(hass: HomeAssistant, data: dict[str, Any]) -> dict[str, Any]:
    client = ScreenLineApiClient(
        async_get_clientsession(hass),
        data[CONF_HOST],
        data[CONF_TOKEN],
        verify_ssl=data.get(CONF_VERIFY_SSL, False),
    )
    plant = await client.async_get_plant()
    plant_name = plant.get("name")
    title = (
        plant_name
        if plant_name and not str(plant_name).startswith("@")
        else f"ScreenLine WISE ({data[CONF_HOST]})"
    )
    return {"title": title}


class ScreenLineConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a ScreenLine WISE config flow."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        errors: dict[str, str] = {}
        if user_input is not None:
            host = user_input[CONF_HOST].strip()
            user_input[CONF_HOST] = host
            await self.async_set_unique_id(host.lower())
            self._abort_if_unique_id_configured()
            try:
                info = await _validate_input(self.hass, user_input)
            except ScreenLineAuthError:
                errors["base"] = "invalid_auth"
            except ScreenLineConnectionError:
                errors["base"] = "cannot_connect"
            except ScreenLineError:
                errors["base"] = "unknown"
            except Exception:  # noqa: BLE001
                errors["base"] = "unknown"
            else:
                return self.async_create_entry(title=info["title"], data=user_input)

        schema = vol.Schema(
            {
                vol.Required(CONF_HOST, default=(user_input or {}).get(CONF_HOST, "")): str,
                vol.Required(CONF_TOKEN, default=(user_input or {}).get(CONF_TOKEN, "")): str,
                vol.Optional(
                    CONF_VERIFY_SSL,
                    default=(user_input or {}).get(CONF_VERIFY_SSL, False),
                ): bool,
            }
        )
        return self.async_show_form(step_id="user", data_schema=schema, errors=errors)

    async def async_step_reauth(self, entry_data: dict[str, Any]) -> FlowResult:
        """Start reauthentication."""
        self._reauth_entry = self.hass.config_entries.async_get_entry(
            self.context["entry_id"]
        )
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Update an expired token."""
        errors: dict[str, str] = {}
        entry = self._reauth_entry
        if user_input is not None and entry is not None:
            updated = {**entry.data, CONF_TOKEN: user_input[CONF_TOKEN]}
            try:
                await _validate_input(self.hass, updated)
            except ScreenLineAuthError:
                errors["base"] = "invalid_auth"
            except ScreenLineConnectionError:
                errors["base"] = "cannot_connect"
            except ScreenLineError:
                errors["base"] = "unknown"
            else:
                return self.async_update_reload_and_abort(
                    entry, data_updates={CONF_TOKEN: user_input[CONF_TOKEN]}
                )

        return self.async_show_form(
            step_id="reauth_confirm",
            data_schema=vol.Schema({vol.Required(CONF_TOKEN): str}),
            errors=errors,
        )

    @staticmethod
    def async_get_options_flow(config_entry: config_entries.ConfigEntry):
        return ScreenLineOptionsFlow(config_entry)


class ScreenLineOptionsFlow(config_entries.OptionsFlow):
    """Handle ScreenLine options."""

    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        self._entry = config_entry

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)
        current = self._entry.options.get(
            CONF_SCAN_INTERVAL,
            self._entry.data.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL),
        )
        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_SCAN_INTERVAL, default=current): vol.All(
                        vol.Coerce(int),
                        vol.Range(min=MIN_SCAN_INTERVAL, max=MAX_SCAN_INTERVAL),
                    )
                }
            ),
        )
