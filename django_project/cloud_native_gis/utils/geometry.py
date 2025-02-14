# coding=utf-8
"""Geometry utils."""

import re

from django.contrib.gis.geos import Point
from django.db import connection


def parse_coord(x: str, y: str, srid: str = '4326') -> Point:
    """Parse string DD/DM/DMS coordinate input. Split by °,',".

    Signed degrees or suffix E/W/N/S.

    :param x: (longitude)
    :type x: str
    :param y: Y (latitude)
    :type y: str
    :param srid: SRID (default=4326).
    :type srid: int
    :raises ValueError: If string could not be parsed
    :return: point wih srid
    :rtype: Point
    """
    try:
        srid = int(srid)
    except ValueError:
        raise ValueError(f"SRID: '{srid}' not valid")
    # Parse Coordinate try DD / otherwise DMS
    coords = {'x': x, 'y': y}
    degrees = 0.0
    minutes = 0.0
    seconds = 0.0

    for coord, val in coords.items():
        try:
            # Determine hemisphere from cardinal direction
            # (override signed degree)
            sign = None
            for direction in ['N', 'n', 'E', 'e']:
                if direction in val.upper():
                    sign = 1
                val = val.replace(direction, '')

            for direction in ['S', 's', 'W', 'w']:
                if direction in val.upper():
                    sign = -1
                val = val.replace(direction, '')

            # Split and get rid of empty space
            coord_parts = [v for v in re.split(r'[°\'"]+', val) if v]
            if len(coord_parts) >= 4:
                raise ValueError
            # Degree, minute, decimal seconds
            elif len(coord_parts) == 3:
                degrees = int(coord_parts[0])
                minutes = int(coord_parts[1])
                seconds = float(coord_parts[2].replace(',', '.'))
            # Degree, decimal minutes
            elif len(coord_parts) == 2:
                degrees = int(coord_parts[0])
                minutes = float(coord_parts[1].replace(',', '.'))
                seconds = 0.0
            # Decimal degree
            elif len(coord_parts) == 1:
                degrees = float(coord_parts[0].replace(',', '.'))
                minutes = 0.0
                seconds = 0.0

            # Determine hemisphere from sign if direction wasn't specified
            if sign is None:
                sign = -1 if degrees <= 0 else 1
            coords[coord] = (
                sign * (abs(degrees) + (minutes / 60.0) + (seconds / 3600.0))
            )

        except ValueError:
            raise ValueError(
                f"Coord '{coords[coord]}' parse failed. "
                f"Not valid DD, DM, DMS (°,',\")")
    return Point(coords['x'], coords['y'], srid=srid)


def query_features(
        table_name: str,
        field_names: list,
        coordinates: list,
        tolerance: float,
        srid: int = 4326):
    """
    Return raw feature data for multiple (x, y) coordinates within a radius.

    Args:
        table_name (str): The name of the database table
            containing the features.
        field_names (list): A list of field names to retrieve from the table.
        coordinates (list): A list of tuples containing (x, y)
            coordinate pairs.
        tolerance (float): The radius tolerance for the spatial query.
        srid (int, optional): Spatial Reference System Identifier.
            Defaults to 4326.

    Returns:
        list: A list of dictionaries representing the feature data.
    """
    data = []

    status_message = ''

    for x, y in coordinates:
        point_geometry = f"ST_SetSRID(ST_MakePoint({x}, {y}), {srid})"

        sql = f"""
            SELECT {', '.join([f'"{field}"' for field in field_names])},
                   ST_AsGeoJSON(ST_Transform(geometry, {srid})) AS geometry
            FROM {table_name}
            WHERE ST_DWithin(
                ST_Transform(geometry, {srid}),
                {point_geometry},
                {tolerance}
            )
            ORDER BY ST_Distance(
                ST_Transform(geometry, {srid}),
                {point_geometry}
            )
            LIMIT 1;
        """

        try:
            with connection.cursor() as cursor:
                cursor.execute(sql)
                row = cursor.fetchone()
                if row:
                    feature = {
                        field: row[i] for i, field in enumerate(field_names)
                    }
                    data.append({'coordinates': (x, y),
                                 'feature': feature})
                else:
                    data.append({'coordinates': (x, y),
                                 'feature': {
                                     field: '' for field in field_names}
                                 })
        except Exception as e:
            error_message = str(e)
            if "does not exist" in error_message:
                missing_column = error_message.split('"')[1]
                status_message = (
                    f"Column '{missing_column}' does not exist."
                )
            else:
                status_message = f"An error occurred: {error_message}"
            break

    return {
        'status_message': status_message,
        'result': data
    }
