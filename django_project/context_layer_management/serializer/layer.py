# coding=utf-8
"""Context Layer Management."""

from rest_framework import serializers

from context_layer_management.models.layer import Layer
from context_layer_management.utils.layer import layer_style_url


class LayerSerializer(serializers.ModelSerializer):
    """Serializer for layer."""

    tile_url = serializers.SerializerMethodField()
    created_by = serializers.SerializerMethodField()
    default_style = serializers.SerializerMethodField()
    styles = serializers.SerializerMethodField()

    def get_tile_url(self, obj: Layer):
        """Return tile_url."""
        request = self.context.get('request', None)
        return obj.absolute_tile_url(request)

    def get_created_by(self, obj: Layer):
        """Return created_by."""
        return obj.created_by.username

    def get_default_style(self, obj: Layer):
        """Return default style url."""
        if obj.default_style:
            return layer_style_url(
                obj, obj.default_style, self.context.get('request', None)
            )
        else:
            return None

    def get_styles(self, obj: Layer):
        """Return styles layer."""
        return [
            {
                'id': style.id,
                'name': style.name,
                'style': layer_style_url(
                    obj, style, self.context.get('request', None)
                )
            } for style in obj.styles.all()
        ]

    class Meta:  # noqa: D106
        model = Layer
        exclude = ['unique_id']
