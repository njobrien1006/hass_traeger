"""Tests for the number platform."""

import asyncio
import json
import logging

import pytest
from aiointercept import aiointercept
from homeassistant.core import HomeAssistant, State
from homeassistant.helpers import entity_registry
from pytest_homeassistant_custom_component.common import MockConfigEntry
from syrupy.assertion import SnapshotAssertion

from custom_components.traeger.const import DOMAIN

from .zzcommon import CallbackAPI, client_connect, client_disconnect, client_publish
from .zzMockResp import api_user_self

_LOGGER: logging.Logger = logging.getLogger(__package__)


async def test_number_platform(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    snapshot: SnapshotAssertion,
) -> None:
    """Test the number platform setup."""
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
            and entry.domain == "number"
        ],
        key=lambda entry: entry["entity_id"],
    )

    assert entries == snapshot


@pytest.mark.usefixtures("socket_enabled")
@pytest.mark.parametrize(
    "platform, entity_id, mqtt_loca",
    [
        ("number", "traeger_0123456789ab_cook_timer", "cook_timer_start"),
        ("number", "traeger_0123456789ab_cook_timer", "cook_timer_end"),
    ],
)
async def test_number(
    platform,
    entity_id,
    mqtt_loca,
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    snapshot: SnapshotAssertion,
    http: aiointercept,
) -> None:
    """Test Numbers"""
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

    # Get Entity Happy Check
    entity = hass.states.get(f"{platform}.{entity_id}")
    # Check Enttity
    assert isinstance(entity, State)
    assert entity.state != "unavailable"
    assert entity == snapshot(name="02-ready")

    # Change Entity
    mqtt_msg_change = traeger_client.mqtt_client.grills_status["0123456789ab"]
    mqtt_msg_change["status"][mqtt_loca] = 600
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


@pytest.mark.usefixtures("socket_enabled")
async def test_number_settimer(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    snapshot: SnapshotAssertion,
    http: aiointercept,
) -> None:
    """Test Set Timer"""

    traeger_client = hass.data[DOMAIN][mock_config_entry.entry_id]
    CallbackAPI(traeger_client, http)
    await client_connect(hass, traeger_client, api_user_self["resp"]["things"])

    # Get Entity Init Check
    entity = hass.states.get("number.traeger_0123456789ab_cook_timer")
    # Check Entity
    assert isinstance(entity, State)
    assert entity.state == "unavailable"
    assert entity == snapshot(name="01-init")

    # Change Entity
    mqtt_msg_change = traeger_client.mqtt_client.grills_status["0123456789ab"]
    mqtt_msg_change["status"]["connected"] = True
    await client_publish(hass, traeger_client, mqtt_msg_change)

    # Get Entity Happy Check
    entity = hass.states.get("number.traeger_0123456789ab_cook_timer")
    # Check Enttity
    assert isinstance(entity, State)
    assert entity.state != "unavailable"
    assert entity == snapshot(name="02-ready")

    # Change Before Ready for expected `NotImplementedError`
    with pytest.raises(NotImplementedError):
        await hass.services.async_call(
            "number",
            "SET_VALUE",
            {
                "entity_id": "number.traeger_0123456789ab_cook_timer",
                "value": 60,
            },
            blocking=True,
        )
        await hass.async_block_till_done()
        await asyncio.sleep(0.1)

    # Put Grill in cook mode so we can expect the switch to be available.
    mqtt_msg_change = traeger_client.mqtt_client.grills_status["0123456789ab"]
    mqtt_msg_change["status"]["system_status"] = 6
    await client_publish(hass, traeger_client, mqtt_msg_change)

    # Get Entity Happy Check
    entity = hass.states.get("number.traeger_0123456789ab_cook_timer")
    # Check Enttity
    assert isinstance(entity, State)
    assert entity.state != "unavailable"
    assert entity == snapshot(name="02-ready2cook")

    # Change Value
    await hass.services.async_call(
        "number",
        "SET_VALUE",
        {
            "entity_id": "number.traeger_0123456789ab_cook_timer",
            "value": 60,
        },
        blocking=True,
    )
    await hass.async_block_till_done()
    await asyncio.sleep(0.05)
    # Get Entity Trig Check
    entity_ids = [
        "number.traeger_0123456789ab_cook_timer",
        "sensor.traeger_0123456789ab_cook_timer_start",
        "sensor.traeger_0123456789ab_cook_timer_end",
    ]
    for entity_id in entity_ids:
        entity = hass.states.get(entity_id)
        # Check Enttity
        assert isinstance(entity, State)
    assert [hass.states.get(eid) for eid in entity_ids] == snapshot(
        name="03-TrackedEntities"
    )

    # Reset Timer
    await hass.services.async_call(
        "number",
        "SET_VALUE",
        {
            "entity_id": "number.traeger_0123456789ab_cook_timer",
            "value": 0,
        },
        blocking=True,
    )
    await hass.async_block_till_done()
    await asyncio.sleep(0.05)
    # Get Entity Trig Check
    entity_ids = [
        "number.traeger_0123456789ab_cook_timer",
        "sensor.traeger_0123456789ab_cook_timer_start",
        "sensor.traeger_0123456789ab_cook_timer_end",
    ]
    for entity_id in entity_ids:
        entity = hass.states.get(entity_id)
        # Check Enttity
        assert isinstance(entity, State)
    assert [hass.states.get(eid) for eid in entity_ids] == snapshot(
        name="04-TrackedEntities"
    )

    # Change Entity
    mqtt_msg_change = traeger_client.mqtt_client.grills_status["0123456789ab"]
    mqtt_msg_change["status"]["connected"] = False
    await client_publish(hass, traeger_client, mqtt_msg_change)

    # Get Entity Offline
    entity = hass.states.get("number.traeger_0123456789ab_cook_timer")
    # Check Enttity
    assert isinstance(entity, State)
    assert entity.state == "unavailable"
    assert entity == snapshot(name="05-not_connected")

    await client_disconnect(hass, traeger_client)


