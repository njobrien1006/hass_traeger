"""Common Test Functions"""

import asyncio
import json

# import logging
from .conftest import MQTTPORT

# _LOGGER: logging.Logger = logging.getLogger(__package__)


async def client_connect(hass, client, grill_list):
    """Connect to MQTT Client"""
    client.mqtt_client.ssl = False
    client.mqtt_client.port = MQTTPORT
    await client.mqtt_client.connect(
        grill_list,
        "wss://127.0.0.1/mqtt?1391charsWORTHofCreds",
    )
    await hass.async_block_till_done()
    await asyncio.sleep(0.1)


async def client_publish(hass, client, msg, dly=0.1):
    """Publish to MQTT Client"""
    await asyncio.sleep(dly / 2)
    client.mqtt_client.mqtt_client.publish(
        "prod/thing/update/0123456789ab",
        json.dumps(msg).encode("utf-8"),
        qos=0,
    )
    await hass.async_block_till_done()
    await asyncio.sleep(dly)


async def client_disconnect(hass, client):
    """Disconnect from MQTT Client"""
    await hass.async_block_till_done()
    await client.mqtt_client.disconnect()
    await hass.async_block_till_done()
    await asyncio.sleep(0.1)


async def redactnotidata(data):
    """Remove Android and IOS specfics from snapshots"""
    untracednotidata = ["clickAction", "url", "notification_icon_color", "color"]
    if "data" in data:
        for key in untracednotidata:
            data["data"].pop(key, None)
