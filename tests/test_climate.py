"""Tests for the climate platform."""

import asyncio
import copy
import json
import logging
import pytest

from aiointercept import aiointercept, CallbackResult
from homeassistant.core import HomeAssistant, State
from homeassistant.const import UnitOfTemperature
from homeassistant.helpers import entity_registry
from homeassistant.util.unit_system import US_CUSTOMARY_SYSTEM, METRIC_SYSTEM

from pytest_homeassistant_custom_component.common import MockConfigEntry
from syrupy.assertion import SnapshotAssertion

from custom_components.traeger.const import (
    DOMAIN,
    GRILL_MODE_COOL_DOWN,
    PROBE_PRESET_MODES,
)
from .conftest import Broker, MQTTPORT
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
    http: aiointercept,
) -> None:
    """Check async add for the post init additions"""

    def callback(url, **kwargs):
        """Setup API Callbacks"""
        _LOGGER.warning("Was at callbacks %s - %s", url, kwargs["json"])
        mqtt_msg_change = copy.deepcopy(mqtt_msg)
        if kwargs["json"]["command"] == "90":
            traeger_client.mqtt_client.mqtt_client.publish(
                "prod/thing/update/0123456789ab",
                json.dumps(mqtt_msg_change).encode("utf-8"),
                qos=1,
            )
            return CallbackResult(status=200, payload=None)
        return CallbackResult(status=404, payload=None)

    # Register Callbacks
    http.post(api_commands["url"], callback=callback, repeat=True)
    http.post(api_commands["urlg2"], callback=callback, repeat=True)
    traeger_client = hass.data[DOMAIN][mock_config_entry.entry_id]
    traeger_client.mqtt_client.ssl = False
    traeger_client.mqtt_client.port = MQTTPORT
    await traeger_client.mqtt_client.connect(  # Need to connect
        api_user_self["resp"]["things"],
        "wss://127.0.0.1/mqtt?1391charsWORTHofCreds",
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
    "platform, entity_id, unit",
    [
        ("climate", "traeger_0123456789ab_climate", "F"),
        ("climate", "traeger_0123456789ab_climate", "C"),
    ],
)
# pylint: disable=too-many-statements
async def test_climate_setgrilltemp_cmd(
    platform,
    entity_id,
    unit,
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    connected_amqtt: Broker,
    snapshot: SnapshotAssertion,
    http: aiointercept,
) -> None:
    """test climate cmds"""
    if unit == "F":
        mqtt_msg["status"]["units"] = 1
        hass.config.units = US_CUSTOMARY_SYSTEM
    elif unit == "C":
        mqtt_msg["status"]["units"] = 0
        hass.config.units = METRIC_SYSTEM

    def callback(url, **kwargs):
        """Setup API Callbacks"""
        _LOGGER.warning("Was at callbacks %s - %s", url, kwargs["json"])
        if traeger_client.mqtt_client.grills_status == {}:
            mqtt_msg_change = copy.deepcopy(mqtt_msg)
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
            return CallbackResult(status=200, payload=None)
        if kwargs["json"]["command"] == "17":
            mqtt_msg_change["status"]["system_status"] = GRILL_MODE_COOL_DOWN
            traeger_client.mqtt_client.mqtt_client.publish(
                "prod/thing/update/0123456789ab",
                json.dumps(mqtt_msg_change).encode("utf-8"),
                qos=1,
            )
            return CallbackResult(status=200, payload=None)
        if kwargs["json"]["command"] == "90":
            traeger_client.mqtt_client.mqtt_client.publish(
                "prod/thing/update/0123456789ab",
                json.dumps(mqtt_msg_change).encode("utf-8"),
                qos=1,
            )
            return CallbackResult(status=200, payload=None)
        return CallbackResult(status=404, payload=None)

    # Register Callbacks
    http.post(api_commands["url"], callback=callback, repeat=True)
    http.post(api_commands["urlg2"], callback=callback, repeat=True)
    traeger_client = hass.data[DOMAIN][mock_config_entry.entry_id]
    traeger_client.mqtt_client.ssl = False
    traeger_client.mqtt_client.port = MQTTPORT
    await traeger_client.mqtt_client.connect(  # Need to connect
        api_user_self["resp"]["things"],
        "wss://127.0.0.1/mqtt?1391charsWORTHofCreds",
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
    mqtt_msg_change = traeger_client.mqtt_client.grills_status["0123456789ab"]
    mqtt_msg_change["status"]["connected"] = True
    traeger_client.mqtt_client.mqtt_client.publish(  # The actual change
        "prod/thing/update/0123456789ab",
        json.dumps(mqtt_msg_change).encode("utf-8"),
        qos=1,
    )
    _LOGGER.error("Wait for onConnect to Subscribe")
    await asyncio.sleep(0.2)

    snapshotname = 2
    for system_status in [2, 3, 4, 5, 6, 7, 9, 2, 99]:
        mqtt_msg_change = traeger_client.mqtt_client.grills_status["0123456789ab"]
        mqtt_msg_change["status"]["system_status"] = system_status
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
        assert entity == snapshot(
            name=f"{snapshotname:02d}-system_status({system_status})"
        )
        snapshotname += 1

    # Change Before Ready for expected `NotImplementedError`
    with pytest.raises(NotImplementedError):
        await hass.services.async_call(
            "climate",
            "SET_TEMPERATURE",
            {
                "entity_id": f"{platform}.{entity_id}",
                "temperature": 255,
            },
            blocking=True,
        )
        await hass.async_block_till_done()
        await asyncio.sleep(0.1)

    # Change Before Ready for expected `NotImplementedError`
    with pytest.raises(NotImplementedError):
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

    # Put Grill in cook mode so we can expect the switch to be available.
    mqtt_msg_change = traeger_client.mqtt_client.grills_status["0123456789ab"]
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
    assert entity == snapshot(name=f"{snapshotname:02d}-ready")
    snapshotname += 1

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
    assert entity == snapshot(name=f"{snapshotname:02d}-changed")
    snapshotname += 1

    await asyncio.sleep(0.1)
    await hass.services.async_call(
        "climate",
        "SET_TEMPERATURE",
        {
            "entity_id": f"{platform}.{entity_id}",
            "temperature": 255,
        },
        blocking=True,
    )
    await hass.async_block_till_done()
    await asyncio.sleep(0.1)
    # Get Entity Trig Check
    entity = hass.states.get(f"{platform}.{entity_id}")
    # Check Enttity
    assert entity.state != "unavailable"
    assert entity == snapshot(name=f"{snapshotname:02d}-changed2")
    snapshotname += 1

    # Climate Sensor States
    for item in [
        {"sts": 5, "grill": 180, "set": 255, "rslt": "heating"},
        {"sts": 6, "grill": 255, "set": 255, "rslt": "at_temp"},
        {"sts": 6, "grill": 280, "set": 255, "rslt": "over_temp"},
        {"sts": 6, "grill": 265, "set": 255, "rslt": "at_temp"},
        {"sts": 6, "grill": 230, "set": 255, "rslt": "under_temp"},
        {"sts": 6, "grill": 245, "set": 255, "rslt": "at_temp"},
        {"sts": 6, "grill": 255, "set": 255, "rslt": "at_temp"},
        {"sts": 6, "grill": 255, "set": 295, "rslt": "heating"},
        {"sts": 6, "grill": 295, "set": 295, "rslt": "at_temp"},
        {"sts": 6, "grill": 295, "set": 255, "rslt": "cooling"},
        {"sts": 6, "grill": 255, "set": 255, "rslt": "at_temp"},
    ]:
        # Climate Sensor Preheat..heating
        _LOGGER.error("doing sensor step: %s", item)
        await asyncio.sleep(0.1)
        mqtt_msg_change = traeger_client.mqtt_client.grills_status["0123456789ab"]
        mqtt_msg_change["status"]["system_status"] = item["sts"]
        mqtt_msg_change["status"]["grill"] = item["grill"]
        mqtt_msg_change["status"]["set"] = item["set"]
        traeger_client.mqtt_client.mqtt_client.publish(  # The actual change
            "prod/thing/update/0123456789ab",
            json.dumps(mqtt_msg_change).encode("utf-8"),
            qos=1,
        )
        await asyncio.sleep(0.1)
        entity = hass.states.get("sensor.traeger_0123456789ab_heating_state")
        # Check Enttity
        assert entity.state == item["rslt"]

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
    assert entity == snapshot(name=f"{snapshotname:02d}-cool")
    snapshotname += 1

    # Put Grill back out of cook mode to make unavailable.
    mqtt_msg_change = traeger_client.mqtt_client.grills_status["0123456789ab"]
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
    mqtt_msg_change = traeger_client.mqtt_client.grills_status["0123456789ab"]
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
    assert entity == snapshot(name=f"{snapshotname:02d}-not_connected")
    snapshotname += 1

    # Shut it down
    await asyncio.sleep(0.1)
    traeger_client.mqtt_client.disconnect()
    await asyncio.sleep(0.1)

    if unit == "C":
        mqtt_msg["status"]["units"] = 1
        hass.config.units = US_CUSTOMARY_SYSTEM


@pytest.mark.usefixtures("socket_enabled")
@pytest.mark.parametrize(
    "mqtt_msg_acc",
    mqtt_msg["status"]["acc"],
)
# pylint: disable=too-many-statements,too-many-locals
async def test_climate_setprobetemp_cmds(
    mqtt_msg_acc,
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    connected_amqtt: Broker,
    snapshot: SnapshotAssertion,
    http: aiointercept,
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
            mqtt_msg_change = copy.deepcopy(mqtt_msg)
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
            return CallbackResult(status=200, payload=None)
        if cmdsplit[0] == "120" and len(cmdsplit) == 4:
            # "command": "120,10,p0,120"
            acc_indx120 = 0
            acc120 = {}
            for acc120 in mqtt_msg_change["status"]["acc"]:
                if acc120["uuid"] == cmdsplit[2]:
                    break
                acc_indx120 += 1
            mqtt_msg_change["status"]["acc"][acc_indx120][acc120["type"]][
                "set_temp"
            ] = int(cmdsplit[3])
            mqtt_msg_change["status"]["acc"][acc_indx120][acc120["type"]][
                "get_temp"
            ] = int(cmdsplit[3]) / 2
            traeger_client.mqtt_client.mqtt_client.publish(
                "prod/thing/update/0123456789ab",
                json.dumps(mqtt_msg_change).encode("utf-8"),
                qos=1,
            )
            return CallbackResult(status=200, payload=None)
        if kwargs["json"]["command"] == "90":
            traeger_client.mqtt_client.mqtt_client.publish(
                "prod/thing/update/0123456789ab",
                json.dumps(mqtt_msg_change).encode("utf-8"),
                qos=1,
            )
            return CallbackResult(status=200, payload=None)
        return CallbackResult(status=404, payload=None)

    # Register Callbacks
    http.post(api_commands["url"], callback=callback, repeat=True)
    http.post(api_commands["urlg2"], callback=callback, repeat=True)
    traeger_client = hass.data[DOMAIN][mock_config_entry.entry_id]
    traeger_client.mqtt_client.ssl = False
    traeger_client.mqtt_client.port = MQTTPORT
    await traeger_client.mqtt_client.connect(  # Need to connect
        api_user_self["resp"]["things"],
        "wss://127.0.0.1/mqtt?1391charsWORTHofCreds",
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
    mqtt_msg_change = traeger_client.mqtt_client.grills_status["0123456789ab"]
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
            "temperature": 95,
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
            "temperature": 100,
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

    # Attempt turning Switching States
    for item in ["off", "cool", "heat"]:
        await asyncio.sleep(0.1)
        try:
            await hass.services.async_call(
                "climate",
                "set_hvac_mode",
                {
                    "entity_id": f"{platform}.{entity_id}",
                    "hvac_mode": item,
                },
                blocking=True,
            )
            await hass.async_block_till_done()
            assert False
        except NotImplementedError as exception:
            _LOGGER.info("This succesfully failed - %s", exception)
            assert True
        except Exception as exception:  # pylint: disable=broad-except
            _LOGGER.error("This should be failing - %s", exception)
            assert False
        await asyncio.sleep(0.1)

    # Run Through Presets
    for item in PROBE_PRESET_MODES:  # pylint: disable=consider-using-dict-items
        await asyncio.sleep(0.05)
        await hass.services.async_call(
            "climate",
            "set_preset_mode",
            {
                "entity_id": f"{platform}.{entity_id}",
                "preset_mode": item,
            },
            blocking=True,
        )
        await hass.async_block_till_done()
        await asyncio.sleep(0.05)
        entity = hass.states.get(f"{platform}.{entity_id}")
        # Check Enttity
        # if unit == "F":
        assert (
            entity.attributes.get("temperature")
            == PROBE_PRESET_MODES[item][UnitOfTemperature.FAHRENHEIT]
        )
        # else:
        #    assert entity.state == PROBE_PRESET_MODES[mode][UnitOfTemperature.CELSIUS]

    # Indi Probe Alarm Fired (per acc)
    await asyncio.sleep(0.1)
    mqtt_msg_change = traeger_client.mqtt_client.grills_status["0123456789ab"]
    for item in mqtt_msg_change["status"]["acc"]:
        item[item["type"]]["alarm_fired"] = 1
    traeger_client.mqtt_client.mqtt_client.publish(  # The actual change
        "prod/thing/update/0123456789ab",
        json.dumps(mqtt_msg_change).encode("utf-8"),
        qos=1,
    )
    await asyncio.sleep(0.1)
    entity = hass.states.get(f"sensor.0123456789ab_probe_state_{mqtt_msg_acc['uuid']}")
    # Check Enttity
    # if unit == "F":
    assert entity.state == "at_temp"

    # Prove Over Temp ALM (per acc)
    await asyncio.sleep(0.1)
    mqtt_msg_change = traeger_client.mqtt_client.grills_status["0123456789ab"]
    for item in mqtt_msg_change["status"]["acc"]:
        item[item["type"]]["get_temp"] = 250
    traeger_client.mqtt_client.mqtt_client.publish(  # The actual change
        "prod/thing/update/0123456789ab",
        json.dumps(mqtt_msg_change).encode("utf-8"),
        qos=1,
    )
    await asyncio.sleep(0.1)
    entity = hass.states.get(f"sensor.0123456789ab_probe_state_{mqtt_msg_acc['uuid']}")
    # Check Enttity
    # if unit == "F":
    assert entity.state == "fell_out"

    # Disconnect Probes
    await asyncio.sleep(0.1)
    mqtt_msg_change = traeger_client.mqtt_client.grills_status["0123456789ab"]
    for item in mqtt_msg_change["status"]["acc"]:
        item["con"] = 0
    traeger_client.mqtt_client.mqtt_client.publish(  # The actual change
        "prod/thing/update/0123456789ab",
        json.dumps(mqtt_msg_change).encode("utf-8"),
        qos=1,
    )
    await asyncio.sleep(0.1)

    # Change Entity
    await asyncio.sleep(0.1)
    mqtt_msg_change = traeger_client.mqtt_client.grills_status["0123456789ab"]
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
