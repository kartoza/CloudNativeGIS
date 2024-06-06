# coding=utf-8
"""Cloud Native GIS."""

from rest_framework import serializers

from cloud_native_gis.models.general import License


class LicenseSerializer(serializers.ModelSerializer):
    """Serializer for License."""

    class Meta:  # noqa: D106
        model = License
        fields = '__all__'
