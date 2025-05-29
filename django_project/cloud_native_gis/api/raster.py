# coding=utf-8
"""Cloud Native GIS."""
import os

from django.http import Http404
from django.shortcuts import get_object_or_404

from cloud_native_gis.api.base import serve_bytes_range
from cloud_native_gis.models import Layer, LayerUpload


def serve_cog(request, layer_uuid):
    """Serve cog file."""
    layer = get_object_or_404(Layer, unique_id=layer_uuid)

    # find latest layer upload
    layer_upload = LayerUpload.objects.filter(
        layer=layer
    ).order_by('-created_at').first()
    if not layer_upload:
        raise Http404("COG file not found for this layer.")

    # get all files in the upload directory
    files = layer_upload.files
    if not files:
        raise Http404("No files found in the layer upload.")

    # find the COG file
    cog_file = next((f for f in files if f.endswith('.tif')), None)
    if not cog_file:
        raise Http404("COG file not found in the layer upload.")

    full_path = layer_upload.filepath(cog_file)

    if not os.path.exists(full_path):
        raise Http404("COG file does not exist.")

    serve_bytes_range(request, full_path, 'image/tiff')
