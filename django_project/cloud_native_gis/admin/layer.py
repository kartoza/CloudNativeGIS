# coding=utf-8
"""Cloud Native GIS."""
import tempfile

from django.contrib import admin
from django.http import FileResponse
from django.utils.safestring import mark_safe

from cloud_native_gis.forms.layer import LayerForm, LayerUploadForm
from cloud_native_gis.models.layer import Layer, LayerAttributes
from cloud_native_gis.models.layer_upload import LayerUpload
from cloud_native_gis.tasks import import_data
from cloud_native_gis.utils.type import FileType


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


def create_download_action(file_type, description, extension, action_name):
    """Create a download action for a specific file type."""

    @admin.action(description=description)
    def download_action(modeladmin, request, queryset):
        """Download layer in the specified format."""
        if queryset.count() != 1:
            modeladmin.message_user(
                request,
                'Please select exactly one layer to download.',
                level='error')
            return

        layer = queryset.first()
        with tempfile.TemporaryDirectory() as working_dir:
            export_filepath, message = layer.export_layer(
                file_type, working_dir
            )
            if export_filepath:
                response = FileResponse(
                    open(export_filepath, 'rb'),
                    as_attachment=True,
                    filename=f'{layer.name}{extension}'
                )
                return response
            else:
                modeladmin.message_user(request, message, level='error')

    download_action.__name__ = action_name
    return download_action


# Create download actions for each file type
download_geojson = create_download_action(
    FileType.GEOJSON, 'Download as GeoJSON', '.geojson', 'download_geojson'
)
download_shapefile = create_download_action(
    FileType.SHAPEFILE, 'Download as Shapefile', '.zip', 'download_shapefile'
)
download_geopackage = create_download_action(
    FileType.GEOPACKAGE, 'Download as GeoPackage', '.gpkg',
    'download_geopackage'
)
download_kml = create_download_action(
    FileType.KML, 'Download as KML', '.kml', 'download_kml'
)


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
    actions = [
        generate_pmtiles,
        download_geojson,
        download_shapefile,
        download_geopackage,
        download_kml
    ]

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
