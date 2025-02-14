# coding=utf-8
"""Cloud Native GIS."""
import os
import mmap

from django.http import Http404, HttpResponse
from django.shortcuts import get_object_or_404

from cloud_native_gis.models import Layer


class PMTilesReader:
    """Read file using mmap."""

    def __init__(self, filepath):
        """Initialize PMTilesReader."""
        self.filepath = filepath
        self.file = open(filepath, 'rb')
        try:
            self.mmap = mmap.mmap(
                self.file.fileno(), 0, access=mmap.ACCESS_READ
            )
        except Exception as e:
            self.file.close()
            raise OSError(f"Failed to create memory map: {e}")

    def read_range(self, offset, length):
        """Read range bytes."""
        if offset < 0:
            raise ValueError("Offset cannot be negative")
        file_size = len(self.mmap)
        if offset >= file_size:
            raise ValueError("Offset exceeds file size")

        # Adjust length if it would exceed file size
        length = min(length, file_size - offset)

        self.mmap.seek(offset)
        return self.mmap.read(length)

    def read_all(self):
        """Read all bytes."""
        self.mmap.seek(0)
        return self.mmap.read()

    def close(self):
        """Close resources."""
        if hasattr(self, 'mmap') and self.mmap:
            self.mmap.close()
        if hasattr(self, 'file') and self.file:
            self.file.close()


def serve_pmtiles(request, layer_uuid):
    """Serve pmtiles."""
    layer = get_object_or_404(Layer, unique_id=layer_uuid)

    if not layer.pmtile:
        raise Http404("PMTile file not found for this layer.")

    full_path = layer.pmtile.path

    if not os.path.exists(full_path):
        raise Http404("PMTile file does not exist.")

    reader = PMTilesReader(full_path)
    try:
        range_header = request.headers.get('Range')

        if not range_header:
            # Return entire file if no range is specified
            data = reader.read_all()
            response = HttpResponse(data)
            response['Content-Type'] = 'application/octet-stream'
            response['Content-Length'] = len(data)
            response['Accept-Ranges'] = 'bytes'
            return response

        # Parse range header
        try:
            range_match = range_header.replace('bytes=', '').split('-')
            start = int(range_match[0])
            end = int(range_match[1]) if range_match[1] else None
        except (ValueError, IndexError):
            return HttpResponse(status=400)

        # Read the requested range
        length = (
            (end - start + 1) if end is not None else
            (os.path.getsize(full_path) - start)
        )
        data = reader.read_range(start, length)

        response = HttpResponse(data, status=206)
        response['Content-Type'] = 'application/octet-stream'
        response['Content-Length'] = len(data)
        response['Content-Range'] = (
            f'bytes {start}-{start + len(data) - 1}/'
            f'{os.path.getsize(full_path)}'
        )
        response['Accept-Ranges'] = 'bytes'
        return response
    finally:
        reader.close()
