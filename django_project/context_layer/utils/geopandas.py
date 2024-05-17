# coding=utf-8
"""Context Layer Management."""

import geopandas as gpd
from django.db import connection
from sqlalchemy import create_engine

from context_layer.utils.connection import create_schema, delete_table


def shapefile_to_postgis(filepath, table_name, schema_name):
    """Save shapefile data to postgis."""
    create_schema(schema_name)
    delete_table(schema_name, table_name)

    gdf = gpd.read_file(filepath)
    con = 'postgresql://{USER}:{PASSWORD}@{HOST}:{PORT}/{NAME}'.format(
        **connection.settings_dict
    )
    engine = create_engine(con)
    # TODO:
    #  Fix this makes test database can't be deleted
    gdf.to_postgis(table_name, con=engine, schema=schema_name)
