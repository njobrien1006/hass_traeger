"""Fixtures for testing."""

import asyncio
import logging
import pytest

from aiointercept import aiointercept, CallbackResult
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.util.unit_system import US_CUSTOMARY_SYSTEM
from pytest_homeassistant_custom_component.common import MockConfigEntry
from pytest_homeassistant_custom_component.syrupy import HomeAssistantSnapshotExtension
from syrupy.assertion import SnapshotAssertion
from amqtt.broker import Broker

from custom_components.traeger.const import (
    CONF_PASSWORD,
    CONF_USERNAME,
    DOMAIN,
    CONF_OPT_MOBILE_APP,
)
from custom_components.traeger.traeger import Traeger as TraegerTestClient
from .zzMockResp import api_token, api_mqtt, api_user_self

_LOGGER: logging.Logger = logging.getLogger(__package__)

# The MQTT port we will use instead of 443
MQTTPORT = 4447


# pylint: disable=unused-argument,too-many-arguments,too-many-positional-arguments,redefined-outer-name,invalid-name
@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations):  # pylint: disable=unused-argument
    """Enable Custom Integrations"""
    yield


@pytest.fixture
def snapshot(snapshot: SnapshotAssertion) -> SnapshotAssertion:
    """Return snapshot assertion fixture with the Home Assistant extension."""
    return snapshot.use_extension(HomeAssistantSnapshotExtension)


@pytest.fixture(autouse=True)
def allowed_hosts(socket_enabled):
    """Allows aiointercept to spin up its local loopback server safely"""
    pass  # pylint: disable=unnecessary-pass


@pytest.fixture
async def http():
    """Fixture to mock `aiohttp` requests."""
    async with aiointercept(mock_external_urls=True) as mock:

        def callback(url, **kwargs):
            """Setup API Callbacks"""
            _LOGGER.info("Was at conftest callbacks %s - %s", url, kwargs["json"])
            return CallbackResult(status=200, payload={})

        mock.post(api_token["url"], payload=api_token["resp"], repeat=True)
        mock.get(api_user_self["url"], payload=api_user_self["resp"], repeat=True)
        mock.post(api_mqtt["url"], payload=api_mqtt["resp"], repeat=True)
        mock.post(
            "https://mobile-apps.home-assistant.io/api/sendPushNotification",
            callback=callback,
            repeat=True,
        )
        # cmd API handled in tests as they are variable.
        # mock.post(api_commands['url'], payload=api_commands['resp'], repeat=True)
        # mock.post(api_commands['urlg2'], payload=api_commands['resp'], repeat=True)
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
                "amqtt.plugins.sys.broker.BrokerSysPlugin": {"sys_interval": 30},
            },
        },
        loop=hass.loop,
    )
    return mBroker


@pytest.fixture
async def connected_amqtt(mock_broker: Broker):
    """Fixture to connect & gracefull disc amqtt patricularily on fail"""
    # Start Broker
    _LOGGER.error("Start Broker")
    await mock_broker.start()
    await asyncio.sleep(0.01)

    yield  # this is where the testing happens

    # Shutdown MQTT
    _LOGGER.error("Stop Broker")
    await mock_broker.shutdown()
    await asyncio.sleep(0.01)


@pytest.fixture
async def traeger_client(hass: HomeAssistant, http: aiointercept) -> TraegerTestClient:
    """Traeger Test Client"""
    session = async_get_clientsession(hass)
    client = TraegerTestClient(
        "johnytraeger@traeger.com", "johnytraeger'spassword", hass, session
    )
    return client


@pytest.fixture
async def mock_config_entry(
    hass: HomeAssistant,
    traeger_client: TraegerTestClient,
    http: aiointercept,
    caplog: pytest.LogCaptureFixture,
) -> MockConfigEntry:
    """HASS Mock Config Entry"""
    hass.config.units = US_CUSTOMARY_SYSTEM
    caplog.set_level(logging.WARNING)

    mobile_app = []
    registry = dr.async_get(hass)

    # Android Entry
    entry = MockConfigEntry(
        domain="mobile_app",
        title="Johny's Android",
        data={
            "app_id": "io.homeassistant.companion.android",
            "app_data": {
                "push_token": "142CharToken",
                "push_url": "https://mobile-apps.home-assistant.io/api/sendPushNotification",
            },
            "app_name": "Home Assistant Companion",
            "app_version": "2026.1.1",
            "device_name": "Android Phone",
            "device_id": "mock_Android",
            "manufacturer": "Google",
            "model": "Pixel",
            "os_name": "Android",
            "os_version": "14",
            "supports_encryption": False,
            "user_id": "32CharUserUUID",
            "webhook_id": "mock_webhook_id_98765",
        },
        unique_id="mock_android_uuid_12345",
    )
    entry.add_to_hass(hass)
    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    devices = dr.async_entries_for_config_entry(registry, entry.entry_id)
    mobile_app.append(devices[0].id)

    # iPhone Entry
    entry = MockConfigEntry(
        domain="mobile_app",
        title="Johny's iPhone",
        data={
            "app_id": "io.homeassistant.companion.iphone",
            "app_data": {
                "push_token": "142CharToken",
                "push_url": "https://mobile-apps.home-assistant.io/api/sendPushNotification",
            },
            "app_name": "Home Assistant Companion",
            "app_version": "2026.1.1",
            "device_name": "iPhone",
            "device_id": "mock_Android",
            "manufacturer": "Apple",
            "model": "iPhone17,1",
            "os_name": "iOS",
            "os_version": "26.6",
            "supports_encryption": False,
            "user_id": "32CharUserUUID",
            "webhook_id": "mock_webhook_id_98766",
        },
        unique_id="mock_apple_uuid_12346",
    )
    entry.add_to_hass(hass)
    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    devices = dr.async_entries_for_config_entry(registry, entry.entry_id)
    mobile_app.append(devices[0].id)

    _LOGGER.info("MobileAppIds: %s", mobile_app)

    entry = MockConfigEntry(
        domain=DOMAIN,
        data={
            CONF_USERNAME: "johnytraeger@traeger.com",
            CONF_PASSWORD: "johnytraeger'spassword",
            CONF_OPT_MOBILE_APP: mobile_app,
        },
    )
    hass.data[DOMAIN] = {entry.entry_id: traeger_client}
    entry.add_to_hass(hass)
    await hass.config_entries.async_setup(entry.entry_id)
    hass_traeger_client = hass.data[DOMAIN][entry.entry_id]
    # Start with pending task cancelled.
    await hass_traeger_client.kill()
    await hass_traeger_client.get_entities()

    yield entry

    await hass_traeger_client.kill()
