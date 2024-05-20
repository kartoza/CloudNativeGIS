# coding=utf-8
"""Context Layer Management."""

from .prod import *  # noqa

TEST_RUNNER = 'context_layer_management.tests.runner.PostgresSchemaTestRunner'
DEBUG = True

# Disable caching while in development
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.dummy.DummyCache',
    }
}
