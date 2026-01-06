"""Test the Traeger Client."""
# This is a WIP. Changes to come.
#import random

#import pytest
#from homeassistant.core import HomeAssistant
from paho.mqtt.client import MQTTMessage

from .conftest import TraegerTestClient


class TestMessageParsing:
    """Test Message Parsing"""

    def test_handle_messages(self, traeger_client: TraegerTestClient) -> None:
        """test handling MQTT messages."""
        message = MQTTMessage(topic=b"unknown")
        message.payload = b"whatever"
        # Don't throw on this:
        traeger_client.mqtt_client.mqtt_onmessage(traeger_client.mqtt_client,
                                                  None, message)
        #traeger_client.hass.block_till_done()
        assert traeger_client.mqtt_client.grills_status['unkown'] == "whatever"

    async def test_parse_state(self, traeger_client: TraegerTestClient):  # pylint: disable=unused-argument
        """test states"""
        assert True
        #await Traeger_client.apply_state_messages({"party": "1"})
        #Traeger_client.mqtt_client.grills_status['unkown'] == "whatever"
