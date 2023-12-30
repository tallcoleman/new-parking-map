from abc import ABC, abstractmethod
from datetime import datetime, timezone

import geojson
import geopandas
import overpass
import requests


class BikeData(ABC):
  """Shared interface for bike data regardless of source"""

  def __init__(self, dataset_name: str):
    self.dataset_name = dataset_name

  @property
  @abstractmethod
  def last_updated(self):
    pass
  
  @property
  @abstractmethod
  def response_geojson(self):
    pass

  @abstractmethod
  def normalize(self, filter_properties, transform_properties, *, format="geodataframe"):
    pass


# CITY OF TORONTO OPEN DATA
# -------------------------

class BikeDataToronto(BikeData):
  """Wrapper for working with bicycle parking data from open.toronto.ca"""

  def __init__(self, dataset_name, resource_name):
    super().__init__(dataset_name)
    self.resource_name = resource_name

    # get metadata and download url
    meta_url = "https://ckan0.cf.opendata.inter.prod-toronto.ca/api/3/action/package_show"
    meta_params = {"id": dataset_name}
    self.metadata = requests.get(meta_url, params=meta_params).json()
    [self.metadata_resource] = [
      rs for rs 
      in self.metadata['result']['resources'] 
      if rs['name'] == resource_name
      ]
    self.download_url = self.metadata_resource['url']

    # get resource data
    self._response = requests.get(self.download_url)
  
  @property
  def last_updated(self):
    """Date-time the dataset was last updated according to the City of Toronto API"""
    # Note: ckan default is UTC for datetime: https://docs.ckan.org/en/latest/maintaining/configuration.html#ckan-display-timezone
    # "+00:00" at the end indicates UTC timezone
    return datetime.fromisoformat(self.metadata_resource['last_modified'] + "+00:00")

  @property
  def response_geojson(self):
    """GeoJSON returned from request"""
    return self._response.json()

  def normalize(self, filter_properties, transform_properties, *, format="geodataframe"):
    """Downloads, filters, and transforms open cycling data from open.toronto.ca
    
    Parameters
    ----------
    filter_properties: function(properties: dict) -> bool
      Function should take a dict of properties and return True/False.
    
    transform_properties: function(properties: dict, global_properties: dict = {}) -> dict
      Function should take a dict of properties and an optional dict of global_properties and return a new dict with the transformed keys and values.
      
    format: str either "geodataframe" or "geojson"
    
    Returns
    -------
    if format="geodataframe": GeoPandas.GeoDataFrame
    if format="geojson": dict
      geojson format
    """
    features = self.response_geojson['features'] 
    
    # apply filters
    filtered_features = [
      feature for feature in features
      if filter_properties(feature['properties'])
      ]
    
    # define global properties
    global_props = {
      "meta_source": f"https://open.toronto.ca/dataset/{self.dataset_name}/",
      "meta_source_last_updated": self.last_updated.isoformat()
    }

    # apply transforms
    transformed_features = [
      {
        'type': feature['type'],
        'geometry': feature['geometry'],
        'properties': transform_properties(feature['properties'], global_props)
      }
      for feature
      in filtered_features
    ]
    
    # return normalized data
    output_geojson = self.response_geojson.copy()
    output_geojson['features'] = transformed_features

    if (format == "geodataframe"):
      return geopandas.GeoDataFrame.from_features(output_geojson, crs=4326)
    elif (format == "geojson"):
      return output_geojson
    else:
      raise ValueError("Format must be either \"geodataframe\" or \"geojson\"")


# OPENSTREETMAP
# -------------

class BikeDataOSM(BikeData):
  """Wrapper for working with bicycle parking data from the OpenStreetMap overpass API"""

  def __init__(self, dataset_name: str, overpass_query: str):
    super().__init__(dataset_name)

    api = overpass.API()
    self._response = api.get(overpass_query, responseformat="geojson", verbosity="geom")
    meta_query = "\n".join([
      "[out:json][timeout:25];",
      overpass_query,
      "out meta;"
    ])
    self._metadata = api.get(meta_query, build=False)

  @property
  def last_updated(self):
    """Date-time the dataset was last updated as measured by the most recent date-time a feature was updated in the source data. Note that the most recent feature may not appear in the normalized output if it is filtered out."""
    # Had previously used Date-time the dataset was last cached (timestamp_osm_base) according to the Overpass API. There's also timestamp_areas_base which might be slightly different.
    # timestamp_osm_base is in UTC format (noted with "Z" at end of response string)
    # return line: datetime.fromisoformat(self._metadata['osm3s']['timestamp_osm_base'])
    features = geopandas.GeoDataFrame.from_features(self.response_geojson, crs=4326)
    return features['meta_feature_last_updated'].transform(lambda x: datetime.fromisoformat(x)).max()
  
  @property
  def response_geojson(self):
    """GeoJSON returned from request with added "meta_" properties indicating datetime the feature was last edited and OSM node id"""

    # add datetime feature was last updated from metadata
    response_out = self._response.copy()
    for feature in response_out["features"]:
      [feature_last_updated] = [
        element["timestamp"] for element 
        in self._metadata["elements"]
        if element["id"] == feature["id"]
      ]
      # convert "Z" suffix to "+00:00"
      feature_last_updated = datetime.fromisoformat(feature_last_updated).isoformat()
      feature["properties"]["meta_feature_last_updated"] = feature_last_updated
      feature["properties"]["meta_osm_node_id"] = feature["id"]
    
    return response_out

  def normalize(self, filter_properties, transform_properties, *, format="geodataframe"):
    """Downloads, filters, and transforms amenity=bicycle_parking features from the from the OpenStreetMap overpass API.
    
    Parameters
    ----------
    filter_properties: function(gdf: geodataframe) -> geodataframe
      Function takes a GeoPandas geodataframe of features and returns a filtered geodataframe.
    
    transform_properties: function(gdf: geodataframe, global_properties: dict = {}) -> geodataframe
      Function should take a geodataframe and an optional dict of global_properties and return a new geodataframe with the transformed values.

    format: str either "geodataframe" or "geojson"
    
    Returns
    -------
    if format="geodataframe": GeoPandas.GeoDataFrame
    if format="geojson": dict
      geojson format
    """
    features = geopandas.GeoDataFrame.from_features(self.response_geojson, crs=4326)

    # apply filters
    filtered_features = filter_properties(features)

    # NOTE: transform_properties function currently not used

    # add global properties
    filtered_features = filtered_features.assign(meta_source = "Source data from OpenStreetMap (See: https://www.openstreetmap.org/copyright)")
    filtered_features = filtered_features.assign(meta_source_last_updated = self.last_updated.isoformat())

    # apply transforms
    transformed_features = filtered_features

    # return normalized data
    if (format == "geodataframe"):
      return transformed_features
    elif (format == "geojson"):
      return geojson.loads(transformed_features.to_json(na="drop", drop_id=True))
    else:
      raise ValueError("Format must be either \"geodataframe\" or \"geojson\"")