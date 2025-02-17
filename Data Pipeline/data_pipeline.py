# DATA PROCESSING SCRIPT - TORONTO BICYCLE PARKING LOCATIONS
# ==========================================================
#
# This script downloads, filters, and transforms data from two major sources: City of Toronto Open Data and OpenStreetMap. The goal of the script is to provide a clean and uniform data set that can be used to create a map that helps cyclists find bicycle parking in Toronto.


# IMPORTS
# -------

from datetime import datetime, timezone
from itertools import chain
import json
from zoneinfo import ZoneInfo

import geojson
import geopandas
import numpy as np
import pandas as pd
from pathlib import Path
from shapely import Polygon
import overpass

from pandas.api.types import is_datetime64_any_dtype

import conversions
from wrappers import BikeData, BikeDataToronto, BikeDataOSM, BikeLockersToronto
from downstream import (
    group_proximate_rings,
    group_proximate_racks,
    drop_mapped_city_lockers,
)

geopandas.options.io_engine = "pyogrio"


def ref_cols_to_str(gdf: geopandas.GeoDataFrame) -> geopandas.GeoDataFrame:
    """Convert dtype for ref columns to string"""
    ref_cols = gdf.filter(like="ref:open.toronto.ca", axis=1)
    for name, values in ref_cols.items():
        gdf[name] = values.astype("str")
    return gdf


def dt_cols_to_str(gdf: geopandas.GeoDataFrame) -> geopandas.GeoDataFrame:
    """Convert dtype for datetime columns to string"""
    json_not_supported_cols = gdf.columns[
        [is_datetime64_any_dtype(gdf[c]) for c in gdf.columns]
    ].union(gdf.columns[gdf.dtypes == "object"])
    if len(json_not_supported_cols) > 0:
        gdf = gdf.astype({c: "string" for c in json_not_supported_cols})
    return gdf

    # SCRIPT EXECUTION
    # ----------------


print("Loading sources and statuses...")


