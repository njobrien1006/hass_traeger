"""Tests for the switch platform."""

import asyncio
import logging

import pytest
from aiointercept import aiointercept
from homeassistant.const import ATTR_ENTITY_ID, SERVICE_TURN_OFF, SERVICE_TURN_ON
from homeassistant.core import HomeAssistant, State
from homeassistant.helpers import entity_registry
from pytest_homeassistant_custom_component.common import MockConfigEntry
from syrupy.assertion import SnapshotAssertion

from custom_components.traeger.const import DOMAIN

from .zzcommon import CallbackAPI, client_connect, client_disconnect, client_publish
from .zzMockResp import api_user_self

_LOGGER: logging.Logger = logging.getLogger(__package__)


async def test_switch_platform(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    snapshot: SnapshotAssertion,
) -> None:
    """Test the switch platform setup."""
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
            and entry.domain == "switch"
        ],
        key=lambda entry: entry["entity_id"],
    )

    assert entries == snapshot


@pytest.mark.usefixtures("socket_enabled")
@pytest.mark.parametrize(
    "platform, entity_id",
    [
        ("switch", "traeger_0123456789ab_keepwarm"),
        ("switch", "traeger_0123456789ab_smoke"),
    ],
)
async def test_switch_cmds(
    platform,
    entity_id,
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    snapshot: SnapshotAssertion,
    http: aiointercept,
) -> None:
    """test switch cmds"""
    # pylint: disable=too-many-arguments,too-many-positional-arguments

    traeger_client = hass.data[DOMAIN][mock_config_entry.entry_id]
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
    mqtt_msg_change["status"]["connected"] = True
    await client_publish(hass, traeger_client, mqtt_msg_change)
    _LOGGER.error("Wait for onConnect to Subscribe")

    # Put Grill in cook mode so we can expect the switch to be available.
    mqtt_msg_change = traeger_client.mqtt_client.grills_status["0123456789ab"]
    mqtt_msg_change["status"]["system_status"] = 6
    await client_publish(hass, traeger_client, mqtt_msg_change)

    await hass.services.async_call(
        "switch",
        SERVICE_TURN_ON,
        {ATTR_ENTITY_ID: f"{platform}.{entity_id}"},
        blocking=True,
    )
    await hass.async_block_till_done()
    await asyncio.sleep(0.05)
    # Get Entity Trig Check
    entity = hass.states.get(f"{platform}.{entity_id}")
    # Check Enttity
    assert entity.state == "on"
    assert entity == snapshot(name=f"02-{entity.state}")

    await hass.services.async_call(
        "switch",
        SERVICE_TURN_OFF,
        {ATTR_ENTITY_ID: f"{platform}.{entity_id}"},
        blocking=True,
    )
    await hass.async_block_till_done()
    await asyncio.sleep(0.05)
    # Get Entity Trig Check
    entity = hass.states.get(f"{platform}.{entity_id}")
    # Check Enttity
    assert entity.state == "off"
    assert entity == snapshot(name=f"03-{entity.state}")

    # Put Grill back out of cook mode to make unavailable.
    mqtt_msg_change = traeger_client.mqtt_client.grills_status["0123456789ab"]
    mqtt_msg_change["status"]["system_status"] = 0
    await client_publish(hass, traeger_client, mqtt_msg_change)

    # Get Entity Trig Check
    entity = hass.states.get(f"{platform}.{entity_id}")
    # Check Enttity
    assert entity.state == "unavailable"
    assert entity == snapshot(name=f"04-{entity.state}")

    await client_disconnect(hass, traeger_client)
