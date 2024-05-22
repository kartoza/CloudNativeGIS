# coding=utf-8
"""Context Layer Management."""

from django.urls import include, path
from rest_framework.routers import DefaultRouter

from context_layer_management.api.layer import LayerViewSet
from context_layer_management.api.vector_tile import (VectorTileLayer)

router = DefaultRouter()
router.register(
    r'layer', LayerViewSet, basename='context-layer-management-view-set'
)

urlpatterns = [
    path(
        '<str:identifier>/tile/<int:z>/<int:x>/<int:y>/',
        VectorTileLayer.as_view(),
        name='context-layer-management-tile-api'
    ),
    path('api/', include(router.urls)),
]
