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
import threading
import time
import urllib
import uuid

import aiohttp
import async_timeout
import homeassistant.const
import paho.mqtt.client as mqtt

TIMEOUT = 60

_LOGGER: logging.Logger = logging.getLogger(__package__)


class traeger:  # pylint: disable=invalid-name,too-many-instance-attributes,too-many-public-methods
    """Traeger API Wrapper"""

    def __init__(self, username, password, hass, request_library):
        self.username = username
        self.password = password
        self.mqtt_uuid = str(uuid.uuid1())
        self.mqtt_thread_running = False
        self.mqtt_thread = None
        self.mqtt_thread_refreshing = False
        self.grills_active = False
        self.grills = None
        self.hass = hass
        self.loop = hass.loop
        self.task = None
        self.mqtt_url = None
        self.mqtt_client = None
        self.grill_status = {}
        self.access_token = None
        self.token = None
        self.token_expires = 0
        self.mqtt_url_expires = time.time()
        self.request = request_library
        self.grill_callbacks = {}
        self.mqtt_client_inloop = False
        self.autodisconnect = False

    def __token_remaining(self):
        """Report remaining token time."""
        return self.token_expires - time.time()

    async def __do_cognito(self):
        """Intial API Login for MQTT Token GEN"""
        t = datetime.datetime.utcnow()
        _LOGGER.info("do_cognito t:%s", t)
        _LOGGER.info("do_cognito self.username:%s", self.username)
        return await self.__api_wrapper(
            "post",
            "https://auth-api.iot.traegergrills.io/tokens",
            data={
                "password": self.password,
                "username": self.username
            },
            headers={'content-type': 'application/json'})

    async def __refresh_token(self):
        """Refresh Token if expiration is soon."""
        if self.__token_remaining() < 60:
            request_time = time.time()
            response = await self.__do_cognito()
            _LOGGER.debug("Do Cognito Response: %s", response)
            try:
                self.token_expires = response["expiresIn"] + request_time
                self.token = response["idToken"]
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
                'authorization': self.token,
                'content-type': 'application/json'
            })

    async def __send_command(self, thingName, command):
        """
        Send Grill Commands to API.
        Command are via API and not MQTT.
        """
        _LOGGER.debug("Send Command Topic: %s, Send Command: %s", thingName,
                      command)
        await self.__refresh_token()
        api_url = "https://mobile-iot-api.iot.traegergrills.io"
        await self.__api_wrapper(
            "post_raw",
            f"{api_url}/things/{thingName}/commands",
            data={'command': command},
            headers={
                'authorization': self.token,
                "content-type": "application/json",
                "accept-language": "en-US",
                "user-agent": "Traeger/11 CFNetwork/1209 Darwin/20.2.0",
            })

    async def __update_state(self, thingName):
        """Update State"""
        await self.__send_command(thingName, "90")

    async def set_temperature(self, thingName, temp):
        """Set Grill Temp Setpoint"""
        await self.__send_command(thingName, f"11,{temp}")

    async def set_probe_temperature(self, thingName, temp):
        """Set Probe Temp Setpoint"""
        await self.__send_command(thingName, f"14,{temp}")

    async def set_switch(self, thingName, switchval):
        """Set Binary Switch"""
        await self.__send_command(thingName, str(switchval))

    async def shutdown_grill(self, thingName):
        """Request Grill Shutdown"""
        await self.__send_command(thingName, "17")

    async def set_timer_sec(self, thingName, time_s):
        """Set Timer in Seconds"""
        await self.__send_command(thingName, f"12,{time_s:05d}")

    async def reset_timer(self, thingName):
        """Reset Timer"""
        await self.__send_command(thingName, "13")

    async def __update_grills(self):
        """Get an update of available grills"""
        myjson = await self.get_user_data()
        self.grills = myjson["things"]

    def get_grills(self):
        """Get Grills from Class."""
        return self.grills

    def set_callback_for_grill(self, grill_id, callback):
        """Add to grill callbacks"""
        if grill_id not in self.grill_callbacks:
            self.grill_callbacks[grill_id] = []
        self.grill_callbacks[grill_id].append(callback)

    async def grill_callback(self, grill_id):
        """Do Grill Callbacks"""
        if grill_id in self.grill_callbacks:
            for callback in self.grill_callbacks[grill_id]:
                callback()

    def __mqtt_url_remaining(self):
        """Available MQTT time left."""
        return self.mqtt_url_expires - time.time()

    async def __refresh_mqtt_url(self):
        """Update MQTT Token"""
        await self.__refresh_token()
        if self.__mqtt_url_remaining() < 60:
            try:
                mqtt_request_time = time.time()
                myjson = await self.__api_wrapper(
                    "post",
                    "https://mobile-iot-api.iot.traegergrills.io/mqtt-connections",
                    headers={'Authorization': self.token})
                self.mqtt_url_expires = myjson["expirationSeconds"] + \
                    mqtt_request_time
                self.mqtt_url = myjson["signedUrl"]
            except KeyError as exception:
                _LOGGER.error("Key Error Failed to Parse MQTT URL %s - %s",
                              myjson, exception)
            except Exception as exception:  # pylint: disable=broad-except
                _LOGGER.error("Other Error Failed to Parse MQTT URL %s - %s",
                              myjson, exception)
        _LOGGER.debug("MQTT URL:%s Expires @:%s", self.mqtt_url,
                      self.mqtt_url_expires)

    def mqtt_connect_func(self):
        """
        MQTT Thread Function.
        Anything called from self.mqtt_client is not async and needs to be thread safe.
        """
        if self.mqtt_client is not None:
            _LOGGER.debug("Start MQTT Loop Forever")
            while self.mqtt_thread_running:
                self.mqtt_client_inloop = True
                self.mqtt_client.loop_forever()
                self.mqtt_client_inloop = False
                while (self.__mqtt_url_remaining() < 60 or
                       self.mqtt_thread_refreshing
                      ) and self.mqtt_thread_running:
                    time.sleep(1)
        _LOGGER.debug("Should be the end of the thread.")

    async def __get_mqtt_client(self):
        """Setup the MQTT Client and run in a thread."""
        await self.__refresh_mqtt_url()
        if self.mqtt_client is not None:
            _LOGGER.debug("ReInit Client")
        else:
            self.mqtt_client = mqtt.Client(transport="websockets")
            #self.mqtt_client.on_log = self.mqtt_onlog
            #logging passed via enable_logger this would be redundant.
            self.mqtt_client.on_connect = self.mqtt_onconnect
            self.mqtt_client.on_connect_fail = self.mqtt_onconnectfail
            self.mqtt_client.on_subscribe = self.mqtt_onsubscribe
            self.mqtt_client.on_message = self.mqtt_onmessage
            if _LOGGER.level <= 10:  #Add these callbacks only if our logging is Debug or less.
                self.mqtt_client.enable_logger(_LOGGER)
                self.mqtt_client.on_publish = self.mqtt_onpublish  #We dont Publish to MQTT
                self.mqtt_client.on_unsubscribe = self.mqtt_onunsubscribe
                self.mqtt_client.on_disconnect = self.mqtt_ondisconnect
                self.mqtt_client.on_socket_open = self.mqtt_onsocketopen
                self.mqtt_client.on_socket_close = self.mqtt_onsocketclose
                self.mqtt_client.on_socket_register_write = self.mqtt_onsocketregisterwrite
                self.mqtt_client.on_socket_unregister_write = self.mqtt_onsocketunregisterwrite
            context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
            context.check_hostname = False
            context.verify_mode = ssl.CERT_NONE
            self.mqtt_client.tls_set_context(context)
            self.mqtt_client.reconnect_delay_set(min_delay=10, max_delay=160)
        mqtt_parts = urllib.parse.urlparse(self.mqtt_url)
        headers = {
            "Host": "{0:s}".format(mqtt_parts.netloc),  # pylint: disable=consider-using-f-string
        }
        self.mqtt_client.ws_set_options(
            path=f"{mqtt_parts.path}?{mqtt_parts.query}", headers=headers)
        _LOGGER.info("Thread Active Count:%s", threading.active_count())
        self.mqtt_client.connect(mqtt_parts.netloc, 443, keepalive=300)
        if self.mqtt_thread_running is False:
            self.mqtt_thread = threading.Thread(target=self.mqtt_connect_func)
            self.mqtt_thread_running = True
            self.mqtt_thread.start()

