"""Tests to check HA Logs."""

import asyncio
import json
import logging
import pytest

from aioresponses import CallbackResult
from homeassistant.core import HomeAssistant

from pytest_homeassistant_custom_component.common import MockConfigEntry
from syrupy.assertion import SnapshotAssertion

from custom_components.traeger.const import DOMAIN
from .conftest import Broker, aioresponses, MQTTPORT
from .zzMockResp import api_commands, api_user_self, mqtt_msg

_LOGGER: logging.Logger = logging.getLogger(__package__)

@pytest.mark.usefixtures("socket_enabled")
async def test_zz_ha_log(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    connected_amqtt: Broker,
    snapshot: SnapshotAssertion,
    http: aioresponses,
    caplog: pytest.LogCaptureFixture
) -> None:
    """Test HA Logs"""

    def callback(url, **kwargs):
        """Setup API Callbacks"""
        _LOGGER.warning("Was at callbacks %s - %s", url, kwargs["json"])
        mqtt_msg_change = mqtt_msg
        if kwargs["json"]["command"] == "90":
            traeger_client.mqtt_client.mqtt_client.publish(
                "prod/thing/update/0123456789ab",
                json.dumps(mqtt_msg_change).encode("utf-8"),
                qos=0,
            )
            return CallbackResult(status=400, payload=None)
        return CallbackResult(status=404, payload=None)

    # Register Callbacks
    http.post(api_commands["url"], callback=callback, repeat=True)
    http.post(api_commands["urlg2"], callback=callback, repeat=True)
    traeger_client = hass.data[DOMAIN][mock_config_entry.entry_id]
    await traeger_client.mqtt_client.connect(  #Need to connect
        api_user_self["resp"]["things"],
        "wss://127.0.0.1/mqtt?1391charsWORTHofCreds",
        False,
        MQTTPORT,
    )
    await asyncio.sleep(0.2)  #Sleep on it

    #Check a known log exists.
    assert any("Was at callbacks" in record.message for record in caplog.records)

    #Check if we have used any deprec items
    assert not any("Detected that custom integration 'traeger'" in record.message for record in caplog.records)

    #Shutdown MQTT
    await asyncio.sleep(0.1)
    traeger_client.mqtt_client.disconnect()
    await asyncio.sleep(0.1)
