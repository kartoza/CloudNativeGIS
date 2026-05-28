"""URL patterns for dynamic per-user pygeoapi endpoints."""

from django.urls import path

from . import collections, items, landing

urlpatterns = [
    # Landing / meta
    path('', landing.landing_page, name='landing-page'),
    path('openapi', landing.openapi, name='openapi'),
    path('conformance', landing.conformance, name='conformance'),

    # Collections list & detail
    path('collections', collections.collections, name='collections'),
    path(
        'collections/<str:collection_id>',
        collections.collections,
        name='collection-detail',
    ),

    # Collection sub-resources
    path(
        'collections/<str:collection_id>/schema',
        collections.collection_schema,
        name='collection-schema',
    ),
    path(
        'collections/<str:collection_id>/queryables',
        collections.collection_queryables,
        name='collection-queryables',
    ),

    # Items
    path(
        'collections/<str:collection_id>/items',
        items.collection_items,
        name='collection-items',
    ),
    path(
        'collections/<str:collection_id>/items/<str:item_id>',
        items.collection_item,
        name='collection-item',
    ),
]
