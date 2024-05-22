# coding=utf-8
"""
Context Layer Management.

.. note:: Project level settings.
"""
import os  # noqa

from .contrib import *  # noqa
from .utils import absolute_path

ALLOWED_HOSTS = ['*']
ADMINS = ()
DATABASES = {
    'default': {
        'ENGINE': 'django.contrib.gis.db.backends.postgis',
        'NAME': os.environ['DATABASE_NAME'],
        'USER': os.environ['DATABASE_USERNAME'],
        'PASSWORD': os.environ['DATABASE_PASSWORD'],
        'HOST': os.environ['DATABASE_HOST'],
        'PORT': 5432,
        'TEST_NAME': 'unittests',
    }
}

# Set debug to false for production
DEBUG = TEMPLATE_DEBUG = False

# Extra installed apps
INSTALLED_APPS = INSTALLED_APPS + (
    'core',
    'frontend',
    'context_layer_management'
)

TEMPLATES[0]['DIRS'] += [
    absolute_path('frontend', 'templates'),
]
