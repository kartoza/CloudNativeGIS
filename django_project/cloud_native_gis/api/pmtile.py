# coding=utf-8
"""Cloud Native GIS."""
import os

from django.http import Http404
from django.shortcuts import get_object_or_404

from cloud_native_gis.api.base import serve_bytes_range
from cloud_native_gis.models import Layer


def serve_pmtiles(request, layer_uuid):
    """Serve pmtiles."""
    layer = get_object_or_404(Layer, unique_id=layer_uuid)

    if not layer.pmtile:
        raise Http404("PMTile file not found for this layer.")

    full_path = layer.pmtile.path

    if not os.path.exists(full_path):
        raise Http404("PMTile file does not exist.")

    return serve_bytes_range(request, full_path, 'application/octet-stream')
