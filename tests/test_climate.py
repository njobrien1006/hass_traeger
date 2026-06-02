"""Tests for the climate platform."""

import asyncio
import json
import logging
import pytest

from aioresponses import CallbackResult
from homeassistant.core import HomeAssistant, State
from homeassistant.helpers import entity_registry

from pytest_homeassistant_custom_component.common import MockConfigEntry
from syrupy.assertion import SnapshotAssertion

from custom_components.traeger.const import DOMAIN, GRILL_MODE_COOL_DOWN
from .conftest import Broker, aioresponses, MQTTPORT
from .zzMockResp import api_commands, api_user_self, mqtt_msg

_LOGGER: logging.Logger = logging.getLogger(__package__)


# pylint: disable=unused-argument,too-many-arguments,too-many-positional-arguments
async def test_climate_platform(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    snapshot: SnapshotAssertion,
) -> None:
    """Test the climate platform setup."""
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
            and entry.domain == "climate"
        ],
        key=lambda entry: entry["entity_id"],
    )

    assert entries == snapshot


@pytest.mark.usefixtures("socket_enabled")
async def test_climate_platform_asyncadd(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    connected_amqtt: Broker,
    snapshot: SnapshotAssertion,
    http: aioresponses,
) -> None:
    """Check async add for the post init additions"""

    def callback(url, **kwargs):
        """Setup API Callbacks"""
        _LOGGER.warning("Was at callbacks %s - %s", url, kwargs["json"])
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
    await traeger_client.mqtt_client.connect(  # Need to connect
        api_user_self["resp"]["things"],
        "wss://127.0.0.1/mqtt?1391charsWORTHofCreds",
        False,
        MQTTPORT,
    )
    await asyncio.sleep(0.2)  # Sleep on it

    assert traeger_client.mqtt_client.grills_status.get("0123456789ab", {}) == mqtt_msg

    traeger_client.mqtt_client.disconnect()
    await asyncio.sleep(0.1)
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
            and entry.domain == "climate"
        ],
        key=lambda entry: entry["entity_id"],
    )

    assert entries == snapshot


