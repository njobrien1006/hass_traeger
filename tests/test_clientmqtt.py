"""Test the Traeger Client."""

import asyncio
import logging
import json
import pytest
from aioresponses import aioresponses
from paho.mqtt.client import MQTTMessage

from .conftest import TraegerTestClient, Broker, MQTTPORT
from .zzMockResp import api_user_self, mqtt_msg

_LOGGER: logging.Logger = logging.getLogger(__package__)
"""Test Traeger MQTT"""


#pylint: disable=unused-argument,too-many-arguments,too-many-positional-arguments
@pytest.mark.enable_socket
async def test_connect_pub(traeger_client: TraegerTestClient,
                           connected_amqtt: Broker, http: aioresponses) -> None:
    '''Test connect and publish'''
    await asyncio.sleep(0.1)
    await traeger_client.mqtt_client.connect(
        api_user_self["resp"]["things"],
        "wss://127.0.0.1/mqtt?1391charsWORTHofCreds",
        False,
        MQTTPORT,
    )
    _LOGGER.warning("Wait for onConnect to Subscribe")
    await asyncio.sleep(0.2)
    traeger_client.mqtt_client.mqtt_client.publish(
        "prod/thing/update/0123456789ab", b"{}", qos=1)
    await asyncio.sleep(0.1)
    assert traeger_client.mqtt_client.grills_status["0123456789ab"] == {}
    traeger_client.mqtt_client.disconnect()
    await asyncio.sleep(0.1)


@pytest.mark.enable_socket
async def test_connect_bad_pub(traeger_client: TraegerTestClient,
                               connected_amqtt: Broker,
                               http: aioresponses) -> None:
    '''Test connect and bad publish'''
    await asyncio.sleep(0.1)
    await traeger_client.mqtt_client.connect(
        api_user_self["resp"]["things"],
        "wss://127.0.0.1/mqtt?1391charsWORTHofCreds",
        False,
        MQTTPORT,
    )
    _LOGGER.warning("Wait for onConnect to Subscribe")
    await asyncio.sleep(0.2)
    traeger_client.mqtt_client.mqtt_client.publish(
        "prod/thing/update/0123456789ab", b"{badjson}", qos=1)
    await asyncio.sleep(0.1)
    assert traeger_client.mqtt_client.grills_status.get("0123456789ab",
                                                        {}) == {}
    await asyncio.sleep(0.1)
    traeger_client.mqtt_client.disconnect()
    await asyncio.sleep(0.1)


@pytest.mark.enable_socket
async def test_connect_grillmsg(traeger_client: TraegerTestClient,
                                connected_amqtt: Broker,
                                http: aioresponses) -> None:
    '''Test connect and send grill mqtt msg'''
    await asyncio.sleep(0.1)
    await traeger_client.mqtt_client.connect(
        api_user_self["resp"]["things"],
        "wss://127.0.0.1/mqtt?1391charsWORTHofCreds",
        False,
        MQTTPORT,
    )
    _LOGGER.warning("Wait for onConnect to Subscribe")
    await asyncio.sleep(0, 1)
    traeger_client.mqtt_client.mqtt_client.publish(
        "prod/thing/update/0123456789ab",
        json.dumps(mqtt_msg).encode("utf-8"),
        qos=1)
    await asyncio.sleep(0.1)
    assert traeger_client.mqtt_client.grills_status.get("0123456789ab",
                                                        {}) == mqtt_msg
    await asyncio.sleep(0.1)
    traeger_client.mqtt_client.disconnect()
    await asyncio.sleep(0.1)


def test_handle_bad_topic(traeger_client: TraegerTestClient) -> None:
    """test handling MQTT messages."""
    message = MQTTMessage(topic=b"prod/thing/updb")
    message.payload = b"InvalidJSON"
    # Don't throw on this:
    traeger_client.mqtt_client.mqtt_onmessage(traeger_client.mqtt_client, None,
                                              message)
    assert traeger_client.mqtt_client.grills_status == {}


def test_handle_bad_message(traeger_client: TraegerTestClient) -> None:
    """test handling MQTT messages."""
    message = MQTTMessage(topic=b"prod/thing/update/0123456789ab")
    message.payload = b"InvalidJSON"
    # Don't throw on this:
    traeger_client.mqtt_client.mqtt_onmessage(traeger_client.mqtt_client, None,
                                              message)
    assert traeger_client.mqtt_client.grills_status == {}


def test_handle_good_topic_and_message(
        traeger_client: TraegerTestClient) -> None:
    """test handling MQTT messages."""
    message = MQTTMessage(topic=b"prod/thing/update/0123456789ab")
    message.payload = b'{"thingerName":"Johnys Grill"}'
    # Don't throw on this:
    traeger_client.mqtt_client.mqtt_onmessage(traeger_client.mqtt_client, None,
                                              message)
    assert traeger_client.mqtt_client.grills_status[
        "0123456789ab"] == json.loads(message.payload)
