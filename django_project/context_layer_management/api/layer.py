# coding=utf-8
"""Context Layer Management."""

from django.http import Http404
from rest_framework.generics import get_object_or_404
from rest_framework.response import Response

from context_layer_management.api.base import BaseApi, BaseReadApi
from context_layer_management.forms.layer import LayerForm
from context_layer_management.forms.style import LayerStyleForm
from context_layer_management.models.layer import Layer, LayerStyle
from context_layer_management.serializer.layer import LayerSerializer
from context_layer_management.serializer.style import StyleOfLayerSerializer


class LayerViewSet(BaseApi):
    """API for layer."""

    form_class = LayerForm
    queryset = Layer.objects.all()
    serializer_class = LayerSerializer

    def get_serializer_context(self):
        """Extra context provided to the serializer class."""
        return {
            'request': self.request,
            'format': self.format_kwarg,
            'view': self,
            'user': self.request.user
        }


class StyleOfLayerViewSet(BaseReadApi):
    """API layer style."""

    form_class = LayerStyleForm
    serializer_class = StyleOfLayerSerializer

    def _get_layer(self) -> Layer:  # noqa: D102
        layer_id = self.kwargs.get('layer_id')
        return get_object_or_404(
            Layer.objects.filter(pk=layer_id)
        )

    def get_serializer_context(self):
        """Extra context provided to the serializer class."""
        return {
            'request': self.request,
            'format': self.format_kwarg,
            'view': self,
            'user': self.request.user,
            'layer': self._get_layer()
        }

    def get_serializer(self, *args, **kwargs):
        """Return the serializer instance."""
        serializer_class = self.get_serializer_class()
        kwargs.setdefault('context', self.get_serializer_context())
        return serializer_class(*args, **kwargs)

    def get_queryset(self):
        """Return queryset of API."""
        layer = self._get_layer()
        ids = layer.styles.values_list('id', flat=True)
        return LayerStyle.objects.filter(id__in=ids)

    def list(self, request, *args, **kwargs):
        """Return just default style."""
        layer = self._get_layer()
        if layer.default_style:
            serializer = self.get_serializer(layer.default_style)
            return Response(serializer.data)
        else:
            raise Http404
