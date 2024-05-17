# coding=utf-8
"""Context Layer Management."""

from context_layer.api.base import BaseApi
from context_layer.forms.layer import LayerForm
from context_layer.models.layer import Layer
from context_layer.serializer.layer import LayerSerializer


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
