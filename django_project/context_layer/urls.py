# coding=utf-8

from django.urls import path

from context_layer.api.vector_tile import (VectorTileLayer)

urlpatterns = [
    path(
        '<str:identifier>/tile/<int:z>/<int:x>/<int:y>/',
        VectorTileLayer.as_view(),
        name='layer-tile-api'
    ),
]
