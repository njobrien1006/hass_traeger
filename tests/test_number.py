"""Tests for the number platform."""

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
        ("number", "0123456789ab_cook_timer", "cook_timer_start"),
        ("number", "0123456789ab_cook_timer", "cook_timer_end"),
    ],
)
async def test_number(
    platform,
    entity_id,
    mqtt_loca,
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    connected_amqtt: Broker,
    snapshot: SnapshotAssertion,
    http: aioresponses,
) -> None:
    """Test Numbers"""

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
    await traeger_client.mqtt_client.connect(  # Need to connect
        api_user_self["resp"]["things"],
        "wss://127.0.0.1/mqtt?1391charsWORTHofCreds",
        False,
        MQTTPORT,
    )
    await asyncio.sleep(0.05)  # Sleep on it

    # Get Entity Init Check
    entity = hass.states.get(f"{platform}.{entity_id}")
    # Check Entity
    assert isinstance(entity, State)
    assert entity == snapshot

    # Change Entity
    await asyncio.sleep(0.05)  # Sleep on it
    mqtt_msg_change = mqtt_msg
    mqtt_msg_change["status"]["connected"] = True
    traeger_client.mqtt_client.mqtt_client.publish(  # The actual change
        "prod/thing/update/0123456789ab",
        json.dumps(mqtt_msg_change).encode("utf-8"),
        qos=1,
    )
    await asyncio.sleep(0.05)
    await hass.async_block_till_done()
    # Get Entity Happy Check
    entity = hass.states.get(f"{platform}.{entity_id}")
    # Check Enttity
    assert isinstance(entity, State)
    assert entity == snapshot

    # Change Entity
    await asyncio.sleep(0.05)
    mqtt_msg_change = mqtt_msg
    mqtt_msg_change["status"][mqtt_loca] = 600
    traeger_client.mqtt_client.mqtt_client.publish(  # The actual change
        "prod/thing/update/0123456789ab",
        json.dumps(mqtt_msg_change).encode("utf-8"),
        qos=1,
    )
    await asyncio.sleep(0.05)
    await hass.async_block_till_done()
    # Get Entity Trig Check
    entity = hass.states.get(f"{platform}.{entity_id}")
    # Check Enttity
    assert isinstance(entity, State)
    assert entity == snapshot

    # Change Entity
    await asyncio.sleep(0.05)
    mqtt_msg_change = mqtt_msg
    mqtt_msg_change["status"]["connected"] = False
    traeger_client.mqtt_client.mqtt_client.publish(  # The actual change
        "prod/thing/update/0123456789ab",
        json.dumps(mqtt_msg_change).encode("utf-8"),
        qos=1,
    )
    await asyncio.sleep(0.05)
    await hass.async_block_till_done()
    # Get Entity Offline
    entity = hass.states.get(f"{platform}.{entity_id}")
    # Check Enttity
    assert isinstance(entity, State)
    assert entity == snapshot

    # Shutdown MQTT
    await asyncio.sleep(0.05)
    traeger_client.mqtt_client.disconnect()
    await asyncio.sleep(0.05)


