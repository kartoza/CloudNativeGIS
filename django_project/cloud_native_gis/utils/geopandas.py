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

    if 'index' in gdf.columns:
        use_index = False
        index_label = None
    else:
        gdf = gdf.reset_index(drop=True)
        gdf.index += 1
        use_index = True
        index_label = 'index'

    # Connect and save
    con = 'postgresql://{USER}:{PASSWORD}@{HOST}:{PORT}/{NAME}'.format(
        **connection.settings_dict
    )
    engine = create_engine(con)

    gdf.to_postgis(
        table_name,
        con=engine,
        schema=schema_name,
        index=use_index,
        index_label=index_label
    )

    engine.dispose()
    return metadata
