"""Number/Timer platform for Traeger."""
import asyncio
import json
import logging

from homeassistant.components.number import NumberEntity

from .const import (
    DOMAIN,
    GRILL_MODE_COOL_DOWN,
    GRILL_MODE_CUSTOM_COOK,
    GRILL_MODE_IDLE,
    GRILL_MODE_IGNITING,
    GRILL_MODE_SHUTDOWN,
    GRILL_MODE_SLEEPING,
)

from .entity import TraegerBaseEntity
from .utils import (
    call_service_set_climate,
    call_service_set_climate_mode,
    call_service_set_number,
    call_service_set_switch,
)

_LOGGER: logging.Logger = logging.getLogger(__package__)


async def async_setup_entry(hass, entry, async_add_entities):
    """
    Setup Number/Timer platform.
    """
    client = hass.data[DOMAIN][entry.entry_id]
    grills = client.get_grills()
    entities = []
    for grill in grills:
        entities.append(
            TraegerNumberEntity(client, grill["thingName"], "cook_timer")
        )
        entities.append(
            CookCycNumberEntity(client, grill["thingName"], "cook_cycle", hass)
        )
    if entities:
        async_add_entities(entities)


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
        if self.grill_mqtt_msg.get("details", None) is None:
            return f"{self.grill_id}_{self.devname}"
        name = self.grill_mqtt_msg["details"]["friendlyName"]
        return f"{name} {self.devname.capitalize()}"

    @property
    def unique_id(self):
        """Return the unique id."""
        return f"{self.grill_id}_{self.devname}"

    @property
    def icon(self):
        """Set the default MDI Icon"""
        return "mdi:chef-hat"

    @property
    def native_step(self):
        """Return the supported step."""
        return 1

    def scan_next_step(self, curstep):
        '''Scan for next step'''
        if "use_timer" in curstep:
            if self.grill_mqtt_msg["status"]["cook_timer_complete"]:
                self.num_value = self.num_value + 1
        elif self.grill_mqtt_msg["status"]["probe_alarm_fired"]:
            self.num_value = self.num_value + 1
        elif "act_temp_adv" in curstep:
            if self.grill_mqtt_msg["status"]["grill"] >= curstep["act_temp_adv"]:
                self.num_value = self.num_value + 1
        elif (
            "probe_act_temp_adv" in curstep
            and self.grill_mqtt_msg["status"]["probe"] >= curstep["probe_act_temp_adv"]
        ):
            self.num_value = self.num_value + 1

    def in_step_change(self, curstep):
        '''In Step Change'''
        curstep["max_grill_delta_temp"] = min(
            curstep["max_grill_delta_temp"],
            self.grill_mqtt_msg["limits"]["max_grill_temp"],
        )

        if (
            self.grill_mqtt_msg["status"]["set"] < curstep["max_grill_delta_temp"]
            and self.grill_mqtt_msg["status"]["probe"]
            > self.grill_mqtt_msg["status"]["set"] - curstep["min_delta"]
        ):
            set_temp = self.grill_mqtt_msg["status"]["set"] + 5
            call_service_set_climate(
                self.hass,
                self.client.sync_grill_get_entity(f"{self.grill_id}_climate"),
                round(set_temp),
            )

    def next_step(self, curstep):
        '''Cmd Next Step'''
        if "time_set" in curstep:
            call_service_set_number(
                self.hass,
                self.client.sync_grill_get_entity(f"{self.grill_id}_cook_timer"),
                round(curstep["time_set"]),
            )
        if "probe_set_temp" in curstep:
            call_service_set_climate(
                self.hass,
                self.client.sync_grill_get_entity(f"{self.grill_id}_probe_p0"),
                round(curstep["probe_set_temp"]),
            )
        if "set_temp" in curstep:
            call_service_set_climate(
                self.hass,
                self.client.sync_grill_get_entity(f"{self.grill_id}_climate"),
                round(curstep["set_temp"]),
            )
        if (
            "smoke" in curstep
            and self.grill_mqtt_msg["features"]["super_smoke_enabled"] == 1
            and self.grill_mqtt_msg["status"]["smoke"] != curstep["smoke"]
            and self.grill_mqtt_msg["status"]["set"] <= 225
        ):
            call_service_set_switch(
                self.hass,
                self.client.sync_grill_get_entity(f"{self.grill_id}_smoke"),
                curstep["smoke"],
            )
        if (
            "keepwarm" in curstep
            and self.grill_mqtt_msg["status"]["keepwarm"] != curstep["keepwarm"]
        ):
            call_service_set_switch(
                self.hass,
                self.client.sync_grill_get_entity(f"{self.grill_id}_keepwarm"),
                curstep["keepwarm"],
            )
        if "shutdown" in curstep:
            call_service_set_climate_mode(
                self.hass,
                self.client.sync_grill_get_entity(f"{self.grill_id}_climate"),
                "cool",
            )

    # Value Properties
    @property
    def native_value(self):
        """
        Return the value reported by the number.
        This also serves the cook cycle.
        """
        if self.num_value > len(self.cook_cycle):
            _LOGGER.info("B.Cook Cycles out of indexes.")
            self.num_value = 0
            return self.num_value
        if self.num_value > 0 and self.grill_mqtt_msg["status"]["system_status"] in [
            GRILL_MODE["Cool_Down"],
            GRILL_MODE["Sleeping"],
            GRILL_MODE["Shutdown"],
            GRILL_MODE["Idle"],
        ]:
            _LOGGER.info("Steps not available when not cooking. Revert to 0.")
            self.num_value = 0
            return self.num_value
        ########################################################################
        # Scan for next step advance
        if self.num_value > 0 and self.num_value == self.old_num_value:
            curstep = self.cook_cycle[self.num_value - 1]
            self.scan_next_step(curstep)
            ####################################################################
            # In step change
            if "min_delta" in curstep and "max_grill_delta_temp" in curstep:
                self.in_step_change(curstep)
        ########################################################################
        # Implement next step
        if (
            self.num_value > 0 and self.num_value != self.old_num_value
        ):  # Only hit once per step.
            curstep = self.cook_cycle[self.num_value - 1]
            self.next_step(curstep)
        self.old_num_value = self.num_value
        _LOGGER.debug("CookCycle Steps:%s", self.cook_cycle)
        return self.num_value

    @property
    def native_min_value(self):
        """Return the minimum value."""
        return 0

    @property
    def native_max_value(self):
        """Return the maximum value."""
        return 999

    @property
    def extra_state_attributes(self):
        """Return the optional state attributes."""
        # default_attributes = super().state_attributes
        prev_step = {}
        curr_step = {}
        next_step = {}
        if self.num_value > 1:
            prev_step = f"{self.num_value - 1}: {json.dumps(self.cook_cycle[self.num_value - 2])}"
        if self.num_value > 0:
            curr_step = (
                f"{self.num_value}: {json.dumps(self.cook_cycle[self.num_value - 1])}"
            )
        if self.num_value < len(self.cook_cycle):
            next_step = (
                f"{self.num_value + 1}: {json.dumps(self.cook_cycle[self.num_value])}"
            )
        custom_attributes = {
            "prev_step": str(prev_step),
            "curr_step": str(curr_step),
            "next_step": str(next_step),
        }
        intstep = 1
        for step in self.cook_cycle:
            custom_attributes[f"_step{intstep:02d}"] = str(json.dumps(step))
            intstep = intstep + 1
        attributes = {}
        attributes.update(custom_attributes)
        return attributes

    # Value Set Method
    async def async_set_native_value(self, value: float):
        """Set new Val and callback to update value above."""
        self.num_value = round(value)
        # Need to call callback now so that it fires step #1 or commanded step immediatlly.
        await self.client.grill_callback(self.grill_id)

    # Recieve Custom Cook Command
    def set_custom_cook(self, **kwargs):
        """From Service, Update the number's cook cycle steps."""
        self.cook_cycle = kwargs["steps"]
        _LOGGER.info("Traeger: Set Cook Cycle:%s", self.cook_cycle)
        # Need to call callback now so that it fires state cust atrib update.
        asyncio.run_coroutine_threadsafe(
            self.client.grill_callback(self.grill_id), self.hass.loop
        )


