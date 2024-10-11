# coding=utf-8
"""Cloud Native GIS."""

import json

from rest_framework import serializers

from cloud_native_gis.models.style import Style


class LayerStyleSerializer(serializers.ModelSerializer):
    """Serializer for layer."""

    def get_style(self, obj: Style):
        """Return style."""
        style = obj.style
        layer = self.context.get('layer', None)
        request = self.context.get('request', None)
        if layer:
            # Append uuid to style
            if 'sources' not in style:
                style['sources'] = {}
            style['sources'][str(layer.unique_id)] = {
                "type": "vector"
            }
            if layer.pmtile:
                style['sources'][str(layer.unique_id)]['url'] = (
                    layer.absolute_pmtiles_url(request)
                )
            else:
                style['sources'][str(layer.unique_id)]['tiles'] = (
                    [layer.absolute_tile_url(request)]
                )
            style = json.dumps(style).replace(
                '<uuid>', str(layer.unique_id)
            )
            style = json.loads(style)

        # Append version
        if 'version' not in style:
            style['version'] = 8
        return style

    def to_representation(self, instance):
        """Return representation of layer."""
        data = super(LayerStyleSerializer, self).to_representation(instance)
        data.update(self.get_style(obj=instance))
        return data

    class Meta:  # noqa: D106
        model = Style
        fields = ['id', 'name']
