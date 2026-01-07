"""Sensor platform for Traeger."""
from datetime import datetime, timezone
from homeassistant.const import EntityCategory, UnitOfTemperature
from homeassistant.components.sensor import SensorDeviceClass, SensorEntity

from .const import (DOMAIN, GRILL_MIN_TEMP_C, GRILL_MIN_TEMP_F,
                    GRILL_MODE_COOL_DOWN, GRILL_MODE_CUSTOM_COOK,
                    GRILL_MODE_IDLE, GRILL_MODE_IGNITING,
                    GRILL_MODE_MANUAL_COOK, GRILL_MODE_OFFLINE,
                    GRILL_MODE_PREHEATING, GRILL_MODE_SHUTDOWN,
                    GRILL_MODE_SLEEPING)
from .entity import TraegerBaseEntity, TraegerGrillMonitor

SENSOR_ENTITIES = {
    "Ambient Temperature": {
        "json_loca": "status;ambient",
        "unit": "temp",
        "icon": "mdi:thermometer",
        "device_class": SensorDeviceClass.TEMPERATURE
    },
    "Grill Connected": {
        "json_loca": "status;connected",
        "unit": "",
        "icon": "mdi:lan-connect",
        "enabledbydflt": False
    },
    "Cook ID": {
        "json_loca": "status;cook_id",
        "unit": None,
        "icon": "mdi:food",
        "enabledbydflt": False
    },
    "Cook Timer End": {
        "json_loca": "status;cook_timer_end",
        "unit": None,
        "icon": "mdi:timer",
        "device_class": SensorDeviceClass.TIMESTAMP
    },
    "Cook Timer Start": {
        "json_loca": "status;cook_timer_start",
        "unit": None,
        "icon": "mdi:timer",
        "device_class": SensorDeviceClass.TIMESTAMP
    },
    "Current Cycle": {
        "json_loca": "status;current_cycle",
        "unit": "",
        "icon": "mdi:food",
        "enabledbydflt": False
    },
    "Current Step": {
        "json_loca": "status;current_step",
        "unit": "",
        "icon": "mdi:food",
        "enabledbydflt": False
    },
    "Errors": {
        "json_loca": "status;errors",
        "unit": "",
        "icon": "mdi:alert-circle",
        "enabledbydflt": False
    },
    "Pellet Level": {
        "json_loca": "status;pellet_level",
        "unit": "%",
        "icon": "mdi:gauge"
    },
    "Server Status": {
        "json_loca": "status;server_status",
        "unit": "",
        "icon": "mdi:alert-circle",
        "enabledbydflt": False
    },
    "Sys Timer End": {
        "json_loca": "status;sys_timer_end",
        "unit": "",
        "icon": "mdi:timer",
        "enabledbydflt": False,
        "device_class": SensorDeviceClass.TIMESTAMP
    },
    "Sys Timer Start": {
        "json_loca": "status;sys_timer_start",
        "unit": "",
        "icon": "mdi:timer",
        "enabledbydflt": False,
        "device_class": SensorDeviceClass.TIMESTAMP
    },
    "Grill Time": {
        "json_loca": "status;time",
        "unit": None,
        "icon": "mdi:clock-time-twelve-outline",
        "enabledbydflt": False,
        "device_class": SensorDeviceClass.TIMESTAMP
    },
    "Auger Runtime": {
        "json_loca": "usage;auger",
        "unit": "sec",
        "icon": "mdi:timer",
        "enabledbydflt": False
    },
    "Fan Runtime": {
        "json_loca": "usage;fan",
        "unit": "sec",
        "icon": "mdi:timer",
        "enabledbydflt": False
    },
    "Grill Runtime": {
        "json_loca": "usage;runtime",
        "unit": "sec",
        "icon": "mdi:timer",
        "enabledbydflt": False
    },
    "Hotrod Runtime": {
        "json_loca": "usage;hotrod",
        "unit": "sec",
        "icon": "mdi:timer",
        "enabledbydflt": False
    },
    "Cook Cycle": {
        "json_loca": "usage;cook_cycles",
        "unit": "",
        "icon": "mdi:counter",
        "enabledbydflt": False
    },
    "Ignite Fail Count": {
        "json_loca": "usage;error_stats;ignite_fail",
        "unit": "",
        "icon": "mdi:counter",
        "enabledbydflt": False
    },
    "Overheat Count": {
        "json_loca": "usage;error_stats;overheat",
        "unit": "",
        "icon": "mdi:counter",
        "enabledbydflt": False
    },
    "Lowtemp Count": {
        "json_loca": "usage;error_stats;lowtemp",
        "unit": "",
        "icon": "mdi:counter",
        "enabledbydflt": False
    },
    "State Index Count": {
        "json_loca": "stateIndex",
        "unit": "",
        "icon": "mdi:counter",
        "enabledbydflt": False
    },
    "WifI RSSI": {
        "json_loca": "settings;rssi",
        "unit": "dBm",
        "icon": "mdi:wifi-strength-2",
        "enabledbydflt": False,
        "entity_category": EntityCategory.DIAGNOSTIC
    },
    "WifI SSID": {
        "json_loca": "settings;ssid",
        "unit": None,
        "icon": "mdi:wifi",
        "enabledbydflt": False,
        "entity_category": EntityCategory.DIAGNOSTIC
    }
}


