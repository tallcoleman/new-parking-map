# New Toronto Bicycle Parking Map

Development for new BikeSpace Toronto parking map

Folder content is as follows:

* Source Files: data received from the original source before any upstream filtering or transformation
* Output Files: data after upstream filtering and transformation
* Display Files: final data after downstream filtering and transformation

## Data Processing Script - Toronto Bicycle Parking Locations

Main script is `Data Pipeline/data_pipeline.py`

Run with:
```
$ uv run --python 3.11 Data\ Pipeline/data_pipeline.py  
```

### About

This script downloads, filters, and transforms data from two major sources: City of Toronto Open Data and OpenStreetMap. The goal of the script is to provide a clean and uniform data set that can be used to create a map that helps cyclists find bicycle parking in Toronto.

### Data Sources:

The OpenStreetMap data includes all elements with the tag "amenity=bicycle_parking" within the City of Toronto relation (id=324211).
The City of Toronto Open Data portal has four current datasets:
- "bicycle-parking-high-capacity-outdoor"
- "bicycle-parking-racks"
- "bicycle-parking-bike-stations-indoor"
- "street-furniture-bicycle-parking"

More information about these datasets can be found on open.toronto.ca

### Upstream Filtering

Upstream filtering removes irrelevant features (e.g. features in City data that have been "temporarily removed" or not yet marked as installed). 

### Upstream Transformation

The primary goal of upstream data transformations is to ensure a consistent output format. The output format is based on the OpenStreetMap tagging schema, with the addition of fields with the "meta_" prefix for information that may be useful but does not fit with a logical OpenStreetMap tag. (In many cases, in OpenStreetMap this meta information would be inferred from the edit history, the geography, or added as a relation).

### Downstream Filtering and Transformation

Downstream filtering and transformation is applied to clean and organize the data in more complex ways, and requires analyzing features and datasets in relation to each other. Examples include:

Handling of overlapping entries between City data and OpenStreetMap. Features are currently retained or excluded as follows:

OpenStreetMap:
* Retain: OpenStreetMap features that have a ref tag linking the feature to a City dataset (e.g. `ref:open.toronto.ca:street-furniture-bicycle-parking:id`)
* Retain: OpenStreetMap features that have any value for "ref:open.toronto.ca" (intended to allow for "ref:open.toronto.ca"="no" for City of Toronto features not included in any City dataset).
* Exclude: Any other feature with operator like "City of Toronto".

City of Toronto:
* Exclude: features where the ID matches a retained feature from OpenStreetMap
* Exclude: features included in `Data Pipeline/city_modifications/open_toronto_ca_exclusions.json` (intended to allow for City of Toronto features which have been removed, but have not yet been updated in the City dataset).

Clustering of city ring and posts (i.e. `"bicycle_parking"="bollard"`) to reduce clutter - ring and post features within 5m of each other are combined into a single point.

De-duplication of bicycle racks across multiple City datasets - in many cases, racks from different City datasets within 30m of each other are duplicates. Since there may be cases where they are not duplicates, the processing combines the features into a single point that retains the properties of all of them. In order to prevent racks from being combined, they should be surveyed to verify their number, capacity, and locations, and added to OpenStreetMap.

## Overpass query to get existing data

```
[out:xml][timeout:25];
// fetch area “City of Toronto” to search in
area(id:3600324211)->.searchArea;
// gather results
nwr["ref:open.toronto.ca:bicycle-parking-high-capacity-outdoor:id"](area.searchArea);
(._;>;); // get nodes for ways
// print results
out meta;
```