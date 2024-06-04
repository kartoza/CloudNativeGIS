# coding=utf-8
"""Cloud Native GIS."""

from django.http import Http404
from rest_framework.generics import get_object_or_404
from rest_framework.response import Response

from cloud_native_gis.api.base import BaseApi, BaseReadApi
from cloud_native_gis.forms.layer import LayerForm
from cloud_native_gis.forms.style import StyleForm
from cloud_native_gis.models.layer import Layer
from cloud_native_gis.models.style import Style
from cloud_native_gis.serializer.layer import LayerSerializer
from cloud_native_gis.serializer.style import LayerStyleSerializer
from cloud_native_gis.utils.layer import layer_style_url, MAPUTNIK_URL


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


class LayerStyleViewSet(BaseReadApi):
    """API layer style."""

    form_class = StyleForm
    serializer_class = LayerStyleSerializer

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
        return Style.objects.filter(id__in=ids)

    def list(self, request, *args, **kwargs):
        """Return just default style."""
        layer = self._get_layer()
        if layer.default_style:
            serializer = self.get_serializer(layer.default_style)
            return Response(serializer.data)
        else:
            raise Http404

    def update(self, request, *args, **kwargs):
        """Update style."""
        _id = int(self.kwargs.get('id'))
        layer = self._get_layer()
        is_default = request.data['isDefault']

        style = None
        if layer.default_style and layer.default_style.pk == _id:
            style = layer.default_style
            is_default = True
        if not style:
            try:
                style = layer.styles.get(id=_id)
            except Style.DoesNotExist:
                pass
        if not style:
            raise Http404

        # Clean style requests
        style_request = {
            'layers': []
        }
        for style_layer in request.data['style']['layers']:
            if style_layer['type'] != 'raster':
                style_layer['id'] = '<uuid>'
                style_layer['source'] = '<uuid>'
                style_request['layers'].append(style_layer)

        # Save the style
        if style.is_default_style:
            style.id = None
        style.name = request.data['name']
        if style.name in Style.default_names():
            style.name = f'{style.name} ({layer.unique_id})'
        style.style = style_request
        style.save()

        if is_default:
            layer.default_style = style
            layer.save()
        layer.styles.add(style)

        return Response(
            f'{MAPUTNIK_URL}?styleUrl='
            f'{layer_style_url(layer, style, self.request)}'
        )
