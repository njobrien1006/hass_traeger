"""Tests for the climate platform."""

import asyncio
import logging

import pytest
from aiointercept import aiointercept
from homeassistant.const import UnitOfTemperature
from homeassistant.core import HomeAssistant, State
from homeassistant.helpers import entity_registry
from homeassistant.util.unit_system import METRIC_SYSTEM, US_CUSTOMARY_SYSTEM
from pytest_homeassistant_custom_component.common import MockConfigEntry
from syrupy.assertion import SnapshotAssertion

from custom_components.traeger.const import (
    DOMAIN,
    PROBE_PRESET_MODES,
)

from .zzcommon import CallbackAPI, client_connect, client_disconnect, client_publish
from .zzMockResp import api_user_self, mqtt_msg

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
    snapshot: SnapshotAssertion,
    http: aiointercept,
) -> None:
    """Check async add for the post init additions"""

    traeger_client = hass.data[DOMAIN][mock_config_entry.entry_id]
    CallbackAPI(traeger_client, http)
    await client_connect(hass, traeger_client, api_user_self["resp"]["things"])

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
async def test_climate_setgrilltemp_cmd(
    platform,
    entity_id,
    unit,
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    snapshot: SnapshotAssertion,
    http: aiointercept,
) -> None:
    """test climate cmds"""
    # pylint: disable=too-many-arguments,too-many-positional-arguments,too-many-statements

    if unit == "F":
        mqtt_msg["status"]["units"] = 1
        hass.config.units = US_CUSTOMARY_SYSTEM
    elif unit == "C":
        mqtt_msg["status"]["units"] = 0
        hass.config.units = METRIC_SYSTEM

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

    snapshotname = 2
    for system_status in [2, 3, 4, 5, 6, 7, 9, 2, 99]:
        mqtt_msg_change = traeger_client.mqtt_client.grills_status["0123456789ab"]
        mqtt_msg_change["status"]["system_status"] = system_status
        await client_publish(hass, traeger_client, mqtt_msg_change)

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
        await asyncio.sleep(0.05)

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
        await asyncio.sleep(0.05)

    # Put Grill in cook mode so we can expect the switch to be available.
    mqtt_msg_change = traeger_client.mqtt_client.grills_status["0123456789ab"]
    mqtt_msg_change["status"]["system_status"] = 6
    mqtt_msg_change["limits"]["max_grill_temp"] = 0
    await client_publish(hass, traeger_client, mqtt_msg_change)

    # Get Entity Happy Check
    entity = hass.states.get(f"{platform}.{entity_id}")
    # Check Enttity
    assert isinstance(entity, State)
    assert entity.state != "unavailable"
    assert entity.attributes.get("min_temp", 999) < entity.attributes.get("max_temp")
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
    await asyncio.sleep(0.05)
    # Get Entity Trig Check
    entity = hass.states.get(f"{platform}.{entity_id}")
    # Check Enttity
    assert entity.state != "unavailable"
    assert entity == snapshot(name=f"{snapshotname:02d}-changed")
    snapshotname += 1

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
    await asyncio.sleep(0.05)
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
        _LOGGER.debug("doing sensor step: %s", item)
        mqtt_msg_change = traeger_client.mqtt_client.grills_status["0123456789ab"]
        mqtt_msg_change["status"]["system_status"] = item["sts"]
        mqtt_msg_change["status"]["grill"] = item["grill"]
        mqtt_msg_change["status"]["set"] = item["set"]
        await client_publish(hass, traeger_client, mqtt_msg_change, 0.01)

        entity = hass.states.get("sensor.traeger_0123456789ab_heating_state")
        # Check Enttity
        assert entity.state == item["rslt"]

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
    await asyncio.sleep(0.05)
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
    await client_publish(hass, traeger_client, mqtt_msg_change)

    # Get Entity Trig Check
    entity = hass.states.get(f"{platform}.{entity_id}")
    # Check Enttity
    assert entity.state == "off"
    assert entity == snapshot(name="06-off")

    # Change Entity
    mqtt_msg_change = traeger_client.mqtt_client.grills_status["0123456789ab"]
    mqtt_msg_change["status"]["connected"] = False
    await client_publish(hass, traeger_client, mqtt_msg_change)
    # Get Entity Offline
    entity = hass.states.get(f"{platform}.{entity_id}")
    # Check Enttity
    assert isinstance(entity, State)
    assert entity.state == "unavailable"
    assert entity == snapshot(name=f"{snapshotname:02d}-not_connected")
    snapshotname += 1

    await client_disconnect(hass, traeger_client)

    if unit == "C":
        mqtt_msg["status"]["units"] = 1
        hass.config.units = US_CUSTOMARY_SYSTEM


