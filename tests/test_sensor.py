"""Tests for the sensor platform."""

import asyncio
import json
import logging
import pytest

from aioresponses import CallbackResult
from homeassistant.core import HomeAssistant, State
from homeassistant.helpers import entity_registry

from homeassistant.const import ATTR_ENTITY_ID, SERVICE_TURN_ON, SERVICE_TURN_OFF

from pytest_homeassistant_custom_component.common import MockConfigEntry
from syrupy.assertion import SnapshotAssertion

from .conftest import Broker, aioresponses
from .zzMockResp import api_commands, api_token, api_mqtt, api_user_self, mqtt_msg
from custom_components.traeger.const import DOMAIN
from custom_components.traeger.sensor import SENSOR_ENTITIES

_LOGGER: logging.Logger = logging.getLogger(__package__)


@pytest.mark.enable_socket
async def test_sensor_platform(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    snapshot: SnapshotAssertion,
    http: aioresponses,
) -> None:
    """Test the sensor platform setup."""
    registry = entity_registry.async_get(hass)

    # Map registry entries to a simplified dict for the snapshot
    entries = sorted(
        [{
            "entity_id": entry.entity_id,
            "unique_id": entry.unique_id,
            "translation_key": entry.translation_key,
            "device_class": entry.device_class,
            "original_name": entry.original_name,
        }
         for entry in registry.entities.values()
         if entry.config_entry_id == mock_config_entry.entry_id and
         entry.domain == "sensor"],
        key=lambda entry: entry["entity_id"],
    )
    assert entries == snapshot


@pytest.mark.enable_socket
async def test_sensor_platform_asyncadd(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    mock_broker: Broker,
    snapshot: SnapshotAssertion,
    http: aioresponses,
) -> None:
    def callback(url, **kwargs):
        """Setup API Callbacks"""
        _LOGGER.error("Was at callbacks %s - %s", url, kwargs["json"])
        mqtt_msg_change = mqtt_msg
        if kwargs["json"]["command"] == "90":
            traeger_client.mqtt_client.mqtt_client.publish(
                "prod/thing/update/0123456789ab",
                json.dumps(mqtt_msg_change).encode("utf-8"),
                qos=1,
            )
            return CallbackResult(status=400, payload=None)
        return CallbackResult(status=404, payload=None)
    # Register Callbacks
    http.post(api_commands["url"], callback=callback, repeat=True)
    http.post(api_commands["urlg2"], callback=callback, repeat=True)
    traeger_client = hass.data[DOMAIN][mock_config_entry.entry_id]
    await mock_broker.start()
    traeger_client.mqtt_client.port = 4443
    await asyncio.sleep(0.1)
    await traeger_client.mqtt_client.connect(
        api_user_self["resp"]["things"],
        "wss://127.0.0.1/mqtt?1391charsWORTHofCreds",
        False,
    )
    _LOGGER.warning("Wait for onConnect to Subscribe")
    await asyncio.sleep(1)
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
    await mock_broker.shutdown()
    await asyncio.sleep(0.1)
    """Test the climate platform setup."""
    registry = entity_registry.async_get(hass)

    # Map registry entries to a simplified dict for the snapshot
    entries = sorted(
        [{
            "entity_id": entry.entity_id,
            "unique_id": entry.unique_id,
            "translation_key": entry.translation_key,
            "device_class": entry.device_class,
            "original_name": entry.original_name,
        }
         for entry in registry.entities.values()
         if entry.config_entry_id == mock_config_entry.entry_id and
         entry.domain == "sensor"],
        key=lambda entry: entry["entity_id"],
    )
    assert entries == snapshot


@pytest.mark.enable_socket
@pytest.mark.parametrize(
    "platform, entity_id, mqtt_loca",
    [('sensor', '0123456789ab_ambient_temperature',
      SENSOR_ENTITIES['Ambient Temperature']['json_loca'])])
