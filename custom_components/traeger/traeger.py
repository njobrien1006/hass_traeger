"""
Library to interact with traeger grills

Copyright 2020 by Keith Baker All rights reserved.
This file is part of the traeger python library,
and is released under the "GNU GENERAL PUBLIC LICENSE Version 2".
Please see the LICENSE file that should have been included as part of this package.
"""

import asyncio
import datetime
import json
import logging
import socket
import ssl
import time
import urllib

import aiohttp
import async_timeout
import homeassistant.const

from homeassistant.components.mqtt.async_client import AsyncMQTTClient

TIMEOUT = 60

_LOGGER: logging.Logger = logging.getLogger(__package__)


class Traeger:
    """Traeger API Wrapper"""

    def __init__(self, username, password, hass, request_library):
        self._api = {
            "username": username,
            "password": password,
            "api_token": "",
            "api_expires": 0,
            "mqtt_url_expires": time.time(),
            "mqtt_url": None
        }
        self.hass = hass
        self.request = request_library

        self.loop_task = None
        self.grill_callbacks = {}

        self.grills = None
        self.mqtt_client = TraegerMQTTClient(self.hass,
                                        self.sync_grill_callback,
                                        self.sync_update_state)

    def __token_remaining(self):
        """Report remaining token time."""
        return self._api['api_expires'] - time.time()

    async def __do_cognito(self):
        """Intial API Login"""
        t = datetime.datetime.utcnow()
        _LOGGER.info("do_cognito t:%s", t)
        _LOGGER.info("do_cognito self.username:%s", self._api['username'])
        return await self.__api_wrapper(
            "post",
            "https://auth-api.iot.traegergrills.io/tokens",
            data={
                "password": self._api['password'],
                "username": self._api['username']
            },
            headers={'content-type': 'application/json'})

    async def __refresh_token(self):
        """Refresh Token if expiration is soon."""
        if self.__token_remaining() < 60:
            request_time = time.time()
            response = await self.__do_cognito()
            _LOGGER.debug("Do Cognito Response: %s", response)
            try:
                self._api['api_expires'] = response["expiresIn"] + request_time
                self._api['api_token'] = response["idToken"]
            except Exception as exception:  # pylint: disable=broad-except
                _LOGGER.error(
                    "We had an exception: %s \n \
                Do Cognito Response: %s", exception, response)

    async def get_user_data(self):
        """Get User Data."""
        await self.__refresh_token()
        return await self.__api_wrapper(
            "get",
            "https://mobile-iot-api.iot.traegergrills.io/users/self",
            headers={
                'authorization': self._api['api_token'],
                'content-type': 'application/json'
            })

    async def __send_command(self, thingname, command):
        """
        Send Grill Commands to API.
        Command are via API and not MQTT.
        """
        _LOGGER.debug("Send Command Topic: %s, Send Command: %s", thingname,
                      command)
        await self.__refresh_token()
        api_url = "https://mobile-iot-api.iot.traegergrills.io"
        await self.__api_wrapper(
            "post_raw",
            f"{api_url}/things/{thingname}/commands",
            data={'command': command},
            headers={
                'authorization': self._api['api_token'],
                "content-type": "application/json",
                "accept-language": "en-US",
                "user-agent": "Traeger/11 CFNetwork/1209 Darwin/20.2.0",
            })

    def sync_update_state(self, thingname):
        """Update State"""
        asyncio.run_coroutine_threadsafe(
            self.__update_state(thingname), self.hass.loop)

    async def __update_state(self, thingname):
        """Update State"""
        await self.__send_command(thingname, "90")

    async def set_temperature(self, thingname, temp):
        """Set Grill Temp Setpoint"""
        await self.__send_command(thingname, f"11,{temp}")

    async def set_probe_temperature(self, thingname, temp):
        """Set Probe Temp Setpoint"""
        await self.__send_command(thingname, f"14,{temp}")

    async def set_switch(self, thingname, switchval):
        """Set Binary Switch"""
        await self.__send_command(thingname, str(switchval))

    async def shutdown_grill(self, thingname):
        """Request Grill Shutdown"""
        await self.__send_command(thingname, "17")

    async def set_timer_sec(self, thingname, time_s):
        """Set Timer in Seconds"""
        await self.__send_command(thingname, f"12,{time_s:05d}")

    async def reset_timer(self, thingname):
        """Reset Timer"""
        await self.__send_command(thingname, "13")

    async def __update_grills(self):
        """Get an update of available grills"""
        myjson = await self.get_user_data()
        try:
            self.grills = myjson["things"]
        except Exception as exception:  # pylint: disable=broad-except
            _LOGGER.error(
                "We had an exception: %s \n \
            User Data Response: %s", exception, myjson)

    def get_grills(self):
        """Get Grills from Class."""
        return self.grills

    def set_callback_for_grill(self, grill_id, callback):
        """Add to grill callbacks"""
        if grill_id not in self.grill_callbacks:
            self.grill_callbacks[grill_id] = []
        self.grill_callbacks[grill_id].append(callback)

    def sync_grill_callback(self, grill_id):
        """Do Grill Callbacks"""
        asyncio.run_coroutine_threadsafe(
            self.grill_callback(grill_id), self.hass.loop)

    async def grill_callback(self, grill_id):
        """Do Grill Callbacks"""
        if grill_id in self.grill_callbacks:
            for callback in self.grill_callbacks[grill_id]:
                #_LOGGER.debug(f"Print: {callback}")
                callback()

    def __mqtt_url_remaining(self):
        """Available MQTT time left."""
        return self._api['mqtt_url_expires'] - time.time()

    async def __refresh_mqtt_url(self):
        """Update MQTT Token"""
        await self.__refresh_token()
        if self.__mqtt_url_remaining() < 60:
            try:
                mqtt_request_time = time.time()
                myjson = await self.__api_wrapper(
                    "post",
                    "https://mobile-iot-api.iot.traegergrills.io/mqtt-connections",
                    headers={'Authorization': self._api['api_token']})
                self._api['mqtt_url_expires'] = myjson["expirationSeconds"] + \
                    mqtt_request_time
                self._api['mqtt_url'] = myjson["signedUrl"]
            except KeyError as exception:
                _LOGGER.error("Key Error Failed to Parse MQTT URL %s - %s",
                              myjson, exception)
            except Exception as exception:  # pylint: disable=broad-except
                _LOGGER.error("Other Error Failed to Parse MQTT URL %s - %s",
                              myjson, exception)
        _LOGGER.debug("MQTT URL:%s Expires @:%s", self._api['mqtt_url'],
                      self._api['mqtt_url_expires'])

    async def __get_mqtt_client(self):
        """Setup the MQTT Client and let HA deal with it."""
        await self.__refresh_mqtt_url()
        _LOGGER.debug("Connect Client")
        await self.mqtt_client.connect(self.grills, self._api['mqtt_url'])

    def get_mqtt_msg_for_grill(self, thingname):
        """Get specifics of status"""
        if thingname not in self.mqtt_client.grills_status:
            return {}
        return self.mqtt_client.grills_status[thingname]

    def get_state_for_device(self, thingname):
        """Get specifics of status"""
        if thingname not in self.mqtt_client.grills_status:
            return None
        return self.mqtt_client.grills_status[thingname]["status"]

    def get_cloudconnect(self, thingname):
        """Indicate wheather MQTT is connected."""
        if thingname not in self.mqtt_client.grills_status:
            return False
        return self.mqtt_client.isconnected

    def get_units_for_device(self, thingname):
        """Parse what units the grill is operating in."""
        if thingname not in self.mqtt_client.grills_status:
            return homeassistant.const.UnitOfTemperature.FAHRENHEIT
        if self.mqtt_client.grills_status[thingname]["status"]["units"] == 0:
            return homeassistant.const.UnitOfTemperature.CELSIUS
        return homeassistant.const.UnitOfTemperature.FAHRENHEIT

    def get_details_for_accessory(self, thingname, accessory_id):
        """Get Details for Probes"""
        state = self.get_state_for_device(thingname)
        if state is None:
            return None
        for accessory in state["acc"]:
            if accessory["uuid"] == accessory_id:
                return accessory
        return None

    async def start(self, delay):
        """
        This is the entry point to start MQTT connect.
        It does have a delay before doing MQTT connect to
        allow HA to finish starting up before lauching MQTT.
        """
        await self.__update_grills()
        _LOGGER.info("Call_Later in: %s seconds.", delay)
        self.loop_task = self.hass.loop.call_later(delay, self.__syncmain)

    def __syncmain(self):
        """
        Small wrapper to switch from the call_later def back to the async loop
        """
        _LOGGER.debug("@Call_Later SyncMain CreatingTask for async Main.")
        self.hass.async_create_task(self.__main())

    async def __main(self):
        """This is the loop that keeps the tokens updated."""
        _LOGGER.debug("Current Main Loop Time: %s", time.time())
        _LOGGER.debug(
            "MQTT Logger Token Time Remaining:%s MQTT Time Remaining:%s",
            self.__token_remaining(), self.__mqtt_url_remaining())
        if self.__mqtt_url_remaining() < 60:
            if self.mqtt_client.isconnected:
                self.mqtt_client.disconnect()
            await self.__get_mqtt_client()
        _LOGGER.debug("Call_Later @: %s", self._api['mqtt_url_expires'])
        delay = max(self.__mqtt_url_remaining(), 30)
        self.loop_task = self.hass.loop.call_later(delay, self.__syncmain)

    async def kill(self):
        """This terminates the main loop and shutsdown the MQTT."""
        if self.mqtt_client.isconnected:
            _LOGGER.info("Killing Task")
            _LOGGER.debug("Task Info: %s", self.loop_task)
            self.loop_task.cancel()
            _LOGGER.debug("Task Info: %s TaskCancelled Status: %s", self.loop_task,
                        self.loop_task.cancelled())
            self.loop_task = None
            self.mqtt_client.disconnect()
            while self.mqtt_client.isconnected:  #Wait for disconnect to finish
                await asyncio.sleep(0.1)
            self._api['mqtt_url_expires'] = time.time()
            for grill in self.grills:  #Mark the grill(s) disconnected so they report unavail.
                grill_id = grill[
                    "thingName"]  #Also hit the callbacks to update HA
                self.mqtt_client.grills_status[grill_id]["status"]["connected"] = False
                await self.grill_callback(grill_id)
        else:
            _LOGGER.info("Client Was not Connected?")

    # pylint: disable=dangerous-default-value
    async def __api_wrapper(self,
                            method: str,
                            url: str,
                            data: dict = {},
                            headers: dict = {}) -> dict:
        """Get information from the API."""
        try:
            async with async_timeout.timeout(TIMEOUT):
                if method == "get":
                    response = await self.request.get(url, headers=headers)
                    data = await response.read()
                    return json.loads(data)

                if method == "post_raw":
                    await self.request.post(url, headers=headers, json=data)

                elif method == "post":
                    response = await self.request.post(url,
                                                       headers=headers,
                                                       json=data)
                    data = await response.read()
                    return json.loads(data)
        except asyncio.TimeoutError as exception:
            _LOGGER.error("Timeout error fetching information from %s - %s",
                          url, exception)
        except (KeyError, TypeError) as exception:
            _LOGGER.error("Error parsing information from %s - %s", url,
                          exception)
        except (aiohttp.ClientError, socket.gaierror) as exception:
            _LOGGER.error("Error fetching information from %s - %s", url,
                          exception)
        except Exception as exception:  # pylint: disable=broad-except
            _LOGGER.error("Something really wrong happend! - %s", exception)

