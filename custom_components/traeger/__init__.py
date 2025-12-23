"""
Custom integration to integrate traeger with Home Assistant.

For more details about this integration, please refer to
https://github.com/njobrien1006/hass_traeger
"""
import asyncio
import logging
from datetime import timedelta

import voluptuous as vol

from homeassistant.components.number import DOMAIN as NUMBER_DOMAIN
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (EVENT_HOMEASSISTANT_STOP)
from homeassistant.core import Event, HomeAssistant
from homeassistant.helpers import config_validation as cv, service
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.typing import ConfigType

from .const import (CONF_PASSWORD, CONF_USERNAME, DOMAIN, PLATFORMS,
                    STARTUP_MESSAGE)
from .traeger import traeger

_LOGGER: logging.Logger = logging.getLogger(__package__)


async def async_setup(hass: HomeAssistant, config: ConfigType):  # pylint: disable=unused-argument
    """
    Set up this integration using YAML is not supported.
    Setup Service platform.
    """
    service.async_register_platform_entity_service(
        hass,
        DOMAIN,
        "set_custom_cook",
        entity_domain=NUMBER_DOMAIN,
        schema={vol.Required("steps", default=dict): list},
        func="set_custom_cook",
    )
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry):
    """Set up this integration using UI."""
    if hass.data.get(DOMAIN) is None:
        hass.data.setdefault(DOMAIN, {})
        _LOGGER.info(STARTUP_MESSAGE)

    username = entry.data.get(CONF_USERNAME)
    password = entry.data.get(CONF_PASSWORD)

    session = async_get_clientsession(hass)

    client = traeger(username, password, hass, session)

    await client.start(15)
    hass.data[DOMAIN][entry.entry_id] = client

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    async def async_shutdown(event: Event):  # pylint: disable=unused-argument
        """Shut down the client."""
        await client.kill()

    hass.bus.async_listen_once(EVENT_HOMEASSISTANT_STOP, async_shutdown)
    entry.add_update_listener(async_reload_entry)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Handle removal of an entry."""
    client = hass.data[DOMAIN][entry.entry_id]
    await client.kill()
    if unloaded := await hass.config_entries.async_unload_platforms(
            entry, PLATFORMS):
        hass.data[DOMAIN].pop(entry.entry_id)
    return unloaded


async def async_reload_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Reload config entry."""
    await async_unload_entry(hass, entry)
    await async_setup_entry(hass, entry)
