"""Adds config flow for Blueprint."""
import logging

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.helpers import selector
from homeassistant.helpers.aiohttp_client import async_create_clientsession
from slugify import slugify

from .const import CONF_PASSWORD, CONF_USERNAME, DOMAIN
from .traeger import Traeger

_LOGGER: logging.Logger = logging.getLogger(__package__)


class BlueprintFlowHandler(config_entries.ConfigFlow, domain=DOMAIN):  # pylint: disable=too-few-public-methods
    """Config flow for Blueprint."""

    VERSION = 1
    CONNECTION_CLASS = config_entries.CONN_CLASS_CLOUD_POLL

    def __init__(self):
        """Initialize."""

    async def async_step_user(
        self,
        user_input: dict | None = None,
    ) -> config_entries.ConfigFlowResult:
        """Handle a flow initialized by the user."""
        _errors = {}
        if user_input is not None:
            rtrn = await self._test_credentials(
                username=user_input[CONF_USERNAME],
                password=user_input[CONF_PASSWORD],
            )
            if rtrn:
                await self.async_set_unique_id(
                    unique_id=slugify(user_input[CONF_USERNAME]))
                self._abort_if_unique_id_configured()
                return self.async_create_entry(
                    title=user_input[CONF_USERNAME],
                    data=user_input,
                )
            _errors["base"] = "auth"

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        CONF_USERNAME,
                        default=(user_input or {}).get(CONF_USERNAME, vol.UNDEFINED),
                    ):
                        selector.TextSelector(
                            selector.TextSelectorConfig(
                                type=selector.TextSelectorType.TEXT,),),
                    vol.Required(CONF_PASSWORD):
                        selector.TextSelector(
                            selector.TextSelectorConfig(
                                type=selector.TextSelectorType.PASSWORD,),),
                },),
            errors=_errors,
        )

    async def _test_credentials(self, username, password):
        """Return true if credentials is valid."""
        try:
            session = async_create_clientsession(self.hass)
            client = Traeger(username, password, self.hass, session)
            response = await client.get_user_data()
            if response is None:
                _LOGGER.error("Login failed with: %s", response)
                return False
            _LOGGER.debug("Full Login Response %s", response)
            _LOGGER.debug(
                "Hello %s",
                response.get("fullName", "That was Null...Failed Login?"))
            return True
        except Exception as exception:  # pylint: disable=broad-except
            _LOGGER.error("Failed to login %s", exception)
        return False
