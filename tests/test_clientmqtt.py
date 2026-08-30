"""Test the Traeger Client."""

import asyncio
import json
import logging

import pytest
from aiointercept import aiointercept
from paho.mqtt.client import MQTTMessage

from .conftest import Broker, TraegerTestClient
from .zzCommon import client_connect, client_disconnect
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
