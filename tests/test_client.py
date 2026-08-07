"""Test the Traeger Client."""

import asyncio
import copy
import json
import logging
import pytest

from aiointercept import aiointercept, CallbackResult
from homeassistant.core import HomeAssistant

from homeassistant.const import ATTR_ENTITY_ID, SERVICE_TURN_ON, SERVICE_TURN_OFF

from pytest_homeassistant_custom_component.common import MockConfigEntry
from syrupy.assertion import SnapshotAssertion

from custom_components.traeger.const import DOMAIN

from .conftest import TraegerTestClient, Broker, MQTTPORT
from .zzMockResp import api_commands, api_token, api_mqtt, api_user_self, mqtt_msg

_LOGGER: logging.Logger = logging.getLogger(__package__)


# TestTraegerClient
async def test_handle_tokens(
    traeger_client: TraegerTestClient, http: aiointercept
) -> None:
    """test getting token"""
    http.clear()
    http.post(api_token["url"], payload=api_token["resp"])
    traeger_client.api["username"] = "JohnyTraeger@traeger.com"
    traeger_client.api["password"] = "abc123"
    response = await traeger_client.do_cognito()
    _LOGGER.warning("do cognito resp: %s", response)
    assert response.get("idToken", None) not in [None, ""]
    assert response.get("expiresIn", None) not in [None, ""]


async def test_handle_tokens_bad_user_pass(
    traeger_client: TraegerTestClient, http: aiointercept
) -> None:
    """test getting token with bad PAR"""
    http.clear()
    http.post(api_token["url"], payload={"error": "badpass"})
    traeger_client.api["username"] = ""
    traeger_client.api["password"] = ""
    response = await traeger_client.do_cognito()
    _LOGGER.warning("do cognito resp: %s", response)


async def test_handle_user(
    traeger_client: TraegerTestClient, http: aiointercept
) -> None:
    """test getting user data"""
    http.clear()
    http.post(api_token["url"], payload=api_token["resp"])
    http.get(api_user_self["url"], payload=api_user_self["resp"])
    traeger_client.api["username"] = "JohnyTraeger@traeger.com"
    traeger_client.api["password"] = "abc123"
    response = await traeger_client.get_user_data()
    _LOGGER.warning("do cognito resp: %s", response)
    assert response.get("username", None) not in [None, ""]
    assert response.get("things", None) not in [None, ""]


async def test_handle_user_bad(
    traeger_client: TraegerTestClient, http: aiointercept
) -> None:
    """test getting user data with bad data"""
    http.clear()
    http.post(api_token["url"], payload={"error": "badpass"})
    http.get(api_user_self["url"], payload={"error": "badtoken"})
    traeger_client.api["username"] = ""
    traeger_client.api["password"] = ""
    response = await traeger_client.get_user_data()
    _LOGGER.warning("do cognito resp: %s", response)


async def test_handle_mqtturl(
    traeger_client: TraegerTestClient, http: aiointercept
) -> None:
    """test getting mqtt url"""
    http.clear()
    http.post(api_token["url"], payload=api_token["resp"])
    http.post(api_mqtt["url"], payload=api_mqtt["resp"])
    traeger_client.api["username"] = "JohnyTraeger@traeger.com"
    traeger_client.api["password"] = "abc123"
    response = await traeger_client.refresh_mqtt_url()
    _LOGGER.warning("do cognito resp: %s", response)
    assert traeger_client.api["mqtt_url_expires"] not in [None, "", 0]
    assert traeger_client.api["mqtt_url"] not in [None, "", 0]


async def test_handle_mqtturl_bad(
    traeger_client: TraegerTestClient, http: aiointercept
) -> None:
    """test getting mqtt url bad"""
    http.clear()
    http.post(api_token["url"], payload={"error": "badpass"})
    http.post(api_mqtt["url"], payload={"error": "badtoken"})
    traeger_client.api["username"] = ""
    traeger_client.api["password"] = ""
    response = await traeger_client.refresh_mqtt_url()
    _LOGGER.warning("do cognito resp: %s", response)


async def test_handle_cmd(
    traeger_client: TraegerTestClient, http: aiointercept
) -> None:
    """test grill command"""
    http.clear()
    http.post(api_token["url"], payload=api_token["resp"])
    http.post(api_commands["url"], payload=api_commands["resp"])
    traeger_client.api["username"] = "JohnyTraeger@traeger.com"
    traeger_client.api["password"] = "abc123"
    response = await traeger_client.update_state("0123456789ab")
    _LOGGER.warning("do cognito resp: %s", response)
    assert True


async def test_handle_cmd_bad(
    traeger_client: TraegerTestClient, http: aiointercept
) -> None:
    """test grill command"""
    http.clear()
    http.post(api_token["url"], payload={"error": "badpass"})
    http.post(api_commands["url"], payload={"error": "badtoken"})
    traeger_client.api["username"] = "JohnyTraeger@traeger.com"
    traeger_client.api["password"] = None
    await traeger_client.update_state("0123456789ab")
    assert True


