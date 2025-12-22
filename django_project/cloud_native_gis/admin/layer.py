# coding=utf-8
"""Cloud Native GIS."""
import os
import tempfile

from django.conf import settings
from django.contrib import admin
from django.http import FileResponse, HttpResponseRedirect
from django.urls import reverse
from django.utils.safestring import mark_safe

from cloud_native_gis.forms.layer import LayerForm, LayerUploadForm
from cloud_native_gis.models.layer import Layer, LayerAttributes
from cloud_native_gis.models.layer_download import LayerDownload
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


def create_layer_download_action(
        file_type, description, extension, action_name
):
    """Create a download action using LayerDownload model."""

    @admin.action(description=description)
    def download_action(modeladmin, request, queryset):
        """Download layer using LayerDownload model."""
        if queryset.count() != 1:
            modeladmin.message_user(
                request,
                'Please select exactly one layer to download.',
                level='error')
            return

        layer = queryset.first()
        working_dir = os.path.join(settings.MEDIA_ROOT, 'tmp')

        # Create LayerDownload instance
        layer_download = LayerDownload.export_layer(
            request.user, layer, file_type, working_dir
        )

        # Run the download task
        layer_download.run()

        # Check if download was successful
        if layer_download.path:
            response = FileResponse(
                open(layer_download.path, 'rb'),
                as_attachment=True,
                filename=f'{layer.name}{extension}'
            )
            return response
        else:
            modeladmin.message_user(
                request,
                layer_download.note or 'Download failed.',
                level='error'
            )

    download_action.__name__ = action_name
    return download_action


# Create LayerDownload-based download actions for each file type
download_original_tracked = create_layer_download_action(
    FileType.ORIGINAL, 'Download Original (Tracked)', '.zip',
    'download_original_tracked'
)
download_geojson_tracked = create_layer_download_action(
    FileType.GEOJSON, 'Download as GeoJSON (Tracked)', '.geojson',
    'download_geojson_tracked'
)
download_shapefile_tracked = create_layer_download_action(
    FileType.SHAPEFILE, 'Download as Shapefile (Tracked)', '.zip',
    'download_shapefile_tracked'
)
download_geopackage_tracked = create_layer_download_action(
    FileType.GEOPACKAGE, 'Download as GeoPackage (Tracked)', '.gpkg',
    'download_geopackage_tracked'
)
download_kml_tracked = create_layer_download_action(
    FileType.KML, 'Download as KML (Tracked)', '.kml',
    'download_kml_tracked'
)


def create_layer_download_async_action(file_type, description, action_name):
    """Create an async download action using LayerDownload model and Celery."""

    @admin.action(description=description)
    def download_action(modeladmin, request, queryset):
        """Queue layer download using LayerDownload model and Celery."""
        if queryset.count() != 1:
            modeladmin.message_user(
                request,
                'Please select exactly one layer to download.',
                level='error')
            return

        layer = queryset.first()
        working_dir = os.path.join(settings.MEDIA_ROOT, 'tmp')

        # Create LayerDownload instance
        layer_download = LayerDownload.export_layer(
            request.user, layer, file_type, working_dir
        )

        # Schedule async task
        layer_download.schedule_task()

        # Redirect to download API
        download_url = reverse(
            'download-file',
            kwargs={'unique_id': layer_download.unique_id}
        )

        modeladmin.message_user(
            request,
            f'Download task queued for {layer.name}. '
            f'Redirecting to download URL...',
            level='success'
        )

        return HttpResponseRedirect(download_url)

    download_action.__name__ = action_name
    return download_action


# Create async download actions for each file type
download_original_async = create_layer_download_async_action(
    FileType.ORIGINAL, 'Download Original (Async)', 'download_original_async'
)
download_geojson_async = create_layer_download_async_action(
    FileType.GEOJSON, 'Download as GeoJSON (Async)', 'download_geojson_async'
)
download_shapefile_async = create_layer_download_async_action(
    FileType.SHAPEFILE, 'Download as Shapefile (Async)',
    'download_shapefile_async'
)
download_geopackage_async = create_layer_download_async_action(
    FileType.GEOPACKAGE, 'Download as GeoPackage (Async)',
    'download_geopackage_async'
)
download_kml_async = create_layer_download_async_action(
    FileType.KML, 'Download as KML (Async)', 'download_kml_async'
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
        download_kml,
        download_original_tracked,
        download_geojson_tracked,
        download_shapefile_tracked,
        download_geopackage_tracked,
        download_kml_tracked,
        download_original_async,
        download_geojson_async,
        download_shapefile_async,
        download_geopackage_async,
        download_kml_async
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


@admin.register(LayerDownload)
class LayerDownloadAdmin(admin.ModelAdmin):
    """LayerDownload admin."""

    list_display = (
        'created_at', 'created_by', 'layer', 'file_type', 'status',
        'download_link', 'path_display'
    )
    list_filter = ['layer', 'file_type', 'status']
    readonly_fields = (
        'unique_id', 'status', 'note', 'layer', 'file_type',
        'working_dir', 'filename', 'task_id', 'path', 'download_link'
    )

    def has_add_permission(self, request):
        """Disable add permission."""
        return False

    def download_link(self, obj):
        """Return download link if available."""
        from cloud_native_gis.models.layer_download import DownloadStatus
        if obj.status == DownloadStatus.SUCCESS and obj.path:
            download_url = reverse(
                'download-file',
                kwargs={'unique_id': obj.unique_id}
            )
            return mark_safe(
                f'<a href="{download_url}" target="_blank">Download</a>'
            )
        elif obj.status == DownloadStatus.SUCCESS and not obj.path:
            return mark_safe(
                '<span style="color: gray;">Already downloaded</span>')
        elif obj.status == DownloadStatus.FAILED:
            return mark_safe('<span style="color: red;">Failed</span>')
        else:
            return mark_safe(
                f'<span style="color: orange;">{obj.status}</span>'
            )

    download_link.short_description = 'Download'
    download_link.allow_tags = True

    def path_display(self, obj):
        """Display path with truncation."""
        if obj.path:
            # Show just the filename, not the full path
            import os
            filename = os.path.basename(obj.path)
            return mark_safe(
                f'<span title="{obj.path}">{filename}</span>'
            )
        return mark_safe('<span style="color: gray;">-</span>')

    path_display.short_description = 'File'
    path_display.allow_tags = True
