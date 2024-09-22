# Script to update primary keys for bicycle-parking-high-capacity dataset used in OpenStreetMap

from pathlib import Path
import os

import geopandas as gpd

ARCHIVE_PATH = Path("Source Files")
DATASET_NAME = "bicycle-parking-high-capacity-outdoor"
OUTPUT_PATH = Path("high_capacity_pk_update") / "output"


def get_spatial_duplicates(gdf: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    """Returns only rows that are spatial duplicates"""
    return gdf[gdf["geometry"].duplicated(False)]


def agg_spatial_duplicates(gdf: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    """Aggregates points that are spatial duplicates (e.g. two points with the same geometry, one has ID "23" and the other ID "46", returns only one row with the ID "23; 46")"""
    aggregated = (
        gdf
        .groupby("geometry", as_index=False)
        .aggregate(lambda x: ";".join([str(_) for _ in x]))
    )
    return gpd.GeoDataFrame(aggregated, geometry=aggregated["geometry"])


def find_pk_change():
    """Searches subsequent pairs of folders in /Output Files and outputs informational files for the bicycle-parking-high-capacity-outdoor dataset indicating the success of matching them spatially from one week to the next and whether the ID primary key has changed."""
    archive_folders = sorted([f for f in ARCHIVE_PATH.iterdir() if f.is_dir()])
    folder_pairs = list(zip(archive_folders[:-1], archive_folders[1:]))

    for first, second in folder_pairs:
        first_file = first / (DATASET_NAME + ".geojson")
        second_file = second / (DATASET_NAME + ".geojson")
        # .explode() converts multipoint into single point
        first_gdf = gpd.read_file(first_file).explode()
        second_gdf = gpd.read_file(second_file).explode()
        first_gdf_sdupe = get_spatial_duplicates(first_gdf)
        second_gdf_sdupe = get_spatial_duplicates(second_gdf)
        first_agg = agg_spatial_duplicates(first_gdf[["geometry", "ID"]])
        second_agg = agg_spatial_duplicates(second_gdf[["geometry", "ID"]])
        sjoined = first_agg.sjoin(
            second_agg, how="left").drop(columns="index_right")
        no_match = sjoined[sjoined["ID_right"].isna()]
        id_change = sjoined[sjoined["ID_left"] != sjoined["ID_right"]]

        # output
        output_dir = OUTPUT_PATH / f"{first.name}_{second.name}"
        os.makedirs(output_dir, exist_ok=True)

        first_gdf_sdupe.to_file(
            output_dir / "first_spatial_dupes.geojson", driver="GeoJSON")
        second_gdf_sdupe.to_file(
            output_dir / "second_spatial_dupes.geojson", driver="GeoJSON")

        if len(no_match) > 0:
            no_match.to_file(output_dir / "no_match.geojson", driver="GeoJSON")

        if len(id_change) > 0:
            id_change.to_file(
                output_dir / "id_change.geojson", driver="GeoJSON")


if __name__ == "__main__":
    find_pk_change()
