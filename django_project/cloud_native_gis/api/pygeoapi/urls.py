"""URL patterns for dynamic per-user pygeoapi endpoints."""

from django.urls import path

from . import collections, items, landing

urlpatterns = [
    # Landing / meta
    path('', landing.landing_page, name='landing-page'),
    path('openapi', landing.openapi, name='openapi'),
    path('openapi/', landing.openapi, name='openapi-slash'),
    path('conformance', landing.conformance, name='conformance'),
    path('conformance/', landing.conformance, name='conformance-slash'),

    # Collections list & detail
    path('collections', collections.collections, name='collections'),
    path('collections/', collections.collections, name='collections-slash'),
    path(
        'collections/<str:collection_id>',
        collections.collections,
        name='collection-detail',
    ),
    path(
        'collections/<str:collection_id>/',
        collections.collections,
        name='collection-detail-slash',
    ),

    # Collection sub-resources
    path(
        'collections/<str:collection_id>/schema',
        collections.collection_schema,
        name='collection-schema',
    ),
    path(
        'collections/<str:collection_id>/schema/',
        collections.collection_schema,
        name='collection-schema-slash',
    ),
    path(
        'collections/<str:collection_id>/queryables',
        collections.collection_queryables,
        name='collection-queryables',
    ),
    path(
        'collections/<str:collection_id>/queryables/',
        collections.collection_queryables,
        name='collection-queryables-slash',
    ),

    # Items
    path(
        'collections/<str:collection_id>/items',
        items.collection_items,
        name='collection-items',
    ),
    path(
        'collections/<str:collection_id>/items/',
        items.collection_items,
        name='collection-items-slash',
    ),
    path(
        'collections/<str:collection_id>/items/<str:item_id>',
        items.collection_item,
        name='collection-item',
    ),
    path(
        'collections/<str:collection_id>/items/<str:item_id>/',
        items.collection_item,
        name='collection-item-slash',
    ),
]
