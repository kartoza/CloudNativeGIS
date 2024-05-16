# coding=utf-8
"""Context Layer Management."""

import geopandas as gpd
from django.db import connection
from sqlalchemy import create_engine

from context_layer.utils.connection import create_schema, delete_table


def shapefile_to_postgis(filepath, table_name, schema):
    """Save shapefile data to postgis."""
    create_schema(schema)
    delete_table(schema, table_name)

    gdf = gpd.read_file(filepath)
    con = 'postgresql://{USER}:{PASSWORD}@{HOST}:{PORT}/{NAME}'.format(
        **connection.settings_dict
    )
    engine = create_engine(con)
    gdf.to_postgis(table_name, con=engine, schema=schema)
