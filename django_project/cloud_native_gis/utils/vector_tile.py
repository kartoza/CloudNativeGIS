# coding=utf-8
"""Cloud Native GIS."""

from django.db import connection
import math


def querying_vector_tile(
        table_name: str, field_names: list, z: int, x: int, y: int
):
    """Return vector tile from table name."""
    # Define the zoom level at which to start simplifying geometries
    simplify_zoom_threshold = 5

    # Apply exponential tolerance for simplification if zoom level is less than the threshold
    simplify_tolerance = (
        0 if z > simplify_zoom_threshold else 1000 * math.exp(simplify_zoom_threshold - z)
    )

    # Conditional geometry transformation
    geometry_transform = (
        f"ST_Simplify(ST_Transform(geometry, 3857), {simplify_tolerance})"
        if simplify_tolerance > 0 else "ST_Transform(geometry, 3857)"
    )

    sql = f"""
        WITH mvtgeom AS
        (
            SELECT {','.join([f'"{f}"' for f in field_names])} ,
                ST_AsMVTGeom(
                    {geometry_transform},
                    ST_TileEnvelope({z}, {x}, {y}),
                    extent => 4096, buffer => 64
                ) as geom
                FROM {table_name}
        )
        SELECT ST_AsMVT(mvtgeom.*)
        FROM mvtgeom;
    """

    tiles = []

    # Raw query it
    with connection.cursor() as cursor:
        cursor.execute(sql)
        rows = cursor.fetchall()
        for row in rows:
            tiles.append(bytes(row[0]))
    return tiles
