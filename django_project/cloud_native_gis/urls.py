# coding=utf-8
"""Cloud Native GIS."""

from django.urls import include, path
from django.views.generic import TemplateView
from rest_framework.routers import DefaultRouter
from rest_framework_nested.routers import NestedSimpleRouter

from cloud_native_gis.api.layer import (
    LayerViewSet, LayerStyleViewSet
)
from cloud_native_gis.api.vector_tile import (VectorTileLayer)

router = DefaultRouter()
router.register(
    r'layer', LayerViewSet, basename='cloud-native-gis-view-set'
)
layer_router = NestedSimpleRouter(
    router, r'layer', lookup='layer'
)
layer_router.register(
    'style', LayerStyleViewSet,
    basename='cloud-native-gis-style-view-set'
)

urlpatterns = [
    path(
        '<str:identifier>/tile/<int:z>/<int:x>/<int:y>/',
        VectorTileLayer.as_view(),
        name='cloud-native-gis-tile-api'
    ),
    path('api/', include(router.urls)),
    path('api/', include(layer_router.urls)),
    path(
        'maputnik/',
        TemplateView.as_view(template_name='maputnik/index.html')
    )
]
