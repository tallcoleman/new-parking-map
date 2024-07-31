import geopandas as gpd

bike_thefts: gpd.GeoDataFrame = gpd.read_file("https://ckan0.cf.opendata.inter.prod-toronto.ca/dataset/c7d34d9b-23d2-44fe-8b3b-cd82c8b38978/resource/e7fe6133-17d8-4a39-88af-352440dec684/download/bicycle-thefts.geojson")

bike_thefts_min: gpd.GeoDataFrame = bike_thefts[[
  "EVENT_UNIQUE_ID", 
  "OCC_DATE", 
  "REPORT_DATE", 
  "LOCATION_TYPE", 
  "PREMISES_TYPE", 
  "STATUS", 
  "geometry",
]]

bike_thefts_min.to_file(
  "bicycle-thefts.geojson", 
  driver="GeoJSON", 
  index=False, 
)