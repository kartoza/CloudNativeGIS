# coding=utf-8
"""Context Layer Management."""

from django.contrib import admin

from context_layer_management.forms.style import StyleForm
from context_layer_management.models.style import Style


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
