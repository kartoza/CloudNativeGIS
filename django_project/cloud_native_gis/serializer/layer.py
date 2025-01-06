# coding=utf-8
"""Cloud Native GIS."""

from rest_framework import serializers

from cloud_native_gis.models.layer import Layer, LayerAttributes
from cloud_native_gis.models.style import Style
from cloud_native_gis.serializer.general import LicenseSerializer
from cloud_native_gis.utils.layer import layer_style_url


class LayerSerializer(serializers.ModelSerializer):
    """Serializer for layer."""

    tile_url = serializers.SerializerMethodField()
    created_by = serializers.SerializerMethodField()
    default_style = serializers.SerializerMethodField()
    styles = serializers.SerializerMethodField()
    license = serializers.SerializerMethodField()

    def style_serializer(self, layer: Layer, style: Style):
        """Serialize a style for a layer."""
        return {
            'id': style.id,
            'name': style.name,
            'style_url': layer_style_url(
                layer, style, self.context.get('request', None)
            )
        }

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
            return self.style_serializer(obj, obj.default_style)
        else:
            return None

    def get_styles(self, obj: Layer):
        """Return styles layer."""
        return [
            self.style_serializer(obj, style)
            for style in obj.styles.all().order_by('name')
        ]

    def get_license(self, obj: Layer):
        """Return license."""
        if not obj.license:
            return None
        return LicenseSerializer(obj.license).data

    class Meta:  # noqa: D106
        model = Layer
        exclude = ['unique_id']


class LayerAttributeSerializer(serializers.ModelSerializer):
    """Serializer for layer attribute."""

    class Meta:  # noqa: D106
        model = LayerAttributes
        exclude = ['layer']
