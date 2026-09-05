"""Climate platform for Traeger grills"""

from homeassistant.components.climate import ClimateEntity
from homeassistant.components.climate.const import (
    PRESET_NONE,
    ClimateEntityFeature,
    HVACMode,
)
from homeassistant.const import ATTR_TEMPERATURE, UnitOfTemperature

from custom_components.traeger.notify_helper import (
    notifyclearliveupdate,
    notifyliveupdate_text,
)

from .const import (
    DOMAIN,
    GRILL_MIN_TEMP_C,
    GRILL_MIN_TEMP_F,
    GRILL_MODE,
    PROBE_PRESET_MODES,
)
from .entity import TraegerBaseEntity, TraegerGrillMonitor


async def async_setup_entry(hass, entry, async_add_entities):
    """Setup climate platform."""
    client = hass.data[DOMAIN][entry.entry_id]
    grills = client.get_grills()
    entities = []
    for grill in grills:
        grill_id = grill["thingName"]
        entities.append(TraegerClimateEntity(client, grill_id, "Climate"))
        TraegerGrillMonitor(client, grill_id, async_add_entities,
                            AccessoryTraegerClimateEntity)
    if entities:
        async_add_entities(entities)


class TraegerBaseClimate(ClimateEntity, TraegerBaseEntity):
    """Base Climate Class Common to All"""

    _enable_turn_on_off_backwards_compatibility = False

    def __init__(self, client, grill_id, friendly_name):
        super().__init__(client, grill_id)
        self.friendly_name = friendly_name
        self.curtemp = None
        self.settemp = None

    # Generic Properties
    @property
    def name(self):
        """Return the name of the grill"""
        if self.grill_mqtt_msg.get("details", None) is None:
            return f"{self.grill_id} {self.friendly_name}"
        name = self.grill_mqtt_msg["details"]["friendlyName"]
        return f"{name} {self.friendly_name}"

    # Climate Properties
    @property
    def temperature_unit(self):
        """Return the unit of measurement used by the grill."""
        if self.grill_units == UnitOfTemperature.CELSIUS:
            return UnitOfTemperature.CELSIUS
        return UnitOfTemperature.FAHRENHEIT

    @property
    def target_temperature_step(self):
        """Return the supported step of target temperature."""
        return 5

    @property
    def supported_features(self):
        """Return the list of supported features for the grill"""
        return (ClimateEntityFeature.TARGET_TEMPERATURE |
                ClimateEntityFeature.TURN_OFF | ClimateEntityFeature.TURN_ON)


