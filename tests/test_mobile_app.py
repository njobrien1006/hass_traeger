"""Tests for the binary sensor platform."""

import copy
import json
import logging
import time

import pytest
from aiointercept import CallbackResult, aiointercept
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry
from pytest_homeassistant_custom_component.common import MockConfigEntry
from syrupy.assertion import SnapshotAssertion

from custom_components.traeger.const import DOMAIN

from .conftest import Broker
from .zzcommon import client_connect, client_disconnect, client_publish
from .zzMockResp import api_commands, api_user_self, mqtt_msg

_LOGGER: logging.Logger = logging.getLogger(__package__)


# pylint: disable=unused-argument,too-many-arguments,too-many-positional-arguments
async def test_mobile_app_platform(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    snapshot: SnapshotAssertion,
) -> None:
    """Test the mobile app platform setup."""
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
            if entry.platform == "mobile_app"
        ],
        key=lambda entry: entry["entity_id"],
    )

    assert entries == snapshot


@pytest.mark.usefixtures("socket_enabled")
@pytest.mark.parametrize(
    "manu",
    [
        ("Apple"),
        ("Google"),
    ],
)
# pylint: disable=too-many-statements
async def test_mobile_app_manu_sys(
    manu,
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    connected_amqtt: Broker,
    snapshot: SnapshotAssertion,
    http: aiointercept,
) -> None:
    """Test Mobile App Live Updates for Sys Timer"""

    def callback(url, **kwargs):
        """Setup API Callbacks"""
        _LOGGER.warning("Was at callbacks %s - %s", url, kwargs["json"])
        if kwargs["json"]["command"] == "90":
            mqtt_msg_change = copy.deepcopy(mqtt_msg)
        else:
            return CallbackResult(status=404, payload=None)
        # Publish Change
        traeger_client.mqtt_client.mqtt_client.publish(
            "prod/thing/update/0123456789ab",
            json.dumps(mqtt_msg_change).encode("utf-8"),
            qos=1,
        )
        return CallbackResult(status=200, payload=None)

    # Register Callbacks
    http.post(api_commands["url"], callback=callback, repeat=True)
    http.post(api_commands["urlg2"], callback=callback, repeat=True)
    traeger_client = hass.data[DOMAIN][mock_config_entry.entry_id]
    for noti in traeger_client.notify:
        if traeger_client.notify[noti]["manu"] != manu:
            traeger_client.notify[noti] = {}
    await client_connect(hass, traeger_client, api_user_self["resp"]["things"])

    # Prep State
    mqtt_msg_change = traeger_client.mqtt_client.grills_status["0123456789ab"]
    mqtt_msg_change["status"]["system_status"] = 4
    mqtt_msg_change["status"]["sys_timer_complete"] = 0
    mqtt_msg_change["status"]["connected"] = True
    await client_publish(hass, traeger_client, mqtt_msg_change)

    # Cook Preheat Mode & Timer Start
    mqtt_msg_change = traeger_client.mqtt_client.grills_status["0123456789ab"]
    mqtt_msg_change["status"]["system_status"] = 5
    mqtt_msg_change["status"]["sys_timer_start"] = time.time()
    mqtt_msg_change["status"]["sys_timer_end"] = time.time() + 60
    await client_publish(hass, traeger_client, mqtt_msg_change)
    jsondata = http.last_request.kwargs.get("json", {})
    jsondata["data"]["when"] = 1785560400
    assert jsondata["data"].get("live_update",False)
    assert jsondata == snapshot(name="01-live")

    # Timer done, Preheat Complete
    mqtt_msg_change = traeger_client.mqtt_client.grills_status["0123456789ab"]
    mqtt_msg_change["status"]["system_status"] = 6
    mqtt_msg_change["status"]["sys_timer_complete"] = 1
    await client_publish(hass, traeger_client, mqtt_msg_change)
    jsondata = http.last_request.kwargs.get("json", {})
    assert jsondata == snapshot(name="02-preheatcmplt")

    # Clear Timer and Timer Flag
    mqtt_msg_change = traeger_client.mqtt_client.grills_status["0123456789ab"]
    mqtt_msg_change["status"]["sys_timer_complete"] = 0
    mqtt_msg_change["status"]["sys_timer_start"] = 0
    mqtt_msg_change["status"]["sys_timer_end"] = 0
    await client_publish(hass, traeger_client, mqtt_msg_change)


    # Begin Cooldown Mode & Timer Start
    mqtt_msg_change["status"]["system_status"] = 8
    mqtt_msg_change["status"]["sys_timer_start"] = time.time()
    mqtt_msg_change["status"]["sys_timer_end"] = time.time() + 120
    await client_publish(hass, traeger_client, mqtt_msg_change)
    jsondata = http.last_request.kwargs.get("json", {})
    jsondata["data"]["when"] = 1785560400
    assert jsondata["data"].get("live_update",False)
    assert jsondata == snapshot(name="03-livecooldown")

    # Cooldown Timer Complete
    mqtt_msg_change = traeger_client.mqtt_client.grills_status["0123456789ab"]
    mqtt_msg_change["status"]["system_status"] = 9
    mqtt_msg_change["status"]["sys_timer_complete"] = 1
    mqtt_msg_change["status"]["sys_timer_start"] = 0
    mqtt_msg_change["status"]["sys_timer_end"] = 0
    await client_publish(hass, traeger_client, mqtt_msg_change)
    jsondata = http.last_request.kwargs.get("json", {})
    assert jsondata == snapshot(name="04-cooldowncmplt")

    await client_disconnect(hass, traeger_client)


