# coding=utf-8
# SPDX-FileCopyrightText: 2024 Kartoza <info@kartoza.com>
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Cloud Native GIS."""

from django.db import connection
from django.db.utils import ProgrammingError


class Field:
    """Class contains fields."""

    def __init__(self, field_name, field_type):
        """Field constructor."""
        self.name = field_name
        self.type = field_type


def create_schema(schema_name):
    """Create temp schema for temporary database."""
    with connection.cursor() as cursor:
        cursor.execute(
            f'CREATE SCHEMA IF NOT EXISTS {schema_name}'
        )


def delete_table(schema_name, table_name):
    """Delete table from specific name."""
    with connection.cursor() as cursor:
        cursor.execute(
            f'DROP TABLE IF EXISTS {schema_name}.{table_name}'
        )


def fields(schema_name, table_name):
    """Return field names of table."""
    _fields = []
    with connection.cursor() as cursor:
        cursor.execute(
            f"SELECT column_name, data_type FROM information_schema.columns "
            f"WHERE table_schema = '{schema_name}' "
            f"AND table_name   = '{table_name}'"
        )
        rows = cursor.fetchall()
        for row in rows:
            _fields.append(Field(row[0], row[1]))
    return _fields


def count_features(schema_name, table_name):
    """Return count of features of table."""
    count = 0
    with connection.cursor() as cursor:
        try:
            cursor.execute(
                f"SELECT count(*) FROM {schema_name}.{table_name}"
            )
            rows = cursor.fetchall()
            for row in rows:
                count = row[0]
        except ProgrammingError as e:
            if 'does not exist' in str(e):
                count = None
    return count


def get_features(schema_name, table_name):
    """Return features of table."""
    with connection.cursor() as cursor:
        try:
            cursor.execute(
                f"SELECT * FROM {schema_name}.{table_name}"
            )
            return cursor.fetchall()
        except ProgrammingError:
            return []
    return []


def get_json_features(schema_name, table_name):
    """Return features as list of dicts with column names from the query."""
    with connection.cursor() as cursor:
        try:
            cursor.execute(
                f"SELECT * FROM {schema_name}.{table_name}"
            )
            columns = [col.name for col in cursor.description]
            return [
                dict(zip(columns, row)) for row in cursor.fetchall()
            ]
        except ProgrammingError:
            return []