@pytest.mark.usefixtures("socket_enabled")
@pytest.mark.parametrize(
    "mqtt_msg_acc",
    mqtt_msg["status"]["acc"],
)
async def test_climate_setprobetemp_cmds(
    mqtt_msg_acc,
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    snapshot: SnapshotAssertion,
    http: aiointercept,
) -> None:
    """test climate cmds"""
    # pylint: disable=too-many-statements

    platform = "climate"
    entity_id = f"0123456789ab_probe_{mqtt_msg_acc['uuid']}"

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

    # Get Entity Happy Check
    entity = hass.states.get(f"{platform}.{entity_id}")
    # Check Enttity
    assert isinstance(entity, State)
    assert entity.state != "unavailable"
    assert entity.attributes.get("min_temp", 999) < entity.attributes.get("max_temp")
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
    await asyncio.sleep(0.05)
    # Get Entity Trig Check
    entity = hass.states.get(f"{platform}.{entity_id}")
    # Check Enttity
    assert entity.state != "unavailable"
    assert entity == snapshot(name="03-changed")

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
    await asyncio.sleep(0.05)
    # Get Entity Trig Check
    entity = hass.states.get(f"{platform}.{entity_id}")
    # Check Enttity
    assert entity.state != "unavailable"
    assert entity == snapshot(name="04-changed2")

    # Attempt turning Switching States
    for item in ["off", "cool", "heat"]:
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
        await asyncio.sleep(0.05)

    # Run Through Presets
    for item in PROBE_PRESET_MODES:  # pylint: disable=consider-using-dict-items
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
    mqtt_msg_change = traeger_client.mqtt_client.grills_status["0123456789ab"]
    for item in mqtt_msg_change["status"]["acc"]:
        item[item["type"]]["alarm_fired"] = 1
    await client_publish(hass, traeger_client, mqtt_msg_change)

    entity = hass.states.get(f"sensor.0123456789ab_probe_state_{mqtt_msg_acc['uuid']}")
    # Check Enttity
    assert entity.state == "at_temp"
    entity = hass.states.get(
        f"binary_sensor.0123456789ab_probe_alarm_{mqtt_msg_acc['uuid']}"
    )
    # Check Enttity
    assert entity.state

    # Prove Over Temp ALM (per acc)
    mqtt_msg_change = traeger_client.mqtt_client.grills_status["0123456789ab"]
    for item in mqtt_msg_change["status"]["acc"]:
        item[item["type"]]["get_temp"] = 250
    await client_publish(hass, traeger_client, mqtt_msg_change)

    entity = hass.states.get(f"sensor.0123456789ab_probe_state_{mqtt_msg_acc['uuid']}")
    # Check Enttity
    # if unit == "F":
    assert entity.state == "fell_out"

    # Disconnect Probes
    mqtt_msg_change = traeger_client.mqtt_client.grills_status["0123456789ab"]
    for item in mqtt_msg_change["status"]["acc"]:
        item["con"] = 0
    await client_publish(hass, traeger_client, mqtt_msg_change)

    # Change Entity
    mqtt_msg_change = traeger_client.mqtt_client.grills_status["0123456789ab"]
    mqtt_msg_change["status"]["connected"] = False
    await client_publish(hass, traeger_client, mqtt_msg_change)

    # Get Entity Offline
    entity = hass.states.get(f"{platform}.{entity_id}")
    # Check Enttity
    assert isinstance(entity, State)
    assert entity.state == "unavailable"
    assert entity == snapshot(name="05-not_connected")

    await client_disconnect(hass, traeger_client)
