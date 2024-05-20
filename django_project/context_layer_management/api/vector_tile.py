# coding=utf-8
"""Context Layer Management."""

from django.http import Http404, HttpResponse
from django.shortcuts import get_object_or_404
from rest_framework.views import APIView

from context_layer_management.models.layer import Layer
from context_layer_management.utils.vector_tile import querying_vector_tile


class VectorTileLayer(APIView):
    """Return Layer in vector tile protobuf."""

    def get(self, request, identifier, z, x, y):
        """Return BasemapLayer list."""
        layer = get_object_or_404(Layer, unique_id=identifier)
        tiles = querying_vector_tile(
            layer.query_table_name, fields=layer.fields,
            z=z, x=x, y=y
        )

        # If no tile 404
        if not len(tiles):
            raise Http404()
        return HttpResponse(tiles, content_type="application/x-protobuf")
