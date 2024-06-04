# coding=utf-8
"""Context Layer Management."""

from django.conf import settings
from django.contrib import admin
from django.utils.safestring import mark_safe

from context_layer_management.forms.layer import LayerForm, LayerUploadForm
from context_layer_management.models.layer import Layer, LayerField
from context_layer_management.models.layer_upload import LayerUpload
from context_layer_management.tasks import import_data
from context_layer_management.utils.layer import layer_style_url, MAPUTNIK_URL


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
        'unique_id', 'name', 'created_by', 'created_at', 'tile_url', 'editor'
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
        return obj.absolute_tile_url(self.request)

    def field_names(self, obj: Layer):
        """Return fields."""
        return obj.field_names

    def editor(self, obj: Layer):
        """Return fields."""
        return mark_safe(
            f"<a target='__blank__' href='{MAPUTNIK_URL}?"
            f"styleUrl={layer_style_url(obj, obj.default_style, self.request)}"
            f"'>Editor</a>"
        )

    editor.allow_tags = True


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


admin.site.register(Layer, LayerAdmin)
admin.site.register(LayerUpload, LayerUploadAdmin)
