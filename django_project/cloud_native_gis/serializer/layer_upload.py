# coding=utf-8
"""
GeoSight is UNICEF's geospatial web-based business intelligence platform.

Contact : geosight-no-reply@unicef.org

.. note:: This program is free software; you can redistribute it and/or modify
    it under the terms of the GNU Affero General Public License as published by
    the Free Software Foundation; either version 3 of the License, or
    (at your option) any later version.

"""
__author__ = 'irwan@kartoza.com'
__date__ = '23/07/2024'
__copyright__ = ('Copyright 2023, Unicef')

from rest_framework import serializers

from cloud_native_gis.models.layer_upload import LayerUpload


class LayerUploadSerializer(serializers.ModelSerializer):
    """Serializer for LayerUpload."""

    class Meta:  # noqa: D106
        model = LayerUpload
        exclude = ()
