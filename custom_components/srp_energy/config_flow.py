"""Config flow for SRP Energy."""
from __future__ import annotations

import logging
from typing import Any

from srpenergy.client import SrpEnergyClient
import voluptuous as vol

from homeassistant import config_entries
from homeassistant.const import CONF_ID, CONF_NAME, CONF_PASSWORD, CONF_USERNAME
from homeassistant.core import HomeAssistant, callback
from homeassistant.data_entry_flow import FlowResult
from homeassistant.exceptions import HomeAssistantError

from .const import CONF_IS_TOU, DEFAULT_NAME, DOMAIN

_LOGGER = logging.getLogger(__name__)

DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_ID): str,
        vol.Required(CONF_USERNAME): str,
        vol.Required(CONF_PASSWORD): str,
        vol.Optional(CONF_NAME, default=DEFAULT_NAME): str,
        vol.Optional(CONF_IS_TOU, default=False): bool,
    }
)


async def validate_input(hass: HomeAssistant, data: dict[str, Any]) -> dict[str, Any]:
    """Validate the user input allows us to connect.

    Data has the keys from DATA_SCHEMA with values provided by the user.
    """
    _LOGGER.debug("Validate User Input with client")
    srp_client = SrpEnergyClient(
        data[CONF_ID],
        data[CONF_USERNAME],
        data[CONF_PASSWORD],
    )

    is_valid = await hass.async_add_executor_job(srp_client.validate)

    _LOGGER.debug("Is valid User Input with client: %s", is_valid)
    if not is_valid:
        raise InvalidAuth

    return is_valid


class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle an SRP Energy config flow."""

    VERSION = 1

    @callback
    def _show_form(self, errors: dict[str, Any] | None = None) -> FlowResult:
        """Show the form to the user."""
        _LOGGER.debug("Show Form")
        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_ID): str,
                    vol.Required(CONF_USERNAME): str,
                    vol.Required(CONF_PASSWORD): str,
                    vol.Optional(
                        CONF_NAME, default=self.hass.config.location_name
                    ): str,
                    vol.Optional(CONF_IS_TOU, default=False): bool,
                }
            ),
            errors=errors or {},
        )

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle a flow initialized by the user."""
        _LOGGER.debug("Config entry")
        if not user_input:
            return self._show_form()

        errors = {}

        try:
            await validate_input(self.hass, user_input)
        except ValueError:
            errors["base"] = "invalid_account"
            return self._show_form(errors)
        except InvalidAuth:
            errors["base"] = "invalid_auth"
            return self._show_form(errors)
        except Exception:  # pylint: disable=broad-except
            _LOGGER.exception("Unexpected exception")
            return self.async_abort(reason="unknown")

        await self.async_set_unique_id(user_input.get(CONF_ID))
        self._abort_if_unique_id_configured()

        return self.async_create_entry(title=user_input[CONF_NAME], data=user_input)


class InvalidAuth(HomeAssistantError):
    """Error to indicate there is invalid auth."""