@pytest.mark.usefixtures("socket_enabled")
@pytest.mark.parametrize(
    "manu",
    [
        ("Apple"),
        ("Google"),
    ],
)
async def test_mobile_app_manu_cook(
    manu,
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    connected_amqtt: Broker,
    snapshot: SnapshotAssertion,
    http: aiointercept,
) -> None:
    """Test Mobile App Live Updates for Cook Timer"""

    def callback(url, **kwargs):
        """Setup API Callbacks"""
        _LOGGER.warning("Was at callbacks %s - %s", url, kwargs["json"])
        if kwargs["json"]["command"] == "90":
            mqtt_msg_change = copy.deepcopy(mqtt_msg)
        else:
            return CallbackResult(status=404, payload=None)
        # Publish Change
        traeger_client.mqtt_client.mqtt_client.publish(
            "prod/thing/update/0123456789ab",
            json.dumps(mqtt_msg_change).encode("utf-8"),
            qos=1,
        )
        return CallbackResult(status=200, payload=None)

    # Register Callbacks
    http.post(api_commands["url"], callback=callback, repeat=True)
    http.post(api_commands["urlg2"], callback=callback, repeat=True)
    traeger_client = hass.data[DOMAIN][mock_config_entry.entry_id]
    for noti in traeger_client.notify:
        if traeger_client.notify[noti]["manu"] != manu:
            traeger_client.notify[noti] = {}
    await client_connect(hass, traeger_client, api_user_self["resp"]["things"])

    # Prep State
    mqtt_msg_change = traeger_client.mqtt_client.grills_status["0123456789ab"]
    mqtt_msg_change["status"]["system_status"] = 6
    mqtt_msg_change["status"]["cook_timer_complete"] = 0
    mqtt_msg_change["status"]["connected"] = True
    await client_publish(hass, traeger_client, mqtt_msg_change)

    # Cook Mode & Timer Start
    mqtt_msg_change = traeger_client.mqtt_client.grills_status["0123456789ab"]
    mqtt_msg_change["status"]["cook_timer_start"] = time.time()
    mqtt_msg_change["status"]["cook_timer_end"] = time.time() + 60
    await client_publish(hass, traeger_client, mqtt_msg_change)
    jsondata = http.last_request.kwargs.get("json", {})
    jsondata["data"]["when"] = 1785560400
    assert jsondata["data"].get("live_update",False)
    assert jsondata == snapshot(name="01-live")

    # Timer done, Preheat Complete
    mqtt_msg_change = traeger_client.mqtt_client.grills_status["0123456789ab"]
    mqtt_msg_change["status"]["system_status"] = 6
    mqtt_msg_change["status"]["cook_timer_complete"] = 1
    await client_publish(hass, traeger_client, mqtt_msg_change)
    jsondata = http.last_request.kwargs.get("json", {})
    assert jsondata == snapshot(name="02-timercomplete")

    # Clear Timer and Timer Flag
    mqtt_msg_change = traeger_client.mqtt_client.grills_status["0123456789ab"]
    mqtt_msg_change["status"]["cook_timer_complete"] = 0
    mqtt_msg_change["status"]["cook_timer_start"] = 0
    mqtt_msg_change["status"]["cook_timer_end"] = 0
    await client_publish(hass, traeger_client, mqtt_msg_change)

    await client_disconnect(hass, traeger_client)


