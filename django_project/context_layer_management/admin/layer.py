# coding=utf-8
"""Context Layer Management."""

from django.contrib import admin

from context_layer_management.forms.layer import LayerForm
from context_layer_management.models.layer import Layer, LayerField, LayerStyle


class LayerFieldInline(admin.TabularInline):
    """LayerField inline."""

    model = LayerField
    extra = 0

    def has_add_permission(self, request, obj):
        """Disable add permission."""
        return False


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
        'field_names'
    )
    inlines = [LayerFieldInline]
    filter_horizontal = ['styles']

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

    def field_names(self, obj: Layer):
        """Return fields."""
        return obj.field_names


class LayerStyleAdmin(admin.ModelAdmin):
    """Layer Style admin."""

    list_display = (
        'name', 'created_by', 'created_at'
    )


admin.site.register(Layer, LayerAdmin)
admin.site.register(LayerStyle, LayerStyleAdmin)
