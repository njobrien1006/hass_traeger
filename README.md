# HomeAssistant(hass) Traeger Component

[![GitHub Release][releases-shield]][releases]
[![License][license-shield]](LICENSE)
[![hacs][hacsbadge]][hacs]

_Component to integrate with [Traeger WiFire Grills][traeger]._

[![Open your Home Assistant instance and open a repository inside the Home Assistant Community Store.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=njobrien1006&repository=hass_traeger&category=integration)

**This component will set up the following platforms.**

Platform | Description
-- | --
`sensor` | Shows various temperature readings from the grill or accessories
`climate` | Allows temperature control of the grill and probe
`number` | Allows minutes input to the timer and cook cycles.
`switch` | Allow SuperSmoke, Keepwarm, and connectivity switch
`binary sensor ` | Show values of boolean entities

## Examples

| Native Devices           |
| ------------------------ |
| ![device][deviceimg]     |

| Grill Climate      | Probe Climate      |
| ------------------ | ------------------ |
| ![grill][grillimg] | ![probe][probeimg] |

| Example Lovelace         |
| ------------------------ |
| ![lovelace][lovelaceimg] |


## Installation (HACS)

1. Add this repository to HACS
2. Search for Traeger in HACS

## Installation (Manual)

1. Using the tool of choice open the directory (folder) for your HA configuration (where you find `configuration.yaml`).
2. If you do not have a `custom_components` directory (folder) there, you need to create it.
3. In the `custom_components` directory (folder) create a new folder called `traeger`.
4. Download _all_ the files from the `custom_components/traeger/` directory (folder) in this repository.
5. Place the files you downloaded in the new directory (folder) you created.
6. Restart Home Assistant
7. In the HA UI go to "Configuration" -> "Integrations" click "+" and search for "Traeger"

## Platform Details
Some of the platforms are fairly self-explanatory, others could use a little more explaining. Below are more details on some of those platforms.
### Grill State Sensor
This sensor aligns with the status values in the Traeger app.
State | Description
-- | --
`offline` | Powered off (or not accessible)
`sleeping` | Standing by (power switch on, screen off)
`idle` | Standing by (power switch on, screen on)
`igniting` | Igniting the fire pot
`preheating` | Ignition is complete, heating to set temperature
`manual_cook` | Cooking mode
`custom_cook` | Cooking mode, using preset cook cycle
`cool_down` | Cool down cycle
`shutdown` | Cool down cycle complete, heading to sleep
`unknown` | Unknown state, report to developers

### Heating State Sensor
This sensor tries to provide more useful insight into the heating status of the grill. Many of these values can be trigger off of to provide notifications that are not available in the Traeger app.
State | Description
-- | --
`idle` | Not in igniting, preheating, cooking or cool_down modes
`preheating` | Igniting or preheating (and under 165°F)
`heating` | Trying to get temperature **up** to new target temperature
`cooling` | Trying to get temperature **down** to new target temperature
`at_temp` | Temperature has reached the target temperature (and is holding at ±20°F of target temperature)
`over_temp` | Was `at_temp`, but is now more than 20°F **above** target temperature
`under_temp` | Was `at_temp`, but is now more than 20°F **below** target temperature
`cool_down` | Cool down cycle

### Probe State Sensor
This sensor provides triggers for useful probe events such as being close to the target temperature or reaching the target temperature.
State | Description
-- | --
`idle` | Probe target temperature is **not** set (or grill is not in igniting, preheating or cooking modes)
`set` | Probe target temperature **is** set
`close` | Probe temperature is within 5°F of target temperature
`at_temp` | Probe alarm has fired
`fell_out` | Probe probably fell out of the meat (Probe temperature is greater than 215°F)

### Cook Cycle Number
This number indicates the current cook step. It runs the cook cycle as called by the `set_custom_cook` service.
State | Description
-- | --
`number.cook_cycl_step` | Full list of cook steps. Must be set by `set_custom_cook`.
`number.prev_step` | The previous step.
`number.curr_step` | The current step.
`number.next_step` | The next step.

### set_custom_cook Service
Service to set the list of steps for a cook sequence. The service must be against `number.____cook_cycle`.

See `Developer Tools : SERVICES : Traeger: Set Cook Cycle` for a default cook steps list.
Step Type | Description
-- | --
`service[].set_temp` | Set Grill Temp. *Only up to your grill's MaxTemp.
`service[].smoke` | Set Smoke Mode 1 or 0. *Only Avail if grill supports.
`service[].keepwarm` | Set keepwarm, Mode 1 or 0.
`service[].time_set` | Set Timer in Minutes.
`service[].use_timer` | Use Timer to Advance State. *Only applies to current state.
`service[].min_delta` | Min DELTA temp between Grill and Probe. *Requires `max_grill_delta_temp`.
`service[].max_grill_delta_temp` | Max Temp it will increase to from probe `min_delta`. *Requires `min_delta`.
`service[].act_temp_adv` | Grill Temp at which the State will advance.
`service[].probe_act_temp_adv` | Probe Temp at which the State will advance.
`service[].shutdown` | Call Grill Shutdown.

## InAction DEMO
![inaction][inaction]


## Configuration is done in the UI

<!---->

## Contributions are welcome!

If you want to contribute to this please read the [Contribution guidelines](CONTRIBUTING.md)

***

[traeger]: https://www.traegergrills.com/
[hacs]: https://github.com/custom-components/hacs
[hacsbadge]: https://img.shields.io/badge/HACS-Custom-orange.svg?style=flat
[deviceimg]: images/device.png
[lovelaceimg]: images/lovelace.png
[probeimg]: images/probe.png
[grillimg]: images/grill.png
[inaction]: images/CodeSpace_CooksCycle.gif
[license-shield]: https://img.shields.io/github/license/custom-components/blueprint.svg?style=flat
[releases-shield]: https://img.shields.io/github/v/release/njobrien1006/hass_traeger.svg?style=flat
[releases]: https://github.com/njobrien1006/hass_traeger/releases