#===========================Paho MQTT Functions=====================================================

    def mqtt_onlog(self, client, userdata, level, buf):
        """MQTT Thread on_log"""
        _LOGGER.debug("OnLog Callback. Client:%s userdata:%s level:%s buf:%s",
                      client, userdata, level, buf)

    def mqtt_onconnect(self, client, userdata, flags, rc):  # pylint: disable=unused-argument
        """MQTT Thread on_connect"""
        _LOGGER.info("Grill Connected")
        for grill in self.grills:
            grill_id = grill["thingName"]
            if grill_id in self.grill_status:
                del self.grill_status[grill_id]
            client.subscribe((f"prod/thing/update/{grill_id}", 1))

    def mqtt_onconnectfail(self, client, userdata):
        """MQTT Thread on_connect_fail"""
        _LOGGER.debug("Connect Fail Callback. Client:%s userdata:%s", client,
                      userdata)
        _LOGGER.warning("Grill Connect Failed! MQTT Client Kill.")
        asyncio.run_coroutine_threadsafe(
            self.kill(), self.loop)  #Shutdown if we arn't getting anywhere.

    def mqtt_onsubscribe(self, client, userdata, mid, granted_qos):
        """MQTT Thread on_subscribe"""
        _LOGGER.debug(
            "OnSubscribe Callback. Client:%s userdata:%s mid:%s granted_qos:%s",
            client, userdata, mid, granted_qos)

        for grill in self.grills:
            grill_id = grill["thingName"]
            if grill_id in self.grill_status:
                del self.grill_status[grill_id]
            asyncio.run_coroutine_threadsafe(self.__update_state(grill_id),
                                             self.loop)

    def mqtt_onmessage(self, client, userdata, message):  # pylint: disable=unused-argument
        """MQTT Thread on_message"""
        _LOGGER.debug("grill_message: message.topic = %s, message.payload = %s",
                      message.topic, message.payload)
        _LOGGER.info("Token Time Remaining:%s MQTT Time Remaining:%s",
                     self.__token_remaining(), self.__mqtt_url_remaining())
        if message.topic.startswith("prod/thing/update/"):
            grill_id = message.topic[len("prod/thing/update/"):]
            self.grill_status[grill_id] = json.loads(message.payload)
            asyncio.run_coroutine_threadsafe(self.grill_callback(grill_id),
                                             self.loop)
            if self.grills_active is False:  #Go see if any grills are doing work.
                for grill in self.grills:  #If nobody is working next MQTT refresh
                    grill_id = grill["thingName"]  #It'll call kill.
                    state = self.get_state_for_device(grill_id)
                    if state is None:
                        return
                    if state["connected"]:
                        if 4 <= state["system_status"] <= 8:
                            self.grills_active = True

    def mqtt_onpublish(self, client, userdata, mid):
        """MQTT Thread on_publish"""
        _LOGGER.debug("OnPublish Callback. Client:%s userdata:%s mid:%s",
                      client, userdata, mid)

    def mqtt_onunsubscribe(self, client, userdata, mid):
        """MQTT Thread on_unsubscribe"""
        _LOGGER.debug("OnUnsubscribe Callback. Client:%s userdata:%s mid:%s",
                      client, userdata, mid)

    def mqtt_ondisconnect(self, client, userdata, rc):
        """MQTT Thread on_undisconnect"""
        _LOGGER.debug("OnDisconnect Callback. Client:%s userdata:%s rc:%s",
                      client, userdata, rc)

    def mqtt_onsocketopen(self, client, userdata, sock):
        """MQTT Thread on_socketopen"""
        _LOGGER.debug("Sock.Open.Report...Client: %s UserData: %s Sock: %s",
                      client, userdata, sock)

    def mqtt_onsocketclose(self, client, userdata, sock):
        """MQTT Thread on_socketclose"""
        _LOGGER.debug("Sock.Clse.Report...Client: %s UserData: %s Sock: %s",
                      client, userdata, sock)

    def mqtt_onsocketregisterwrite(self, client, userdata, sock):
        """MQTT Thread on_socketregwrite"""
        _LOGGER.debug("Sock.Regi.Write....Client: %s UserData: %s Sock: %s",
                      client, userdata, sock)

    def mqtt_onsocketunregisterwrite(self, client, userdata, sock):
        """MQTT Thread on_socketunregwrite"""
        _LOGGER.debug("Sock.UnRg.Write....Client: %s UserData: %s Sock: %s",
                      client, userdata, sock)


