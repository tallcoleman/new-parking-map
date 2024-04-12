import "./thirdparty/maplibre-gl.js";
import "./thirdparty/maplibre-gl-geocoder.min.js"

const displayData = "https://raw.githubusercontent.com/tallcoleman/new-parking-map/main/Display%20Files/all_sources.geojson";
const bikeLaneURL = "data/cycling-network.geojson";

const map = new maplibregl.Map({
  container: 'map',
  style: 'https://api.maptiler.com/maps/streets/style.json?key=MlRGiaPF42qIx2cAP9Hn',
  center: [-79.416, 43.714],
  zoom: 10.5
});

function generatePropertyTable(properties) {
  let content = [];
  content.push(`<h2>${properties['bicycle_parking'] ?? "Unknown Type"}</h2>`);
  content.push(`<p>${properties['meta_source']}</p>`);
  content.push(`<dl>`);
  for (const [key, value] of Object.entries(properties)) {
    content.push(`
      <dt>${key}</dt>
      <dd>${value}</dd>
    `);
  }
  content.push(`</dl>`);

  return content.join("");
}

class BBox {
  constructor(xmin, xmax, ymin, ymax) {
    this.xmin = xmin;
    this.xmax = xmax;
    this.ymin = ymin;
    this.ymax = ymax;
  }
  getURLParams() {
    return `${this.xmin},${this.ymin},${this.xmax},${this.ymax}`;
  }
}
const torontoBBox = new BBox(-79.6392832, -79.1132193, 43.5796082, 43.8554425);

const geocoderApi = {
  forwardGeocode: async (config) => {
      const features = [];
      try {
          const request =
      `https://nominatim.openstreetmap.org/search?q=${
          config.query
      }&format=geojson&polygon_geojson=1&addressdetails=1&countrycodes=CA&viewbox=${torontoBBox.getURLParams()}&bounded=1`;
          const response = await fetch(request);
          const geojson = await response.json();
          for (const feature of geojson.features) {
              const center = [
                  feature.bbox[0] +
              (feature.bbox[2] - feature.bbox[0]) / 2,
                  feature.bbox[1] +
              (feature.bbox[3] - feature.bbox[1]) / 2
              ];
              const point = {
                  type: 'Feature',
                  geometry: {
                      type: 'Point',
                      coordinates: center
                  },
                  place_name: feature.properties.display_name,
                  properties: feature.properties,
                  text: feature.properties.display_name,
                  place_type: ['place'],
                  center
              };
              features.push(point);
          }
      } catch (e) {
          console.error(`Failed to forwardGeocode with error: ${e}`);
      }

      return {
          features
      };
  }
};

map.on('load', () => {
  map.addControl(new maplibregl.NavigationControl(), 'top-left');
  map.addControl(new maplibregl.GeolocateControl(), 'top-left');
  map.addControl(
    new MaplibreGeocoder(geocoderApi, {
        maplibregl
    })
  );

  map.addSource('bicycle-parking', {
      'type': 'geojson',
      'data': displayData,
  });
  map.addSource('bicycle-lanes', {
    'type': 'geojson',
    'data': bikeLaneURL,
  });

  // Add a layer showing bike lanes
  map.addLayer({
    'id': 'bicycle-lanes',
    'type': 'line',
    'source': 'bicycle-lanes',
    'layout': {
      'line-cap': 'round',
    },
    'paint': {
      'line-width': 2,
      'line-color': [
        "match",
        ["get", "INFRA_HIGHORDER"],
        [
          "Cycle Track",
          "Cycle Track - Contraflow",
          "Bi-Directional Cycle Track"
        ],
        "hsl(137, 68%, 23%)",
        [
          "Multi-Use Trail - Boulevard",
          "Multi-Use Trail - Entrance",
          "Multi-Use Trail - Existing Connector",
          "Multi-Use Trail - Connector",
          "Multi-Use Trail",
          "Park Road"
        ],
        "#8c5535",
        [
          "Bike Lane - Buffered",
          "Bike Lane",
          "Bike Lane - Contraflow"
        ],
        "hsl(137, 68%, 36%)",
        [
          "Sharrows - Wayfinding",
          "Sharrows - Arterial - Connector",
          "Signed Route (No Pavement Markings)",
          "Sharrows"
        ],
        "hsl(137, 56%, 62%)",
        "#2c3b42"
      ]
    },
  })  

  // Add a layer showing the parking
  map.addLayer({
      'id': 'bicycle-parking',
      'type': 'circle',
      'source': 'bicycle-parking',
      'paint': {
        'circle-color': [
            'match',
            ['get', 'meta_source'],
            "Source data from OpenStreetMap (See: https://www.openstreetmap.org/copyright)", "blue",
            "black"
        ],
        'circle-radius': [
            'match',
            ['get', 'bicycle_parking'],
            "bollard", 3,
            "post_hoop", 3,
            "stands", 3,
            "hoops", 3,
            5
        ]
      }
  });

  // When a click event occurs on a feature in the bicycle-parking layer, open a popup at the
  // location of the feature, with description HTML from its properties.
  map.on('click', 'bicycle-parking', (e) => {
    console.log(e.features[0].properties);
      const coordinates = e.features[0].geometry.coordinates.slice();
      const description = generatePropertyTable(e.features[0].properties);

      // Ensure that if the map is zoomed out such that multiple
      // copies of the feature are visible, the popup appears
      // over the copy being pointed to.
      while (Math.abs(e.lngLat.lng - coordinates[0]) > 180) {
          coordinates[0] += e.lngLat.lng > coordinates[0] ? 360 : -360;
      }

      new maplibregl.Popup()
          .setLngLat(coordinates)
          .setHTML(description)
          .setMaxWidth("300px")
          .addTo(map);
  });

  // Change the cursor to a pointer when the mouse is over the bicycle-parking layer.
  map.on('mouseenter', 'bicycle-parking', () => {
      map.getCanvas().style.cursor = 'pointer';
  });

  // Change it back to a pointer when it leaves.
  map.on('mouseleave', 'bicycle-parking', () => {
      map.getCanvas().style.cursor = '';
  });
});