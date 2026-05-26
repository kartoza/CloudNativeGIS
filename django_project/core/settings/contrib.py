# coding=utf-8
# SPDX-FileCopyrightText: 2024 Kartoza <info@kartoza.com>
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Cloud Native GIS.

.. note:: Settings for 3rd party.
"""
from .base import *  # noqa
from .utils import absolute_path

# Extra installed apps
INSTALLED_APPS = INSTALLED_APPS + (
    'rest_framework',
    'rest_framework_gis',
    'corsheaders',
    'webpack_loader',
    'guardian',
    'django_cleanup.apps.CleanupConfig',
    'django_celery_beat',
    'django_celery_results',
    'drf_yasg',
    'pygeoapi',
)

WEBPACK_LOADER = {
    'DEFAULT': {
        'BUNDLE_DIR_NAME': 'frontend/',  # must end with slash
        'STATS_FILE': absolute_path('frontend', 'webpack-stats.prod.json'),
        'POLL_INTERVAL': 0.1,
        'TIMEOUT': None,
        'IGNORE': [r'.+\.hot-update.js', r'.+\.map'],
        'LOADER_CLASS': 'webpack_loader.loader.WebpackLoader',
    }
}
REST_FRAMEWORK = {
    'DEFAULT_PAGINATION_CLASS': (
        'rest_framework.pagination.LimitOffsetPagination'
    ),
    'PAGE_SIZE': 100
}

AUTHENTICATION_BACKENDS = (
    'django.contrib.auth.backends.ModelBackend',  # default
    'guardian.backends.ObjectPermissionBackend',
)
DEFAULT_AUTO_FIELD = 'django.db.models.AutoField'
CELERY_RESULT_BACKEND = 'django-db'

TEMPLATES[0]['OPTIONS']['context_processors'] += [
    'django.template.context_processors.request',
]

SENTRY_DSN = os.environ.get('SENTRY_DSN', '')

# --------------------------------------------------------------------------------
# ----------------------------------- PyGeoAPI -----------------------------------
# --------------------------------------------------------------------------------
_pygeoapi_config_path = os.environ.get(
    'PYGEOAPI_CONFIG',
    absolute_path('core', 'settings', 'pygeoapi', 'pygeoapi-config.yml'),
)
PYGEOAPI_OPENAPI = os.environ.get(
    'PYGEOAPI_OPENAPI',
    absolute_path('core', 'settings', 'pygeoapi', 'pygeoapi-openapi.yml'),
)
PYGEOAPI_SERVER_URL = os.environ.get(
    'PYGEOAPI_SERVER_URL', 'http://localhost:5000/ogc'
)
os.environ.setdefault('PYGEOAPI_CONFIG', _pygeoapi_config_path)
os.environ.setdefault('PYGEOAPI_OPENAPI', PYGEOAPI_OPENAPI)
os.environ.setdefault('PYGEOAPI_SERVER_URL', PYGEOAPI_SERVER_URL)
os.environ.setdefault(
    'PYGEOAPI_TEMPLATES_PATH',
    os.environ.get(
        'PYGEOAPI_TEMPLATES_PATH',
        absolute_path('cloud_native_gis', 'templates', 'pygeoapi'),
    ),
)

from pygeoapi.config import get_config  # noqa: E402
from pygeoapi.openapi import load_openapi_document  # noqa: E402
from pygeoapi.util import get_api_rules  # noqa: E402

PYGEOAPI_CONFIG = get_config()
OPENAPI_DOCUMENT = load_openapi_document()
API_RULES = get_api_rules(PYGEOAPI_CONFIG)
