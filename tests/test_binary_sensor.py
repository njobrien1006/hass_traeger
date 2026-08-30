"""Tests for the binary sensor platform."""

import asyncio
import copy
import json
import logging
import time

import pytest
from aiointercept import CallbackResult, aiointercept
from homeassistant.core import HomeAssistant, State
from homeassistant.helpers import entity_registry

from pytest_homeassistant_custom_component.common import MockConfigEntry
from syrupy.assertion import SnapshotAssertion

from custom_components.traeger.const import DOMAIN

from .conftest import Broker
from .zzCommon import client_connect, client_disconnect, client_publish
from .zzMockResp import api_commands, api_user_self, mqtt_msg

_LOGGER: logging.Logger = logging.getLogger(__package__)


# pylint: disable=unused-argument,too-many-arguments,too-many-positional-arguments
async def test_binary_sensor_platform(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    snapshot: SnapshotAssertion,
) -> None:
    """Test the binary sensor platform setup."""
    registry = entity_registry.async_get(hass)

    # Map registry entries to a simplified dict for the snapshot
    entries = sorted(
        [
            {
                "entity_id": entry.entity_id,
                "unique_id": entry.unique_id,
                "translation_key": entry.translation_key,
                "device_class": entry.device_class,
                "original_name": entry.original_name,
            }
            for entry in registry.entities.values()
            if entry.config_entry_id == mock_config_entry.entry_id
            and entry.domain == "binary_sensor"
        ],
        key=lambda entry: entry["entity_id"],
    )

    assert entries == snapshot


@pytest.mark.usefixtures("socket_enabled")
@pytest.mark.parametrize(
    "platform, entity_id, mqtt_loca",
    [
        (
            "binary_sensor",
            "traeger_0123456789ab_probe_alarm_fired",
            "probe_alarm_fired",
        ),
        (
            "binary_sensor",
            "traeger_0123456789ab_cook_timer_complete",
            "cook_timer_complete",
        ),
        (
            "binary_sensor",
            "traeger_0123456789ab_system_timer_complete",
            "sys_timer_complete",
        ),
    ],
)
async def test_binary_sensor_par(
    platform,
    entity_id,
    mqtt_loca,
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    connected_amqtt: Broker,
    snapshot: SnapshotAssertion,
    http: aiointercept,
) -> None:
    """Test Binary Sensor"""

    def callback(url, **kwargs):
        """Setup API Callbacks"""
        _LOGGER.warning("Was at callbacks %s - %s", url, kwargs["json"])
        mqtt_msg_change = copy.deepcopy(mqtt_msg)
        if kwargs["json"]["command"] == "90":
            traeger_client.mqtt_client.mqtt_client.publish(
                "prod/thing/update/0123456789ab",
                json.dumps(mqtt_msg_change).encode("utf-8"),
                qos=0,
            )
            return CallbackResult(status=200, payload=None)
        return CallbackResult(status=404, payload=None)

    # Register Callbacks
    http.post(api_commands["url"], callback=callback, repeat=True)
    http.post(api_commands["urlg2"], callback=callback, repeat=True)
    traeger_client = hass.data[DOMAIN][mock_config_entry.entry_id]
    await client_connect(hass, traeger_client, api_user_self["resp"]["things"])

    # Get Entity Init Check
    entity = hass.states.get(f"{platform}.{entity_id}")
    # Check Entity
    assert isinstance(entity, State)
    assert entity.state == "unavailable"
    assert entity == snapshot(name="01-init")

    # Change Entity
    mqtt_msg_change = traeger_client.mqtt_client.grills_status["0123456789ab"]
    mqtt_msg_change["status"]["system_status"] = 5
    mqtt_msg_change["status"]["connected"] = True
    await client_publish(hass, traeger_client, mqtt_msg_change)

    mqtt_msg_change = traeger_client.mqtt_client.grills_status["0123456789ab"]
    if "complete" in mqtt_loca:
        mqtt_msg_change["status"][mqtt_loca.replace("complete", "start")] = int(
            time.time()
        )
        mqtt_msg_change["status"][mqtt_loca.replace("complete", "end")] = (
            int(time.time()) + 60
        )

    await client_publish(hass, traeger_client, mqtt_msg_change)

    # Get Entity Ready Check
    entity = hass.states.get(f"{platform}.{entity_id}")
    # Check Enttity
    assert isinstance(entity, State)
    assert entity.state != "unavailable"
    assert entity == snapshot(name="02-ready")

    # Change Entity
    mqtt_msg_change = traeger_client.mqtt_client.grills_status["0123456789ab"]
    mqtt_msg_change["status"]["system_status"] = 7
    mqtt_msg_change["status"][mqtt_loca] = 1
    await client_publish(hass, traeger_client, mqtt_msg_change)

    # Get Entity Trig Check
    entity = hass.states.get(f"{platform}.{entity_id}")
    # Check Enttity
    assert isinstance(entity, State)
    assert entity.state != "unavailable"
    assert entity == snapshot(name="03-changed")

    # Change Entity
    mqtt_msg_change = traeger_client.mqtt_client.grills_status["0123456789ab"]
    mqtt_msg_change["status"]["connected"] = False
    await client_publish(hass, traeger_client, mqtt_msg_change)

    # Get Entity Offline
    entity = hass.states.get(f"{platform}.{entity_id}")
    # Check Enttity
    assert isinstance(entity, State)
    assert entity.state == "unavailable"
    assert entity == snapshot(name="04-not_connected")

    await client_disconnect(hass, traeger_client)
