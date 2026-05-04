# SPDX-FileCopyrightText: 2024 Kartoza <info@kartoza.com>
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Cloud Native GIS."""

from django.urls import path

from .views import HomeView, SentryProxyView

urlpatterns = [
    path('', HomeView.as_view(), name='home'),
    path('sentry-proxy/', SentryProxyView.as_view(), name='sentry-proxy'),
]
