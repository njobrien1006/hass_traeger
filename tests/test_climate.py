"""Tests for the climate platform."""

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


async def test_climate_platform(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    snapshot: SnapshotAssertion,
) -> None:
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
         entry.domain == "climate"],
        key=lambda entry: entry["entity_id"],
    )

    assert entries == snapshot


@pytest.mark.enable_socket
async def test_climate_platform_asyncadd(
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
         entry.domain == "climate"],
        key=lambda entry: entry["entity_id"],
    )

    assert entries == snapshot
