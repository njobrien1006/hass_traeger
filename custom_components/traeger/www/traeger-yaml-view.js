import "./js-yaml.js";
const jsyaml = globalThis.jsyaml;
class ContentCardExample extends HTMLElement {
  // card is connected to the DOM
  connectedCallback() {
    // initial render
    this._render();
  }

  // renders the html of the card, just if needed
  _render = () => {
    this.innerHTML = `
<ha-card>
  <h1 style="text-align:center;">This Page YAML</h1>
  <p style=";
  overflow-x: auto;
  max-height: 300px;
  user-select: text;
  white-space: pre;
  margin: 16px;
  padding: 16px;
  background-color:hsla(0, 0%, 0%, 0.6)
  ">
${jsyaml.dump(JSON.parse(this.config.context)).replaceAll("\n", "<br>")}
  </p>
</ha-card>
`;
  };

  // The user supplied configuration. Throw an exception and Home Assistant
  // will render an error card.
  setConfig(config) {
    if (!config.context) {
      throw new Error("You need to define context");
    }
    this.config = config;
  }
}

customElements.define("traeger-yaml-view", ContentCardExample);
