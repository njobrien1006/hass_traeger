"""Fixtures for testing."""

import logging
import pytest

from aioresponses import aioresponses
from collections.abc import Generator
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from pytest_homeassistant_custom_component.common import MockConfigEntry
from typing import Any
from amqtt.broker import Broker

from .zzMockResp import api_commands, api_token, api_mqtt, api_user_self
from custom_components.traeger.const import CONF_PASSWORD, CONF_USERNAME, DOMAIN
from custom_components.traeger.traeger import Traeger as TraegerTestClient

_LOGGER: logging.Logger = logging.getLogger(__package__)


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations):  # pylint: disable=unused-argument
    '''Enable Custom Integrations'''
    yield


@pytest.fixture
def http() -> Generator[aioresponses, Any]:
    """Fixture to mock `aiohttp` requests."""
    with aioresponses() as mock:
        mock.post(api_token['url'], payload=api_token['resp'], repeat=True)
        mock.get(api_user_self['url'],
                 payload=api_user_self['resp'],
                 repeat=True)
        mock.post(api_mqtt['url'], payload=api_mqtt['resp'], repeat=True)
        #cmd API handled in tests as they are variable.
        #mock.post(api_commands['url'], payload=api_commands['resp'], repeat=True)
        #mock.post(api_commands['urlg2'], payload=api_commands['resp'], repeat=True)
        yield mock


@pytest.fixture
async def mock_broker(hass: HomeAssistant) -> Broker:
    """Fixture to Serve MQTT Client"""
    mBroker = Broker(
        {
            "listeners": {
                "default": {
                    "bind": "127.0.0.1:4443",
                    "type": "ws",
                    "ssl": False,
                    "max_connections": 10,
                },
            },
            "plugins": {
                "amqtt.plugins.authentication.AnonymousAuthPlugin": {
                    "allow_anonymous": True
                },
                "amqtt.plugins.sys.broker.BrokerSysPlugin": {
                    "sys_interval": 30
                },
            },
        },
        loop=hass.loop)
    return mBroker


@pytest.fixture
async def traeger_client(hass: HomeAssistant,
                         http: aioresponses) -> TraegerTestClient:
    """Traeger Test Client"""
    session = async_get_clientsession(hass)
    client = TraegerTestClient("johnytraeger@traeger.com",
                               "johnytraeger'spassword", hass, session)
    return client


@pytest.fixture
async def mock_config_entry(hass: HomeAssistant,
                            traeger_client: TraegerTestClient,
                            http: aioresponses) -> MockConfigEntry:
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={
            CONF_USERNAME: "johnytraeger@traeger.com",
            CONF_PASSWORD: "johnytraeger'spassword",
        },
    )
    hass.data[DOMAIN] = {entry.entry_id: traeger_client}
    entry.add_to_hass(hass)
    await hass.config_entries.async_setup(entry.entry_id)
    return entry