@pytest.mark.usefixtures("socket_enabled")
@pytest.mark.parametrize(
    "platform, entity_id",
    [("climate", "traeger_0123456789ab_climate")],
)
# pylint: disable=too-many-statements
async def test_climate_setgrilltemp_cmd(
    platform,
    entity_id,
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    connected_amqtt: Broker,
    snapshot: SnapshotAssertion,
    http: aioresponses,
) -> None:
    """test climate cmds"""

    def callback(url, **kwargs):
        """Setup API Callbacks"""
        _LOGGER.warning("Was at callbacks %s - %s", url, kwargs["json"])
        if traeger_client.mqtt_client.grills_status == {}:
            mqtt_msg_change = mqtt_msg
        else:
            mqtt_msg_change = traeger_client.mqtt_client.grills_status["0123456789ab"]
        cmdsplit = kwargs["json"]["command"].split(",")
        if cmdsplit[0] == "11":
            mqtt_msg_change["status"]["set"] = int(cmdsplit[1])
            traeger_client.mqtt_client.mqtt_client.publish(
                "prod/thing/update/0123456789ab",
                json.dumps(mqtt_msg_change).encode("utf-8"),
                qos=1,
            )
            return CallbackResult(status=400, payload=None)
        if kwargs["json"]["command"] == "17":
            mqtt_msg_change["status"]["system_status"] = GRILL_MODE_COOL_DOWN
            traeger_client.mqtt_client.mqtt_client.publish(
                "prod/thing/update/0123456789ab",
                json.dumps(mqtt_msg_change).encode("utf-8"),
                qos=1,
            )
            return CallbackResult(status=400, payload=None)
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
    await traeger_client.mqtt_client.connect(  # Need to connect
        api_user_self["resp"]["things"],
        "wss://127.0.0.1/mqtt?1391charsWORTHofCreds",
        False,
        MQTTPORT,
    )
    await asyncio.sleep(0.2)  # Sleep on it

    # Get Entity Init Check
    entity = hass.states.get(f"{platform}.{entity_id}")
    # Check Entity
    assert isinstance(entity, State)
    assert entity.state == "unavailable"
    assert entity == snapshot(name="01-init")

    # Change Entity
    await asyncio.sleep(0.1)
    mqtt_msg_change = mqtt_msg
    mqtt_msg_change["status"]["connected"] = True
    traeger_client.mqtt_client.mqtt_client.publish(  # The actual change
        "prod/thing/update/0123456789ab",
        json.dumps(mqtt_msg_change).encode("utf-8"),
        qos=1,
    )
    _LOGGER.error("Wait for onConnect to Subscribe")
    await asyncio.sleep(0.2)
    # Put Grill in cook mode so we can expect the switch to be available.
    mqtt_msg_change = mqtt_msg
    mqtt_msg_change["status"]["system_status"] = 6
    mqtt_msg_change["limits"]["max_grill_temp"] = 0
    traeger_client.mqtt_client.mqtt_client.publish(
        "prod/thing/update/0123456789ab",
        json.dumps(mqtt_msg_change).encode("utf-8"),
        qos=1,
    )
    await asyncio.sleep(0.1)
    await hass.async_block_till_done()
    # Get Entity Happy Check
    entity = hass.states.get(f"{platform}.{entity_id}")
    # Check Enttity
    assert isinstance(entity, State)
    assert entity.state != "unavailable"
    assert entity.attributes.get("min_temp") < entity.attributes.get("max_temp")
    assert entity == snapshot(name="02-ready")

    await hass.services.async_call(
        "climate",
        "SET_TEMPERATURE",
        {
            "entity_id": f"{platform}.{entity_id}",
            "temperature": 170,
        },
        blocking=True,
    )
    await hass.async_block_till_done()
    await asyncio.sleep(0.1)
    # Get Entity Trig Check
    entity = hass.states.get(f"{platform}.{entity_id}")
    # Check Enttity
    assert entity.state != "unavailable"
    assert entity == snapshot(name="03-changed")

    await asyncio.sleep(0.1)
    await hass.services.async_call(
        "climate",
        "SET_TEMPERATURE",
        {
            "entity_id": f"{platform}.{entity_id}",
            "temperature": 495,
        },
        blocking=True,
    )
    await hass.async_block_till_done()
    await asyncio.sleep(0.1)
    # Get Entity Trig Check
    entity = hass.states.get(f"{platform}.{entity_id}")
    # Check Enttity
    assert entity.state != "unavailable"
    assert entity == snapshot(name="04-changed2")

    await asyncio.sleep(0.1)
    await hass.services.async_call(
        "climate",
        "set_hvac_mode",
        {
            "entity_id": f"{platform}.{entity_id}",
            "hvac_mode": "cool",
        },
        blocking=True,
    )
    await hass.async_block_till_done()
    await asyncio.sleep(0.1)
    # Get Entity Trig Check
    entity = hass.states.get(f"{platform}.{entity_id}")
    # Check Enttity
    assert entity.state != "unavailable"
    assert entity == snapshot(name="05-cool")

    # Put Grill back out of cook mode to make unavailable.
    mqtt_msg_change = mqtt_msg
    mqtt_msg_change["limits"]["max_grill_temp"] = 500
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
    assert entity.state == "off"
    assert entity == snapshot(name="06-off")

    # Change Entity
    await asyncio.sleep(0.1)
    mqtt_msg_change = mqtt_msg
    mqtt_msg_change["status"]["connected"] = False
    traeger_client.mqtt_client.mqtt_client.publish(  # The actual change
        "prod/thing/update/0123456789ab",
        json.dumps(mqtt_msg_change).encode("utf-8"),
        qos=1,
    )
    await asyncio.sleep(0.1)
    await hass.async_block_till_done()
    # Get Entity Offline
    entity = hass.states.get(f"{platform}.{entity_id}")
    # Check Enttity
    assert isinstance(entity, State)
    assert entity.state == "unavailable"
    assert entity == snapshot(name="07-not_connected")

    # Shut it down
    await asyncio.sleep(0.1)
    traeger_client.mqtt_client.disconnect()
    await asyncio.sleep(0.1)


