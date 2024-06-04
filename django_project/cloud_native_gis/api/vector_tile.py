# coding=utf-8
"""Cloud Native GIS."""

from django.http import Http404, HttpResponse
from django.shortcuts import get_object_or_404
from rest_framework.views import APIView

from cloud_native_gis.models.layer import Layer
from cloud_native_gis.utils.vector_tile import querying_vector_tile


class VectorTileLayer(APIView):
    """Return Layer in vector tile protobuf."""

    def get(self, request, identifier, z, x, y):
        """Return BasemapLayer list."""
        layer = get_object_or_404(Layer, unique_id=identifier)
        tiles = querying_vector_tile(
            layer.query_table_name, field_names=layer.field_names,
            z=z, x=x, y=y
        )

        # If no tile 404
        if not len(tiles):
            raise Http404()
        return HttpResponse(tiles, content_type="application/x-protobuf")