#===========================/Paho MQTT Functions===================================================

    def get_state_for_device(self, thingName):
        """Get specifics of status"""
        if thingName not in self.grill_status:
            return None
        return self.grill_status[thingName]["status"]

    def get_details_for_device(self, thingName):
        """Get specifics of details"""
        if thingName not in self.grill_status:
            return None
        return self.grill_status[thingName]["details"]

    def get_limits_for_device(self, thingName):
        """Get specifics of limits"""
        if thingName not in self.grill_status:
            return None
        return self.grill_status[thingName]["limits"]

    def get_settings_for_device(self, thingName):
        """Get specifics of settings"""
        if thingName not in self.grill_status:
            return None
        return self.grill_status[thingName]["settings"]

    def get_features_for_device(self, thingName):
        """Get specifics of features"""
        if thingName not in self.grill_status:
            return None
        return self.grill_status[thingName]["features"]

    def get_cloudconnect(self, thingName):
        """Indicate wheather MQTT is connected."""
        if thingName not in self.grill_status:
            return False
        return self.mqtt_thread_running

    def get_units_for_device(self, thingName):
        """Parse what units the grill is operating in."""
        state = self.get_state_for_device(thingName)
        if state is None:
            return homeassistant.const.UnitOfTemperature.FAHRENHEIT
        if state["units"] == 0:
            return homeassistant.const.UnitOfTemperature.CELSIUS
        return homeassistant.const.UnitOfTemperature.FAHRENHEIT

    def get_details_for_accessory(self, thingName, accessory_id):
        """Get Details for Probes"""
        state = self.get_state_for_device(thingName)
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
        allow HA to finish starting up before lauching threads.
        """
        await self.__update_grills()
        self.grills_active = True
        _LOGGER.info("Call_Later in: %s seconds.", delay)
        self.task = self.loop.call_later(delay, self.__syncmain)

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
            self.mqtt_thread_refreshing = True
            if self.mqtt_thread_running:
                self.mqtt_client.disconnect()
                self.mqtt_client = None
            await self.__get_mqtt_client()
            self.mqtt_thread_refreshing = False
        _LOGGER.debug("Call_Later @: %s", self.mqtt_url_expires)
        delay = max(self.__mqtt_url_remaining(), 30)
        self.task = self.loop.call_later(delay, self.__syncmain)

    async def kill(self):
        """This terminates the main loop and shutsdown the thread."""
        if self.mqtt_thread_running:
            _LOGGER.info("Killing Task")
            _LOGGER.debug("Task Info: %s", self.task)
            self.task.cancel()
            _LOGGER.debug("Task Info: %s TaskCancelled Status: %s", self.task,
                          self.task.cancelled())
            self.task = None
            self.mqtt_thread_running = False
            self.mqtt_client.disconnect()
            while self.mqtt_client_inloop:  #Wait for disconnect to finish
                await asyncio.sleep(0.25)
            self.mqtt_url_expires = time.time()
            for grill in self.grills:  #Mark the grill(s) disconnected so they report unavail.
                grill_id = grill[
                    "thingName"]  #Also hit the callbacks to update HA
                self.grill_status[grill_id]["status"]["connected"] = False
                await self.grill_callback(grill_id)
        else:
            _LOGGER.info("Task Already Dead")

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
