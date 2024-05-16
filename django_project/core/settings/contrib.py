# coding=utf-8
"""
Context Layer Management.

.. note:: Settings for 3rd party.
"""
from .base import *  # noqa
from .utils import absolute_path

# Extra installed apps
INSTALLED_APPS = INSTALLED_APPS + (
    'rest_framework',
    'rest_framework_gis',
    'webpack_loader',
    'guardian',
    'django_cleanup.apps.CleanupConfig',
    'django_celery_beat',
    'django_celery_results',
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
