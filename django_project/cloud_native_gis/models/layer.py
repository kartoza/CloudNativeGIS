# coding=utf-8
"""Cloud Native GIS."""

import os
import subprocess
import uuid
import zipfile
from pathlib import Path

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.files import File
from django.db import connection, models
from django.db.models.signals import post_delete
from django.dispatch import receiver
from django.urls import reverse

from cloud_native_gis.models.general import (
    AbstractTerm, AbstractResource, License
)
from cloud_native_gis.models.style import Style
from cloud_native_gis.utils.connection import delete_table
from cloud_native_gis.utils.type import FileType
from cloud_native_gis.utils.fiona import list_layers

FOLDER_FILES = 'cloud_native_gis_files'
PMTILES_FOLDER = 'pmtile_files'
FOLDER_ROOT = os.path.join(
    settings.MEDIA_ROOT, FOLDER_FILES
)
FOLDER_URL = os.path.join(
    settings.MEDIA_URL, FOLDER_FILES
)


User = get_user_model()


class LayerType(object):
    """A quick couple of variable and Layer type."""

    VECTOR_TILE = 'Vector Tile'
    RASTER_TILE = 'Raster Tile'


class Layer(AbstractTerm, AbstractResource):
    """Model contains layer information."""

    unique_id = models.UUIDField(
        unique=True,
        default=uuid.uuid4,
        editable=False
    )
    layer_type = models.CharField(
        max_length=256,
        default=LayerType.VECTOR_TILE,
        choices=(
            (LayerType.VECTOR_TILE, LayerType.VECTOR_TILE),
            (LayerType.RASTER_TILE, LayerType.RASTER_TILE),
        )
    )

    is_ready = models.BooleanField(
        default=False,
        help_text='Indicates if the layer is ready.'
    )

    # METADATA
    license = models.ForeignKey(
        License,
        null=True, blank=True,
        on_delete=models.SET_NULL
    )
    abstract = models.TextField(
        null=True, blank=True
    )

    attribution = models.CharField(
        max_length=512,
        null=True, blank=True
    )
    metadata = models.JSONField(
        null=True, blank=True
    )

    # STYLES
    default_style = models.ForeignKey(
        Style, null=True, blank=True, on_delete=models.SET_NULL,
        help_text='Default layer style',
        related_name='default_style'
    )
    styles = models.ManyToManyField(
        Style, blank=True,
        help_text='Style list for the layer.'
    )
    pmtile = models.FileField(
        upload_to=f'{PMTILES_FOLDER}/',
        null=True, blank=True,
        help_text='Optional PMTile file associated with the layer.'
    )

    def __str__(self):
        """Return str."""
        return f'{self.name}'

    @property
    def table_name(self):
        """Return table name of this layer."""
        return f'layer_{self.unique_id}'.replace('-', '_')

    @property
    def query_table_name(self):
        """Return table name of this layer."""
        return f'{self.schema_name}.{self.table_name}'

    @property
    def schema_name(self):
        """Return schema name of this layer."""
        try:
            tenant = connection.get_tenant()
            return f'{tenant.schema_name}_gis'
        except AttributeError:
            return 'public_gis'

    @property
    def tile_url(self):
        """Return tile url of layer."""
        if not self.is_ready:
            return None

        return reverse(
            'cloud-native-gis-vector-tile',
            kwargs={
                'identifier': self.unique_id,
                'x': '0',
                'y': '1',
                'z': '2',
            }
        ).replace(
            '/0/', '/{x}/'
        ).replace(
            '/1/', '/{y}/'
        ).replace(
            '/2/', '/{z}/'
        )

    @property
    def attribute_names(self):
        """Return list of field names in this layer."""
        return list(
            self.layerattributes_set.all().values_list(
                'attribute_name', flat=True
            ).order_by('attribute_name')
        )

    def absolute_tile_url(self, request):
        """Return absolute tile url."""
        if self.tile_url and request:
            return request.build_absolute_uri('/')[:-1] + self.tile_url
        else:
            return None

    def absolute_pmtiles_url(self, request):
        """Return absolute pmtiles url."""
        if self.tile_url and request:
            return (
                f'pmtiles://{request.build_absolute_uri("/")[:-1]}'
                + reverse('serve-pmtiles', kwargs={
                    'layer_uuid': self.unique_id,
                })
            )
        else:
            return None

    def maputnik_url(self, request):
        """Return absolute url for maputnik."""
        from cloud_native_gis.utils.layer import layer_api_url, maputnik_url
        if self.tile_url and request:
            return f"{maputnik_url()}?api-url={layer_api_url(self, request)}"
        else:
            return None

    def update_default_style(self, style: Style):
        """Update default style."""
        self.default_style = style
        self.styles.add(style)
        self.save()

    def _convert_to_geojson(self, layer_upload, layer_files: list):
        """
        Convert resource to geojson if needed.

        Returns:
            tuple:
                - str: FileType
                - str: json_filepath
        """
        file_type = None
        layer_filename = None
        for layer_file in layer_files:
            file_type = FileType.guess_type(layer_file)
            if file_type:
                layer_filename = layer_file
                break

        if file_type is None:
            return None, None

        if file_type == FileType.GEOJSON:
            return file_type, layer_upload.filepath(layer_filename)

        layer_file_path = layer_upload.filepath(layer_filename)
        base_name = os.path.splitext(layer_filename)[0]
        json_filename = f"{base_name}.json"
        json_filepath = (
            os.path.join(
                settings.MEDIA_ROOT,
                PMTILES_FOLDER, json_filename)
        )

        cmd = [
            'ogr2ogr',
            '-t_srs',
            'EPSG:4326',
            json_filepath,
            layer_file_path
        ]
        if file_type == FileType.GEOPACKAGE or file_type == FileType.KML:
            layers = list_layers(layer_file_path, file_type)
            layer_name = layers[0] if layers else 'default'
            cmd.append(layer_name)

        subprocess.run(cmd, check=True)
        return file_type, json_filepath

    def generate_pmtiles(self):
        """
        Generate PMTiles for the current layer.

        This method converts a shapefile/geojson/GPKG/KML associated
        with the latest uploaded layer into PMTiles format
        using the 'ogr2ogr' and 'tippecanoe' tools.

        Returns:
            tuple:
                - bool: Success status of the operation.
                - str: Message indicating the outcome
        """
        layer_upload = self.layerupload_set.last()
        layer_files = layer_upload.files
        if not layer_files:
            return (
                False, f"No resource found for layer '{self.name}'.",
            )
        if layer_files:
            ogr2ogr_installed = (
                    subprocess.call(
                        ['which', 'ogr2ogr'],
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE) == 0)
            tippecanoe_installed = (
                    subprocess.call(
                        ['which', 'tippecanoe'],
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE) == 0
            )

            if not ogr2ogr_installed or not tippecanoe_installed:
                return (
                    False,
                    "ogr2ogr or tippecanoe is not installed on the server."
                )

            pmtiles_folder = (
                os.path.join(
                    settings.MEDIA_ROOT,
                    PMTILES_FOLDER
                )
            )
            if not os.path.exists(pmtiles_folder):
                os.mkdir(pmtiles_folder)

            try:
                file_type, json_filepath = self._convert_to_geojson(
                    layer_upload,
                    layer_files
                )
                if file_type is None:
                    return (
                        False,
                        "No resource found (.shp/.geojson/.gpkg/.kml) "
                        f"for layer '{self.name}'.",
                    )

                base_name = os.path.splitext(
                    os.path.basename(json_filepath)
                )[0]
                pmtiles_filename = f"{base_name}.pmtiles"
                pmtiles_filepath = (
                    os.path.join(
                        str(pmtiles_folder),
                        pmtiles_filename)
                )

                if os.path.exists(pmtiles_filepath):
                    os.remove(pmtiles_filepath)

                subprocess.run(
                    [
                        'tippecanoe',
                        '-zg',
                        '--projection=EPSG:4326',
                        '-o',
                        pmtiles_filepath,
                        '-l',
                        'default',
                        json_filepath],
                    check=True
                )

                with open(pmtiles_filepath, 'rb') as pmtiles_file:
                    self.pmtile.save(
                        pmtiles_filename,
                        File(pmtiles_file),
                        save=True)

                os.remove(json_filepath)
                os.remove(pmtiles_filepath)

                return (
                    True,
                    f"PMTiles generated successfully for layer '{self.name}'."
                )
            except subprocess.CalledProcessError:
                return (
                    False,
                    f"Failed to generate PMTiles for layer '{self.name}'."
                )

    def _zip_shapefile(self, shp_filepath, working_dir, remove_file=True):
        zip_filepath = os.path.join(
            working_dir,
            shp_filepath.replace('.shp', '.zip')
        )
        file_name = os.path.basename(shp_filepath).replace('.shp', '')
        shp_files = ['.shp', '.dbf', '.shx', '.cpg', '.prj']
        with zipfile.ZipFile(
                zip_filepath, 'w', zipfile.ZIP_DEFLATED) as archive:
            for suffix in shp_files:
                shape_file = os.path.join(
                    working_dir,
                    file_name
                ) + suffix
                if not os.path.exists(shape_file):
                    continue
                archive.write(
                    shape_file,
                    arcname=file_name + suffix
                )
                if remove_file:
                    os.remove(shape_file)
        return zip_filepath

    def export_layer(
        self, type: FileType, working_dir: str, filename = None
    ):
        """
        Export the current layer to requested format.

        This method converts a layer in postgis table into
        shapefile/geojson/GPKG/KML using the 'ogr2ogr.

        Returns:
            tuple:
                - bool: Success status of the operation.
                - str: Message indicating the outcome
        """
        driver_dict = {
            FileType.GEOJSON: 'GeoJSON',
            FileType.GEOPACKAGE: 'GPKG',
            FileType.KML: 'KML',
            FileType.SHAPEFILE: 'ESRI Shapefile'
        }
        ext = (
            '.shp' if type == FileType.SHAPEFILE else
            FileType.to_extension(type)
        )
        name = Path(filename).stem if filename else str(self.unique_id)
        export_filepath = os.path.join(
            working_dir,
            f'{name}{ext}'
        )
        conn_str = (
            'PG:dbname={NAME} user={USER} password={PASSWORD} '
            'host={HOST} port={PORT}'.format(
                **connection.settings_dict
            )
        )
        sql_str = (
            'SELECT * FROM {table_name}'.format(
                table_name=self.query_table_name
            )
        )
        cmd_list = [
            'ogr2ogr',
            '-t_srs',
            'EPSG:4326',
            '-f',
            f'{driver_dict[type]}',
            export_filepath,
            conn_str,
            '-sql',
            sql_str
        ]
        if type == FileType.SHAPEFILE:
            cmd_list.append('-lco')
            cmd_list.append('ENCODING=UTF-8')

        try:
            subprocess.run(cmd_list, check=True)

            if type == FileType.SHAPEFILE:
                # zip the files
                export_filepath = self._zip_shapefile(
                    export_filepath, working_dir
                )

            return (
                export_filepath,
                'Success'
            )
        except subprocess.CalledProcessError:
            return (
                None,
                f'Failed to export layer {self.name} to format {type}'
            )


class LayerAttributes(models.Model):
    """Field of layer."""

    layer = models.ForeignKey(
        Layer,
        on_delete=models.CASCADE
    )
    attribute_name = models.CharField(max_length=256)
    attribute_type = models.CharField(max_length=256)
    attribute_label = models.CharField(
        max_length=256, null=True, blank=True
    )
    attribute_description = models.TextField(
        null=True, blank=True
    )
    attribute_order = models.IntegerField(default=0)


@receiver(post_delete, sender=Layer)
def layer_on_delete(sender, instance: Layer, using, **kwargs):
    """Delete table and PMTile file when the layer is deleted."""
    delete_table(instance.schema_name, instance.table_name)

    if instance.pmtile and os.path.isfile(instance.pmtile.path):
        instance.pmtile.delete(save=False)
