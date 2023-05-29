"""Number/Timer platform for Traeger."""
import re
import voluptuous as vol
from homeassistant.components.number import NumberEntity
from homeassistant.helpers import entity_platform
from homeassistant.helpers import config_validation as cv
import logging

SERVICE_CUSTOMCOOK = "set_custom_cook"
ENTITY_ID = "entity_id"
SCHEMA_CUSTOMCOOK = {
    vol.Required(ENTITY_ID): cv.string,
    vol.Required("steps", default=dict): list
}

from .const import (
    DOMAIN,
    GRILL_MODE_COOL_DOWN,
    GRILL_MODE_SLEEPING,
    GRILL_MODE_SHUTDOWN,
    GRILL_MODE_IDLE,
)

_LOGGER: logging.Logger = logging.getLogger(__package__)

from .entity import TraegerBaseEntity


async def async_setup_entry(hass, entry, async_add_devices):
    """Setup Service platform."""
    platform = entity_platform.current_platform.get()
    platform.async_register_entity_service(SERVICE_CUSTOMCOOK,
                                           SCHEMA_CUSTOMCOOK, "set_custom_cook")
    """Setup Number/Timer platform."""
    client = hass.data[DOMAIN][entry.entry_id]
    grills = client.get_grills()
    for grill in grills:
        grill_id = grill["thingName"]
        async_add_devices(
            [TraegerNumberEntity(client, grill["thingName"], "cook_timer")])
        async_add_devices([
            CookCycNumberEntity(client, grill["thingName"], "cook_cycle", hass)
        ])