class TraegerNumberEntity(NumberEntity, TraegerBaseEntity):
    """Traeger Number/Timer Value class."""

    def __init__(self, client, grill_id, devname):
        super().__init__(client, grill_id)
        self.devname = devname
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
            return f"{self.grill_id}_{self.devname}"
        name = self.grill_mqtt_msg["details"]["friendlyName"]
        return f"{name} {self.devname.capitalize()}"

    @property
    def unique_id(self):
        """Return the unique id."""
        return f"{self.grill_id}_{self.devname}"

    @property
    def icon(self):
        """Set the default MDI Icon"""
        return "mdi:timer"

    @property
    def native_step(self):
        """Return the supported step."""
        return 1

    # Timer Properties
    @property
    def native_value(self):
        """Return the value reported by the number."""
        end_time = self.grill_mqtt_msg["status"][f"{self.devname}_end"]
        start_time = self.grill_mqtt_msg["status"][f"{self.devname}_start"]
        tot_time = (end_time - start_time) / 60
        return tot_time

    @property
    def native_min_value(self):
        """Return the minimum value."""
        return 0

    @property
    def native_max_value(self):
        """Return the maximum value."""
        return 1440

    @property
    def native_unit_of_measurement(self):
        """Return the unit of measurement of the entity, if any."""
        return "min"

    # Timer Methods
    async def async_set_native_value(self, value: float):
        """Set new Timer Val."""
        state = self.grill_mqtt_msg["status"]["system_status"]
        if GRILL_MODE_IGNITING <= state <= GRILL_MODE_CUSTOM_COOK:
            if value >= 1:
                await self.client.set_timer_sec(self.grill_id,
                                                (round(value) * 60))
            else:
                await self.client.reset_timer(self.grill_id)
            return
        raise NotImplementedError("Set Timer not supported in current state.")
