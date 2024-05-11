"""Context Layer Management."""

from django.conf import settings


def sentry_dsn(request):
    """Return sentry dsn for context processor."""
    return {
        'SENTRY_DSN': settings.SENTRY_DSN
    }
