# LovelaceUI Example

## Dependencies
1. [Entity Attributes Card](https://raw.githubusercontent.com/custom-cards/entity-attributes-card/master/entity-attributes-card.js
)
2. [Custom Timer Card](https://github.com/njobrien1006/hass_traeger/blob/master/config/www/timer-clock-card/timer-clock-card.js)   [{Ex: Epoch}](https://github.com/njobrien1006/hass_traeger/blob/master/config/www/epoch-clock-card/epoch-clock-card.js)



## The below example(s) can be copied & pasted into a code editor to find/replace some values to match your grill. Then ultimatly copied/pasted to your HA instance.

1. replace `0123456789ab` with your grill id.
2. replace `friendlyname` with your grill's friendly name.
**As of V2026.04.24, the Friendly name will intially populate as the grill ID.**

## Single Page View Editor
```
icon: mdi:grill-outline
badges: []
cards:
  - type: horizontal-stack
    cards:
      - type: thermostat
        entity: climate.0123456789ab_climate
      - type: thermostat
        entity: climate.friendlyname_probe_p0
  - type: entities
    entities:
      - entity: sensor.0123456789ab_ambient_temperature
      - entity: sensor.0123456789ab_cook_timer_end
      - entity: sensor.0123456789ab_cook_timer_start
      - entity: sensor.0123456789ab_pellet_level
      - entity: sensor.0123456789ab_grill_state
      - entity: sensor.0123456789ab_heating_state
      - entity: switch.0123456789ab_smoke
      - entity: switch.0123456789ab_keepwarm
      - entity: switch.0123456789ab_connect
      - entity: number.0123456789ab_cook_timer
      - entity: number.0123456789ab_cook_cycle
      - entity: binary_sensor.0123456789ab_cook_timer_complete
      - entity: binary_sensor.0123456789ab_probe_alarm_fired
      - entity: sensor.friendlyname_probe_state_p0
    title: 'friendlyname Commands / Sensors'
    show_header_toggle: false
  - type: entities
    entities:
      - entity: sensor.0123456789ab_grill_connected
      - entity: sensor.0123456789ab_cook_id
      - entity: sensor.0123456789ab_current_cycle
      - entity: sensor.0123456789ab_current_step
      - entity: sensor.0123456789ab_errors
      - entity: sensor.0123456789ab_server_status
      - entity: sensor.0123456789ab_sys_timer_end
      - entity: sensor.0123456789ab_sys_timer_start
      - entity: sensor.0123456789ab_current_time
      - entity: sensor.0123456789ab_auger_sec
      - entity: sensor.0123456789ab_fan_sec
      - entity: sensor.0123456789ab_runtime_sec
      - entity: sensor.0123456789ab_hotrod_sec
      - entity: sensor.0123456789ab_cook_cycle
      - entity: sensor.0123456789ab_failed_ignite_count
      - entity: sensor.0123456789ab_overtemp_count
      - entity: sensor.0123456789ab_lowtemp_count
      - entity: sensor.0123456789ab_state_index_count
      - entity: sensor.0123456789ab_wifi_rssi
      - entity: sensor.0123456789ab_wifi_ssid
    title: 'friendlyname Diag Sensors'
    show_header_toggle: false
  - type: history-graph
    entities:
      - entity: sensor.0123456789ab_current_time
      - entity: sensor.0123456789ab_state_index_count
    refresh_interval: 0.1
    title: 'friendlyname MQTT History'
    hours_to_show: 1
  - type: history-graph
    entities:
      - entity: climate.0123456789ab_climate
      - entity: sensor.0123456789ab_ambient_temperature
      - entity: sensor.0123456789ab_grill_state
      - entity: sensor.0123456789ab_heating_state
      - entity: climate.friendlyname_probe_p0
    refresh_interval: 0.1
    title: 'friendlyname History'
    hours_to_show: 6
  - type: custom:timer-clock-card
    disable_seconds: false
    start_time: sensor.0123456789ab_cook_timer_start
    end_time: sensor.0123456789ab_cook_timer_end
    display_date: MM/DD/YY HH:mm:ss
    caption: 'friendlyname  Timer'
    theme:
      background: black
      hands: orange
      numbers: white
      border: grey
  - type: vertical-stack
    cards:
      - type: horizontal-stack
        cards:
          - show_name: true
            show_icon: true
            type: button
            name: Step 1
            icon: mdi:chef-hat
            hold_action:
              action: none
            tap_action:
              action: call-service
              service: number.set_value
              service_data:
                value: '1'
              target:
                entity_id: number.0123456789ab_cook_cycle
          - show_name: true
            show_icon: true
            type: button
            name: Step 0
            icon: mdi:cancel
            hold_action:
              action: none
            tap_action:
              action: call-service
              service: number.set_value
              service_data:
                value: '0'
              target:
                entity_id: number.0123456789ab_cook_cycle
          - show_name: true
            show_icon: true
            type: button
            tap_action:
              action: call-service
              service: traeger.set_custom_cook
              data:
                entity_id: number.0123456789ab_cook_cycle
                steps:
                  - time_set: 15
                    set_temp: 225
                    use_timer: 1
                  - time_set: 30
                    use_timer: 1
                  - set_temp: 425
                    act_temp_adv: 400
                  - time_set: 20
                    use_timer: 1
                  - time_set: 20
                    use_timer: 1
                  - shutdown: 1
              target: {}
            name: Chicken
            hold_action:
              action: none
            icon: mdi:food-drumstick
      - type: horizontal-stack
        cards:
          - show_name: true
            show_icon: true
            type: button
            tap_action:
              action: perform-action
              data:
                entity_id: number.0123456789ab_cook_cycle
                steps:
                  - time_set: 15
                    smoke: 1
                    set_temp: 180
                    use_timer: 1
                  - probe_set_temp: 210
                    time_set: 1080
                    min_delta: 30
                    max_grill_delta_temp: 225
                    probe_act_temp_adv: 160
                  - min_delta: 35
                    max_grill_delta_temp: 230
                    probe_act_temp_adv: 170
                  - min_delta: 40
                    max_grill_delta_temp: 250
                  - time_set: 240
                    set_temp: 210
                    use_timer: 1
                  - shutdown: 1
              target: {}
              perform_action: traeger.set_custom_cook
            name: Pork Butt
            icon: mdi:pig
            hold_action:
              action: none
          - show_name: true
            show_icon: true
            type: button
            tap_action:
              action: call-service
              service: traeger.set_custom_cook
              data:
                entity_id: number.0123456789ab_cook_cycle
                steps:
                  - set_temp: 425
                    act_temp_adv: 400
                  - use_timer: 1
                    time_set: 5
                  - set_temp: 475
                    use_timer: 1
                    time_set: 15
                  - time_set: 30
                    use_timer: 1
                  - shutdown: 1
              target: {}
            icon: mdi:pizza
            name: Pizza
            hold_action:
              action: none
          - show_name: true
            show_icon: true
            type: button
            tap_action:
              action: call-service
              service: traeger.set_custom_cook
              service_data:
                entity_id: number.0123456789ab_cook_cycle
                steps:
                  - set_temp: 225
                    act_temp_adv: 220
                  - use_timer: 1
                    time_set: 15
                  - set_temp: 375
                    use_timer: 1
                    time_set: 90
            icon: mdi:pasta
            name: F.Lasagna
            hold_action:
              action: none
      - type: horizontal-stack
        cards:
          - show_name: true
            show_icon: true
            type: button
            tap_action:
              action: call-service
              service: traeger.set_custom_cook
              service_data:
                entity_id: number.0123456789ab_cook_cycle
                steps:
                  - set_temp: 425
                    act_temp_adv: 420
                  - use_timer: 1
                    time_set: 5
                  - set_temp: 465
                    act_temp_adv: 460
                  - use_timer: 1
                    time_set: 5
              target: {}
            icon: mdi:food-steak
            hold_action:
              action: none
            name: Steak
          - show_name: true
            show_icon: true
            type: button
            tap_action:
              action: call-service
              service: traeger.set_custom_cook
              service_data:
                entity_id: number.0123456789ab_cook_cycle
                steps:
                  - set_temp: 200
                    use_timer: 1
                    time_set: 20
                    smoke: 1
                  - set_temp: 180
                    use_timer: 1
                    time_set: 180
                  - set_temp: 190
                    use_timer: 1
                    time_set: 30
                  - set_temp: 195
                    use_timer: 1
                    time_set: 30
                  - set_temp: 200
                    use_timer: 1
                    time_set: 30
                  - set_temp: 205
                    use_timer: 1
                    time_set: 20
                  - set_temp: 210
                    use_timer: 1
                    time_set: 20
                  - set_temp: 215
                    use_timer: 1
                    time_set: 20
                  - set_temp: 220
                    use_timer: 1
                    time_set: 20
                  - set_temp: 225
                    use_timer: 1
                    time_set: 15
                  - set_temp: 230
                    use_timer: 1
                    time_set: 15
                  - set_temp: 235
                    use_timer: 1
                    time_set: 15
                  - set_temp: 240
                    use_timer: 1
                    time_set: 120
                  - shutdown: 1
            icon: ''
            name: P.Ribs
            hold_action:
              action: none
          - show_name: true
            show_icon: true
            type: button
            tap_action:
              action: call-service
              service: traeger.set_custom_cook
              service_data:
                entity_id: number.0123456789ab_cook_cycle
                steps:
                  - set_temp: 180
                    smoke: 1
                    use_timer: 1
                    time_set: 240
                  - set_temp: 200
                    use_timer: 1
                    time_set: 30
                  - set_temp: 205
                    use_timer: 1
                    time_set: 30
                  - set_temp: 210
                    use_timer: 1
                    time_set: 30
                  - set_temp: 215
                    use_timer: 1
                    time_set: 30
                  - set_temp: 220
                    use_timer: 1
                    time_set: 30
                  - set_temp: 225
                    use_timer: 1
                    time_set: 30
                  - set_temp: 230
                    use_timer: 1
                    time_set: 120
                  - shutdown: 1
            icon: ''
            hold_action:
              action: none
            name: Roast
      - type: entity-filter
        entities:
          - number.0123456789ab_cook_cycle
        state_filter:
          - 'on'
        card:
          type: markdown
          title: 'friendlyname CookCycSteps'
          content: >-
            {% set entity = 'number.0123456789ab_cook_cycle'%}{% for attr in
            states[entity].attributes %}{% if '_step' in attr %}{{ attr }} ===
            {{ state_attr(entity, attr) }}


            {% endif %}{% endfor %}
```