class CookCycNumberEntity(NumberEntity, TraegerBaseEntity):
    """Traeger Number/Timer Value class."""

    def __init__(self, client, grill_id, devname, hass):
        super().__init__(client, grill_id)
        self.devname = devname
        self.num_value = 0
        self.old_num_value = 0
        self.cook_cycle = []
        self.hass = hass
        self.grill_register_callback()

    # Generic Properties
    @property
    def name(self):
        """Return the name of the grill"""
        if self.grill_details is None:
            return f"{self.grill_id}_{self.devname}"
        name = self.grill_details["friendlyName"]
        return f"{name} {self.devname.capitalize()}"

    @property
    def unique_id(self):
        return f"{self.grill_id}_{self.devname}"

    @property
    def icon(self):
        return "mdi:chef-hat"

    @property
    def native_native_step(self):
        return 1

    # Value Properties
    @property
    def native_value(self):
        if self.grill_state is None:
            self.num_value = 0
            return self.num_value
        if self.num_value > len(self.cook_cycle):
            _LOGGER.info(f"B.Cook Cycles out of indexes.")
            self.num_value = 0
            return self.num_value
        name = re.sub('[^A-Za-z0-9]+', '', self.grill_details["friendlyName"])
        _LOGGER.info(f"Name: {name}")
        if self.num_value > 0 and self.grill_state["system_status"] in [
                GRILL_MODE_COOL_DOWN, GRILL_MODE_SLEEPING, GRILL_MODE_SHUTDOWN,
                GRILL_MODE_IDLE
        ]:
            _LOGGER.info(f"Steps not available when not cooking. Revert to 0.")
            self.num_value = 0
            return self.num_value
        ########################################################################
        #Scan for next step advance
        if self.num_value > 0 and self.num_value == self.old_num_value:
            curstep = self.cook_cycle[self.num_value - 1]
            if "use_timer" in curstep:
                if curstep["use_timer"]:
                    if self.grill_state["cook_timer_complete"]:
                        self.num_value = self.num_value + 1
            elif self.grill_state["probe_alarm_fired"]:
                self.num_value = self.num_value + 1
            elif "act_temp_adv" in curstep:
                if self.grill_state["grill"] > curstep["act_temp_adv"]:
                    self.num_value = self.num_value + 1
            elif "probe_act_temp_adv" in curstep:
                if self.grill_state["probe"] > curstep["probe_act_temp_adv"]:
                    self.num_value = self.num_value + 1
            ####################################################################
            #In step change
            if "min_delta" in curstep and "max_grill_delta_temp" in curstep:
                if curstep["max_grill_delta_temp"] > self.grill_limits[
                        "max_grill_temp"]:
                    curstep["max_grill_delta_temp"] = self.grill_limits[
                        "max_grill_temp"]
                if self.grill_state["set"] < curstep["max_grill_delta_temp"]:
                    if self.grill_state["probe"] > self.grill_state[
                            "set"] - curstep["min_delta"]:
                        set_temp = self.grill_state["set"] + 5
                        self.hass.async_create_task(
                            self.hass.services.async_call(
                                "climate", "set_temperature", {
                                    "entity_id":
                                        f"climate.{self.grill_id}_climate",
                                    "temperature":
                                        round(set_temp)
                                }, False))
        ########################################################################
        #Implement next step
        if self.num_value > 0 and self.num_value != self.old_num_value:  #Only hit once per step.
            curstep = self.cook_cycle[self.num_value - 1]
            if "time_set" in curstep:
                self.hass.async_create_task(
                    self.hass.services.async_call(
                        "number", "set_value", {
                            "entity_id": f"number.{self.grill_id}_cook_timer",
                            "value": round(curstep["time_set"])
                        }, False))
            if "probe_set_temp" in curstep:
                name = re.sub('[^A-Za-z0-9]+', '',
                              self.grill_details["friendlyName"])
                self.hass.async_create_task(
                    self.hass.services.async_call(
                        "climate", "set_temperature", {
                            "entity_id": f"climate.{name.lower()}_probe_p0",
                            "temperature": round(curstep["probe_set_temp"])
                        }, False))
            if "set_temp" in curstep:
                self.hass.async_create_task(
                    self.hass.services.async_call(
                        "climate", "set_temperature", {
                            "entity_id": f"climate.{self.grill_id}_climate",
                            "temperature": round(curstep["set_temp"])
                        }, False))
            if "smoke" in curstep:
                if self.grill_features[
                        "super_smoke_enabled"] == 1 and self.grill_state[
                            "smoke"] != curstep["smoke"] and self.grill_state[
                                "set"] <= 225:
                    if curstep["smoke"] == 1:
                        self.hass.async_create_task(
                            self.hass.services.async_call(
                                "switch", "turn_on",
                                {"entity_id": f"switch.{self.grill_id}_smoke"},
                                False))
                    else:
                        self.hass.async_create_task(
                            self.hass.services.async_call(
                                "switch", "turn_off",
                                {"entity_id": f"switch.{self.grill_id}_smoke"},
                                False))
            if "keepwarm" in curstep:
                if self.grill_state["keepwarm"] != curstep["keepwarm"]:
                    if curstep["keepwarm"] == 1:
                        self.hass.async_create_task(
                            self.hass.services.async_call(
                                "switch", "turn_on", {
                                    "entity_id":
                                        f"switch.{self.grill_id}_keepwarm"
                                }, False))
                    else:
                        self.hass.async_create_task(
                            self.hass.services.async_call(
                                "switch", "turn_off", {
                                    "entity_id":
                                        f"switch.{self.grill_id}_keepwarm"
                                }, False))
            if "shutdown" in curstep:
                if curstep["shutdown"] == 1:
                    self.hass.async_create_task(
                        self.hass.services.async_call(
                            "climate", "set_hvac_mode", {
                                "entity_id": f"climate.{self.grill_id}_climate",
                                "hvac_mode": "cool"
                            }, False))
                    self.num_value = 0
            self.old_num_value = self.num_value
        _LOGGER.debug(f"CookCycle Steps:{self.cook_cycle}")
        if self.num_value > len(self.cook_cycle):
            _LOGGER.info(f"A.Cook Cycles out of indexes.")
            self.num_value = 0
        return self.num_value

    @property
    def native_min_value(self):
        return 0

    @property
    def native_max_value(self):
        return 999

    @property
    def state_attributes(self):
        """Return the optional state attributes."""
        #default_attributes = super().state_attributes
        prev_step = {}
        curr_step = {}
        next_step = {}
        if self.num_value > 1:
            prev_step = self.cook_cycle[self.num_value - 2]
        if self.num_value > 0:
            curr_step = self.cook_cycle[self.num_value - 1]
        if self.num_value < len(self.cook_cycle):
            next_step = self.cook_cycle[self.num_value]
        custom_attributes = {
            "cook_cycl": self.cook_cycle,
            "cook_cycl_step": str(self.cook_cycle),
            "prev_step": str(prev_step),
            "curr_step": str(curr_step),
            "next_step": str(next_step),
        }
        attributes = {}
        attributes.update(custom_attributes)
        return attributes

    # Value Set Method
    async def async_set_native_value(self, value: float):
        """Set new Val and callback to update value above."""
        self.num_value = round(value)
        #Need to call callback now so that it fires step #1 or commanded step immediatlly.
        await self.client.grill_callback(self.grill_id)

    # Recieve Custom Cook Command
    def set_custom_cook(self, **kwargs):
        self.cook_cycle = kwargs["steps"]
        _LOGGER.info(f"Traeger: Set Cook Cycle:{self.cook_cycle}")
        #Need to call callback now so that it fires state cust atrib update.
        self.hass.async_create_task(self.client.grill_callback(self.grill_id))


class TraegerNumberEntity(NumberEntity, TraegerBaseEntity):
    """Traeger Number/Timer Value class."""

    def __init__(self, client, grill_id, devname):
        super().__init__(client, grill_id)
        self.devname = devname
        self.grill_register_callback()

    # Generic Properties
    @property
    def name(self):
        """Return the name of the grill"""
        if self.grill_details is None:
            return f"{self.grill_id}_{self.devname}"
        name = self.grill_details["friendlyName"]
        return f"{name} {self.devname.capitalize()}"

    @property
    def unique_id(self):
        return f"{self.grill_id}_{self.devname}"

    @property
    def icon(self):
        return "mdi:timer"

    # Timer Properties
    @property
    def native_value(self):
        if self.grill_state is None:
            return 0
        end_time = self.grill_state[f"{self.devname}_end"]
        start_time = self.grill_state[f"{self.devname}_start"]
        tot_time = (end_time - start_time) / 60
        return tot_time

    @property
    def native_min_value(self):
        return 1

    @property
    def native_max_value(self):
        return 1440

    @property
    def native_unit_of_measurement(self):
        return "min"

    # Timer Methods
    async def async_set_native_value(self, value: float):
        """Set new Timer Val."""
        await self.client.set_timer_sec(self.grill_id, (round(value) * 60))
