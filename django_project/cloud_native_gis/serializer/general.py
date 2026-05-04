# coding=utf-8
# SPDX-FileCopyrightText: 2024 Kartoza <info@kartoza.com>
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Cloud Native GIS."""

from rest_framework import serializers

from cloud_native_gis.models.general import License


class LicenseSerializer(serializers.ModelSerializer):
    """Serializer for License."""

    class Meta:  # noqa: D106
        model = License
        fields = '__all__'
