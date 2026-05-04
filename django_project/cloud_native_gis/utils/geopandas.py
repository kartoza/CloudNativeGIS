# coding=utf-8
# SPDX-FileCopyrightText: 2024 Kartoza <info@kartoza.com>
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Cloud Native GIS."""

import geopandas as gpd
from django.db import connection
from sqlalchemy import create_engine

from cloud_native_gis.utils.connection import create_schema
from cloud_native_gis.utils.fiona import list_layers


class Mode:
    """Class contains modes."""

    REPLACE = 'replace'
    APPEND = 'append'


def geopanda_to_postgis(
        gdf, table_name, schema_name,
        mode=Mode.REPLACE
) -> dict:
    """Save geopandas data to postgis."""
    create_schema(schema_name)

    metadata = {}
    try:
        metadata['FEATURE COUNT'] = len(gdf.geometry)
        metadata['GEOMETRY SRS'] = gdf.geometry.crs.srs
        metadata['GEOMETRY TYPE'] = gdf.geometry[0].geom_type
    except IndexError:
        pass

    con = 'postgresql://{USER}:{PASSWORD}@{HOST}:{PORT}/{NAME}'.format(
        **connection.settings_dict
    )
    engine = create_engine(con)
    with engine.begin() as conn:
        gdf.to_postgis(
            table_name,
            con=conn,
            schema=schema_name,
            if_exists=mode
        )
    engine.dispose()
    return metadata


def geojson_to_geopanda(
        geojson, schema_name, table_name, mode=Mode.REPLACE
) -> dict:
    """Save geojson data to geopandas."""
    gdf = gpd.GeoDataFrame.from_features(geojson["features"])

    if "crs" in geojson:
        crs_info = geojson["crs"]
        if isinstance(crs_info, dict):
            gdf.set_crs(
                crs_info.get("properties", {}).get("name", "EPSG:4326"),
                inplace=True)
        else:
            gdf.set_crs("EPSG:4326", inplace=True)
    else:
        gdf.set_crs("EPSG:4326", inplace=True)

    return geopanda_to_postgis(
        gdf, table_name, schema_name, mode=mode
    )


def collection_to_postgis(filepath, table_name, schema_name) -> dict:
    """Save shapefile/GPKG/Geojson/KML data to postgis.

    Note:
        For multilayer GPKG and KML, this will only read the first layer.

    Return metadata
    """
    if filepath.endswith('.gpkg') or filepath.endswith('.kml'):
        layers = list_layers(filepath)
        if not layers:
            raise ValueError('Collection does not have layer!')

        gdf = gpd.read_file(filepath, layer=layers[0])
    else:
        gdf = gpd.read_file(filepath)

    return geopanda_to_postgis(gdf, table_name, schema_name)
