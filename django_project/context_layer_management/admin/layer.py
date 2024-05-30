# coding=utf-8
"""Context Layer Management."""

from django.contrib import admin

from context_layer_management.forms.layer import LayerForm, LayerUploadForm
from context_layer_management.forms.style import LayerStyleForm
from context_layer_management.models.layer import Layer, LayerField, LayerStyle
from context_layer_management.models.layer_upload import LayerUpload
from context_layer_management.tasks import import_data


class LayerFieldInline(admin.TabularInline):
    """LayerField inline."""

    model = LayerField
    extra = 0

    def has_add_permission(self, request, obj):
        """Disable add permission."""
        return False


@admin.action(description='Import data')
def start_upload_data(modeladmin, request, queryset):
    """Import data of layer."""
    for layer in queryset:
        import_data.delay(layer.pk)


class LayerAdmin(admin.ModelAdmin):
    """Layer admin."""

    list_display = (
        'unique_id', 'name', 'created_by', 'created_at', 'tile_url', 'metadata'
    )
    form = LayerForm
    inlines = [LayerFieldInline]
    filter_horizontal = ['styles']

    def get_form(self, request, *args, **kwargs):
        """Return form."""
        form = super(LayerAdmin, self).get_form(request, *args, **kwargs)
        form.user = request.user
        return form

    def get_queryset(self, request):
        """Return queryset for current request."""
        self.request = request
        return super().get_queryset(request)

    def tile_url(self, obj: Layer):
        """Return tile_url."""
        if not obj.tile_url:
            return None
        return self.request.build_absolute_uri('/')[:-1] + obj.tile_url

    def field_names(self, obj: Layer):
        """Return fields."""
        return obj.field_names


class LayerUploadAdmin(admin.ModelAdmin):
    """Layer admin."""

    list_display = (
        'created_at', 'created_by', 'layer', 'status', 'progress', 'note'
    )
    list_filter = ['layer', 'status']
    actions = [start_upload_data]
    form = LayerUploadForm

    def get_form(self, request, *args, **kwargs):
        """Return form."""
        form = super(LayerUploadAdmin, self).get_form(request, *args, **kwargs)
        form.user = request.user
        return form


class LayerStyleAdmin(admin.ModelAdmin):
    """Layer Style admin."""

    form = LayerStyleForm
    list_display = (
        'name', 'created_by', 'created_at'
    )

    def get_form(self, request, *args, **kwargs):
        """Return form."""
        form = super(LayerStyleAdmin, self).get_form(request, *args, **kwargs)
        form.user = request.user
        return form


admin.site.register(Layer, LayerAdmin)
admin.site.register(LayerStyle, LayerStyleAdmin)
admin.site.register(LayerUpload, LayerUploadAdmin)