@pytest.mark.usefixtures("socket_enabled")
async def test_number_cookcycle(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    snapshot: SnapshotAssertion,
    http: aiointercept,
) -> None:
    """Test Cook Cycles"""
    # pylint: disable=too-many-branches,too-many-statements

    traeger_client = hass.data[DOMAIN][mock_config_entry.entry_id]
    CallbackAPI(traeger_client, http)
    await client_connect(hass, traeger_client, api_user_self["resp"]["things"])

    # Get Entity Init Check
    entity = hass.states.get("number.traeger_0123456789ab_cook_cycle")
    # Check Entity
    assert isinstance(entity, State)
    assert entity.state != "unavailable"
    assert entity == snapshot(name="01-init")

    # Put Grill in cook mode so we can expect the switch to be available.
    mqtt_msg_change = traeger_client.mqtt_client.grills_status["0123456789ab"]
    mqtt_msg_change["status"]["connected"] = True
    mqtt_msg_change["status"]["system_status"] = 6
    mqtt_msg_change["status"]["acc"][0]["con"] = 1
    await client_publish(hass, traeger_client, mqtt_msg_change)

    # Get Entity Happy Check
    entity = hass.states.get("number.traeger_0123456789ab_cook_cycle")
    # Check Enttity
    assert isinstance(entity, State)
    assert entity.state != "unavailable"
    assert entity == snapshot(name="02-ready")

    # Load Test Cook Cycle
    await hass.services.async_call(
        "traeger",
        "set_custom_cook",
        {
            "entity_id": "number.traeger_0123456789ab_cook_cycle",
            "steps": [
                {"set_temp": 225, "act_temp_adv": 220},
                {"use_timer": 1, "time_set": 10},
                {"set_temp": 375, "use_timer": 1, "time_set": 10},
                {"probe_set_temp": 165, "probe_act_temp_adv": 140},
                {"time_set": 10},
                {"use_timer": 1},
                {"time_set": 10, "use_timer": 1, "keepwarm": 1},
                {"time_set": 10, "use_timer": 1, "keepwarm": 0},
                {"set_temp": 170, "use_timer": 1, "time_set": 10},
                {"time_set": 10, "use_timer": 1, "smoke": 1},
                {"time_set": 10, "use_timer": 1, "smoke": 0},
                {"time_set": 15, "smoke": 1, "set_temp": 180, "use_timer": 1},
                {
                    "probe_set_temp": 210,
                    "time_set": 1080,
                    "min_delta": 30,
                    "max_grill_delta_temp": 225,
                    "probe_act_temp_adv": 160,
                },
                {
                    "min_delta": 35,
                    "max_grill_delta_temp": 230,
                    "probe_act_temp_adv": 170,
                },
                {"min_delta": 40, "max_grill_delta_temp": 250},
                {"time_set": 10, "set_temp": 210, "use_timer": 1},
                {"shutdown": 1},
            ],
        },
        blocking=True,
    )
    await hass.async_block_till_done()
    # Load Entities for cook cycles
    await traeger_client.get_entities()
    await asyncio.sleep(0.1)
    entity = hass.states.get("number.traeger_0123456789ab_cook_cycle")
    # Check Enttity
    assert isinstance(entity, State)
    assert entity.state != "unavailable"
    assert entity == snapshot(name="03-CookCycServiceInitd")

    # Start Cook Cycle
    await hass.services.async_call(
        "number",
        "SET_VALUE",
        {
            "entity_id": "number.traeger_0123456789ab_cook_cycle",
            "value": 1,
        },
        blocking=True,
    )
    await hass.async_block_till_done()
    await asyncio.sleep(0.05)
    snapshotname = 4

    try:
        async with asyncio.timeout(30):
            while True:
                entity = hass.states.get("number.traeger_0123456789ab_cook_cycle")
                curstep = entity.attributes.get("curr_step", "")
                if entity.state == 0 or curstep == r"{}" or curstep == "":
                    break
                curstepjson = json.loads(curstep[curstep.find(":") + 2 :])
                _LOGGER.info("Cook Seq %s ", entity.state)
                _LOGGER.info("Cook Seq %s ", curstepjson)
                if "act_temp_adv" in curstepjson:
                    _LOGGER.debug(
                        "act_temp_adv %s ", int(curstepjson["act_temp_adv"] / 2)
                    )
                    _LOGGER.debug(
                        "act_temp_adv %s ", int(curstepjson["act_temp_adv"] - 1)
                    )
                    # Increate Actual Temp by 5 to pre ADV
                    for x in range(
                        int(curstepjson["act_temp_adv"] / 2),
                        int(curstepjson["act_temp_adv"] - 1),
                        10,
                    ):
                        _LOGGER.debug("act_temp_adv x %s ", x)
                        mqtt_msg_change = traeger_client.mqtt_client.grills_status[
                            "0123456789ab"
                        ]
                        mqtt_msg_change["status"]["grill"] = int(x)
                        await client_publish(
                            hass, traeger_client, mqtt_msg_change, 0.05
                        )
                    # Check State
                    entity = hass.states.get("number.traeger_0123456789ab_cook_cycle")
                    assert isinstance(entity, State)
                    assert entity.state == snapshot(
                        name=f"{snapshotname:02d}-CookCyleSnapshotsClimActPreAdv"
                    )
                    snapshotname += 1

                    # Increase to ADV Point
                    mqtt_msg_change = traeger_client.mqtt_client.grills_status[
                        "0123456789ab"
                    ]
                    mqtt_msg_change["status"]["grill"] = int(
                        curstepjson["act_temp_adv"]
                    )
                    await client_publish(hass, traeger_client, mqtt_msg_change, 0.1)
                    # Check ADV'd
                    entity = hass.states.get("number.traeger_0123456789ab_cook_cycle")
                    assert isinstance(entity, State)
                    assert entity.state == snapshot(
                        name=f"{snapshotname:02d}-CookCyleSnapshotsClimActPostAdv"
                    )
                    snapshotname += 1

                    await asyncio.sleep(0.05)
                elif "use_timer" in curstepjson:
                    mqtt_msg_change = traeger_client.mqtt_client.grills_status[
                        "0123456789ab"
                    ]
                    _LOGGER.debug(
                        "TimerAdv %s ",
                        int(mqtt_msg_change["status"]["cook_timer_start"]),
                    )
                    _LOGGER.debug(
                        "TimerAdv %s ",
                        int(mqtt_msg_change["status"]["cook_timer_end"] - 1),
                    )
                    # Increate Grill Time between start and end
                    for x in range(
                        int(mqtt_msg_change["status"]["cook_timer_start"]),
                        int(mqtt_msg_change["status"]["cook_timer_end"] - 1),
                        120,
                    ):
                        _LOGGER.debug("TimerAdv x %s ", x)
                        mqtt_msg_change = traeger_client.mqtt_client.grills_status[
                            "0123456789ab"
                        ]
                        mqtt_msg_change["status"]["time"] = int(x)
                        await client_publish(
                            hass, traeger_client, mqtt_msg_change, 0.05
                        )
                    # Check State
                    entity = hass.states.get("number.traeger_0123456789ab_cook_cycle")
                    assert isinstance(entity, State)
                    assert entity.state == snapshot(
                        name=f"{snapshotname:02d}-CookCyleSnapshotsUseTimerPreAdv"
                    )
                    snapshotname += 1

                    # Increase to ADV Point
                    mqtt_msg_change = traeger_client.mqtt_client.grills_status[
                        "0123456789ab"
                    ]
                    mqtt_msg_change["status"]["time"] = int(
                        mqtt_msg_change["status"]["cook_timer_start"]
                    )
                    mqtt_msg_change["status"]["cook_timer_complete"] = 1
                    await client_publish(hass, traeger_client, mqtt_msg_change, 0.1)
                    # Check ADV'd
                    entity = hass.states.get("number.traeger_0123456789ab_cook_cycle")
                    assert isinstance(entity, State)
                    assert entity.state == snapshot(
                        name=f"{snapshotname:02d}-CookCyleSnapshotsUseTimerPostAdv"
                    )
                    snapshotname += 1

                    await asyncio.sleep(0.05)
                elif (
                    "min_delta" in curstepjson and "max_grill_delta_temp" in curstepjson
                ):
                    _LOGGER.debug(
                        "min_delta %s ", int(curstepjson["max_grill_delta_temp"] / 2)
                    )
                    _LOGGER.debug(
                        "min_delta %s ", int(curstepjson["max_grill_delta_temp"] - 1)
                    )
                    # Increate Actual Temp by 5 to pre ADV
                    for x in range(
                        int(curstepjson["max_grill_delta_temp"] / 2),
                        int(
                            curstepjson["max_grill_delta_temp"]
                            - curstepjson["min_delta"]
                            - 1
                        ),
                        10,
                    ):
                        _LOGGER.debug("min_delta x %s ", x)
                        mqtt_msg_change = traeger_client.mqtt_client.grills_status[
                            "0123456789ab"
                        ]
                        mqtt_msg_change["status"]["probe"] = int(x)
                        await client_publish(
                            hass, traeger_client, mqtt_msg_change, 0.05
                        )
                    # Check State
                    entity = hass.states.get("number.traeger_0123456789ab_cook_cycle")
                    assert isinstance(entity, State)
                    assert entity.state == snapshot(
                        name=f"{snapshotname:02d}-CookCyleSnapshotsMinDeltaPreAdv"
                    )
                    snapshotname += 1

                    # Increase to ADV Point
                    mqtt_msg_change = traeger_client.mqtt_client.grills_status[
                        "0123456789ab"
                    ]
                    mqtt_msg_change["status"]["probe"] = int(
                        curstepjson["probe_act_temp_adv"]
                    )
                    await client_publish(hass, traeger_client, mqtt_msg_change, 0.1)
                    # Check ADV'd
                    entity = hass.states.get("number.traeger_0123456789ab_cook_cycle")
                    assert isinstance(entity, State)
                    assert entity.state == snapshot(
                        name=f"{snapshotname:02d}-CookCyleSnapshotsMinDeltaPostAdv"
                    )
                    snapshotname += 1

                    await asyncio.sleep(0.05)
                elif "probe_act_temp_adv" in curstepjson:
                    _LOGGER.debug(
                        "probe_act_temp_adv %s ",
                        int(curstepjson["probe_act_temp_adv"] / 2),
                    )
                    _LOGGER.debug(
                        "probe_act_temp_adv %s ",
                        int(curstepjson["probe_act_temp_adv"] - 1),
                    )
                    # Increate Actual Temp by 5 to pre ADV
                    for x in range(
                        int(curstepjson["probe_act_temp_adv"] / 2),
                        int(curstepjson["probe_act_temp_adv"] - 1),
                        10,
                    ):
                        _LOGGER.debug("probe_act_temp_adv x %s ", x)
                        mqtt_msg_change = traeger_client.mqtt_client.grills_status[
                            "0123456789ab"
                        ]
                        mqtt_msg_change["status"]["probe"] = int(x)
                        await client_publish(
                            hass, traeger_client, mqtt_msg_change, 0.05
                        )
                    # Check State
                    entity = hass.states.get("number.traeger_0123456789ab_cook_cycle")
                    assert isinstance(entity, State)
                    assert entity.state == snapshot(
                        name=f"{snapshotname:02d}-CookCyleSnapshotsProbeActPreAdv"
                    )
                    snapshotname += 1

                    # Increase to ADV Point
                    mqtt_msg_change = traeger_client.mqtt_client.grills_status[
                        "0123456789ab"
                    ]
                    mqtt_msg_change["status"]["probe"] = int(
                        curstepjson["probe_act_temp_adv"]
                    )
                    await client_publish(hass, traeger_client, mqtt_msg_change, 0.1)
                    # Check ADV'd
                    entity = hass.states.get("number.traeger_0123456789ab_cook_cycle")
                    assert isinstance(entity, State)
                    assert entity.state == snapshot(
                        name=f"{snapshotname:02d}-CookCyleSnapshotsProbeActPostAdv"
                    )
                    snapshotname += 1

                    await asyncio.sleep(0.05)
                if mqtt_msg_change["status"]["acc"][0]["probe"]["set_temp"] > 100:
                    _LOGGER.debug(
                        "probe_adv_Dflt %s ",
                        int(
                            mqtt_msg_change["status"]["acc"][0]["probe"]["set_temp"] / 2
                        ),
                    )
                    _LOGGER.debug(
                        "probe_adv_Dflt %s ",
                        int(
                            mqtt_msg_change["status"]["acc"][0]["probe"]["set_temp"] - 1
                        ),
                    )
                    # Increate Actual Temp by 5 to pre ADV
                    mqtt_msg_change = traeger_client.mqtt_client.grills_status[
                        "0123456789ab"
                    ]
                    for x in range(
                        int(mqtt_msg_change["status"]["probe"]),
                        int(
                            mqtt_msg_change["status"]["acc"][0]["probe"]["set_temp"] - 1
                        ),
                        10,
                    ):
                        _LOGGER.debug("probe_adv_Dflt x %s ", x)
                        mqtt_msg_change = traeger_client.mqtt_client.grills_status[
                            "0123456789ab"
                        ]
                        mqtt_msg_change["status"]["probe"] = int(x)
                        await client_publish(
                            hass, traeger_client, mqtt_msg_change, 0.05
                        )
                    # Check State
                    entity = hass.states.get("number.traeger_0123456789ab_cook_cycle")
                    assert isinstance(entity, State)
                    assert entity.state == snapshot(
                        name=f"{snapshotname:02d}-CookCyleSnapshotsProbeAlmPreAdv"
                    )
                    snapshotname += 1

                    # Increase to ADV Point
                    mqtt_msg_change = traeger_client.mqtt_client.grills_status[
                        "0123456789ab"
                    ]
                    mqtt_msg_change["status"]["probe"] = int(
                        mqtt_msg_change["status"]["acc"][0]["probe"]["set_temp"]
                    )
                    mqtt_msg_change["status"]["probe_alarm_fired"] = 1
                    await client_publish(hass, traeger_client, mqtt_msg_change, 0.1)
                    # Check ADV'd
                    entity = hass.states.get("number.traeger_0123456789ab_cook_cycle")
                    assert isinstance(entity, State)
                    assert entity.state == snapshot(
                        name=f"{snapshotname:02d}-CookCyleSnapshotsProbeAlmPostAdv"
                    )
                    snapshotname += 1

                    await asyncio.sleep(0.05)
                await asyncio.sleep(0.05)
                # Get Entity Trig Check
                entity = hass.states.get("number.traeger_0123456789ab_cook_cycle")
                assert isinstance(entity, State)
                assert entity.state != "unavailable"
                assert entity == snapshot(name=f"{snapshotname:02d}-TrackedEntity")
                snapshotname += 1
                if curstepjson == {"shutdown": 1}:
                    break
    except TimeoutError:
        _LOGGER.error("Got stuck in cook cycle!")
        assert False
    except Exception as exception:  # pylint: disable=broad-except
        _LOGGER.error("Something really wrong happend! - %s", exception)
        assert False

    # Try overdoing it...
    await hass.services.async_call(
        "number",
        "SET_VALUE",
        {
            "entity_id": "number.traeger_0123456789ab_cook_cycle",
            "value": 70,
        },
        blocking=True,
    )
    await hass.async_block_till_done()
    await asyncio.sleep(0.1)
    entity = hass.states.get("number.traeger_0123456789ab_cook_cycle")
    # Check Enttity
    assert isinstance(entity, State)
    assert entity.state == "0"
    assert entity == snapshot(name=f"{snapshotname:02d}-checkoutofcookindx")
    snapshotname += 1

    # Change Entity

    mqtt_msg_change = traeger_client.mqtt_client.grills_status["0123456789ab"]
    mqtt_msg_change["status"]["connected"] = False
    await client_publish(hass, traeger_client, mqtt_msg_change)
    # Get Entity Offline
    entity = hass.states.get("number.traeger_0123456789ab_cook_cycle")
    # Check Enttity
    assert isinstance(entity, State)
    assert entity.state == "0"
    assert entity == snapshot(name=f"{snapshotname:02d}-not_connected")

    await client_disconnect(hass, traeger_client)
