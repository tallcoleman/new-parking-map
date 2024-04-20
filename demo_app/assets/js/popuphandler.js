import { bicycleParkingDescriptions as bpd } from "./bicycle_parking descriptions.js";

export class PopUpHandler {
  #selectedFeatures = null;
  /**
   * Class to encapsulate functions and properties managing map popups
   * @param {maplibregl.Map} map 
   * @param {string[]} layers Map layers to check for popup values
   * @param {Node} popUpContainer 
   * @param {Node} layoutTarget
   * @param {string} activeClass 
   */
  constructor(map, layers, popUpContainer, layoutTarget, activeClass) {
    this.map = map;
    this.layers = layers;
    this.popUpContainer = popUpContainer;
    this.layoutTarget = layoutTarget;
    this.activeClass = activeClass;

    // build header etc.
    this.popUpContainer.innerHTML = `
      <div class="puh-header">
        <h2>_ features</h2>
        <button type="button" id="puh-button-close">✕</button>
      </div>
      <div class="puh-content">
      </div>`;

    document.getElementById("puh-button-close")
      .addEventListener("click", () => {
        this.hidePopUp();
        this.selectedFeatures = null;
    });

    // change pointer on leave/exit feature
    for (const layer of layers) {
      this.map.on('mouseenter', layer, () => {
        this.map.getCanvas().style.cursor = 'pointer';
      });
      this.map.on('mouseleave', layer, () => {
        this.map.getCanvas().style.cursor = '';
      });
    }
  }

  get selectedFeatures() {
    return this.#selectedFeatures;
  }

  set selectedFeatures(features) {
    if (this.#selectedFeatures?.length > 0) {
      for (const feature of this.#selectedFeatures) {
        this.map.setFeatureState(
          {source: feature.source, id: feature.id},
          {selected: false},
        );
      }
    }
    if (features?.length > 0) {
      for (const feature of features) {
        this.map.setFeatureState(
          {source: feature.source, id: feature.id},
          {selected: true},
        );
      }
      this.#selectedFeatures = features;
    } else {
      this.#selectedFeatures = null;
    }
  }

  fromPoint(point) {
    const features = this.map.queryRenderedFeatures(
      Object.values(point),
      {'layers': this.layers}
    );
    if (features.length > 0) {  
      this.updatePopUpContent(features);
      this.showPopUp();
      this.selectedFeatures = features;
      this.zoomAndFlyTo(features[0]);
    } else {
      this.hidePopUp();
      this.selectedFeatures = null;
    }
  }

  showPopUp() {
    this.layoutTarget.classList.add("layout-popup");
  }

  hidePopUp() {
    this.layoutTarget.classList.remove(this.activeClass);
  }

  zoomAndFlyTo(feature, zoomLevel = 15) {
    this.map.resize();
    let coordinates;
    if (feature.geometry.type === "LineString") {
      coordinates = feature.geometry.coordinates[0];
    } else {
      coordinates = feature.geometry.coordinates;
    }
    this.map.flyTo({
      center: coordinates,
      zoom: zoomLevel,
    });
  }

  updatePopUpContent(features) {
    const oneFeature = features.length === 1;
    this.popUpContainer.querySelector(".puh-header h2")
      .textContent = `${features.length} feature${oneFeature ? "" : "s"}`;

    let content = [];
    for (const feature of features) {
      content.push(this.featureDetailsSummary(
        feature.properties,
        oneFeature,
      ));
    }
    this.popUpContainer.querySelector(".puh-content")
      .innerHTML = content.join("");
  }

  featureDetailsSummary(properties, oneFeature = false) {
    const capacityDescription = properties['capacity'] ?
      ` (capacity ${properties['capacity']})` : "";
    const parkingType = properties['bicycle_parking'] ?? "unknown type";
    const typeDescription = bpd?.[parkingType] ?? parkingType;

    let content = [];
    content.push(`<details${oneFeature ? " open" : ""}>`);
    content.push(`<summary>${typeDescription}${capacityDescription}</summary>`);
    content.push(`<div class="puh-details-content">`);
    content.push(`<p>${properties['meta_source']}</p>`);
    content.push(`<dl>`);
    for (const [key, value] of Object.entries(properties)) {
      content.push(`
        <dt>${key}</dt>
        <dd>${value}</dd>
      `);
    }
    content.push(`</dl>`);
    content.push(`</div>`);
    content.push(`</details>`);
  
    return content.join("");
  }
}