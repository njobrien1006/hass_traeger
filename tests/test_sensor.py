"""Tests for the sensor platform."""

import asyncio
import json
import logging
import pytest

from aioresponses import CallbackResult
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant, State
from homeassistant.helpers import entity_registry
from homeassistant.helpers.entity_registry import EntityRegistry

from pytest_homeassistant_custom_component.common import MockConfigEntry
from syrupy.assertion import SnapshotAssertion

from custom_components.traeger.const import DOMAIN
from custom_components.traeger.sensor import SENSOR_ENTITIES
from .conftest import Broker, aioresponses, MQTTPORT
from .zzMockResp import api_commands, api_user_self, mqtt_msg

_LOGGER: logging.Logger = logging.getLogger(__package__)


#pylint: disable=unused-argument,too-many-arguments,too-many-positional-arguments
@pytest.mark.usefixtures("socket_enabled")
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


@pytest.mark.usefixtures("socket_enabled")
async def test_sensor_platform_asyncadd(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    connected_amqtt: Broker,
    snapshot: SnapshotAssertion,
    http: aioresponses,
) -> None:
    """Check async add for the post init additions"""

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
        "prod/thing/update/0123456789ab",
        json.dumps(mqtt_msg).encode("utf-8"),
        qos=1)
    await asyncio.sleep(0.1)
    assert traeger_client.mqtt_client.grills_status.get("0123456789ab",
                                                        {}) == mqtt_msg
    await asyncio.sleep(0.1)
    traeger_client.mqtt_client.disconnect()
    await asyncio.sleep(0.1)
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


@pytest.mark.usefixtures("socket_enabled")
@pytest.mark.parametrize(
    "platform, entity_id, friendly_name",
    [('sensor', '0123456789ab_ambient_temperature', 'Ambient Temperature'),
     ('sensor', '0123456789ab_cook_id', 'Cook ID'),
     ('sensor', '0123456789ab_cook_timer_end', 'Cook Timer End'),
     ('sensor', '0123456789ab_cook_timer_start', 'Cook Timer Start'),
     ('sensor', '0123456789ab_current_cycle', 'Current Cycle'),
     ('sensor', '0123456789ab_current_step', 'Current Step'),
     ('sensor', '0123456789ab_errors', 'Errors'),
     ('sensor', '0123456789ab_pellet_level', 'Pellet Level'),
     ('sensor', '0123456789ab_server_status', 'Server Status'),
     ('sensor', '0123456789ab_sys_timer_end', 'Sys Timer End'),
     ('sensor', '0123456789ab_sys_timer_start', 'Sys Timer Start'),
     ('sensor', '0123456789ab_grill_time', 'Grill Time'),
     ('sensor', '0123456789ab_auger_runtime', 'Auger Runtime'),
     ('sensor', '0123456789ab_fan_runtime', 'Fan Runtime'),
     ('sensor', '0123456789ab_cook_cycle', 'Cook Cycle'),
     ('sensor', '0123456789ab_ignite_fail_count', 'Ignite Fail Count'),
     ('sensor', '0123456789ab_overheat_count', 'Overheat Count'),
     ('sensor', '0123456789ab_lowtemp_count', 'Lowtemp Count'),
     ('sensor', '0123456789ab_state_index_count', 'State Index Count'),
     ('sensor', '0123456789ab_wifi_rssi', 'WifI RSSI'),
     ('sensor', '0123456789ab_wifi_ssid', 'WifI SSID')])
#pylint: disable=too-many-statements,redefined-outer-name
async def test_sensor(
    platform,
    entity_id,
    friendly_name,
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    entity_registry: EntityRegistry,
    connected_amqtt: Broker,
    snapshot: SnapshotAssertion,
    http: aioresponses,
) -> None:
    """Test Sensor"""
    mqtt_loca = SENSOR_ENTITIES[friendly_name]['json_loca']
    if SENSOR_ENTITIES[friendly_name].get('enabledbydflt', True) is False:
        # Enable the entity
        entity_registry.async_update_entity(f'{platform}.{entity_id}',
                                            disabled_by=None)
        hass.config_entries.async_schedule_reload(mock_config_entry.entry_id)
        await hass.async_block_till_done()
    if SENSOR_ENTITIES[friendly_name].get('entity_category',
                                          None) is EntityCategory.DIAGNOSTIC:
        # Enable the entity
        entity_registry.async_update_entity(f'{platform}.{entity_id}',
                                            entity_category=None)
        hass.config_entries.async_schedule_reload(mock_config_entry.entry_id)
        await hass.async_block_till_done()

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
    await traeger_client.mqtt_client.connect(  #Need to connect
        api_user_self["resp"]["things"],
        "wss://127.0.0.1/mqtt?1391charsWORTHofCreds",
        False,
        MQTTPORT,
    )
    await asyncio.sleep(0.2)  #Sleep on it

    #Get Entity Init Check
    entity = hass.states.get(f'{platform}.{entity_id}')
    #Check Entity
    assert isinstance(entity, State)
    assert entity == snapshot

    #Change Entity
    await asyncio.sleep(0.1)
    mqtt_msg_change = mqtt_msg
    mqtt_msg_change['status']['connected'] = True
    traeger_client.mqtt_client.mqtt_client.publish(  #The actual change
        "prod/thing/update/0123456789ab",
        json.dumps(mqtt_msg_change).encode("utf-8"),
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