class TraegerClimateEntity(TraegerBaseClimate):
    """Climate entity for Traeger grills"""

    def __init__(self, client, grill_id, friendly_name):
        super().__init__(client, grill_id, friendly_name)
        self.grill_register_callback()

    @property
    def unique_id(self):
        """Return the unique id."""
        return f"{self.grill_id}_climate"

    @property
    def icon(self):
        """Set the default MDI Icon"""
        return "mdi:grill"

    @property
    def available(self):
        """Reports unavailable when the grill is powered off"""
        if self.grill_mqtt_msg.get("status", None) is None:
            return False
        return self.grill_mqtt_msg["status"]["connected"]

    # Climate Properties
    @property
    def current_temperature(self):
        """Return the current temperature."""
        if (
            self.curtemp != self.grill_mqtt_msg["status"]["grill"]
            or self.settemp != self.grill_mqtt_msg["status"]["set"]
        ) and (
            GRILL_MODE["Igniting"]
            <= self.grill_mqtt_msg["status"]["system_status"]
            <= GRILL_MODE["Shutdown"]
        ):
            self.curtemp = self.grill_mqtt_msg["status"]["grill"]
            self.settemp = self.grill_mqtt_msg["status"]["set"]
            if self.settemp - 5 <= self.curtemp <= self.settemp + 5:
                iconcolor = "#FF7900"
            elif self.curtemp < self.settemp - 5:
                iconcolor = "#0000FF"
            else:
                iconcolor = "#FF0000"
            notifyliveupdate_text(
                self.notify,
                self.hass,
                title=f"{self.name}",
                msg=f"Actual: {self.curtemp}\nSet: {self.settemp}",
                tag=self.unique_id,
                icon="mdi:grill",
                icon_color=iconcolor,
                silent=True,
            )
        else:
            if self.grill_mqtt_msg["status"]["system_status"] in [
                GRILL_MODE["Idle"],
                GRILL_MODE["Sleeping"],
            ]:
                notifyclearliveupdate(self.notify, self.hass, tag=self.unique_id)
            self.curtemp = self.grill_mqtt_msg["status"]["grill"]
        return self.curtemp

    @property
    def target_temperature(self):
        """Return the temperature we try to reach."""
        self.settemp = self.grill_mqtt_msg["status"]["set"]
        return self.settemp

    @property
    def extra_state_attributes(self):
        """Return the extra state attributes."""
        custom_attributes = {
            "grill_native_cur_val": self.grill_mqtt_msg["status"]["grill"],
            "grill_native_set_val": self.grill_mqtt_msg["status"]["set"],
        }
        attributes = {}
        attributes.update(custom_attributes)
        return attributes

    @property
    def max_temp(self):
        """Return the maximum temperature."""
        try:
            max_fahrenheit = self.grill_mqtt_msg["limits"]["max_grill_temp"]
        except KeyError:
            max_fahrenheit = 500
        if max_fahrenheit <= GRILL_MIN_TEMP_F:
            max_fahrenheit = 500
        if self.grill_units == UnitOfTemperature.CELSIUS:
            return round((max_fahrenheit - 32) * 5.0 / 9.0)
        return max_fahrenheit

    @property
    def min_temp(self):
        """Return the minimum temperature."""
        if self.grill_units == UnitOfTemperature.CELSIUS:
            return GRILL_MIN_TEMP_C
        return GRILL_MIN_TEMP_F

    @property
    def hvac_mode(self):
        """Return hvac operation ie. heat, cool mode.
        Need to be one of HVAC_MODE_*.
        """

        state = self.grill_mqtt_msg["status"]["system_status"]

        if state in [GRILL_MODE["CoolingDown"]]:
            returnval = HVACMode.COOL
        elif state in [
            GRILL_MODE["Cook_Custom"],
            GRILL_MODE["Cook_Manual"],
            GRILL_MODE["PreHeating"],
            GRILL_MODE["Igniting"],
        ]:
            returnval = HVACMode.HEAT
        elif state in [
            GRILL_MODE["Idle"],
            GRILL_MODE["Sleeping"],
            GRILL_MODE["Offline"],
            GRILL_MODE["Shutdown"],
        ]:
            returnval = HVACMode.OFF
        else:
            returnval = HVACMode.OFF
        return returnval

    @property
    def hvac_modes(self):
        """
        Return the list of available hvac operation modes.
        Need to be a subset of HVAC_MODES.
        """
        return (HVACMode.HEAT, HVACMode.OFF, HVACMode.COOL)

    # Climate Methods
    async def async_set_temperature(self, **kwargs):
        """Set new target temperature."""
        state = self.grill_mqtt_msg["status"]["system_status"]
        if GRILL_MODE["Igniting"] <= state <= GRILL_MODE["Cook_Custom"]:
            temperature = kwargs.get(ATTR_TEMPERATURE, 0)
            await self.client.set_temperature(self.grill_id, round(temperature))
            return
        raise NotImplementedError("Set Temp not supported in current state.")

    async def async_set_hvac_mode(self, hvac_mode):
        """Start grill shutdown sequence"""
        state = self.grill_mqtt_msg["status"]["system_status"]
        if (hvac_mode in (HVACMode.OFF, HVACMode.COOL) and
                GRILL_MODE["Igniting"] <= state <= GRILL_MODE["Cook_Custom"]):
            await self.client.shutdown_grill(self.grill_id)
            return
        raise NotImplementedError(
            "Set HVAC mode not supported in current state.")