# pylint: disable=unused-argument
@pytest.mark.usefixtures("socket_enabled")
async def test_client_missing_sts(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    connected_amqtt: Broker,
    snapshot: SnapshotAssertion,
    http: aiointercept,
) -> None:
    """Test Bad MQTT formation"""

    def callback(url, **kwargs):
        """Setup API Callbacks"""
        _LOGGER.warning("Was at callbacks %s - %s", url, kwargs["json"])
        if kwargs["json"]["command"] == "90":
            traeger_client.mqtt_client.mqtt_client.publish(
                "prod/thing/update/0123456789ab",
                json.dumps(mqtt_msg).encode("utf-8"),
                qos=1,
            )
            return CallbackResult(status=400, payload=None)
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

    # Set Connected
    await asyncio.sleep(0.1)  # Sleep on it
    mqtt_msg_change = mqtt_msg
    mqtt_msg_change["status"]["connected"] = True
    traeger_client.mqtt_client.mqtt_client.publish(  # The actual change
        "prod/thing/update/0123456789ab",
        json.dumps(mqtt_msg_change).encode("utf-8"),
        qos=1,
    )
    await asyncio.sleep(0.1)
    await hass.async_block_till_done()
    grill_msg = traeger_client.mqtt_client.grills_status.get("0123456789ab", {})
    assert grill_msg["status"]

    # Set Null Status
    await asyncio.sleep(0.1)  # Sleep on it
    mqtt_msg_change = copy.deepcopy(mqtt_msg)
    mqtt_msg_change.pop("status", None)
    traeger_client.mqtt_client.mqtt_client.publish(  # The actual change
        "prod/thing/update/0123456789ab",
        json.dumps(mqtt_msg_change).encode("utf-8"),
        qos=1,
    )
    await asyncio.sleep(0.1)
    await hass.async_block_till_done()
    grill_msg = traeger_client.mqtt_client.grills_status.get("0123456789ab", {})
    _LOGGER.warning("Bad Grill MSG: %s", grill_msg)
    assert not grill_msg.get("status", False)

    # Set UnConnected
    await asyncio.sleep(0.1)  # Sleep on it
    mqtt_msg_change = mqtt_msg
    mqtt_msg_change["status"]["connected"] = False
    traeger_client.mqtt_client.mqtt_client.publish(  # The actual change
        "prod/thing/update/0123456789ab",
        json.dumps(mqtt_msg_change).encode("utf-8"),
        qos=1,
    )
    await asyncio.sleep(0.1)
    await hass.async_block_till_done()
    grill_msg = traeger_client.mqtt_client.grills_status.get("0123456789ab", {})
    assert grill_msg["status"]

    # Shut it down
    await asyncio.sleep(0.1)
    traeger_client.mqtt_client.disconnect()
    await asyncio.sleep(0.1)

@pytest.mark.usefixtures("socket_enabled")
async def test_connect_cmds(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    connected_amqtt: Broker,
    snapshot: SnapshotAssertion,
    http: aiointercept,
) -> None:
    """test switch connect cmds"""

    def callback(url, **kwargs):
        """Setup API Callbacks"""
        _LOGGER.error("Was at callbacks %s - %s", url, kwargs["json"])
        if kwargs["json"]["command"] == "90":
            traeger_client.mqtt_client.mqtt_client.publish(
                "prod/thing/update/0123456789ab",
                json.dumps(mqtt_msg).encode("utf-8"),
                qos=1,
            )
            traeger_client.mqtt_client.mqtt_client.publish(
                "prod/thing/update/cd0123456789",
                json.dumps(mqtt_msg).encode("utf-8"),
                qos=1,
            )
            return CallbackResult(status=400, payload=None)
        return CallbackResult(status=404, payload=None)

    # Register Callbacks
    http.post(api_commands["url"], callback=callback, repeat=True)
    http.post(api_commands["urlg2"], callback=callback, repeat=True)
    traeger_client = hass.data[DOMAIN][mock_config_entry.entry_id]
    traeger_client.mqtt_client.ssl = False
    traeger_client.mqtt_client.port = MQTTPORT
    await hass.services.async_call(
        "switch",
        SERVICE_TURN_ON,
        {ATTR_ENTITY_ID: "switch.traeger_0123456789ab_connect"},
        blocking=True,
    )
    await hass.async_block_till_done()
    await asyncio.sleep(2)

    # Get Entity Trig Check
    entity = hass.states.get("switch.traeger_0123456789ab_connect")
    # Check Enttity
    assert traeger_client.mqtt_client.isconnected
    assert entity.state == "on"
    assert entity == snapshot(name="01-On")

    await hass.services.async_call(
        "switch",
        SERVICE_TURN_OFF,
        {ATTR_ENTITY_ID: "switch.traeger_0123456789ab_connect"},
        blocking=True,
    )
    await hass.async_block_till_done()
    await asyncio.sleep(1)

    # Get Entity Trig Check
    entity = hass.states.get("switch.traeger_0123456789ab_connect")
    # Check Enttity
    assert not traeger_client.mqtt_client.isconnected
    assert entity.state == "off"
    assert entity == snapshot(name="02-Off")

    # No Need to shutdown
    #await asyncio.sleep(0.1)
    #traeger_client.mqtt_client.disconnect()
    #await asyncio.sleep(0.1)
