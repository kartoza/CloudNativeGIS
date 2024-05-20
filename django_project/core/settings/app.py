"""Context Layer Management."""
SHARED_APPS = (
    'django_tenants',
    'tenants',

    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.redirects',
    'django.contrib.sessions',
    'django.contrib.sites',
    'django.contrib.sitemaps',
    'django.contrib.staticfiles',
    'django.contrib.gis',
    'django.contrib.messages',

    'rest_framework',
    'rest_framework_gis',
    'webpack_loader',
    'guardian',
    'django_cleanup.apps.CleanupConfig',
    'django_celery_beat',
    'django_celery_results',

    # Project specified
    'core',
    'frontend',
    'context_layer'
)

TENANT_APPS = (
    'rest_framework',
    'rest_framework_gis',
    'guardian',
    'django.contrib.admin',
    'django.contrib.auth',

    # Project specified
    'frontend',
    'context_layer'
)

INSTALLED_APPS = list(SHARED_APPS) + [
    app for app in TENANT_APPS if app not in SHARED_APPS
]