@pytest.mark.usefixtures("socket_enabled")
@pytest.mark.parametrize(
    "mqtt_msg_acc",
    mqtt_msg["status"]["acc"],
)
# pylint: disable=too-many-statements
async def test_climate_setprobetemp_cmds(
    mqtt_msg_acc,
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    connected_amqtt: Broker,
    snapshot: SnapshotAssertion,
    http: aioresponses,
) -> None:
    """test climate cmds"""
    platform = "climate"
    entity_id = f"0123456789ab_probe_{mqtt_msg_acc['uuid']}"
    acc_indx = 0
    for acc in mqtt_msg["status"]["acc"]:
        if acc["uuid"] == mqtt_msg_acc["uuid"]:
            break
        acc_indx += 1

    def callback(url, **kwargs):
        """Setup API Callbacks"""
        _LOGGER.warning("Was at callbacks %s - %s", url, kwargs["json"])
        if traeger_client.mqtt_client.grills_status == {}:
            mqtt_msg_change = mqtt_msg
        else:
            mqtt_msg_change = traeger_client.mqtt_client.grills_status["0123456789ab"]
        cmdsplit = kwargs["json"]["command"].split(",")
        if cmdsplit[0] == "14":
            mqtt_msg_change["status"]["acc"][acc_indx][acc["type"]]["set_temp"] = int(
                cmdsplit[1]
            )
            mqtt_msg_change["status"]["acc"][acc_indx][acc["type"]]["get_temp"] = (
                int(cmdsplit[1]) / 2
            )
            traeger_client.mqtt_client.mqtt_client.publish(
                "prod/thing/update/0123456789ab",
                json.dumps(mqtt_msg_change).encode("utf-8"),
                qos=1,
            )
            return CallbackResult(status=400, payload=None)
        if cmdsplit[0] == "120" and len(cmdsplit) == 4:
            # "command": "120,10,p0,120"
            acc_indx120 = 0
            for acc120 in mqtt_msg["status"]["acc"]:
                if acc120["uuid"] == cmdsplit[2]:
                    break
                acc_indx120 += 1
            mqtt_msg_change["status"]["acc"][acc_indx120][acc120["type"]][
                "set_temp"
            ] = int(cmdsplit[1])
            mqtt_msg_change["status"]["acc"][acc_indx120][acc120["type"]][
                "get_temp"
            ] = int(cmdsplit[1]) / 2
            traeger_client.mqtt_client.mqtt_client.publish(
                "prod/thing/update/0123456789ab",
                json.dumps(mqtt_msg_change).encode("utf-8"),
                qos=1,
            )
            return CallbackResult(status=400, payload=None)
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
    await traeger_client.mqtt_client.connect(  # Need to connect
        api_user_self["resp"]["things"],
        "wss://127.0.0.1/mqtt?1391charsWORTHofCreds",
        False,
        MQTTPORT,
    )
    await asyncio.sleep(0.2)  # Sleep on it

    # Get Entity Init Check
    entity = hass.states.get(f"{platform}.{entity_id}")
    # Check Entity
    assert isinstance(entity, State)
    assert entity.state == "unavailable"
    assert entity == snapshot(name="01-init")

    # Change Entity
    await asyncio.sleep(0.1)
    mqtt_msg_change = mqtt_msg
    mqtt_msg_change["status"]["connected"] = True
    traeger_client.mqtt_client.mqtt_client.publish(  # The actual change
        "prod/thing/update/0123456789ab",
        json.dumps(mqtt_msg_change).encode("utf-8"),
        qos=1,
    )
    _LOGGER.error("Wait for onConnect to Subscribe")
    await hass.async_block_till_done()
    await asyncio.sleep(0.2)
    # Get Entity Happy Check
    entity = hass.states.get(f"{platform}.{entity_id}")
    # Check Enttity
    assert isinstance(entity, State)
    assert entity.state != "unavailable"
    assert entity.attributes.get("min_temp") < entity.attributes.get("max_temp")
    assert entity == snapshot(name="02-ready")

    await hass.services.async_call(
        "climate",
        "SET_TEMPERATURE",
        {
            "entity_id": f"{platform}.{entity_id}",
            "temperature": 170,
        },
        blocking=True,
    )
    await hass.async_block_till_done()
    await asyncio.sleep(0.1)
    # Get Entity Trig Check
    entity = hass.states.get(f"{platform}.{entity_id}")
    # Check Enttity
    assert entity.state != "unavailable"
    assert entity == snapshot(name="03-changed")

    await asyncio.sleep(0.1)
    await hass.services.async_call(
        "climate",
        "SET_TEMPERATURE",
        {
            "entity_id": f"{platform}.{entity_id}",
            "temperature": 180,
        },
        blocking=True,
    )
    await hass.async_block_till_done()
    await asyncio.sleep(0.1)
    # Get Entity Trig Check
    entity = hass.states.get(f"{platform}.{entity_id}")
    # Check Enttity
    assert entity.state != "unavailable"
    assert entity == snapshot(name="04-changed2")

    await asyncio.sleep(0.1)

    # Change Entity
    await asyncio.sleep(0.1)
    mqtt_msg_change = mqtt_msg
    mqtt_msg_change["status"]["connected"] = False
    traeger_client.mqtt_client.mqtt_client.publish(  # The actual change
        "prod/thing/update/0123456789ab",
        json.dumps(mqtt_msg_change).encode("utf-8"),
        qos=1,
    )
    await asyncio.sleep(0.1)
    await hass.async_block_till_done()
    # Get Entity Offline
    entity = hass.states.get(f"{platform}.{entity_id}")
    # Check Enttity
    assert isinstance(entity, State)
    assert entity.state == "unavailable"
    assert entity == snapshot(name="05-not_connected")

    # Shut it down
    await asyncio.sleep(0.1)
    traeger_client.mqtt_client.disconnect()
    await asyncio.sleep(0.1)
