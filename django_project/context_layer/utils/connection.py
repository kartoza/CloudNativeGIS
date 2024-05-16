"""Context Layer Management."""

from django.db import connection


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
