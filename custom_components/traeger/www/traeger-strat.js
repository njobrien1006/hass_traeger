import "./js-yaml.js";
const jsyaml = globalThis.jsyaml;
class TraegerStrategy {
  static async generate(config, hass) {
    var all_cards = [];
    var climcards = [];
    var notdiagcards = [];
    var diagcards = [];
    var histcards = [];
    var thistcards = [];

    const [entities, devices] = await Promise.all([
      hass.callWS({ type: "config/entity_registry/list" }),
      hass.callWS({ type: "config/device_registry/list" }),
    ]);

    //console.log(devices);
    let traegerdevices = devices.filter(
      (item) => item.manufacturer === "Traeger"
    );
    //console.log(traegerdevices);

    let traegerentities = [];
    for (let ii = 0; ii < traegerdevices.length; ++ii) {
      traegerentities = entities.filter(
        (item) => item.device_id === traegerdevices[ii].id
      );
      //console.log(traegerentities);

      //Pluck Clim Entities
      for (let i = 0; i < traegerentities.length; ++i) {
        if (
          traegerentities[i].disabled_by === null &&
          traegerentities[i].entity_id.substring(0, 7) === "climate"
        ) {
          climcards.push({
            type: "thermostat",
            entity: traegerentities[i].entity_id,
          });
        }
      }
      // Push Clim Entities
      if (climcards.length > 0) {
        all_cards.push({
          type: "horizontal-stack",
          cards: climcards,
        });
      }
      //Pluck NonDiag Entities
      for (let i = 0; i < traegerentities.length; ++i) {
        if (
          traegerentities[i].entity_category != "diagnostic" &&
          traegerentities[i].disabled_by === null &&
          traegerentities[i].entity_id.substring(0, 7) != "climate"
        ) {
          notdiagcards.push({
            entity: traegerentities[i].entity_id,
          });
        }
      }
      // Push NonDiag Entities
      if (notdiagcards.length > 0) {
        all_cards.push({
          type: "entities",
          entities: notdiagcards,
          title: traegerdevices[ii].name + " Commands / Sensors",
          show_header_toggle: false,
        });
      }
      //Pluck Diag Entities
      for (let i = 0; i < traegerentities.length; ++i) {
        if (
          traegerentities[i].entity_category === "diagnostic" &&
          traegerentities[i].disabled_by === null
        ) {
          diagcards.push({
            entity: traegerentities[i].entity_id,
          });
        }
      }
      // Push Diag Entities
      if (diagcards.length > 0) {
        all_cards.push({
          type: "entities",
          entities: diagcards,
          title: traegerdevices[ii].name + " Diag Sensors",
          show_header_toggle: false,
        });
      }
      //Pluck Hist Entities
      for (let i = 0; i < traegerentities.length; ++i) {
        if (
          traegerentities[i].disabled_by === null &&
          (traegerentities[i].unique_id.slice(-10) === "stateIndex" ||
            traegerentities[i].unique_id.slice(-5) === "_time")
        ) {
          histcards.push({
            entity: traegerentities[i].entity_id,
          });
        }
      }
      // Push Hist Entities
      if (histcards.length > 0) {
        all_cards.push({
          type: "history-graph",
          entities: histcards,
          refresh_interval: 0.1,
          title: traegerdevices[ii].name + " MQTT History",
          hours_to_show: 1,
        });
      }
      //Pluck THist Entities
      for (let i = 0; i < traegerentities.length; ++i) {
        if (
          traegerentities[i].disabled_by === null &&
          (traegerentities[i].unique_id.slice(-8) === "_climate" ||
            traegerentities[i].unique_id.slice(-9) === "_probe_p0" ||
            traegerentities[i].unique_id.slice(-8) === "_ambient" ||
            traegerentities[i].unique_id.slice(-12) === "_grill_state" ||
            traegerentities[i].unique_id.slice(-14) === "_heating_state")
        ) {
          thistcards.push({
            entity: traegerentities[i].entity_id,
          });
        }
      }
      // Push THist Entities
      if (thistcards.length > 0) {
        all_cards.push({
          type: "history-graph",
          entities: thistcards,
          refresh_interval: 0.1,
          title: traegerdevices[ii].name + " History",
          hours_to_show: 6,
        });
      }
      //Pluck Clock Entities
      for (let i = 0; i < traegerentities.length; ++i) {
        if (
          traegerentities[i].disabled_by === null &&
          traegerentities[i].unique_id.slice(-17) === "_cook_timer_start"
        ) {
          var sTime = traegerentities[i].entity_id;
        }
        if (
          traegerentities[i].disabled_by === null &&
          traegerentities[i].unique_id.slice(-15) === "_cook_timer_end"
        ) {
          var eTime = traegerentities[i].entity_id;
        }
      }
      // Push Clock Entities
      if (sTime != null && eTime != null) {
        all_cards.push({
          type: "custom:timer-clock-card",
          disable_seconds: false,
          start_time: sTime,
          end_time: eTime,
          display_date: "MM/DD/YY HH:mm:ss",
          caption: traegerdevices[ii].name + "  Timer",
          theme: {
            background: "black",
            hands: "orange",
            numbers: "white",
            border: "grey",
          },
        });
      }

      //Pluck cCycle Entity
      for (let i = 0; i < traegerentities.length; ++i) {
        if (
          traegerentities[i].disabled_by === null &&
          traegerentities[i].unique_id.slice(-11) === "_cook_cycle"
        ) {
          var cCycle = traegerentities[i].entity_id;
        }
      }
      // Push cCycle Entity
      if (cCycle != null) {
        all_cards.push({
          type: "vertical-stack",
          cards: [
            {
              type: "horizontal-stack",
              cards: [
                {
                  show_name: true,
                  show_icon: true,
                  type: "button",
                  name: "Step 1",
                  icon: "mdi:chef-hat",
                  hold_action: { action: "none" },
                  tap_action: {
                    action: "call-service",
                    service: "number.set_value",
                    service_data: { value: "1" },
                    target: { entity_id: cCycle },
                  },
                },
                {
                  show_name: true,
                  show_icon: true,
                  type: "button",
                  name: "Step 0",
                  icon: "mdi:cancel",
                  hold_action: { action: "none" },
                  tap_action: {
                    action: "call-service",
                    service: "number.set_value",
                    service_data: { value: "0" },
                    target: { entity_id: cCycle },
                  },
                },
                {
                  show_name: true,
                  show_icon: true,
                  type: "button",
                  tap_action: {
                    action: "call-service",
                    service: "traeger.set_custom_cook",
                    data: {
                      entity_id: cCycle,
                      steps: [
                        { time_set: 15, set_temp: 225, use_timer: 1 },
                        { time_set: 30, use_timer: 1 },
                        { set_temp: 425, act_temp_adv: 400 },
                        { time_set: 20, use_timer: 1 },
                        { time_set: 20, use_timer: 1 },
                        { shutdown: 1 },
                      ],
                    },
                    target: {},
                  },
                  name: "Chicken",
                  hold_action: { action: "none" },
                  icon: "mdi:food-drumstick",
                },
              ],
            },
            {
              type: "horizontal-stack",
              cards: [
                {
                  show_name: true,
                  show_icon: true,
                  type: "button",
                  tap_action: {
                    action: "perform-action",
                    data: {
                      entity_id: cCycle,
                      steps: [
                        { time_set: 15, smoke: 1, set_temp: 180, use_timer: 1 },
                        {
                          probe_set_temp: 210,
                          time_set: 1080,
                          min_delta: 30,
                          max_grill_delta_temp: 225,
                          probe_act_temp_adv: 160,
                        },
                        {
                          min_delta: 35,
                          max_grill_delta_temp: 230,
                          probe_act_temp_adv: 170,
                        },
                        { min_delta: 40, max_grill_delta_temp: 250 },
                        { time_set: 240, set_temp: 210, use_timer: 1 },
                        { shutdown: 1 },
                      ],
                    },
                    target: {},
                    perform_action: "traeger.set_custom_cook",
                  },
                  name: "Pork Butt",
                  icon: "mdi:pig",
                  hold_action: { action: "none" },
                },
                {
                  show_name: true,
                  show_icon: true,
                  type: "button",
                  tap_action: {
                    action: "call-service",
                    service: "traeger.set_custom_cook",
                    data: {
                      entity_id: cCycle,
                      steps: [
                        { set_temp: 425, act_temp_adv: 400 },
                        { use_timer: 1, time_set: 5 },
                        { set_temp: 475, use_timer: 1, time_set: 15 },
                        { time_set: 30, use_timer: 1 },
                        { shutdown: 1 },
                      ],
                    },
                    target: {},
                  },
                  icon: "mdi:pizza",
                  name: "Pizza",
                  hold_action: { action: "none" },
                },
                {
                  show_name: true,
                  show_icon: true,
                  type: "button",
                  tap_action: {
                    action: "call-service",
                    service: "traeger.set_custom_cook",
                    service_data: {
                      entity_id: cCycle,
                      steps: [
                        { set_temp: 225, act_temp_adv: 220 },
                        { use_timer: 1, time_set: 15 },
                        { set_temp: 375, use_timer: 1, time_set: 90 },
                      ],
                    },
                  },
                  icon: "mdi:pasta",
                  name: "F.Lasagna",
                  hold_action: { action: "none" },
                },
              ],
            },
            {
              type: "horizontal-stack",
              cards: [
                {
                  show_name: true,
                  show_icon: true,
                  type: "button",
                  tap_action: {
                    action: "call-service",
                    service: "traeger.set_custom_cook",
                    service_data: {
                      entity_id: cCycle,
                      steps: [
                        { set_temp: 425, act_temp_adv: 420 },
                        { use_timer: 1, time_set: 5 },
                        { set_temp: 465, act_temp_adv: 460 },
                        { use_timer: 1, time_set: 5 },
                      ],
                    },
                    target: {},
                  },
                  icon: "mdi:food-steak",
                  hold_action: { action: "none" },
                  name: "Steak",
                },
                {
                  show_name: true,
                  show_icon: true,
                  type: "button",
                  tap_action: {
                    action: "call-service",
                    service: "traeger.set_custom_cook",
                    service_data: {
                      entity_id: cCycle,
                      steps: [
                        { set_temp: 200, use_timer: 1, time_set: 20, smoke: 1 },
                        { set_temp: 180, use_timer: 1, time_set: 180 },
                        { set_temp: 190, use_timer: 1, time_set: 30 },
                        { set_temp: 195, use_timer: 1, time_set: 30 },
                        { set_temp: 200, use_timer: 1, time_set: 30 },
                        { set_temp: 205, use_timer: 1, time_set: 20 },
                        { set_temp: 210, use_timer: 1, time_set: 20 },
                        { set_temp: 215, use_timer: 1, time_set: 20 },
                        { set_temp: 220, use_timer: 1, time_set: 20 },
                        { set_temp: 225, use_timer: 1, time_set: 15 },
                        { set_temp: 230, use_timer: 1, time_set: 15 },
                        { set_temp: 235, use_timer: 1, time_set: 15 },
                        { set_temp: 240, use_timer: 1, time_set: 120 },
                        { shutdown: 1 },
                      ],
                    },
                  },
                  icon: "",
                  name: "P.Ribs",
                  hold_action: { action: "none" },
                },
                {
                  show_name: true,
                  show_icon: true,
                  type: "button",
                  tap_action: {
                    action: "call-service",
                    service: "traeger.set_custom_cook",
                    service_data: {
                      entity_id: cCycle,
                      steps: [
                        {
                          set_temp: 180,
                          smoke: 1,
                          use_timer: 1,
                          time_set: 240,
                        },
                        { set_temp: 200, use_timer: 1, time_set: 30 },
                        { set_temp: 205, use_timer: 1, time_set: 30 },
                        { set_temp: 210, use_timer: 1, time_set: 30 },
                        { set_temp: 215, use_timer: 1, time_set: 30 },
                        { set_temp: 220, use_timer: 1, time_set: 30 },
                        { set_temp: 225, use_timer: 1, time_set: 30 },
                        { set_temp: 230, use_timer: 1, time_set: 120 },
                        { shutdown: 1 },
                      ],
                    },
                  },
                  icon: "",
                  hold_action: { action: "none" },
                  name: "Roast",
                },
              ],
            },
            {
              type: "entity-filter",
              entities: [cCycle],
              state_filter: ["on"],
              card: {
                type: "markdown",
                title: traegerdevices[ii].name + " CookCycSteps",
                content:
                  "{% set entity = '" +
                  cCycle +
                  "'%}" +
                  "{% for attr in states[entity].attributes %}" +
                  "{% if '_step' in attr %}" +
                  "{{ attr }} === {{ state_attr(entity, attr) }}\n\n" +
                  "{% endif %}" +
                  "{% endfor %}",
              },
            },
          ],
        });
      }
    }

    all_cards.push({
      type: "custom:traeger-yaml-view",
      context: JSON.stringify({ cards: all_cards }),
    });

    return {
      cards: all_cards,
    };
  }
}

customElements.define("ll-strategy-view-traeger-strat", TraegerStrategy);
