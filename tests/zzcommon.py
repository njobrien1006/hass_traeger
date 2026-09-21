"""Common Test Functions"""

import asyncio
import copy
import json
import logging

from aiointercept import CallbackResult

from custom_components.traeger.const import GRILL_MODE

from .conftest import MQTTPORT
from .zzMockResp import api_commands, mqtt_msg

_LOGGER: logging.Logger = logging.getLogger(__package__)


async def client_connect(hass, client, grill_list):
    """Connect to MQTT Client"""
    # client.mqtt_client.ssl = False
    client.mqtt_client.port = MQTTPORT
    await client.mqtt_client.connect(
        grill_list,
        "wss://127.0.0.1/mqtt?1391charsWORTHofCreds",
    )
    await hass.async_block_till_done()
    await asyncio.sleep(0.4)


async def client_publish(hass, client, msg, dly=0.05):
    """Publish to MQTT Client"""
    await asyncio.sleep(dly / 4)
    client.mqtt_client.mqtt_client.publish(
        "prod/thing/update/0123456789ab",
        json.dumps(msg).encode("utf-8"),
        qos=0,
    )
    await hass.async_block_till_done()
    await asyncio.sleep(dly)


async def client_disconnect(hass, client):
    """Disconnect from MQTT Client"""
    await hass.async_block_till_done()
    await client.mqtt_client.disconnect()
    await hass.async_block_till_done()
    await asyncio.sleep(0.1)


class CallbackAPI:
    """Callbacks for grill"""

    # pylint: disable=too-many-branches,too-many-statements,too-few-public-methods
    def __init__(self, traeger_client, http):
        self.traeger_client = traeger_client
        http.post(api_commands["url"], callback=self.callback, repeat=True)
        http.post(api_commands["urlg2"], callback=self.callback, repeat=True)

    def callback(self, url, **kwargs):
        """Setup API Callbacks"""
        end = str(url).rfind("/", 0)
        strt = str(url).rfind("/", 0, end)
        _LOGGER.warning(
            "Was at callbacks %s - %s - %s",
            url,
            kwargs["json"],
            str(url)[strt + 1 : end],
        )

        if self.traeger_client.mqtt_client.grills_status == {}:
            mqtt_msg_change = copy.deepcopy(mqtt_msg)
        else:
            mqtt_msg_change = self.traeger_client.mqtt_client.grills_status[
                "0123456789ab"
            ]
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
        elif cmdsplit[0] == "12":
            mqtt_msg_change["status"]["time"] = 1577836800
            mqtt_msg_change["status"]["cook_timer_start"] = 1577836800
            mqtt_msg_change["status"]["cook_timer_end"] = 1577836800 + int(cmdsplit[1])
        elif kwargs["json"]["command"] == "13":
            mqtt_msg_change["status"]["time"] = 0
            mqtt_msg_change["status"]["cook_timer_start"] = 0
            mqtt_msg_change["status"]["cook_timer_end"] = 0
        elif cmdsplit[0] == "14":
            mqtt_msg_change["status"]["acc"][0]["probe"]["set_temp"] = int(cmdsplit[1])
            mqtt_msg_change["status"]["acc"][0]["probe"]["get_temp"] = (
                int(cmdsplit[1]) / 2
            )
            mqtt_msg_change["status"]["probe"] = int(cmdsplit[1]) / 2
        elif cmdsplit[0] == "120" and len(cmdsplit) == 4:
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
        elif kwargs["json"]["command"] == "17":
            mqtt_msg_change["status"]["system_status"] = GRILL_MODE["CoolingDown"]
        elif kwargs["json"]["command"] == "18":
            mqtt_msg_change["status"]["keepwarm"] = 1
        elif kwargs["json"]["command"] == "19":
            mqtt_msg_change["status"]["keepwarm"] = 0
        elif kwargs["json"]["command"] == "20":
            mqtt_msg_change["status"]["smoke"] = 1
        elif kwargs["json"]["command"] == "21":
            mqtt_msg_change["status"]["smoke"] = 0
        elif kwargs["json"]["command"] == "90":
            mqtt_msg_change = copy.deepcopy(mqtt_msg)
        else:
            return CallbackResult(status=404, payload=None)
        # Publish Change
        self.traeger_client.mqtt_client.mqtt_client.publish(
            "prod/thing/update/0123456789ab",
            json.dumps(mqtt_msg_change).encode("utf-8"),
            qos=1,
        )
        return CallbackResult(status=200, payload=None)
