# coding=utf-8
# SPDX-FileCopyrightText: 2024 Kartoza <info@kartoza.com>
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Cloud Native GIS."""

from django.contrib import admin

from cloud_native_gis.models.general import License


class LicenseAdmin(admin.ModelAdmin):
    """License admin."""

    list_display = (
        'name', 'description'
    )


admin.site.register(License, LicenseAdmin)