@pytest.mark.usefixtures("socket_enabled")
@pytest.mark.parametrize(
    "manu",
    [
        ("Apple"),
        ("Google"),
    ],
)
async def test_mobile_app_manu_grill(
    manu,
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    connected_amqtt: Broker,
    snapshot: SnapshotAssertion,
    http: aiointercept,
) -> None:
    """Test Mobile App Live Updates for Grill Climate"""

    def callback(url, **kwargs):
        """Setup API Callbacks"""
        _LOGGER.warning("Was at callbacks %s - %s", url, kwargs["json"])
        if kwargs["json"]["command"] == "90":
            mqtt_msg_change = copy.deepcopy(mqtt_msg)
        else:
            return CallbackResult(status=404, payload=None)
        # Publish Change
        traeger_client.mqtt_client.mqtt_client.publish(
            "prod/thing/update/0123456789ab",
            json.dumps(mqtt_msg_change).encode("utf-8"),
            qos=1,
        )
        return CallbackResult(status=200, payload=None)

    # Register Callbacks
    http.post(api_commands["url"], callback=callback, repeat=True)
    http.post(api_commands["urlg2"], callback=callback, repeat=True)
    traeger_client = hass.data[DOMAIN][mock_config_entry.entry_id]
    for noti in traeger_client.notify:
        if traeger_client.notify[noti]["manu"] != manu:
            traeger_client.notify[noti] = {}
    await client_connect(hass, traeger_client, api_user_self["resp"]["things"])

    # Prep State
    mqtt_msg_change = traeger_client.mqtt_client.grills_status["0123456789ab"]
    mqtt_msg_change["status"]["system_status"] = 4
    mqtt_msg_change["status"]["grill"] = 165
    mqtt_msg_change["status"]["set"] = 165
    mqtt_msg_change["status"]["connected"] = True
    await client_publish(hass, traeger_client, mqtt_msg_change)

    # Cook Mode
    mqtt_msg_change = traeger_client.mqtt_client.grills_status["0123456789ab"]
    mqtt_msg_change["status"]["system_status"] = 6
    mqtt_msg_change["status"]["grill"] = 200
    mqtt_msg_change["status"]["set"] = 200
    mqtt_msg_change["status"]["connected"] = True
    await client_publish(hass, traeger_client, mqtt_msg_change)
    jsondata = http.last_request.kwargs.get("json", {})
    assert jsondata == snapshot(name="01-startlive")

    # Overtemp
    mqtt_msg_change = traeger_client.mqtt_client.grills_status["0123456789ab"]
    mqtt_msg_change["status"]["grill"] = 210
    mqtt_msg_change["status"]["connected"] = True
    await client_publish(hass, traeger_client, mqtt_msg_change)
    jsondata = http.last_request.kwargs.get("json", {})
    assert jsondata == snapshot(name="02-overtemp")

    # Undertemp
    mqtt_msg_change = traeger_client.mqtt_client.grills_status["0123456789ab"]
    mqtt_msg_change["status"]["grill"] = 190
    mqtt_msg_change["status"]["connected"] = True
    await client_publish(hass, traeger_client, mqtt_msg_change)
    jsondata = http.last_request.kwargs.get("json", {})
    assert jsondata == snapshot(name="03-undertemp")

    # AtTemp
    mqtt_msg_change = traeger_client.mqtt_client.grills_status["0123456789ab"]
    mqtt_msg_change["status"]["grill"] = 200
    mqtt_msg_change["status"]["connected"] = True
    await client_publish(hass, traeger_client, mqtt_msg_change)
    jsondata = http.last_request.kwargs.get("json", {})
    assert jsondata == snapshot(name="04-attemp")

