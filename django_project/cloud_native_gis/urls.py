# coding=utf-8
"""Cloud Native GIS."""

from django.urls import include, path
from django.views.generic import TemplateView
from rest_framework.routers import DefaultRouter
from rest_framework_nested.routers import NestedSimpleRouter

from rest_framework import permissions
from drf_yasg.views import get_schema_view
from drf_yasg import openapi

from cloud_native_gis.api.context import ContextAPIView
from cloud_native_gis.api.layer import (
    LayerViewSet, LayerStyleViewSet
)
from cloud_native_gis.api.pmtile import serve_pmtiles
from cloud_native_gis.api.vector_tile import (VectorTileLayer)

schema_view = get_schema_view(
    openapi.Info(
        title="Cloud Native GIS API",
        default_version='v1',
        description="API documentation for the Cloud Native GIS project",
        terms_of_service="https://www.example.com/terms/",
        contact=openapi.Contact(email="contact@example.com"),
        license=openapi.License(name="BSD License"),
    ),
    public=True,
    permission_classes=(permissions.AllowAny,),
)


router = DefaultRouter()
router.register(
    r'layer', LayerViewSet, basename='cloud-native-gis-layer'
)
layer_router = NestedSimpleRouter(
    router, r'layer', lookup='layer'
)
layer_router.register(
    'style', LayerStyleViewSet,
    basename='cloud-native-gis-style'
)

urlpatterns = [
    path(
        '<str:identifier>/tile/<int:z>/<int:x>/<int:y>/',
        VectorTileLayer.as_view(),
        name='cloud-native-gis-vector-tile'
    ),
    path('api/', include(router.urls)),
    path('api/', include(layer_router.urls)),
    path('api/context/',
         ContextAPIView.as_view(),
         name='cloud-native-gis-context'),
    path(
        'maputnik/',
        TemplateView.as_view(template_name='cloud_native_gis/maputnik.html'),
        name='cloud-native-gis-maputnik'
    ),
    path('swagger/',
         schema_view.with_ui('swagger', cache_timeout=0),
         name='schema-swagger-ui'),
    path('redoc/',
         schema_view.with_ui('redoc', cache_timeout=0),
         name='schema-redoc-ui'),
    path('api/serve-pmtile/<uuid:layer_uuid>/',
         serve_pmtiles, name='serve-pmtiles'),
]
