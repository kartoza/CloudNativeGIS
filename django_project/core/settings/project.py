# coding=utf-8
"""
Context Layer Management.

.. note:: Project level settings.
"""
import os  # noqa

from .app import *  # noqa
from .contrib import *  # noqa
from .utils import absolute_path

ALLOWED_HOSTS = ['*']
ADMINS = ()
DATABASES = {
    'default': {
        'ENGINE': 'django_tenants.postgresql_backend',
        'NAME': os.environ['DATABASE_NAME'],
        'USER': os.environ['DATABASE_USERNAME'],
        'PASSWORD': os.environ['DATABASE_PASSWORD'],
        'HOST': os.environ['DATABASE_HOST'],
        'PORT': 5432,
        'TEST_NAME': 'unittests',
    }
}
ORIGINAL_BACKEND = "django.contrib.gis.db.backends.postgis"
DATABASE_ROUTERS = (
    'django_tenants.routers.TenantSyncRouter',
)

# Set debug to false for production
DEBUG = TEMPLATE_DEBUG = False

TEMPLATES[0]['DIRS'] += [
    absolute_path('frontend', 'templates'),
]