def run_pipeline():
    """Main function to run the data processing pipeline."""

    # get today's date and use to set output folders
    # unlike other dates in this script, uses Toronto time not UTC
    today_toronto_isodate = datetime.now(ZoneInfo("America/Toronto")).strftime(
        "%Y-%m-%d"
    )

    sfp = Path("Source Files/")
    sfp_archive = sfp / f"{today_toronto_isodate}/"
    ofp = Path("Output Files/")
    ofp_archive = ofp / f"{today_toronto_isodate}/"
    dfp = Path("Display Files/")
    dfp_archive = dfp / f"{today_toronto_isodate}/"

    for p in [sfp, sfp_archive, ofp, ofp_archive, dfp, dfp_archive]:
        if not p.exists():
            p.mkdir()

    # load in details and status

    def load_paths(paths: dict) -> dict:
        data = {}
        for label, path in paths.items():
            item_data = None
            if path.exists():
                with path.open() as f:
                    item_data = json.load(f)
            else:
                item_data = {}

            data = data | {label: item_data}

        return data

    # load paths to .json files specifying details and status of data sources
    source_paths = {
        "city": Path("Data Pipeline/sources/open_toronto_ca_sources.json"),
        "osm": Path("Data Pipeline/sources/openstreetmap_sources.json"),
        "lockers": Path("Data Pipeline/sources/toronto_lockers_sources.json"),
    }
    status_paths = {
        "city": Path("Data Pipeline/statuses/open_toronto_ca_statuses.json"),
        "osm": Path("Data Pipeline/statuses/openstreetmap_statuses.json"),
        "lockers": Path("Data Pipeline/statuses/toronto_lockers_statuses.json"),
    }
    sources = load_paths(source_paths)
    statuses = load_paths(status_paths)

    # update function

    def run_update(bike_data: type[BikeData], dataset_status: dict) -> dict:
        """Function to check whether specified dataset is up to date and download new data if required.

        Parameters
        ----------
        bike_data: type[BikeData]
        dataset_status: dict
          - Optional

        Returns
        -------
          Returns a status dict with the following values:
          - last_updated: datetime the source dataset was last updated
          - num_normalized_features: number of features in filtered/transformed output
          - last_checked: datetime the source was last queried
          - days_since_source_update: calculated number of days between last_checked and last_updated to indicate source data freshness

        As a side effect, will save or update the following files:
        - Data received from the source: /Source Files/{bike_data.dataset_name}.geojson
        - Normalized (filtered and transformed) data: /Source Files/{bike_data.dataset_name}-normalized.geojson

        """

        # check if data has been updated
        rec_last_updated_str = dataset_status.setdefault("last_updated", None)
        rec_last_updated = (
            datetime.fromisoformat(rec_last_updated_str)
            if rec_last_updated_str
            # None not allowed in date comparsion; this is like datetime.min but tz aware
            else datetime(1, 1, 1, tzinfo=timezone.utc)
        )

        # save source file
        with open(sfp / f"{bike_data.dataset_name}.geojson", "w") as f:
            geojson.dump(bike_data.response_geojson, f, indent=2)
        with open(sfp_archive / f"{bike_data.dataset_name}.geojson", "w") as f:
            geojson.dump(bike_data.response_geojson, f, indent=2)

        # get normalized output
        filter_properties = conversions.get_filter(bike_data.dataset_name)
        transform_properties = conversions.get_transform(bike_data.dataset_name)
        normalized_gdf = bike_data.normalize(filter_properties, transform_properties)

        # save normalized output
        na_option = "drop" if isinstance(bike_data, BikeDataOSM) else "null"
        with open(ofp / f"{bike_data.dataset_name}-normalized.geojson", "w") as f:
            f.write(normalized_gdf.to_json(na=na_option, drop_id=True, indent=2))
        with open(
            ofp_archive / f"{bike_data.dataset_name}-normalized.geojson", "w"
        ) as f:
            f.write(normalized_gdf.to_json(na=na_option, drop_id=True, indent=2))

        num_normalized_features = len(normalized_gdf)

        # update status from metadata
        dataset_status["last_updated"] = bike_data.last_updated.isoformat()
        dataset_status["num_normalized_features"] = num_normalized_features

        # update check datetime
        last_checked = datetime.now(timezone.utc)
        dataset_status["last_checked"] = last_checked.isoformat()
        dataset_status["days_since_source_update"] = (
            last_checked - datetime.fromisoformat(dataset_status["last_updated"])
        ).days
        return dataset_status

    # City of Toronto Data
    print("Checking and updating City of Toronto data...")

    # check status and update output file if needed
    for dataset in sources["city"]["datasets"]:
        bdt = BikeDataToronto(dataset["dataset_name"], dataset["resource_name"])
        dataset_status = statuses["city"].setdefault(bdt.dataset_name, {})
        # check source and save output files if there are new changes
        updated_status = run_update(bdt, dataset_status)
        statuses["city"][bdt.dataset_name] = (
            statuses["city"][bdt.dataset_name] | updated_status
        )

    # update status JSON
    status_fp = Path("Data Pipeline/statuses/")
    if not status_fp.exists():
        status_fp.mkdir()
    with status_paths["city"].open("w") as f:
        json.dump(statuses["city"], f, indent=2)

    # get output files, do further processing and combine
    city_data = {}
    for dataset in sources["city"]["datasets"]:
        gdf = geopandas.read_file(
            ofp / f"{dataset['dataset_name']}-normalized.geojson"
        ).convert_dtypes()
        gdf = gdf.astype({"meta_source_last_updated": "str", "capacity": "Int64"})
        gdf = ref_cols_to_str(gdf)
        gdf = gdf.explode(index_parts=False)
        gdf.insert(0, "source", dataset["dataset_name"])
        city_data[dataset["dataset_name"]] = gdf

    # OpenStreetMap Data
    print("Checking and updating OpenStreetMap data...")

    # check status and update output file if needed
    for dataset in sources["osm"]["datasets"]:
        bdo = BikeDataOSM(dataset["dataset_name"], dataset["overpass_query"])
        dataset_status = statuses["osm"].setdefault(bdo.dataset_name, {})
        # check source and save output files if there are new changes
        updated_status = run_update(bdo, dataset_status)
        statuses["osm"][bdo.dataset_name] = (
            statuses["osm"][bdo.dataset_name] | updated_status
        )

    # update status JSON
    with status_paths["osm"].open("w") as f:
        json.dump(statuses["osm"], f, indent=2)

    # get output files, do further processing and combine
    osm_data_list = []
    for dataset in sources["osm"]["datasets"]:
        gdf = geopandas.read_file(
            ofp / f"{dataset['dataset_name']}-normalized.geojson"
        ).convert_dtypes()
        gdf = gdf.astype(
            {
                "meta_source_last_updated": "str",
                "meta_feature_last_updated": "str",
            }
        )
        osm_data_list.append(gdf)

    osm_combined = pd.concat(osm_data_list)

    # City Lockers
    print("Checking and updating City of Toronto bike lockers...")

    # check status and update output file if needed
    for dataset in sources["lockers"]["datasets"]:
        blt = BikeLockersToronto(dataset["dataset_name"], dataset["url"])
        dataset_status = statuses["lockers"].setdefault(blt.dataset_name, {})
        # check source and save output files if there are new changes
        updated_status = run_update(blt, dataset_status)
        statuses["lockers"][blt.dataset_name] = (
            statuses["lockers"][blt.dataset_name] | updated_status
        )

    # update status JSON
    with status_paths["lockers"].open("w") as f:
        json.dump(statuses["lockers"], f, indent=2)

    # get output files, do further processing and combine
    lockers_data_list = []
    for dataset in sources["lockers"]["datasets"]:
        gdf = geopandas.read_file(ofp / f"{dataset['dataset_name']}-normalized.geojson")
        gdf = gdf.convert_dtypes().astype(
            {"meta_source_last_updated": "str", "capacity": "Int64"}
        )
        lockers_data_list.append(gdf)

    lockers: geopandas.GeoDataFrame = pd.concat(lockers_data_list)

    # Downstream: City Data Selection
    # -------------------------------
    print("Applying downstream processing: City Data Selection...")

    # get osm with ref tags
    open_toronto_ca_test = (
        osm_combined.filter(like="ref:open.toronto.ca", axis=1).notna().any(axis=1)
    )
    city_verified_osm = osm_combined[open_toronto_ca_test]

    # get all instances of osm city ref tags and split out if needed
    id_lists = {}
    id_cols = city_verified_osm.filter(like="ref:open.toronto.ca", axis=1)
    for ref_type, tags in id_cols.items():
        id_list = []
        for tag_str in tags:
            tags = str(tag_str).split(";")
            id_list.extend([tag.strip() for tag in tags])

        id_lists.setdefault(ref_type, [])
        id_lists[ref_type].extend(id_list)

    # drop city data points if they have matching tags from osm data
    for dataset_name, dataset in city_data.items():
        city_data[dataset_name] = dataset[~dataset.isin(id_lists).any(axis=1)]

    # drop all osm with operator="City of Toronto" (case/space-insensitive) unless they have ref tag.
    # this also retains osm points with ANY value for "ref:open.toronto.ca", including "ref.open.toronto.ca"="no"
    operator_not_city_and_no_ref_test = (
        osm_combined["operator"].str.contains(  # noqa: E712
            r"city\s*?of\s*?toronto", case=False, regex=True
        )
        != True
    ) & (~open_toronto_ca_test)
    osm_filtered = pd.concat(
        [city_verified_osm, osm_combined[operator_not_city_and_no_ref_test]]
    )

    # drop city data points in the manual exclusion file
    city_exclusions_path = Path(
        "Data Pipeline/city_modifications/open_toronto_ca_exclusions.json"
    )
    with city_exclusions_path.open("r") as f:
        city_exclusions = json.load(f)

    city_exclusions_ids = list(chain.from_iterable([x["ids"] for x in city_exclusions]))

    city_exclusions_dict = {}
    for id in city_exclusions_ids:
        [[k, v]] = id.items()
        city_exclusions_dict.setdefault(k, [])
        city_exclusions_dict[k].append(v)

    for dataset_name, dataset in city_data.items():
        city_data[dataset_name] = dataset[
            ~dataset.isin(city_exclusions_dict).any(axis=1)
        ]
    city_unclustered = city_data.copy()
    city_unclustered_combined = pd.concat(
        [dataset for name, dataset in city_unclustered.items()]
    )

    # drop city lockers already in OpenStreetMap
    lockers_unmapped = drop_mapped_city_lockers(lockers, osm_combined)

    # Downstream: Ring and Post Clustering
    # ------------------------------------
    print("Applying downstream processing: Ring and Post Clustering...")

    # special handling for ring and post features from "street-furniture-bicycle-parking"
    furniture = city_data["street-furniture-bicycle-parking"]
    furniture_bollards = furniture[furniture["bicycle_parking"] == "bollard"]
    furniture_not_bollards = furniture[furniture["bicycle_parking"] != "bollard"]

    agg_bollards = group_proximate_rings(furniture_bollards)
    city_data["street-furniture-bicycle-parking"] = pd.concat(
        [furniture_not_bollards, agg_bollards]
    )

    # Downstream: Rack Deduplication
    # ------------------------------
    print("Applying downstream processing: Rack Deduplication...")

    # get boundary for Toronto Metropolitan University
    api = overpass.API()
    response = api.get("way(id:23250594)", responseformat="geojson", verbosity="geom")
    tmupoly = Polygon(response["features"][0]["geometry"]["coordinates"])
    tmugs = geopandas.GeoSeries(tmupoly, crs=4326).to_crs(32617).buffer(20).to_crs(4326)

    # combine city datasets (bicycle stations excluded)
    city_combined = pd.concat(
        [
            city_data["bicycle-parking-high-capacity-outdoor"],
            city_data["bicycle-parking-racks"],
            city_data["street-furniture-bicycle-parking"],
        ]
    )
    city_racks = city_combined[city_combined["bicycle_parking"] == "rack"]
    city_not_racks = city_combined[city_combined["bicycle_parking"] != "rack"]

    # no duplicates at TMU apparently
    city_racks = city_racks.assign(
        tmu=city_racks["geometry"].apply(lambda p: tmugs.intersects(p, align=False))
    )

    # run clustering (excluding TMU)
    city_racks_clustered = group_proximate_racks(city_racks[city_racks["tmu"] == False])  # noqa: E712
    city_full = pd.concat(
        [
            city_racks_clustered,
            city_racks[city_racks["tmu"] == True],  # noqa: E712
            city_not_racks,
            city_data["bicycle-parking-bike-stations-indoor"],
        ]
    )
    city_full = city_full.drop("tmu", axis=1)

    # make combined set from all sources
    all_sources = pd.concat([city_full, osm_filtered, lockers_unmapped])

    # Save display files
    # ------------------
    print("Saving display files...")

    with open(dfp / "open_toronto_ca.geojson", "w") as f:
        f.write(dt_cols_to_str(city_full).to_json(na="drop", drop_id=True, indent=2))
    with open(dfp_archive / "open_toronto_ca.geojson", "w") as f:
        f.write(dt_cols_to_str(city_full).to_json(na="drop", drop_id=True, indent=2))

    with open(dfp / "open_toronto_ca_unclustered.geojson", "w") as f:
        f.write(
            dt_cols_to_str(city_unclustered_combined).to_json(
                na="drop", drop_id=True, indent=2
            )
        )
    with open(dfp_archive / "open_toronto_ca_unclustered.geojson", "w") as f:
        f.write(
            dt_cols_to_str(city_unclustered_combined).to_json(
                na="drop", drop_id=True, indent=2
            )
        )

    with open(dfp / "openstreetmap.geojson", "w") as f:
        f.write(dt_cols_to_str(osm_filtered).to_json(na="drop", drop_id=True, indent=2))
    with open(dfp_archive / "openstreetmap.geojson", "w") as f:
        f.write(dt_cols_to_str(osm_filtered).to_json(na="drop", drop_id=True, indent=2))

    with open(dfp / "toronto_lockers.geojson", "w") as f:
        f.write(
            dt_cols_to_str(lockers_unmapped).to_json(na="drop", drop_id=True, indent=2)
        )
    with open(dfp_archive / "toronto_lockers.geojson", "w") as f:
        f.write(
            dt_cols_to_str(lockers_unmapped).to_json(na="drop", drop_id=True, indent=2)
        )

    with open(dfp / "all_sources.geojson", "w") as f:
        f.write(dt_cols_to_str(all_sources).to_json(na="drop", drop_id=True, indent=2))
    with open(dfp_archive / "all_sources.geojson", "w") as f:
        f.write(dt_cols_to_str(all_sources).to_json(na="drop", drop_id=True, indent=2))


# Script Execution
# ----------------


if __name__ == "__main__":
    run_pipeline()

    # run from command line `python data_pipeline.py
