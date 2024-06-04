# coding=utf-8
"""Cloud Native GIS."""

from types import MethodType

from celery import current_app
from django.conf import settings
from django.db import connections
from django.test.runner import DiscoverRunner


def prepare_database(self):
    """Prepare database for test."""
    with self.cursor() as cursor:
        cursor.execute('CREATE EXTENSION IF NOT EXISTS postgis')
        cursor.execute('CREATE EXTENSION IF NOT EXISTS pg_trgm')
        cursor.execute('CREATE SCHEMA IF NOT EXISTS public_gis')


class PostgresSchemaTestRunner(DiscoverRunner):
    """Postgres schema test runner."""

    def setup_databases(self, **kwargs):
        """Set up database for runner."""
        for connection_name in connections:
            connection = connections[connection_name]
            connection.prepare_database = MethodType(
                prepare_database, connection
            )
        return super().setup_databases(**kwargs)

    @staticmethod
    def __disable_celery():
        """Disabling celery."""
        settings.CELERY_BROKER_URL = \
            current_app.conf.CELERY_BROKER_URL = 'filesystem:///dev/null/'
        data = {
            'data_folder_in': '/tmp',
            'data_folder_out': '/tmp',
            'data_folder_processed': '/tmp',
        }
        settings.BROKER_TRANSPORT_OPTIONS = \
            current_app.conf.BROKER_TRANSPORT_OPTIONS = data

    def setup_test_environment(self, **kwargs):
        """Prepare test env."""
        PostgresSchemaTestRunner.__disable_celery()
        super(PostgresSchemaTestRunner, self).setup_test_environment(**kwargs)
