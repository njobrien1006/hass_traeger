"""Tests for the switch platform."""

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
        [{
            "entity_id": entry.entity_id,
            "unique_id": entry.unique_id,
            "translation_key": entry.translation_key,
            "device_class": entry.device_class,
            "original_name": entry.original_name,
        }
         for entry in registry.entities.values()
         if entry.config_entry_id == mock_config_entry.entry_id and
         entry.domain == "switch"],
        key=lambda entry: entry["entity_id"],
    )

    assert entries == snapshot


@pytest.mark.enable_socket
@pytest.mark.parametrize(
    "platform, entity_id",
    [
        ("switch", "0123456789ab_keepwarm"),
        ("switch", "0123456789ab_smoke"),
    ],
)
async def test_switch_cmds(
    platform,
    entity_id,
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
        if kwargs["json"]["command"] == "18":
            mqtt_msg_change["status"]["keepwarm"] = 1
            traeger_client.mqtt_client.mqtt_client.publish(
                "prod/thing/update/0123456789ab",
                json.dumps(mqtt_msg_change).encode("utf-8"),
                qos=1,
            )
            return CallbackResult(status=400, payload=None)
        if kwargs["json"]["command"] == "19":
            mqtt_msg_change["status"]["keepwarm"] = 0
            traeger_client.mqtt_client.mqtt_client.publish(
                "prod/thing/update/0123456789ab",
                json.dumps(mqtt_msg_change).encode("utf-8"),
                qos=1,
            )
            return CallbackResult(status=400, payload=None)
        if kwargs["json"]["command"] == "20":
            mqtt_msg_change["status"]["smoke"] = 1
            traeger_client.mqtt_client.mqtt_client.publish(
                "prod/thing/update/0123456789ab",
                json.dumps(mqtt_msg_change).encode("utf-8"),
                qos=1,
            )
            return CallbackResult(status=400, payload=None)
        if kwargs["json"]["command"] == "21":
            mqtt_msg_change["status"]["smoke"] = 0
            traeger_client.mqtt_client.mqtt_client.publish(
                "prod/thing/update/0123456789ab",
                json.dumps(mqtt_msg_change).encode("utf-8"),
                qos=1,
            )
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
    _LOGGER.error("Wait for onConnect to Subscribe")
    await asyncio.sleep(1)

    # Get Entity Trig Check
    entity = hass.states.get(f"{platform}.{entity_id}")
    # Check Enttity
    assert isinstance(entity, State)
    assert entity == snapshot

    # Put Grill in cook mode so we can expect the switch to be available.
    mqtt_msg_change = mqtt_msg
    mqtt_msg_change["status"]["system_status"] = 6
    traeger_client.mqtt_client.mqtt_client.publish(
        "prod/thing/update/0123456789ab",
        json.dumps(mqtt_msg_change).encode("utf-8"),
        qos=1,
    )
    await asyncio.sleep(0.1)
    await hass.services.async_call(
        "switch",
        SERVICE_TURN_ON,
        {ATTR_ENTITY_ID: f"{platform}.{entity_id}"},
        blocking=True,
    )
    await hass.async_block_till_done()
    await asyncio.sleep(0.1)

    # Get Entity Trig Check
    entity = hass.states.get(f"{platform}.{entity_id}")
    # Check Enttity
    assert entity == snapshot

    await asyncio.sleep(0.1)
    await hass.services.async_call(
        "switch",
        SERVICE_TURN_OFF,
        {ATTR_ENTITY_ID: f"{platform}.{entity_id}"},
        blocking=True,
    )
    await hass.async_block_till_done()
    await asyncio.sleep(0.1)

    # Get Entity Trig Check
    entity = hass.states.get(f"{platform}.{entity_id}")
    # Check Enttity
    assert entity == snapshot

    # Put Grill back out of cook mode to make unavailable.
    mqtt_msg_change = mqtt_msg
    mqtt_msg_change["status"]["system_status"] = 0
    traeger_client.mqtt_client.mqtt_client.publish(
        "prod/thing/update/0123456789ab",
        json.dumps(mqtt_msg_change).encode("utf-8"),
        qos=1,
    )
    await hass.async_block_till_done()
    await asyncio.sleep(0.1)

    # Get Entity Trig Check
    entity = hass.states.get(f"{platform}.{entity_id}")
    # Check Enttity
    assert entity == snapshot

    # Shut it down
    await asyncio.sleep(0.1)
    traeger_client.mqtt_client.disconnect()
    await asyncio.sleep(0.1)
    await mock_broker.shutdown()
    await asyncio.sleep(0.1)
