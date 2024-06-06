# coding=utf-8
"""Cloud Native GIS."""

import os

from django.urls import reverse

from cloud_native_gis.models.layer import Layer
from cloud_native_gis.models.style import Style


def maputnik_url() -> str:
    """Return url for mapnik layer."""
    try:
        return os.environ['MAPUTNIK_URL']
    except KeyError:
        return reverse('cloud-native-gis-maputnik')


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
        'cloud-native-gis-layer-view-set-detail',
        kwargs={
            'id': layer.id
        }
    )
