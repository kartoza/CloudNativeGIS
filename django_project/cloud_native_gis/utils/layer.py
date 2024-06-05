# coding=utf-8
"""Cloud Native GIS."""

from django.conf import settings
from django.urls import reverse

from cloud_native_gis.models.layer import Layer
from cloud_native_gis.models.style import Style

try:
    MAPUTNIK_URL = settings.MAPUTNIK_URL
except AttributeError:
    MAPUTNIK_URL = '/maputnik'


def layer_style_url(layer: Layer, style: Style, request) -> str:
    """Return layer style url."""
    if not style:
        return None
    return request.build_absolute_uri('/')[:-1] + reverse(
        'cloud-native-gis-style-view-set-detail',
        kwargs={
            'layer_id': layer.id,
            'id': style.id
        }
    )


def layer_api_url(layer: Layer, request) -> str:
    """Return layer api url."""
    return request.build_absolute_uri('/')[:-1] + reverse(
        'cloud-native-gis-view-set-detail',
        kwargs={
            'id': layer.id
        }
    )