async def async_setup_entry(hass, entry, async_add_devices):
    """Setup sensor platform."""
    client = hass.data[DOMAIN][entry.entry_id]
    grills = client.get_grills()
    for grill in grills:
        grill_id = grill["thingName"]
        for friendly, info in SENSOR_ENTITIES.items():
            if info["unit"] == "temp":
                async_add_devices([
                    ValueTemperature(
                        client=client,
                        thingName=grill["thingName"],
                        friendly=friendly,
                        json_loca=info["json_loca"],
                        unit=info["unit"],
                        mdi=info["icon"],
                        enabledbydflt=info.get("enabledbydflt", True),
                        entity_category=info.get("entity_category", None),
                        device_class=info.get("device_class", None))
                ])
            else:
                async_add_devices([
                    TraegerFlexSensor(
                        client=client,
                        thingName=grill["thingName"],
                        friendly=friendly,
                        json_loca=info["json_loca"],
                        unit=info["unit"],
                        mdi=info["icon"],
                        enabledbydflt=info.get("enabledbydflt", True),
                        entity_category=info.get("entity_category", None),
                        device_class=info.get("device_class", None))
                ])
        async_add_devices([
            GrillState(client, grill["thingName"], "Grill State", "grill_state")
        ])
        async_add_devices([
            HeatingState(client, grill["thingName"], "Heating State",
                         "heating_state")
        ])
        TraegerGrillMonitor(client, grill_id, async_add_devices, ProbeState)


class TraegerFlexSensor(TraegerBaseEntity, SensorEntity):
    """Flex Sensor Class Common to All"""

    def __init__(self, **kwargs):
        super().__init__(kwargs.get('client'), kwargs.get('thingName'))
        self.value = kwargs.get('json_loca').split(";")
        self.unit = kwargs.get('unit')
        self.mdi = kwargs.get('mdi')
        self.dev_class = kwargs.get('device_class')
        self.friendly_name = kwargs.get('friendly')
        self._attr_entity_category = kwargs.get('entity_category')
        self._attr_entity_registry_enabled_default = kwargs.get('enabledbydflt')
        self.grill_register_callback()

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
        name = self.grill_mqtt_msg["details"]["friendlyName"]
        return f"{name} {self.friendly_name}"

    @property
    def unique_id(self):
        """Return the unique id."""
        return f"{self.grill_id}_{self.value[-1]}"

    @property
    def icon(self):
        """Set the default MDI Icon"""
        return self.mdi

    @property
    def device_class(self):
        """Set the device class"""
        return self.dev_class

    # Sensor Properties
    @property
    def native_unit_of_measurement(self):
        """Return the unit the value is expressed in."""
        return self.unit

    @property
    def native_value(self):
        """Return the current state of entity."""
        if len(self.value) == 3:
            rtrn = self.grill_mqtt_msg[self.value[0]][self.value[1]][
                self.value[2]]
        if len(self.value) == 2:
            rtrn = self.grill_mqtt_msg[self.value[0]][self.value[1]]
        if len(self.value) == 1:
            rtrn = self.grill_mqtt_msg[self.value[0]]
        if self.dev_class == SensorDeviceClass.TIMESTAMP:
            rtrn = datetime.utcfromtimestamp(rtrn)
            rtrn = rtrn.replace(tzinfo=timezone.utc)
        return rtrn