@pytest.mark.usefixtures("socket_enabled")
async def test_number_settimer(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    connected_amqtt: Broker,
    snapshot: SnapshotAssertion,
    http: aioresponses,
) -> None:
    """Test Set Timer"""

    def callback(url, **kwargs):
        """Setup API Callbacks"""
        _LOGGER.error("Was at callbacks %s - %s", url, kwargs["json"])
        mqtt_msg_change = mqtt_msg
        cmdsplit = kwargs["json"]["command"].split(",")
        if cmdsplit[0] == "12":
            mqtt_msg_change["status"]["time"] = 1577836800
            mqtt_msg_change["status"]["cook_timer_start"] = 1577836800
            mqtt_msg_change["status"]["cook_timer_end"] = 1577836800 + int(cmdsplit[1])
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
    await asyncio.sleep(0.05)  # Sleep on it

    # Get Entity Init Check
    entity = hass.states.get("number.0123456789ab_cook_timer")
    # Check Entity
    assert isinstance(entity, State)
    assert entity == snapshot

    # Change Entity
    await asyncio.sleep(0.05)  # Sleep on it
    mqtt_msg_change = mqtt_msg
    mqtt_msg_change["status"]["connected"] = True
    traeger_client.mqtt_client.mqtt_client.publish(  # The actual change
        "prod/thing/update/0123456789ab",
        json.dumps(mqtt_msg_change).encode("utf-8"),
        qos=1,
    )
    await asyncio.sleep(0.05)
    await hass.async_block_till_done()
    # Get Entity Happy Check
    entity = hass.states.get("number.0123456789ab_cook_timer")
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
    await asyncio.sleep(0.05)
    # Change Value
    await hass.services.async_call(
        "number",
        "SET_VALUE",
        {
            "entity_id": "number.0123456789ab_cook_timer",
            "value": 60,
        },
        blocking=True,
    )
    await hass.async_block_till_done()
    await asyncio.sleep(0.05)
    # Get Entity Trig Check
    entity_ids = [
        "number.0123456789ab_cook_timer",
        "sensor.0123456789ab_cook_timer_start",
        "sensor.0123456789ab_cook_timer_end",
    ]
    for entity_id in entity_ids:
        entity = hass.states.get(entity_id)
        # Check Enttity
        assert isinstance(entity, State)
    assert [hass.states.get(eid) for eid in entity_ids] == snapshot

    # Change Entity
    await asyncio.sleep(0.05)
    mqtt_msg_change = mqtt_msg
    mqtt_msg_change["status"]["connected"] = False
    traeger_client.mqtt_client.mqtt_client.publish(  # The actual change
        "prod/thing/update/0123456789ab",
        json.dumps(mqtt_msg_change).encode("utf-8"),
        qos=1,
    )
    await asyncio.sleep(0.05)
    await hass.async_block_till_done()
    # Get Entity Offline
    entity = hass.states.get("number.0123456789ab_cook_timer")
    # Check Enttity
    assert isinstance(entity, State)
    assert entity == snapshot

    # Shutdown MQTT
    await asyncio.sleep(0.05)
    traeger_client.mqtt_client.disconnect()
    await asyncio.sleep(0.05)


