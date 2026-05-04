# SPDX-FileCopyrightText: 2024 Kartoza <info@kartoza.com>
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Cloud Native GIS."""

from django.conf import settings


def sentry_dsn(request):
    """Return sentry dsn for context processor."""
    return {
        'SENTRY_DSN': settings.SENTRY_DSN
    }
