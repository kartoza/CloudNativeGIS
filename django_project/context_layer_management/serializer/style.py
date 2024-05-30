# coding=utf-8
"""Context Layer Management."""

import json

from rest_framework import serializers

from context_layer_management.models.layer import LayerStyle


class StyleOfLayerSerializer(serializers.ModelSerializer):
    """Serializer for layer."""

    def get_style(self, obj: LayerStyle):
        """Return style."""
        style = obj.style
        layer = self.context.get('layer', None)
        request = self.context.get('request', None)
        if layer:
            # Append uuid to style
            if 'sources' not in style:
                style['sources'] = {}
            style['sources'][str(layer.unique_id)] = {
                "tiles": [
                    request.build_absolute_uri('/')[:-1] + layer.tile_url
                ],
                "type": "vector"
            }
            style = json.dumps(style).replace(
                '<uuid>', str(layer.unique_id)
            )
            style = json.loads(style)

        # Append version
        if 'version' not in style:
            style['version'] = 8
        return style

    def to_representation(self, instance):
        data = super(StyleOfLayerSerializer, self).to_representation(instance)
        data.update(self.get_style(obj=instance))
        return data

    class Meta:  # noqa: D106
        model = LayerStyle
        fields = []
