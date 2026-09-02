"""Binary Sensor platform for Traeger."""

import logging

_LOGGER: logging.Logger = logging.getLogger(__package__)

from .const import DOMAIN, GRILL_MODE
from .entity import TraegerBaseEntity
from .notify_helper import (
    notifyclearliveupdate,
    notifydevices,
    notifystartliveupdate_time,
)


async def async_setup_entry(hass, entry, async_add_entities):
    """Setup Binary Sensor platform."""
    client = hass.data[DOMAIN][entry.entry_id]
    grills = client.get_grills()
    entities = []
    for grill in grills:
        entities.append(
            TraegerTimer(
                client, grill["thingName"], "Cook Timer Complete", "cook_timer_complete"
            )
        )
        entities.append(
            TraegerSysTimer(
                client,
                grill["thingName"],
                "System Timer Complete",
                "sys_timer_complete",
            )
        )
        entities.append(
            TraegerProbe(
                client, grill["thingName"], "Probe Alarm Fired", "probe_alarm_fired"
            )
        )
    if entities:
        async_add_entities(entities)


class TraegerBaseSensor(TraegerBaseEntity):
    """Base Binary Sensor Class Common to All"""

    def __init__(self, client, grill_id, friendly_name, devid):
        super().__init__(client, grill_id)
        self.devid = devid
        self.value = None
        self.grill_timer_val = 0
        self.grill_sts = 0
        self.grill_name = ""
        self.friendly_name = friendly_name
        self.grill_register_callback()

    # Generic Properties
    @property
    def icon(self):
        """Set the default MDI Icon"""
        return "mdi:timer"

    # Generic Properties
    @property
    def available(self):
        """Reports unavailable when the grill is powered off"""
        if self.grill_mqtt_msg.get("status", None) is None:
            return False
        return self.grill_mqtt_msg["status"]["connected"]

    @property
    def name(self):
        """Return the name of the grill"""
        if self.grill_mqtt_msg.get("details", None) is None:
            return f"{self.grill_id} {self.friendly_name}"
        self.grill_name = self.grill_mqtt_msg["details"]["friendlyName"]
        return f"{self.grill_name} {self.friendly_name}"

    @property
    def unique_id(self):
        """Return the unique id."""
        return f"{self.grill_id}_{self.devid}"

    # Sensor Properties
    @property
    def state(self):
        """Return the state of the binary sensor."""
        if (
            not self.value
            and self.value is not None
            and self.grill_mqtt_msg["status"][self.devid]
        ):
            notifydevices(
                self.notify,
                self.hass,
                title=f"{self.friendly_name}",
                msg=f"Probe is done on {self.grill_name}",
            )
        self.value = self.grill_mqtt_msg["status"][self.devid]
        return self.value


class TraegerTimer(TraegerBaseSensor):
    """Binary Sensor Specific to Timer"""

    # Sensor Properties
    @property
    def state(self):
        """Return the state of the binary sensor."""
        if not self.grill_timer_val and self.grill_mqtt_msg["status"]["cook_timer_end"]:
            notifystartliveupdate_time(
                self.notify,
                self.hass,
                title=f"{self.grill_name} Cook Timer",
                msg="Cook timer is in progress",
                tag=self.unique_id,
                unix=self.grill_mqtt_msg["status"]["cook_timer_end"],
            )
        if (
            not self.value
            and self.value is not None
            and self.grill_mqtt_msg["status"][self.devid]
        ):
            notifyclearliveupdate(self.notify, self.hass, tag=self.unique_id)
            notifydevices(
                self.notify,
                self.hass,
                title=f"{self.friendly_name}",
                msg=f"Timer is done on {self.grill_name}",
            )
            self.grill_timer_val = 0
        if self.grill_timer_val > 0 and self.grill_mqtt_msg["status"]["cook_timer_end"] == 0:
            notifyclearliveupdate(self.notify, self.hass, tag=self.unique_id)
        self.grill_timer_val = self.grill_mqtt_msg["status"]["cook_timer_end"]
        self.value = self.grill_mqtt_msg["status"][self.devid]
        return self.value


class TraegerSysTimer(TraegerBaseSensor):
    """Binary Sensor Specific to System Timer"""

    # Sensor Properties
    @property
    def state(self):
        """Return the state of the binary sensor."""
        if not self.grill_timer_val and self.grill_mqtt_msg["status"]["sys_timer_end"]:
            notifystartliveupdate_time(
                self.notify,
                self.hass,
                title=f"{self.grill_name} {GRILL_MODE[self.grill_sts]}",
                msg="System timer is in progress",
                tag=self.unique_id,
                unix=self.grill_mqtt_msg["status"]["sys_timer_end"],
            )
        if (
            not self.value
            and self.value is not None
            and self.grill_mqtt_msg["status"][self.devid]
        ):
            notifyclearliveupdate(self.notify, self.hass, tag=self.unique_id)
            notifydevices(
                self.notify,
                self.hass,
                title=f"{self.friendly_name}",
                msg=f"{self.grill_name} is done {GRILL_MODE[self.grill_sts]}",
            )
            self.grill_timer_val = 0
        if self.grill_timer_val > 0 and self.grill_mqtt_msg["status"]["sys_timer_end"] == 0:
            notifyclearliveupdate(self.notify, self.hass, tag=self.unique_id)
        self.grill_timer_val = self.grill_mqtt_msg["status"]["sys_timer_end"]
        self.grill_sts = self.grill_mqtt_msg["status"]["system_status"]
        self.value = self.grill_mqtt_msg["status"][self.devid]
        return self.value


class TraegerProbe(TraegerBaseSensor):
    """Binary Sensor Specific to Probe"""

    # Generic Properties
    @property
    def icon(self):
        """Set the default MDI Icon"""
        return "mdi:thermometer"
