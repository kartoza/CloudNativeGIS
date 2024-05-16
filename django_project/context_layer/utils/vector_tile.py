# coding=utf-8
"""Context Layer Management."""

from django.db import connection


def querying_vector_tile(
        table_name: str, field_names: list, z: int, x: int, y: int
):
    """Return vector tile from table name."""
    sql = f"""
        WITH mvtgeom AS
        (
            SELECT {','.join([f'"{f}"' for f in field_names])} ,
                ST_AsMVTGeom(
                    ST_Transform(geometry, 3857),
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