async def test_sensor(
    platform,
    entity_id,
    mqtt_loca,
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    mock_broker: Broker,
    snapshot: SnapshotAssertion,
    http: aioresponses,
) -> None:
    """Test Sensor"""
    def callback(url, **kwargs):
        """Setup API Callbacks"""
        _LOGGER.error("Was at callbacks %s - %s", url, kwargs["json"])
        mqtt_msg_change = mqtt_msg
        if kwargs["json"]["command"] == "90":
            traeger_client.mqtt_client.mqtt_client.publish(
                "prod/thing/update/0123456789ab",
                json.dumps(mqtt_msg_change).encode("utf-8"),
                qos=1,
            )
            return CallbackResult(status=400, payload=None)
        return CallbackResult(status=404, payload=None)
    # Register Callbacks
    http.post(api_commands["url"], callback=callback, repeat=True)
    http.post(api_commands["urlg2"], callback=callback, repeat=True)
    traeger_client = hass.data[DOMAIN][mock_config_entry.entry_id]

    #Start Broker
    await mock_broker.start()
    traeger_client.mqtt_client.port = 4443
    await asyncio.sleep(0.1)

    #Get Entity Init Check
    entity = hass.states.get(f'{platform}.{entity_id}')

    #Check Entity
    assert isinstance(entity, State)
    assert entity == snapshot

    #Change Entity
    await asyncio.sleep(0.1)
    await traeger_client.mqtt_client.connect(  #Need to connect
        api_user_self["resp"]["things"],
        "wss://127.0.0.1/mqtt?1391charsWORTHofCreds",
        False,
    )
    await asyncio.sleep(1)  #Sleep on it
    traeger_client.mqtt_client.mqtt_client.publish(  #The actual change
        "prod/thing/update/0123456789ab",
        json.dumps(mqtt_msg).encode("utf-8"),
        qos=1)
    await asyncio.sleep(0.1)
    await hass.async_block_till_done()

    #Get Entity Happy Check
    entity = hass.states.get(f'{platform}.{entity_id}')
    #Check Enttity
    assert isinstance(entity, State)
    assert entity == snapshot

    #Change Entity
    await asyncio.sleep(0.1)
    mqtt_msg_change = mqtt_msg
    mqtt_loca_splt = mqtt_loca.split(";")
    if len(mqtt_loca_splt) == 3:
        mqtt_msg_change[mqtt_loca_splt[0]][mqtt_loca_splt[1]][
            mqtt_loca_splt[2]] = 33
    if len(mqtt_loca_splt) == 2:
        mqtt_msg_change[mqtt_loca_splt[0]][mqtt_loca_splt[1]] = 22
    if len(mqtt_loca_splt) == 1:
        mqtt_msg_change[mqtt_loca_splt[0]] = 11
    traeger_client.mqtt_client.mqtt_client.publish(  #The actual change
        "prod/thing/update/0123456789ab",
        json.dumps(mqtt_msg_change).encode("utf-8"),
        qos=1)
    await asyncio.sleep(0.1)
    await hass.async_block_till_done()

    #Get Entity Trig Check
    entity = hass.states.get(f'{platform}.{entity_id}')

    #Check Enttity
    assert isinstance(entity, State)
    assert entity == snapshot

    #Change Entity
    await asyncio.sleep(0.1)
    mqtt_msg_change = mqtt_msg
    mqtt_msg_change['status']['connected'] = False
    traeger_client.mqtt_client.mqtt_client.publish(  #The actual change
        "prod/thing/update/0123456789ab",
        json.dumps(mqtt_msg_change).encode("utf-8"),
        qos=1)
    await asyncio.sleep(0.1)
    await hass.async_block_till_done()

    #Get Entity Offline
    entity = hass.states.get(f'{platform}.{entity_id}')

    #Check Enttity
    assert isinstance(entity, State)
    assert entity == snapshot

    #Shutdown MQTT
    await asyncio.sleep(0.1)
    traeger_client.mqtt_client.disconnect()
    await asyncio.sleep(0.1)
    await mock_broker.shutdown()
    await asyncio.sleep(0.1)
