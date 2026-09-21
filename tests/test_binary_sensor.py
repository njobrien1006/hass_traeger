"""Tests for the binary sensor platform."""

import logging

import pytest
from aiointercept import aiointercept
from homeassistant.core import HomeAssistant, State
from homeassistant.helpers import entity_registry
from pytest_homeassistant_custom_component.common import MockConfigEntry
from syrupy.assertion import SnapshotAssertion

from custom_components.traeger.const import DOMAIN

from .zzcommon import CallbackAPI, client_connect, client_disconnect, client_publish
from .zzMockResp import api_user_self, mqtt_msg

_LOGGER: logging.Logger = logging.getLogger(__package__)


async def test_binary_sensor_platform(
    hass: HomeAssistant,
    mock_config_entry_mobile_app: MockConfigEntry,
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
            if entry.config_entry_id == mock_config_entry_mobile_app.entry_id
            and entry.domain == "binary_sensor"
        ],
        key=lambda entry: entry["entity_id"],
    )

    assert entries == snapshot


@pytest.mark.usefixtures("socket_enabled")
async def test_binary_sensor_platform_asyncadd(
    hass: HomeAssistant,
    mock_config_entry_mobile_app: MockConfigEntry,
    snapshot: SnapshotAssertion,
    http: aiointercept,
) -> None:
    """Check async add for the post init additions"""

    traeger_client = hass.data[DOMAIN][mock_config_entry_mobile_app.entry_id]
    CallbackAPI(traeger_client, http)
    await client_connect(hass, traeger_client, api_user_self["resp"]["things"])

    await client_publish(hass, traeger_client, mqtt_msg)
    assert traeger_client.mqtt_client.grills_status.get("0123456789ab", {}) == mqtt_msg
    await client_disconnect(hass, traeger_client)
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
            if entry.config_entry_id == mock_config_entry_mobile_app.entry_id
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
    mock_config_entry_mobile_app: MockConfigEntry,
    snapshot: SnapshotAssertion,
    http: aiointercept,
) -> None:
    """Test Binary Sensor"""
    # pylint: disable=too-many-arguments,too-many-positional-arguments
    traeger_client = hass.data[DOMAIN][mock_config_entry_mobile_app.entry_id]
    CallbackAPI(traeger_client, http)
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

    # Get Entity Ready Check
    entity = hass.states.get(f"{platform}.{entity_id}")
    # Check Enttity
    assert isinstance(entity, State)
    assert entity.state != "unavailable"
    assert entity == snapshot(name="02-ready")

    # Change Entity
    mqtt_msg_change = traeger_client.mqtt_client.grills_status["0123456789ab"]
    mqtt_msg_change["status"]["system_status"] = 6
    mqtt_msg_change["status"][mqtt_loca] = 1
    await client_publish(hass, traeger_client, mqtt_msg_change)

    # Get Entity Ready Check
    entity = hass.states.get(f"{platform}.{entity_id}")
    # Check Enttity
    assert isinstance(entity, State)
    assert entity.state != "unavailable"
    assert entity == snapshot(name="03-triggered")

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