class ValueTemperature(TraegerFlexSensor):
    """Traeger Temperature Value class."""
    # Sensor Properties
    @property
    def native_unit_of_measurement(self):
        """Return the unit the value is expressed in."""
        return self.grill_units

    @property
    def suggested_unit_of_measurement(self):
        """Return the suggested UOM"""
        return self.grill_units


class TraegerBaseSensor(TraegerBaseEntity, SensorEntity):
    """Base Sensor Class Common to All"""

    def __init__(self, client, grill_id, friendly_name, value):
        super().__init__(client, grill_id)
        self.value = value
        self.friendly_name = friendly_name
        self.grill_register_callback()

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
        name = self.grill_mqtt_msg["details"]["friendlyName"]
        return f"{name} {self.friendly_name}"

    @property
    def unique_id(self):
        """Return the unique id."""
        return f"{self.grill_id}_{self.value}"

    # Sensor Properties
    @property
    def native_value(self):
        """Return the current state of entity."""
        return self.grill_mqtt_msg["status"][self.value]


class GrillState(TraegerBaseSensor):
    """
    Traeger Grill State class.
    These states correlate with the Traeger application.
    """
    # Generic Properties
    @property
    def icon(self):
        """Set the default MDI Icon"""
        return "mdi:grill"

    # Sensor Properties
    @property
    def state(self):
        """Return the state of the sensor."""
        returnval = "unknown"  # Likely a new state we don't know about
        state = self.grill_mqtt_msg["status"]["system_status"]

        if state == GRILL_MODE_COOL_DOWN:
            returnval = "cool_down"
        elif state == GRILL_MODE_CUSTOM_COOK:
            returnval = "cook_custom"
        elif state == GRILL_MODE_MANUAL_COOK:
            returnval = "cook_manual"
        elif state == GRILL_MODE_PREHEATING:
            returnval = "preheating"
        elif state == GRILL_MODE_IGNITING:
            returnval = "igniting"
        elif state == GRILL_MODE_IDLE:
            returnval = "idle"
        elif state == GRILL_MODE_SLEEPING:
            returnval = "sleeping"
        elif state == GRILL_MODE_OFFLINE:
            returnval = "offline"
        elif state == GRILL_MODE_SHUTDOWN:
            returnval = "shutdown"
        return returnval


class HeatingState(TraegerBaseSensor):
    """Traeger Heating State class."""

    def __init__(self, client, grill_id, friendly_name, value):
        super().__init__(client, grill_id, friendly_name, value)
        self.previous_target_temp = None
        self.previous_state = "idle"
        self.preheat_modes = [GRILL_MODE_PREHEATING, GRILL_MODE_IGNITING]
        self.cook_modes = [GRILL_MODE_CUSTOM_COOK, GRILL_MODE_MANUAL_COOK]

    # Generic Properties
    @property
    def icon(self):
        """Set the default MDI Icon"""
        if self.state == "over_temp":
            return "mdi:fire-alert"
        return "mdi:fire"

    # Sensor Properties
    @property
    def state(self):  # pylint: disable=too-many-branches,too-many-statements
        """Return the state of the sensor."""
        if self.grill_mqtt_msg.get("status", None) is None:
            return "idle"

        target_temp = self.grill_mqtt_msg["status"]["set"]
        grill_mode = self.grill_mqtt_msg["status"]["system_status"]
        current_temp = self.grill_mqtt_msg["status"]["grill"]
        target_changed = target_temp != self.previous_target_temp
        min_cook_temp = (GRILL_MIN_TEMP_C if self.grill_units
                         == UnitOfTemperature.CELSIUS else GRILL_MIN_TEMP_F)
        temp_swing = 11 if self.grill_units == UnitOfTemperature.CELSIUS else 20
        low_temp = target_temp - temp_swing
        high_temp = target_temp + temp_swing

        state = "idle"
        if grill_mode in self.preheat_modes:
            if current_temp < min_cook_temp:
                state = "preheating"
            else:
                state = "heating"
        elif grill_mode in self.cook_modes:
            if self.previous_state in ('heating', 'preheating'):
                if current_temp >= target_temp:
                    state = "at_temp"
                else:
                    state = "heating"
            elif self.previous_state == "cooling":
                if current_temp <= target_temp:
                    state = "at_temp"
                else:
                    state = "cooling"
            elif self.previous_state == "at_temp":
                if current_temp > high_temp:
                    state = "over_temp"
                elif current_temp < low_temp:
                    state = "under_temp"
                else:
                    state = "at_temp"
            elif self.previous_state == "under_temp":
                if current_temp > low_temp:
                    state = "at_temp"
                else:
                    state = "under_temp"
            elif self.previous_state == "over_temp":
                if current_temp < high_temp:
                    state = "at_temp"
                else:
                    state = "over_temp"
            # Catch all if coming from idle/unavailable
            else:
                target_changed = True

            if target_changed:
                if current_temp <= target_temp:
                    state = "heating"
                else:
                    state = "cooling"
        elif grill_mode == GRILL_MODE_COOL_DOWN:
            state = "cool_down"

        self.previous_target_temp = target_temp
        self.previous_state = state
        return state


