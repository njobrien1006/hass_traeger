"""Fixtures for testing."""

#from typing import Any

import pytest
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from paho.mqtt.client import MQTTMessage
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.traeger.const import CONF_PASSWORD, CONF_USERNAME, DOMAIN
from custom_components.traeger.traeger import (
    Traeger,)


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations):  # pylint: disable=unused-argument
    '''Enable Custom Integrations'''
    yield


class TraegerTestClient(Traeger):
    """Override Native Test Client for testing."""

    def __init__(self, username, password, hass: HomeAssistant,
                 request_library) -> None:  # pylint: disable=unused-argument
        super().__init__("johnytraeger@traeger.com", "johnytraeger'spassword",
                         hass, request_library)
        self.published_messages: list[MQTTMessage] = []

    # pylint: disable=dangerous-default-value,unused-private-member,unused-argument
    async def __api_wrapper(self,
                            method: str,
                            url: str,
                            data: dict = {},
                            headers: dict = {}) -> dict:
        """Get information from the API.
           OVerride API wrapper. We dont actualy want to send REQs."""
        assert True


@pytest.fixture
async def traeger_client(hass: HomeAssistant) -> TraegerTestClient:
    """Traeger Test Client"""
    session = async_get_clientsession(hass)
    client = TraegerTestClient("johnytraeger@traeger.com",
                               "johnytraeger'spassword", hass, session)
    #client.state.is_online = True
    return client


@pytest.fixture
async def mock_config_entry(
        hass: HomeAssistant,
        traeger_client_entry: TraegerTestClient) -> MockConfigEntry:
    """Mock Config"""
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={
            CONF_USERNAME: "johnytraeger@traeger.com",
            CONF_PASSWORD: "johnytraeger'spassword"
        },
    )
    hass.data[DOMAIN] = {entry.entry_id: traeger_client_entry}
    entry.add_to_hass(hass)
    await hass.config_entries.async_setup(entry.entry_id)
    return entry
