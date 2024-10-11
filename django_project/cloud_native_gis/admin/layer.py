# coding=utf-8
"""Cloud Native GIS."""
from django.contrib import admin
from django.utils.safestring import mark_safe

from cloud_native_gis.forms.layer import LayerForm, LayerUploadForm
from cloud_native_gis.models.layer import Layer, LayerAttributes
from cloud_native_gis.models.layer_upload import LayerUpload
from cloud_native_gis.tasks import import_data


class LayerAttributeInline(admin.TabularInline):
    """LayerAttribute inline."""

    model = LayerAttributes
    extra = 0

    def has_add_permission(self, request, obj):
        """Disable add permission."""
        return False


@admin.action(description='Import data')
def start_upload_data(modeladmin, request, queryset):
    """Import data of layer."""
    for layer in queryset:
        import_data.delay(layer.pk)


@admin.action(description='Generate pmtiles')
def generate_pmtiles(modeladmin, request, queryset):
    """Generate pmtiles for layer."""
    for layer in queryset:
        success, message = layer.generate_pmtiles()
        modeladmin.message_user(
            request,
            message,
            level='success' if success else 'error')


@admin.register(Layer)
class LayerAdmin(admin.ModelAdmin):
    """Layer admin."""

    list_display = (
        'unique_id', 'name', 'created_by', 'created_at',
        'is_ready', 'tile_url', 'editor'
    )
    form = LayerForm
    inlines = [LayerAttributeInline]
    filter_horizontal = ['styles']
    actions = [generate_pmtiles]


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
        maputnik_url = obj.maputnik_url(self.request)
        if not maputnik_url:
            return None
        return mark_safe(
            f"<a target='__blank__' href='{maputnik_url}'>Editor</a>"
        )

    editor.allow_tags = True


@admin.register(LayerUpload)
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
