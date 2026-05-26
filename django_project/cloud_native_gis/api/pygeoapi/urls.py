"""URL patterns for dynamic per-user pygeoapi endpoints."""

from django.conf import settings
from django.urls import path

from . import collections, items, landing


def _s(url: str) -> str:
    """Strip trailing slash when API_RULES requires strict slashes."""
    if settings.API_RULES.strict_slashes:
        return url.rstrip('/')
    return url


urlpatterns = [
    # Landing / meta
    path('', landing.landing_page, name='landing-page'),
    path(_s('openapi/'), landing.openapi, name='openapi'),
    path(_s('conformance/'), landing.conformance, name='conformance'),

    # Collections list & detail
    path(_s('collections/'), collections.collections, name='collections'),
    path(
        'collections/<str:collection_id>',
        collections.collections,
        name='collection-detail',
    ),

    # Collection sub-resources
    path(
        _s('collections/<str:collection_id>/schema/'),
        collections.collection_schema,
        name='collection-schema',
    ),
    path(
        _s('collections/<str:collection_id>/queryables/'),
        collections.collection_queryables,
        name='collection-queryables',
    ),

    # Items
    path(
        _s('collections/<str:collection_id>/items/'),
        items.collection_items,
        name='collection-items',
    ),
    path(
        'collections/<str:collection_id>/items/<str:item_id>',
        items.collection_item,
        name='collection-item',
    ),

]
