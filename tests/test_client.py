import random

import pytest
from homeassistant.core import HomeAssistant
from paho.mqtt.client import MQTTMessage

from .conftest import TraegerTestClient


class TestMessageParsing:

    def test_handle_messages(self, traeger_client: TraegerTestClient) -> None:
        message = MQTTMessage(topic=b"unknown")
        message.payload = b"whatever"
        # Don't throw on this:
        traeger_client.mqtt_client._mqtt_onmessage(traeger_client.mqtt_client, None, message)
        #traeger_client.hass.block_till_done()
        assert traeger_client.mqtt_client.grills_status['unkown'] == "whatever"

    async def test_parse_state(self, traeger_client: TraegerTestClient):
        traeger_client = traeger_client
        #await Traeger_client.apply_state_messages({"party": "1"})
        #Traeger_client.mqtt_client.grills_status['unkown'] == "whatever"
