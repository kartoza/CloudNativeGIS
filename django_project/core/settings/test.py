# coding=utf-8
"""Cloud Native GIS."""

from .prod import *  # noqa

TEST_RUNNER = 'cloud_native_gis.tests.runner.PostgresSchemaTestRunner'
DEBUG = True

# Disable caching while in development
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.dummy.DummyCache',
    }
}
