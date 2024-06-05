# coding=utf-8
"""Cloud Native GIS."""

from django.contrib import admin

from cloud_native_gis.models.general import License


class LicenseAdmin(admin.ModelAdmin):
    """License admin."""

    list_display = (
        'name', 'description'
    )


admin.site.register(License, LicenseAdmin)
