# coding=utf-8
"""Cloud Native GIS."""

from django.contrib import admin

from cloud_native_gis.forms.style import StyleForm
from cloud_native_gis.models.style import Style


class StyleAdmin(admin.ModelAdmin):
    """Layer Style admin."""

    form = StyleForm
    list_display = (
        'name', 'created_by', 'created_at'
    )

    def get_form(self, request, *args, **kwargs):
        """Return form."""
        form = super(StyleAdmin, self).get_form(request, *args, **kwargs)
        form.user = request.user
        return form


admin.site.register(Style, StyleAdmin)
