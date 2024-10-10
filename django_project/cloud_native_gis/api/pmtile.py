# coding=utf-8
"""Cloud Native GIS."""
import os
import re

from django.http import FileResponse, Http404, HttpResponse
from django.shortcuts import get_object_or_404

from cloud_native_gis.models import Layer


def serve_pmtiles(request, layer_uuid):
    """Serve pmtiles."""
    layer = get_object_or_404(Layer, unique_id=layer_uuid)

    if not layer.pmtile:
        raise Http404("PMTile file not found for this layer.")

    full_path = layer.pmtile.path

    if not os.path.exists(full_path):
        raise Http404("PMTile file does not exist.")

    range_header = request.headers.get('Range')
    if range_header:
        range_match = re.match(
            r'bytes=(\d+)-(\d*)', range_header)
        if range_match:
            start_byte = int(range_match.group(1))
            end_byte = int(
                range_match.group(2)) if (
                range_match.group(2)) else (
                    os.path.getsize(full_path) - 1)

            file_size = os.path.getsize(full_path)
            content_length = end_byte - start_byte + 1
            content_range = f'bytes {start_byte}-{end_byte}/{file_size}'

            file = open(full_path, 'rb')
            file.seek(start_byte)

            response = HttpResponse(
                file.read(content_length),
                status=206,
                content_type='application/octet-stream')
            response['Content-Length'] = content_length
            response['Content-Range'] = content_range
            response['Accept-Ranges'] = 'bytes'
            return response

    return FileResponse(
        open(full_path, 'rb'),
        content_type='application/octet-stream')
