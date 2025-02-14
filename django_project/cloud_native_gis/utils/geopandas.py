# coding=utf-8
"""Cloud Native GIS."""

import geopandas as gpd
from django.db import connection
from sqlalchemy import create_engine

from cloud_native_gis.utils.connection import (
    create_schema, delete_table
)
from cloud_native_gis.utils.fiona import list_layers


def collection_to_postgis(filepath, table_name, schema_name) -> dict:
    """Save shapefile/GPKG/Geojson/KML data to postgis.

    Note:
        For multilayer GPKG and KML, this will only read the first layer.

    Return metadata
    """
    create_schema(schema_name)
    delete_table(schema_name, table_name)

    gdf = None
    if filepath.endswith('.gpkg') or filepath.endswith('.kml'):
        layers = list_layers(filepath)
        if not layers:
            raise ValueError('Collection does not have layer!')

        gdf = gpd.read_file(filepath, layer=layers[0])
    else:
        gdf = gpd.read_file(filepath)

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
    gdf.to_postgis(table_name, con=engine, schema=schema_name)
    engine.dispose()
    return metadata