class TraegerMQTTClient:
    """Traeger MQTT Wrapper"""
    def __init__(self, hass, callback, update_state):
        self.isconnected = False
        self.grills_status = {}

        self._hass = hass
        self._grills = {}

        self.grill_callback = callback
        self.update_state = update_state

        self.mqtt_client = AsyncMQTTClient(transport="websockets")
        self.mqtt_client.on_connect = self._mqtt_onconnect
        self.mqtt_client.on_subscribe = self._mqtt_onsubscribe
        self.mqtt_client.on_message = self._mqtt_onmessage
        if _LOGGER.level <= 10:  #Add these callbacks only if our logging is Debug or less.
            self.mqtt_client.enable_logger(_LOGGER)
            #self.mqtt_client.on_publish = self._mqtt_onpublish  #We dont Publish to MQTT
            self.mqtt_client.on_unsubscribe = self._mqtt_onunsubscribe
            self.mqtt_client.on_disconnect = self._mqtt_ondisconnect
            self.mqtt_client.on_socket_close = self._mqtt_onsocketclose
            self.mqtt_client.on_socket_unregister_write = self._mqtt_onsocketunregisterwrite
        context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
        context.check_hostname = False
        context.verify_mode = ssl.CERT_NONE
        self.mqtt_client.tls_set_context(context)
        self.mqtt_client.reconnect_delay_set(min_delay=10, max_delay=160)

    async def connect(self, grills, mqtt_url) -> None:
        """Call Connect"""
        self._grills = grills
        mqtt_parts = urllib.parse.urlparse(mqtt_url)
        headers = {
            "Host": "{0:s}".format(mqtt_parts.netloc),  # pylint: disable=consider-using-f-string
        }
        self.mqtt_client.ws_set_options(
            path=f"{mqtt_parts.path}?{mqtt_parts.query}", headers=headers)
        self.mqtt_client.connect_async(mqtt_parts.netloc, 443, keepalive=300)
        _LOGGER.debug("Starting Traeger MQTT Class")
        self.mqtt_client.loop_start()
        _LOGGER.debug("Started Traeger MQTT Class")

    def disconnect(self) -> None:
        """Call disconnect"""
        _LOGGER.debug("Stopping Traeger MQTT Class")
        self._hass.async_add_executor_job(self.mqtt_client.disconnect)
        _LOGGER.debug("Stopped Traeger MQTT Class")

    def _mqtt_onconnect(self, client, userdata, flags, rc):  # pylint: disable=unused-argument
        """MQTT on_connect"""
        self.isconnected = True
        _LOGGER.info("Grill Connected")
        for grill in self._grills:
            grill_id = grill["thingName"]
            if grill_id in self.grills_status:
                del self.grills_status[grill_id]
            _LOGGER.debug("Subscribe To: %s", grill_id)
            client.subscribe((f"prod/thing/update/{grill_id}", 1))

    def _mqtt_ondisconnect(self, client, userdata, rc):
        """MQTT on_undisconnect"""
        self.isconnected = False
        _LOGGER.debug("OnDisconnect Callback. Client:%s userdata:%s rc:%s",
                    client, userdata, rc)

    def _mqtt_onmessage(self, client, userdata, message):  # pylint: disable=unused-argument
        """MQTT on_message"""
        _LOGGER.debug("grill_message: message.topic = %s, message.payload = %s",
                    message.topic, message.payload)
        if message.topic.startswith("prod/thing/update/"):
            grill_id = message.topic[len("prod/thing/update/"):]
            self.grills_status[grill_id] = json.loads(message.payload)
            self.grill_callback(grill_id)

    def _mqtt_onpublish(self, client, userdata, mid):
        """MQTT on_publish"""
        _LOGGER.debug("OnPublish Callback. Client:%s userdata:%s mid:%s",
                    client, userdata, mid)

    def _mqtt_onsubscribe(self, client, userdata, mid, granted_qos):
        """MQTT on_subscribe"""
        _LOGGER.debug(
            "OnSubscribe Callback. Client:%s userdata:%s mid:%s granted_qos:%s",
            client, userdata, mid, granted_qos)
        for grill in self._grills:
            grill_id = grill["thingName"]
            if grill_id in self.grills_status:
                del self.grills_status[grill_id]
            self.update_state(grill_id)

    def _mqtt_onunsubscribe(self, client, userdata, mid):
        """MQTT on_unsubscribe"""
        _LOGGER.debug("OnUnsubscribe Callback. Client:%s userdata:%s mid:%s",
                    client, userdata, mid)

    def _mqtt_onsocketclose(self, client, userdata, sock):
        """MQTT on_socketclose"""
        _LOGGER.debug("Sock.Clse.Report...Client: %s UserData: %s Sock: %s",
                    client, userdata, sock)

    def _mqtt_onsocketunregisterwrite(self, client, userdata, sock):
        """MQTT on_socketunregwrite"""
        _LOGGER.debug("Sock.UnRg.Write....Client: %s UserData: %s Sock: %s",
                    client, userdata, sock)
