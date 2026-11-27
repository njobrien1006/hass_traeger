"""Test the Traeger Client."""

import asyncio
import json
import logging
from unittest.mock import AsyncMock, patch

import pytest
from aiointercept import aiointercept
from paho.mqtt.client import MQTTMessage

from custom_components.traeger.traeger import TraegerMQTTClient

from .conftest import Broker, TraegerTestClient
from .zzcommon import client_connect, client_disconnect
from .zzMockResp import api_user_self, mqtt_msg

_LOGGER: logging.Logger = logging.getLogger(__package__)
"""Test Traeger MQTT"""


# pylint: disable=unused-argument,too-many-arguments,too-many-positional-arguments
@pytest.mark.usefixtures("socket_enabled")
async def test_connect_pub(
    traeger_client: TraegerTestClient, connected_amqtt: Broker, http: aiointercept
) -> None:
    """Test connect and publish"""
    await asyncio.sleep(0.1)
    await client_connect(
        traeger_client.hass, traeger_client, api_user_self["resp"]["things"]
    )
    _LOGGER.warning("Wait for onConnect to Subscribe")
    await asyncio.sleep(0.2)
    traeger_client.mqtt_client.mqtt_client.publish(
        "prod/thing/update/0123456789ab", b"{}", qos=1
    )
    await asyncio.sleep(0.1)
    assert traeger_client.mqtt_client.grills_status["0123456789ab"] == {}
    await client_disconnect(traeger_client.hass, traeger_client)


@pytest.mark.usefixtures("socket_enabled")
async def test_connect_pub_unsubscribe(
    traeger_client: TraegerTestClient, connected_amqtt: Broker, http: aiointercept
) -> None:
    """Test connect and publish"""
    await asyncio.sleep(0.1)
    await client_connect(
        traeger_client.hass, traeger_client, api_user_self["resp"]["things"]
    )
    _LOGGER.warning("Wait for onConnect to Subscribe")
    await asyncio.sleep(0.2)
    traeger_client.mqtt_client.mqtt_client.publish(
            "prod/thing/update/0123456789ab", b"{}", qos=1
        )
    await asyncio.sleep(0.1)
    #traeger_client.mqtt_client.mqtt_client.unsubscribe("prod/thing/update/0123456789ab")
    await client_disconnect(traeger_client.hass, traeger_client)


@pytest.mark.usefixtures("socket_enabled")
async def test_connect_bad_pub(
    traeger_client: TraegerTestClient, connected_amqtt: Broker, http: aiointercept
) -> None:
    """Test connect and bad publish"""
    await client_connect(
        traeger_client.hass, traeger_client, api_user_self["resp"]["things"]
    )
    _LOGGER.warning("Wait for onConnect to Subscribe")
    await asyncio.sleep(0.2)
    traeger_client.mqtt_client.mqtt_client.publish(
        "prod/thing/update/0123456789ab", b"{}", qos=1
    )
    traeger_client.mqtt_client.mqtt_client.publish(
        "prod/thing/update/0123456789ab", b"{badjson}", qos=1
    )
    await asyncio.sleep(0.1)
    assert traeger_client.mqtt_client.grills_status.get("0123456789ab", {}) == {}
    await client_disconnect(traeger_client.hass, traeger_client)


@pytest.mark.usefixtures("socket_enabled")
async def test_connect_grillmsg(
    traeger_client: TraegerTestClient, connected_amqtt: Broker, http: aiointercept
) -> None:
    """Test connect and send grill mqtt msg"""
    await client_connect(
        traeger_client.hass, traeger_client, api_user_self["resp"]["things"]
    )
    _LOGGER.warning("Wait for onConnect to Subscribe")
    await asyncio.sleep(0, 1)
    traeger_client.mqtt_client.mqtt_client.publish(
        "prod/thing/update/0123456789ab", json.dumps(mqtt_msg).encode("utf-8"), qos=1
    )
    await asyncio.sleep(0.1)
    assert traeger_client.mqtt_client.grills_status.get("0123456789ab", {}) == mqtt_msg
    await client_disconnect(traeger_client.hass, traeger_client)


def test_handle_bad_topic(traeger_client: TraegerTestClient) -> None:
    """test handling MQTT messages."""
    message = MQTTMessage(topic=b"prod/thing/updb")
    message.payload = b"InvalidJSON"
    # Don't throw on this:
    traeger_client.mqtt_client.mqtt_onmessage(traeger_client.mqtt_client, None, message)
    assert traeger_client.mqtt_client.grills_status == {}


def test_handle_bad_message(traeger_client: TraegerTestClient) -> None:
    """test handling MQTT messages."""
    message = MQTTMessage(topic=b"prod/thing/update/0123456789ab")
    message.payload = b"InvalidJSON"
    # Don't throw on this:
    traeger_client.mqtt_client.mqtt_onmessage(traeger_client.mqtt_client, None, message)
    assert traeger_client.mqtt_client.grills_status == {}


def test_handle_good_topic_and_message(traeger_client: TraegerTestClient) -> None:
    """test handling MQTT messages."""
    message = MQTTMessage(topic=b"prod/thing/update/0123456789ab")
    message.payload = b'{"thingerName":"Johnys Grill"}'
    # Don't throw on this:
    traeger_client.mqtt_client.mqtt_onmessage(traeger_client.mqtt_client, None, message)
    assert traeger_client.mqtt_client.grills_status["0123456789ab"] == json.loads(
        message.payload
    )


@pytest.mark.usefixtures("socket_enabled")
async def test_kill_clears_isconnected_above_debug(
    traeger_client: TraegerTestClient, connected_amqtt: Broker, http: aiointercept
) -> None:
    """Disconnect must be tracked when the integration logs above DEBUG."""
    traeger_logger = logging.getLogger("custom_components.traeger")
    level = traeger_logger.level
    traeger_logger.setLevel(logging.WARNING)
    try:
        traeger_client.mqtt_client = TraegerMQTTClient(
            traeger_client.hass, traeger_client.sync_grill_callback
        )
    finally:
        traeger_logger.setLevel(level)
    traeger_client.grills = [{"thingName": "0123456789ab"}]
    await client_connect(
        traeger_client.hass, traeger_client, api_user_self["resp"]["things"]
    )
    assert traeger_client.mqtt_client.isconnected
    await asyncio.wait_for(traeger_client.kill(), timeout=3)
    assert not traeger_client.mqtt_client.isconnected


async def test_kill_bounded_when_disconnect_unconfirmed(
    traeger_client: TraegerTestClient, caplog: pytest.LogCaptureFixture
) -> None:
    """kill() must not hang if on_disconnect never fires."""
    traeger_client.mqtt_client.isconnected = True
    with patch.object(traeger_client.mqtt_client, "disconnect", AsyncMock()):
        await asyncio.wait_for(traeger_client.kill(), timeout=10)
    assert not traeger_client.mqtt_client.isconnected
    assert "Timed out waiting for MQTT disconnect" in caplog.text