class ProbeState(TraegerBaseSensor):
    """Traeger Probe Heating State class."""

    def __init__(self, client, grill_id, sensor_id):
        super().__init__(client, grill_id, f"Probe State {sensor_id}",
                         f"probe_state_{sensor_id}")
        self.sensor_id = sensor_id
        self.grill_accessory = self.client.get_details_for_accessory(
            self.grill_id, self.sensor_id)
        self.previous_target_temp = None
        self.probe_alarm = False
        self.active_modes = [
            GRILL_MODE_PREHEATING, GRILL_MODE_IGNITING, GRILL_MODE_CUSTOM_COOK,
            GRILL_MODE_MANUAL_COOK
        ]

        # Tell the Traeger client to call grill_accessory_update() when it gets an update
        self.client.set_callback_for_grill(self.grill_id,
                                           self.grill_accessory_update)

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
        """Reports unavailable when the probe is not connected"""
        if (self.grill_mqtt_msg.get("status", None) is None or
                self.grill_mqtt_msg["status"]["connected"] is False or
                self.grill_accessory is None):
            # Reset probe alarm if accessory becomes unavailable
            self.probe_alarm = False
            return False
        connected = self.grill_accessory["con"]
        # Reset probe alarm if accessory is not connected
        if not connected:
            self.probe_alarm = False
        return connected

    @property
    def unique_id(self):
        """Return the unique id."""
        return f"{self.grill_id}_probe_state_{self.sensor_id}"

    @property
    def icon(self):
        """Set the default MDI Icon"""
        return "mdi:thermometer"

    # Sensor Properties
    @property
    def state(self):
        """Return the state of the sensor."""
        if self.grill_accessory is None:
            return "idle"

        acc_type = self.grill_accessory["type"]
        target_temp = self.grill_accessory[acc_type]["set_temp"]
        probe_temp = self.grill_accessory[acc_type]["get_temp"]
        target_changed = target_temp != self.previous_target_temp
        grill_mode = self.grill_mqtt_msg["status"]["system_status"]
        fell_out_temp = 102 if self.grill_units == UnitOfTemperature.CELSIUS else 215

        # Latch probe alarm, reset if target changed or grill leaves active modes
        if "alarm_fired" not in self.grill_accessory[acc_type]:
            self.probe_alarm = False
        elif self.grill_accessory[acc_type]["alarm_fired"]:
            self.probe_alarm = True
        elif ((target_changed and target_temp != 0) or
              (grill_mode not in self.active_modes)):
            self.probe_alarm = False

        state = "idle"
        if probe_temp >= fell_out_temp:
            state = "fell_out"
        elif self.probe_alarm:
            state = "at_temp"
        elif target_temp != 0 and grill_mode in self.active_modes:
            close_temp = 3 if self.grill_units == UnitOfTemperature.CELSIUS else 5
            if probe_temp + close_temp >= target_temp:
                state = "close"
            else:
                state = "set"
        else:
            self.probe_alarm = False

        self.previous_target_temp = target_temp
        return state