@pytest.mark.usefixtures("socket_enabled")
@pytest.mark.parametrize(
    "manu",
    [
        ("Apple"),
        ("Google"),
    ],
)
async def test_mobile_app_manu_probe(
    manu,
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    connected_amqtt: Broker,
    snapshot: SnapshotAssertion,
    http: aiointercept,
) -> None:
    """Test Mobile App Live Updates for Probe"""

    def callback(url, **kwargs):
        """Setup API Callbacks"""
        _LOGGER.warning("Was at callbacks %s - %s", url, kwargs["json"])
        if kwargs["json"]["command"] == "90":
            mqtt_msg_change = copy.deepcopy(mqtt_msg)
        else:
            return CallbackResult(status=404, payload=None)
        # Publish Change
        traeger_client.mqtt_client.mqtt_client.publish(
            "prod/thing/update/0123456789ab",
            json.dumps(mqtt_msg_change).encode("utf-8"),
            qos=1,
        )
        return CallbackResult(status=200, payload=None)

    # Register Callbacks
    http.post(api_commands["url"], callback=callback, repeat=True)
    http.post(api_commands["urlg2"], callback=callback, repeat=True)
    traeger_client = hass.data[DOMAIN][mock_config_entry.entry_id]
    for noti in traeger_client.notify:
        if traeger_client.notify[noti]["manu"] != manu:
            traeger_client.notify[noti] = {}
    await client_connect(hass, traeger_client, api_user_self["resp"]["things"])

    # Prep State
    mqtt_msg_change = traeger_client.mqtt_client.grills_status["0123456789ab"]
    mqtt_msg_change["status"]["system_status"] = 4
    mqtt_msg_change["status"]["acc"][0]["probe"]["get_temp"] = 165
    mqtt_msg_change["status"]["acc"][0]["probe"]["set_temp"] = 165
    mqtt_msg_change["status"]["connected"] = True
    await client_publish(hass, traeger_client, mqtt_msg_change)

    # Cook Mode
    mqtt_msg_change = traeger_client.mqtt_client.grills_status["0123456789ab"]
    mqtt_msg_change["status"]["system_status"] = 6
    mqtt_msg_change["status"]["acc"][0]["probe"]["get_temp"] = 200
    mqtt_msg_change["status"]["acc"][0]["probe"]["set_temp"] = 200
    mqtt_msg_change["status"]["connected"] = True
    await client_publish(hass, traeger_client, mqtt_msg_change)
    jsondata = http.last_request.kwargs.get("json", {})
    assert jsondata == snapshot(name="01-startlive")

    # Overtemp
    mqtt_msg_change = traeger_client.mqtt_client.grills_status["0123456789ab"]
    mqtt_msg_change["status"]["acc"][0]["probe"]["get_temp"] = 210
    mqtt_msg_change["status"]["connected"] = True
    await client_publish(hass, traeger_client, mqtt_msg_change)
    jsondata = http.last_request.kwargs.get("json", {})
    assert jsondata == snapshot(name="02-overtemp")

    # Undertemp
    mqtt_msg_change = traeger_client.mqtt_client.grills_status["0123456789ab"]
    mqtt_msg_change["status"]["acc"][0]["probe"]["get_temp"] = 190
    mqtt_msg_change["status"]["connected"] = True
    await client_publish(hass, traeger_client, mqtt_msg_change)
    jsondata = http.last_request.kwargs.get("json", {})
    assert jsondata == snapshot(name="03-undertemp")

    # AtTemp
    mqtt_msg_change = traeger_client.mqtt_client.grills_status["0123456789ab"]
    mqtt_msg_change["status"]["acc"][0]["probe"]["get_temp"] = 200
    mqtt_msg_change["status"]["connected"] = True
    await client_publish(hass, traeger_client, mqtt_msg_change)
    jsondata = http.last_request.kwargs.get("json", {})
    assert jsondata == snapshot(name="04-attemp")
