export const parkingStyleOptions = {
  // show OSM as blue and City as black
  bySource: {
    nodes: {
      'type': 'circle',
      'paint': {
        'circle-color': [
            'match',
            ['get', 'meta_source'],
            "Source data from OpenStreetMap (See: https://www.openstreetmap.org/copyright)", "blue",
            "black"
        ],
        'circle-stroke-width': [
          'case',
          ['boolean', ['feature-state', 'selected'], false], 
          2, 
          0,
        ],
        'circle-stroke-color': "red", // only shows if stroke width > 0
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
    },
    ways: {
      'type': 'fill',
      'paint': {
        'fill-color': [
          'case',
          ['boolean', ['feature-state', 'selected'], false], 
          "red",
          [
            'match',
            ['get', 'meta_source'],
            "Source data from OpenStreetMap (See: https://www.openstreetmap.org/copyright)", "blue",
            "black"
          ],
        ],
        'fill-opacity': 0.5,
      }
    },
  },
  byQuality: {
    nodes: {
      'type': 'circle',
      'paint': {
        'circle-color': [
            'match',
            ['get', 'bicycle_parking'],
            [
              "bollard", 
              "rack", 
              "stands", 
              "post_hoop", 
              "safe_loops", 
              "hoops", 
              "wide_stands",
              "two-tier",
            ], "#0000E5",
            [
              "wall_loops", 
              "wave", 
              "ground_slots", 
              "handlebar_holder", 
              "crossbar",
              "anchors",
              "lean_and_stick",
            ], "#d99726",
            [
              "lockers", 
              "building", 
              "shed"
            ], "#dc267f",
            ["None"], "grey",
            "grey"
        ],
        'circle-stroke-width': [
          'case',
          ['boolean', ['feature-state', 'selected'], false], 
          2, 
          0,
        ],
        'circle-stroke-color': "red", // only shows if stroke width > 0
        'circle-radius': [
          'interpolate', ['linear'], ['zoom'],
          // if capacity > 4, then 5px at zoom 10, else 3px
          10, [
            'case',
            ['>', ['to-number', ['get', 'capacity'], 0], 4],
            5, 3,
          ],
          // if capacity > 4 then 16px at zoom 22, else 10px
          22, [
            'case',
            ['>', ['to-number', ['get', 'capacity'], 0], 4],
            16, 10,
          ],
        ],
      }
    },
    ways: {
      'type': 'fill',
      'paint': {
        'fill-color': [
          'case',
          ['boolean', ['feature-state', 'selected'], false], "red",
          [
            'match',
            ['get', 'bicycle_parking'],
            [
              "bollard", 
              "rack", 
              "stands", 
              "post_hoop", 
              "safe_loops", 
              "hoops", 
              "wide_stands",
              "two-tier",
            ], "#0000E5",
            [
              "wall_loops", 
              "wave", 
              "ground_slots", 
              "handlebar_holder", 
              "crossbar",
              "anchors",
              "lean_and_stick",
            ], "#d99726",
            [
              "lockers", 
              "building", 
              "shed"
            ], "#dc267f",
            ["None"], "grey",
            "grey"
          ],
        ],
        'fill-opacity': 0.5,
      }
    },
  },
};