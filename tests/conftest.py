"""Fixtures for testing."""

import logging
from collections.abc import Generator
from typing import Any
import pytest

from aioresponses import aioresponses
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from pytest_homeassistant_custom_component.common import MockConfigEntry
from amqtt.broker import Broker

from custom_components.traeger.const import CONF_PASSWORD, CONF_USERNAME, DOMAIN
from custom_components.traeger.traeger import Traeger as TraegerTestClient
from .zzMockResp import api_token, api_mqtt, api_user_self

_LOGGER: logging.Logger = logging.getLogger(__package__)

#The MQTT port we will use instead of 443
MQTTPORT = 4447


#pylint: disable=unused-argument,too-many-arguments,too-many-positional-arguments,redefined-outer-name,invalid-name
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
                    "bind": f"127.0.0.1:{MQTTPORT}",
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
async def connected_amqtt(mock_broker: Broker):
    """Fixture to connect & gracefull disc amqtt patricularily on fail"""
    #Start Broker
    _LOGGER.error("Start Broker")
    await mock_broker.start()

    yield  # this is where the testing happens

    #Shutdown MQTT
    _LOGGER.error("Stop Broker")
    await mock_broker.shutdown()


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
    """HASS Mock Config Entry"""
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
