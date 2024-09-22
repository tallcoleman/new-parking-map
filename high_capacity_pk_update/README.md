# Primary Key update script for bicycle-parking-high-capacity-outdoor dataset

## Purpose

The `ID` primary key field in the [bicycle-parking-high-capacity-outdoor](https://open.toronto.ca/dataset/bicycle-parking-high-capacity-outdoor/) City of Toronto dataset has unfortunately not remained stable over time. The purpose of this script is to help update uses of this field in OpenStreetMap data tagged with `ref:open.toronto.ca:bicycle-parking-high-capacity-outdoor:id`.

## How to run

```bash
$ . .venv/bin/activate
$ python high_capacity_pk_update/high_capacity_pk_update.py
```

The script will generate a folder in `high_capacity_pk_update/output`. Each sub-folder will show information about subsequent pairs from dated folders in the `Output Files` directory:

- Spatial duplicates encountered in the source data for `bicycle-parking-high-capacity-outdoor` (for both files in the pair)
- Any files that were not able to be matched by geometry proximity (e.g. if new points are added from one week to another, or geometry changes over the search radius are made in the source data)
- Any changes to the primary key `ID` field from one week to another

## Intended usage

- Generate the output files
- If there is a folder with an "id_change" file, use that file in JOSM along with the Overpass Query below and the conflation plugin to update the values for `ref:open.toronto.ca:bicycle-parking-high-capacity-outdoor:id`
- Check for cases of mapped values that are not spatially unique in the `bicycle-parking-high-capacity-outdoor` dataset
- Check for cases of values in the `bicycle-parking-high-capacity-outdoor` that were not matched from one week to another

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