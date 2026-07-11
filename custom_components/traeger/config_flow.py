"""Adds config flow for Blueprint."""
import logging

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.helpers.aiohttp_client import async_create_clientsession

from .const import CONF_PASSWORD, CONF_USERNAME, DOMAIN
from .traeger import Traeger

_LOGGER: logging.Logger = logging.getLogger(__package__)


class BlueprintFlowHandler(config_entries.ConfigFlow, domain=DOMAIN):
    """Config flow for Blueprint."""

    VERSION = 1
    CONNECTION_CLASS = config_entries.CONN_CLASS_CLOUD_POLL

    def __init__(self):
        """Initialize."""
        self._errors = {}

    async def async_step_user(self, user_input=None):
        """Handle a flow initialized by the user."""
        self._errors = {}

        # Uncomment the next 2 lines if only a single instance of the integration is allowed:
        # if self._async_current_entries():
        #     return self.async_abort(reason="single_instance_allowed")

        if user_input is not None:
            valid = await self._test_credentials(user_input[CONF_USERNAME],
                                                 user_input[CONF_PASSWORD])
            if valid:
                return self.async_create_entry(title=user_input[CONF_USERNAME],
                                               data=user_input)
            self._errors["base"] = "auth"
            return await self._show_config_form(user_input)

        user_input = {}
        # Provide defaults for form
        user_input[CONF_USERNAME] = ""
        user_input[CONF_PASSWORD] = ""

        return await self._show_config_form(user_input)

    async def _show_config_form(self, user_input):  # pylint: disable=unused-argument
        """Show the configuration form to edit location data."""
        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema({
                vol.Required(CONF_USERNAME, default=user_input[CONF_USERNAME]):
                    str,
                vol.Required(CONF_PASSWORD, default=user_input[CONF_PASSWORD]):
                    str,
            }),
            errors=self._errors,
            description_placeholders={
                "github_url":
                    "[njobrien1006/hass_traeger](https://github.com/njobrien1006/hass_traeger)"
            },
        )

    async def _test_credentials(self, username, password):
        """Return true if credentials is valid."""
        try:
            session = async_create_clientsession(self.hass)
            client = Traeger(username, password, self.hass, session)
            response = await client.get_user_data()
            _LOGGER.debug("Test Creds Resp: %s", response)
            if client.api['api_token'] == "":
                raise PermissionError("Null Token")
            if "userId" not in response:
                raise PermissionError("Bad User Data")
            return True
        except Exception as exception:  # pylint: disable=broad-except
            _LOGGER.error("Failed to login %s", exception)
        return False
