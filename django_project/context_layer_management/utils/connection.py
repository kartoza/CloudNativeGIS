# coding=utf-8
"""Context Layer Management."""

from django.db import connection


class Field:
    """Class contains fields."""

    def __init__(self, field_name, field_type):
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
