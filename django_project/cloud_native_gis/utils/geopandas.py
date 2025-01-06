# coding=utf-8
"""Cloud Native GIS."""

import geopandas as gpd
from django.db import connection
from sqlalchemy import create_engine

from cloud_native_gis.utils.connection import (
    create_schema, delete_table
)


def shapefile_to_postgis(filepath, table_name, schema_name) -> dict:
    """Save shapefile data to postgis.

    Return metadata
    """
    create_schema(schema_name)
    delete_table(schema_name, table_name)

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
