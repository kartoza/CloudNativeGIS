"""Context Layer Management."""

from django.urls import path

from .views import HomeView, SentryProxyView

urlpatterns = [
    path('', HomeView.as_view(), name='home'),
    path('sentry-proxy/', SentryProxyView.as_view(), name='sentry-proxy'),
]
