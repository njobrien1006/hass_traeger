"""Tests for the binary sensor platform."""

import logging
import time

import pytest
from aiointercept import aiointercept
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry
from pytest_homeassistant_custom_component.common import MockConfigEntry
from syrupy.assertion import SnapshotAssertion

from custom_components.traeger.const import DOMAIN

from .zzcommon import CallbackAPI, client_connect, client_disconnect, client_publish
from .zzMockResp import api_user_self

_LOGGER: logging.Logger = logging.getLogger(__package__)


async def test_mobile_app_platform(
    hass: HomeAssistant,
    mock_config_entry_mobile_app: MockConfigEntry,
    snapshot: SnapshotAssertion,
) -> None:
    """Test the mobile app platform setup."""
    # pylint: disable=unused-argument

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
async def test_mobile_app_manu_sys(
    manu,
    hass: HomeAssistant,
    mock_config_entry_mobile_app: MockConfigEntry,
    snapshot: SnapshotAssertion,
    http: aiointercept,
) -> None:
    """Test Mobile App Live Updates for Sys Timer"""
    # pylint: disable=too-many-statements

    traeger_client = hass.data[DOMAIN][mock_config_entry_mobile_app.entry_id]
    CallbackAPI(traeger_client, http)

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
    assert jsondata["data"].get("live_update", False)
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
    assert jsondata["data"].get("live_update", False)
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

    # Cleared
    mqtt_msg_change = traeger_client.mqtt_client.grills_status["0123456789ab"]
    mqtt_msg_change["status"]["system_status"] = 2
    mqtt_msg_change["status"]["connected"] = True
    await client_publish(hass, traeger_client, mqtt_msg_change)
    jsondata = {}
    for req in reversed(http.ordered_requests):
        if "home" in str(req[0][1]):
            reqdata = req[1].kwargs.get("json", {"data": {"tag": ""}})
            if reqdata["data"]["tag"] == "0123456789ab_sys_timer_complete":
                jsondata = reqdata
                break
    assert jsondata["message"] == "clear_notification"
    assert jsondata == snapshot(name="05-clear")

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
    mock_config_entry_mobile_app: MockConfigEntry,
    snapshot: SnapshotAssertion,
    http: aiointercept,
) -> None:
    """Test Mobile App Live Updates for Cook Timer"""

    traeger_client = hass.data[DOMAIN][mock_config_entry_mobile_app.entry_id]
    CallbackAPI(traeger_client, http)

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
    assert jsondata["data"].get("live_update", False)
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

    # Cleared
    mqtt_msg_change = traeger_client.mqtt_client.grills_status["0123456789ab"]
    mqtt_msg_change["status"]["system_status"] = 2
    mqtt_msg_change["status"]["connected"] = True
    await client_publish(hass, traeger_client, mqtt_msg_change)
    jsondata = {}
    for req in reversed(http.ordered_requests):
        if "home" in str(req[0][1]):
            reqdata = req[1].kwargs.get("json", {"data": {"tag": ""}})
            if reqdata["data"]["tag"] == "0123456789ab_cook_timer_complete":
                jsondata = reqdata
                break
    assert jsondata["message"] == "clear_notification"
    assert jsondata == snapshot(name="03-clear")

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
    mock_config_entry_mobile_app: MockConfigEntry,
    snapshot: SnapshotAssertion,
    http: aiointercept,
) -> None:
    """Test Mobile App Live Updates for Grill Climate"""

    traeger_client = hass.data[DOMAIN][mock_config_entry_mobile_app.entry_id]
    CallbackAPI(traeger_client, http)

    for noti in traeger_client.notify:
        if traeger_client.notify[noti]["manu"] != manu:
            traeger_client.notify[noti] = {}
    await client_connect(hass, traeger_client, api_user_self["resp"]["things"])

    for item in [
        {"sts": 4, "grill": 165, "set": 165, "con": True, "snap": None},
        {"sts": 6, "grill": 200, "set": 200, "con": None, "snap": "01-startlive"},
        {"sts": 0, "grill": 210, "set": 0, "con": None, "snap": "02-overtemp"},
        {"sts": 0, "grill": 190, "set": 0, "con": None, "snap": "03-undertemp"},
        {"sts": 0, "grill": 200, "set": 0, "con": None, "snap": "04-attemp"},
    ]:
        mqtt_msg_change = traeger_client.mqtt_client.grills_status["0123456789ab"]
        if item["sts"]:
            mqtt_msg_change["status"]["system_status"] = item["sts"]
        if item["grill"]:
            mqtt_msg_change["status"]["grill"] = item["grill"]
        if item["set"]:
            mqtt_msg_change["status"]["set"] = item["set"]
        if item["con"]:
            mqtt_msg_change["status"]["connected"] = item["con"]
        await client_publish(hass, traeger_client, mqtt_msg_change)
        if item["snap"]:
            jsondata = http.last_request.kwargs.get("json", {})
            assert jsondata == snapshot(name=item["snap"])

    # Cleared
    mqtt_msg_change = traeger_client.mqtt_client.grills_status["0123456789ab"]
    mqtt_msg_change["status"]["system_status"] = 2
    await client_publish(hass, traeger_client, mqtt_msg_change)
    jsondata = {}
    for req in reversed(http.ordered_requests):
        if "home" in str(req[0][1]):
            reqdata = req[1].kwargs.get("json", {"data": {"tag": ""}})
            if reqdata["data"]["tag"] == "0123456789ab_climate":
                jsondata = reqdata
                break
    assert jsondata["message"] == "clear_notification"
    assert jsondata == snapshot(name="05-clear")

    await client_disconnect(hass, traeger_client)


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
    mock_config_entry_mobile_app: MockConfigEntry,
    snapshot: SnapshotAssertion,
    http: aiointercept,
) -> None:
    """Test Mobile App Live Updates for Probe"""

    traeger_client = hass.data[DOMAIN][mock_config_entry_mobile_app.entry_id]
    CallbackAPI(traeger_client, http)

    for noti in traeger_client.notify:
        if traeger_client.notify[noti]["manu"] != manu:
            traeger_client.notify[noti] = {}
    await client_connect(hass, traeger_client, api_user_self["resp"]["things"])

    for item in [
        {"sts": 4, "get": 165, "set": 165, "con": True, "snap": None},
        {"sts": 6, "get": 200, "set": 200, "con": None, "snap": "01-startlive"},
        {"sts": 0, "get": 210, "set": 0, "con": None, "snap": "02-overtemp"},
        {"sts": 0, "get": 190, "set": 0, "con": None, "snap": "03-undertemp"},
        {"sts": 0, "get": 200, "set": 0, "con": None, "snap": "04-attemp"},
    ]:
        mqtt_msg_change = traeger_client.mqtt_client.grills_status["0123456789ab"]
        if item["sts"]:
            mqtt_msg_change["status"]["system_status"] = item["sts"]
        if item["get"]:
            mqtt_msg_change["status"]["acc"][0]["probe"]["get_temp"] = item["get"]
        if item["set"]:
            mqtt_msg_change["status"]["acc"][0]["probe"]["set_temp"] = item["set"]
        if item["con"]:
            mqtt_msg_change["status"]["connected"] = item["con"]
        await client_publish(hass, traeger_client, mqtt_msg_change)
        if item["snap"]:
            jsondata = http.last_request.kwargs.get("json", {})
            assert jsondata == snapshot(name=item["snap"])

    # Cleared
    mqtt_msg_change = traeger_client.mqtt_client.grills_status["0123456789ab"]
    mqtt_msg_change["status"]["system_status"] = 2
    await client_publish(hass, traeger_client, mqtt_msg_change)
    jsondata = {}
    for req in reversed(http.ordered_requests):
        if "home" in str(req[0][1]):
            reqdata = req[1].kwargs.get("json", {"data": {"tag": ""}})
            if reqdata["data"]["tag"] == "0123456789ab_probe_p0":
                jsondata = reqdata
                break
    assert jsondata == snapshot(name="05-clear")

    await client_disconnect(hass, traeger_client)