class AccessoryTraegerClimateEntity(TraegerBaseClimate):
    """Climate entity for Traeger grills"""

    def __init__(self, client, grill_id, sensor_id):
        super().__init__(client, grill_id, f"Probe {sensor_id}")
        self.sensor_id = sensor_id
        self.entity_id = f"climate.{self.grill_id.lower()}_probe_{self.sensor_id.lower()}"
        self.grill_accessory = self.client.get_details_for_accessory(
            self.grill_id, self.sensor_id)
        self.current_preset_mode = PRESET_NONE

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
        """Reports unavailable when the grill is powered off"""
        if (self.grill_mqtt_msg.get("status", None) is None or
                self.grill_mqtt_msg["status"]["connected"] is False or
                self.grill_accessory is None):
            return False
        return self.grill_accessory["con"]

    @property
    def unique_id(self):
        """Return the unique id."""
        return f"{self.grill_id}_probe_{self.sensor_id}"

    @property
    def icon(self):
        """Set the default MDI Icon"""
        return "mdi:thermometer"

    # Climate Properties
    @property
    def current_temperature(self):
        """Return the current temperature."""
        acc_type = self.grill_accessory["type"]
        if (
            self.curtemp != self.grill_accessory[acc_type]["get_temp"]
            or self.settemp != self.grill_accessory[acc_type]["set_temp"]
        ) and (
            GRILL_MODE["Igniting"]
            <= self.grill_mqtt_msg["status"]["system_status"]
            <= GRILL_MODE["Shutdown"]
        ):
            self.curtemp = self.grill_accessory[acc_type]["get_temp"]
            self.settemp = self.grill_accessory[acc_type]["set_temp"]
            if self.settemp - 5 <= self.curtemp <= self.settemp + 5:
                iconcolor = "#FF7900"
            elif self.curtemp < self.settemp - 5:
                iconcolor = "#0000FF"
            else:
                iconcolor = "#FF0000"
            notifyliveupdate_text(
                self.notify,
                self.hass,
                title=f"{self.name}",
                msg=f"Actual: {self.curtemp}\nSet: {self.settemp}",
                tag=self.unique_id,
                icon="mdi:thermometer-probe",
                icon_color=iconcolor,
                silent=True,
            )
        else:
            if self.grill_mqtt_msg["status"]["system_status"] in [
                GRILL_MODE["Idle"],
                GRILL_MODE["Sleeping"],
            ]:
                notifyclearliveupdate(self.notify, self.hass, tag=self.unique_id)
        self.curtemp = self.grill_accessory[acc_type]["get_temp"]
        return self.curtemp

    @property
    def target_temperature(self):
        """Return the temperature we try to reach."""
        acc_type = self.grill_accessory["type"]
        self.settemp = self.grill_accessory[acc_type]["set_temp"]
        return self.settemp

    @property
    def extra_state_attributes(self):
        """Return the extra state attributes."""
        acc_type = self.grill_accessory["type"]
        custom_attributes = {
            "grill_native_cur_val": self.grill_accessory[acc_type]["get_temp"],
            "grill_native_set_val": self.grill_accessory[acc_type]["set_temp"],
        }
        attributes = {}
        attributes.update(custom_attributes)
        return attributes

    @property
    def max_temp(self):
        """Return the maximum temperature."""
        # this was the max the traeger would let me set
        if self.grill_units == UnitOfTemperature.CELSIUS:
            return 100
        return 215

    @property
    def min_temp(self):
        """Return the minimum temperature."""
        # this was the min the traeger would let me set
        if self.grill_units == UnitOfTemperature.CELSIUS:
            return 27
        return 80

    @property
    def hvac_mode(self):
        """
        Return hvac operation ie. heat, cool mode.
        Need to be one of HVAC_MODE_*.
        """
        state = self.grill_accessory["con"]

        if state == 1:  # Probe Connected
            return HVACMode.HEAT
        return HVACMode.OFF

    @property
    def hvac_modes(self):
        """
        Return the list of available hvac operation modes.
        Need to be a subset of HVAC_MODES.
        """
        return (HVACMode.HEAT, HVACMode.OFF, HVACMode.COOL)

    @property
    def preset_mode(self):
        """Return the current preset mode, e.g., home, away, temp."""
        if (self.grill_mqtt_msg.get("status", None) is None or
                self.grill_mqtt_msg["status"]["probe_con"] == 0 or
                self.target_temperature == 0):
            # Reset current preset mode
            self.current_preset_mode = PRESET_NONE

        return self.current_preset_mode

    @property
    def preset_modes(self):
        """Return a list of available preset modes."""
        return list(PROBE_PRESET_MODES.keys())

    @property
    def supported_features(self):
        """Return the list of supported features for the grill"""
        return (ClimateEntityFeature.TARGET_TEMPERATURE |
                ClimateEntityFeature.PRESET_MODE |
                ClimateEntityFeature.TURN_OFF | ClimateEntityFeature.TURN_ON)

    # Climate Methods
    async def async_set_temperature(self, **kwargs):
        """Set new target temperature."""
        self.current_preset_mode = PRESET_NONE
        temperature = kwargs.get(ATTR_TEMPERATURE,0)
        await self.client.set_probe_temperature(self.grill_id,
                                                round(temperature),
                                                self.sensor_id)

    async def async_set_hvac_mode(self, hvac_mode):
        """Start grill shutdown sequence"""
        if hvac_mode in (HVACMode.HEAT, HVACMode.OFF, HVACMode.COOL):
            raise NotImplementedError(
                "HVAC Mode is determined based on the probe being plugged in.")

    async def async_set_preset_mode(self, preset_mode):
        """Set new target preset mode"""
        self.current_preset_mode = preset_mode
        temperature = PROBE_PRESET_MODES[preset_mode][self.grill_units]
        await self.client.set_probe_temperature(self.grill_id,
                                                round(temperature),
                                                self.sensor_id)
