# coding=utf-8
"""Context Layer Management."""


from rest_framework import serializers

from context_layer_management.models.layer import Layer


class LayerSerializer(serializers.ModelSerializer):
    """Serializer for layer."""

    tile_url = serializers.SerializerMethodField()
    created_by = serializers.SerializerMethodField()

    def get_tile_url(self, obj: Layer):
        """Return tile_url."""
        return obj.tile_url

    def get_created_by(self, obj: Layer):
        """Return created_by."""
        return obj.created_by.username

    class Meta:  # noqa: D106
        model = Layer
        exclude = ['unique_id']
