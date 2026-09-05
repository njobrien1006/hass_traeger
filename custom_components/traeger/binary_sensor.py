"""Binary Sensor platform for Traeger."""

import logging

_LOGGER: logging.Logger = logging.getLogger(__package__)

from .const import DOMAIN, GRILL_MODE
from .entity import TraegerBaseEntity, TraegerGrillMonitor
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
        grill_id = grill["thingName"]
        entities.append(
            TraegerTimer(
                client, grill_id, "Cook Timer Complete", "cook_timer_complete"
            )
        )
        entities.append(
            TraegerSysTimer(
                client,
                grill_id,
                "System Timer Complete",
                "sys_timer_complete",
            )
        )
        entities.append(
            TraegerProbe(
                client, grill_id, "Probe Alarm Fired", "probe_alarm_fired"
            )
        )
        TraegerGrillMonitor(client, grill_id, async_add_entities,
                                    AccessoryTraegerBSensorEntity)
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
                title=f"{self.grill_name} "
                f"{GRILL_MODE[self.grill_mqtt_msg['status']['system_status']]}",
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

class AccessoryTraegerBSensorEntity(TraegerBaseSensor):
    """Binary Sensor entity for Traeger grills"""

    def __init__(self, client, grill_id, sensor_id):
        super().__init__(client, grill_id, "Probe Alarm", f"Probe_alarm {sensor_id}")
        self.sensor_id = sensor_id
        self.entity_id = (
            f"binary_sensor.{self.grill_id.lower()}_probe_"
            f"alarm_{self.sensor_id.lower()}"
        )
        self.grill_accessory = self.client.get_details_for_accessory(
            self.grill_id, self.sensor_id
        )

        # Tell the Traeger client to call grill_accessory_update() when it gets an update
        self.client.set_callback_for_grill(self.grill_id, self.grill_accessory_update)

    def grill_accessory_update(self):
        """This gets called when the grill has an update. Update state variable"""
        self.grill_refresh_state()
        self.grill_accessory = self.client.get_details_for_accessory(
            self.grill_id, self.sensor_id)

        if self.hass is None:
            return

        # Tell HA we have an update
        self.schedule_update_ha_state()

    # Generic Properties
    @property
    def available(self):
        """Reports unavailable when the grill is powered off"""
        if (
            self.grill_mqtt_msg.get("status", None) is None
            or self.grill_mqtt_msg["status"]["connected"] is False
            or self.grill_accessory is None
            or "alarm_fired" not in self.grill_accessory[self.grill_accessory["type"]]
        ):
            return False
        return self.grill_accessory["con"]

    @property
    def unique_id(self):
        """Return the unique id."""
        return f"{self.grill_id}_probe_alarm_{self.sensor_id}"

    @property
    def icon(self):
        """Set the default MDI Icon"""
        return "mdi:thermometer"

    # Sensor Properties
    @property
    def state(self):
        acc_type = self.grill_accessory["type"]
        if "alarm_fired" in self.grill_accessory[acc_type]:
            return self.grill_accessory[acc_type]["alarm_fired"]
        return False