@pytest.mark.usefixtures("socket_enabled")
async def test_number_cookcycle(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    connected_amqtt: Broker,
    snapshot: SnapshotAssertion,
    http: aioresponses,
) -> None:
    """Test Cook Cycles"""

    # Tracked entities for test.
    entity_ids = [
        "number.0123456789ab_cook_cycle",
        "number.0123456789ab_cook_timer",
        "binary_sensor.0123456789ab_cook_timer_complete",
        "binary_sensor.0123456789ab_probe_alarm_fired",
        "climate.0123456789ab_climate",
        "climate.0123456789ab_probe_p0",
    ]

    def callback(url, **kwargs):
        """Setup API Callbacks"""
        _LOGGER.error("Was at callbacks %s - %s", url, kwargs["json"])
        if traeger_client.mqtt_client.grills_status == {}:
            mqtt_msg_change = mqtt_msg
        else:
            mqtt_msg_change = traeger_client.mqtt_client.grills_status["0123456789ab"]
            if mqtt_msg_change["status"]["cook_timer_complete"]:
                mqtt_msg_change["status"]["cook_timer_start"] = 0
                mqtt_msg_change["status"]["cook_timer_end"] = 0
                mqtt_msg_change["status"]["time"] = 0
                mqtt_msg_change["status"]["cook_timer_complete"] = 0
            if mqtt_msg_change["status"]["probe_alarm_fired"]:
                mqtt_msg_change["status"]["probe"] = 0
                mqtt_msg_change["status"]["acc"][0]["probe"]["set_temp"] = 0
                mqtt_msg_change["status"]["probe_alarm_fired"] = 0
        cmdsplit = kwargs["json"]["command"].split(",")
        if cmdsplit[0] == "11":
            mqtt_msg_change["status"]["set"] = int(cmdsplit[1])
            mqtt_msg_change["status"]["grill"] = int(cmdsplit[1]) / 2
            traeger_client.mqtt_client.mqtt_client.publish(
                "prod/thing/update/0123456789ab",
                json.dumps(mqtt_msg_change).encode("utf-8"),
                qos=1,
            )
            return CallbackResult(status=400, payload=None)
        if cmdsplit[0] == "12":
            mqtt_msg_change["status"]["time"] = 1577836800
            mqtt_msg_change["status"]["cook_timer_start"] = 1577836800
            mqtt_msg_change["status"]["cook_timer_end"] = 1577836800 + int(cmdsplit[1])
            traeger_client.mqtt_client.mqtt_client.publish(
                "prod/thing/update/0123456789ab",
                json.dumps(mqtt_msg_change).encode("utf-8"),
                qos=1,
            )
            return CallbackResult(status=400, payload=None)
        if cmdsplit[0] == "14":
            mqtt_msg_change["status"]["acc"][0]["probe"]["set_temp"] = int(cmdsplit[1])
            mqtt_msg_change["status"]["acc"][0]["probe"]["get_temp"] = (
                int(cmdsplit[1]) / 2
            )
            mqtt_msg_change["status"]["probe"] = int(cmdsplit[1]) / 2
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
    await asyncio.sleep(0.05)  # Sleep on it

    # Get Entity Init Check
    entity = hass.states.get("number.0123456789ab_cook_cycle")
    # Check Entity
    assert isinstance(entity, State)
    assert entity == snapshot

    # Change Entity
    await asyncio.sleep(0.05)  # Sleep on it
    mqtt_msg_change = mqtt_msg
    mqtt_msg_change["status"]["connected"] = True
    traeger_client.mqtt_client.mqtt_client.publish(  # The actual change
        "prod/thing/update/0123456789ab",
        json.dumps(mqtt_msg_change).encode("utf-8"),
        qos=1,
    )
    await asyncio.sleep(0.05)
    await hass.async_block_till_done()
    # Get Entity Happy Check
    entity = hass.states.get("number.0123456789ab_cook_cycle")
    # Check Enttity
    assert isinstance(entity, State)
    assert entity == snapshot

    # Put Grill in cook mode so we can expect the switch to be available.
    mqtt_msg_change = mqtt_msg
    mqtt_msg_change["status"]["system_status"] = 6
    mqtt_msg_change["status"]["acc"][0]["con"] = 1
    traeger_client.mqtt_client.mqtt_client.publish(
        "prod/thing/update/0123456789ab",
        json.dumps(mqtt_msg_change).encode("utf-8"),
        qos=1,
    )
    await asyncio.sleep(0.05)
    # Load Test Cook Cycle
    await hass.services.async_call(
        "traeger",
        "set_custom_cook",
        {
            "entity_id": "number.0123456789ab_cook_cycle",
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
    await asyncio.sleep(0.05)
    entity = hass.states.get("number.0123456789ab_cook_cycle")
    # Check Enttity
    assert isinstance(entity, State)
    assert entity == snapshot

    # Start Cook Cycle
    await hass.services.async_call(
        "number",
        "SET_VALUE",
        {
            "entity_id": "number.0123456789ab_cook_cycle",
            "value": 1,
        },
        blocking=True,
    )
    await hass.async_block_till_done()
    await asyncio.sleep(0.05)
    # Get Entity Trig Check
    for entity_id in entity_ids:
        entity = hass.states.get(entity_id)
        # Check Enttity
        assert isinstance(entity, State)
    assert [hass.states.get(eid) for eid in entity_ids] == snapshot

    try:
        async with asyncio.timeout(30):
            while True:
                entity = hass.states.get("number.0123456789ab_cook_cycle")
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
                        5,
                    ):
                        _LOGGER.debug("act_temp_adv x %s ", x)
                        mqtt_msg_change = traeger_client.mqtt_client.grills_status[
                            "0123456789ab"
                        ]
                        mqtt_msg_change["status"]["grill"] = int(x)
                        traeger_client.mqtt_client.mqtt_client.publish(  # The actual change
                            "prod/thing/update/0123456789ab",
                            json.dumps(mqtt_msg_change).encode("utf-8"),
                            qos=1,
                        )
                        await asyncio.sleep(0.05)
                    # Check State
                    entity = hass.states.get("number.0123456789ab_cook_cycle")
                    assert isinstance(entity, State)
                    assert entity.state == snapshot
                    # Increase to ADV Point
                    mqtt_msg_change = traeger_client.mqtt_client.grills_status[
                        "0123456789ab"
                    ]
                    mqtt_msg_change["status"]["grill"] = int(
                        curstepjson["act_temp_adv"]
                    )
                    traeger_client.mqtt_client.mqtt_client.publish(  # The actual change
                        "prod/thing/update/0123456789ab",
                        json.dumps(mqtt_msg_change).encode("utf-8"),
                        qos=1,
                    )
                    await asyncio.sleep(0.05)
                    await hass.async_block_till_done()
                    # Check ADV'd
                    entity = hass.states.get("number.0123456789ab_cook_cycle")
                    assert isinstance(entity, State)
                    assert entity.state == snapshot
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
                        60,
                    ):
                        _LOGGER.debug("TimerAdv x %s ", x)
                        mqtt_msg_change = traeger_client.mqtt_client.grills_status[
                            "0123456789ab"
                        ]
                        mqtt_msg_change["status"]["time"] = int(x)
                        traeger_client.mqtt_client.mqtt_client.publish(  # The actual change
                            "prod/thing/update/0123456789ab",
                            json.dumps(mqtt_msg_change).encode("utf-8"),
                            qos=1,
                        )
                        await asyncio.sleep(0.05)
                    # Check State
                    entity = hass.states.get("number.0123456789ab_cook_cycle")
                    assert isinstance(entity, State)
                    assert entity.state == snapshot
                    # Increase to ADV Point
                    mqtt_msg_change = traeger_client.mqtt_client.grills_status[
                        "0123456789ab"
                    ]
                    mqtt_msg_change["status"]["time"] = int(
                        mqtt_msg_change["status"]["cook_timer_start"]
                    )
                    mqtt_msg_change["status"]["cook_timer_complete"] = 1
                    traeger_client.mqtt_client.mqtt_client.publish(  # The actual change
                        "prod/thing/update/0123456789ab",
                        json.dumps(mqtt_msg_change).encode("utf-8"),
                        qos=1,
                    )
                    await asyncio.sleep(0.05)
                    await hass.async_block_till_done()
                    # Check ADV'd
                    entity = hass.states.get("number.0123456789ab_cook_cycle")
                    assert isinstance(entity, State)
                    assert entity.state == snapshot
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
                        5,
                    ):
                        _LOGGER.debug("min_delta x %s ", x)
                        mqtt_msg_change = traeger_client.mqtt_client.grills_status[
                            "0123456789ab"
                        ]
                        mqtt_msg_change["status"]["probe"] = int(x)
                        traeger_client.mqtt_client.mqtt_client.publish(  # The actual change
                            "prod/thing/update/0123456789ab",
                            json.dumps(mqtt_msg_change).encode("utf-8"),
                            qos=1,
                        )
                        await asyncio.sleep(0.05)
                    # Check State
                    entity = hass.states.get("number.0123456789ab_cook_cycle")
                    assert isinstance(entity, State)
                    assert entity.state == snapshot
                    # Increase to ADV Point
                    mqtt_msg_change = traeger_client.mqtt_client.grills_status[
                        "0123456789ab"
                    ]
                    mqtt_msg_change["status"]["probe"] = int(
                        curstepjson["probe_act_temp_adv"]
                    )
                    traeger_client.mqtt_client.mqtt_client.publish(  # The actual change
                        "prod/thing/update/0123456789ab",
                        json.dumps(mqtt_msg_change).encode("utf-8"),
                        qos=1,
                    )
                    await asyncio.sleep(0.05)
                    await hass.async_block_till_done()
                    # Check ADV'd
                    entity = hass.states.get("number.0123456789ab_cook_cycle")
                    assert isinstance(entity, State)
                    assert entity.state == snapshot
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
                        5,
                    ):
                        _LOGGER.debug("probe_act_temp_adv x %s ", x)
                        mqtt_msg_change = traeger_client.mqtt_client.grills_status[
                            "0123456789ab"
                        ]
                        mqtt_msg_change["status"]["probe"] = int(x)
                        traeger_client.mqtt_client.mqtt_client.publish(  # The actual change
                            "prod/thing/update/0123456789ab",
                            json.dumps(mqtt_msg_change).encode("utf-8"),
                            qos=1,
                        )
                        await asyncio.sleep(0.05)
                    # Check State
                    entity = hass.states.get("number.0123456789ab_cook_cycle")
                    assert isinstance(entity, State)
                    assert entity.state == snapshot
                    # Increase to ADV Point
                    mqtt_msg_change = traeger_client.mqtt_client.grills_status[
                        "0123456789ab"
                    ]
                    mqtt_msg_change["status"]["probe"] = int(
                        curstepjson["probe_act_temp_adv"]
                    )
                    traeger_client.mqtt_client.mqtt_client.publish(  # The actual change
                        "prod/thing/update/0123456789ab",
                        json.dumps(mqtt_msg_change).encode("utf-8"),
                        qos=1,
                    )
                    await asyncio.sleep(0.05)
                    await hass.async_block_till_done()
                    # Check ADV'd
                    entity = hass.states.get("number.0123456789ab_cook_cycle")
                    assert isinstance(entity, State)
                    assert entity.state == snapshot
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
                        5,
                    ):
                        _LOGGER.debug("probe_adv_Dflt x %s ", x)
                        mqtt_msg_change = traeger_client.mqtt_client.grills_status[
                            "0123456789ab"
                        ]
                        mqtt_msg_change["status"]["probe"] = int(x)
                        traeger_client.mqtt_client.mqtt_client.publish(  # The actual change
                            "prod/thing/update/0123456789ab",
                            json.dumps(mqtt_msg_change).encode("utf-8"),
                            qos=1,
                        )
                        await asyncio.sleep(0.05)
                    # Check State
                    entity = hass.states.get("number.0123456789ab_cook_cycle")
                    assert isinstance(entity, State)
                    assert entity.state == snapshot
                    # Increase to ADV Point
                    mqtt_msg_change = traeger_client.mqtt_client.grills_status[
                        "0123456789ab"
                    ]
                    mqtt_msg_change["status"]["probe"] = int(
                        mqtt_msg_change["status"]["acc"][0]["probe"]["set_temp"]
                    )
                    mqtt_msg_change["status"]["probe_alarm_fired"] = 1
                    traeger_client.mqtt_client.mqtt_client.publish(  # The actual change
                        "prod/thing/update/0123456789ab",
                        json.dumps(mqtt_msg_change).encode("utf-8"),
                        qos=1,
                    )
                    await asyncio.sleep(0.05)
                    await hass.async_block_till_done()
                    # Check ADV'd
                    entity = hass.states.get("number.0123456789ab_cook_cycle")
                    assert isinstance(entity, State)
                    assert entity.state == snapshot
                    await asyncio.sleep(0.05)
                    # Get Entity Trig Check
                    for entity_id in entity_ids:
                        entity = hass.states.get(entity_id)
                        # Check Enttity
                        assert isinstance(entity, State)
                    assert [hass.states.get(eid) for eid in entity_ids] == snapshot
                await asyncio.sleep(0.05)
    except TimeoutError:
        _LOGGER.error("Got stuck in cook cycle!")
        assert False

    # Change Entity
    await asyncio.sleep(0.05)
    mqtt_msg_change = mqtt_msg
    mqtt_msg_change["status"]["connected"] = False
    traeger_client.mqtt_client.mqtt_client.publish(  # The actual change
        "prod/thing/update/0123456789ab",
        json.dumps(mqtt_msg_change).encode("utf-8"),
        qos=1,
    )
    await asyncio.sleep(0.05)
    await hass.async_block_till_done()
    # Get Entity Offline
    entity = hass.states.get("number.0123456789ab_cook_cycle")
    # Check Enttity
    assert isinstance(entity, State)
    assert entity == snapshot

    # Shutdown MQTT
    await asyncio.sleep(0.05)
    traeger_client.mqtt_client.disconnect()
    await asyncio.sleep(0.05)
