# coding=utf-8
"""Context Layer Management."""

from django.contrib import admin

from context_layer.forms.layer import LayerForm
from context_layer.models.layer import Layer


@admin.action(description='Import data')
def import_data(modeladmin, request, queryset):
    """Import data of layer."""
    for layer in queryset:
        layer.import_data()


class LayerAdmin(admin.ModelAdmin):
    """Layer admin."""

    actions = [import_data, ]
    form = LayerForm
    list_display = (
        'unique_id', 'name', 'created_by', 'created_at', 'tile_url',
        'fields'
    )

    def get_queryset(self, request):
        """Return queryset for current request."""
        self.request = request
        return super().get_queryset(request)

    def get_form(self, request, *args, **kwargs):
        """Return form."""
        form = super(LayerAdmin, self).get_form(request, *args, **kwargs)
        form.user = request.user
        return form

    def tile_url(self, obj: Layer):
        """Return tile_url."""
        if not obj.tile_url:
            return None
        return self.request.build_absolute_uri('/')[:-1] + obj.tile_url


admin.site.register(Layer, LayerAdmin)
