# coding=utf-8
"""Context Layer Management."""

from django.urls import include, path
from rest_framework.routers import DefaultRouter
from rest_framework_nested.routers import NestedSimpleRouter

from context_layer_management.api.layer import (
    LayerViewSet, StyleOfLayerViewSet
)
from context_layer_management.api.vector_tile import (VectorTileLayer)

router = DefaultRouter()
router.register(
    r'layer', LayerViewSet, basename='context-layer-management-view-set'
)
layer_router = NestedSimpleRouter(
    router, r'layer', lookup='layer'
)
layer_router.register(
    'style', StyleOfLayerViewSet,
    basename='context-layer-management-style-view-set'
)

urlpatterns = [
    path(
        '<str:identifier>/tile/<int:z>/<int:x>/<int:y>/',
        VectorTileLayer.as_view(),
        name='context-layer-management-tile-api'
    ),
    path('api/', include(router.urls)),
    path('api/', include(layer_router.urls)),
]
