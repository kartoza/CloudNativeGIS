# coding=utf-8
"""Cloud Native GIS."""

import os
import shutil
import zipfile

from django.conf import settings
from django.db import models
from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver

from cloud_native_gis.models.general import AbstractResource
from cloud_native_gis.models.layer import Layer, LayerAttributes
from cloud_native_gis.models.style import (
    Style, LINE, POINT, POLYGON
)
from cloud_native_gis.tasks import import_data
from cloud_native_gis.utils.connection import fields
from cloud_native_gis.utils.geopandas import collection_to_postgis
from cloud_native_gis.utils.main import id_generator
from cloud_native_gis.utils.type import FileType

FOLDER_FILES = 'cloud_native_gis_files'
FOLDER_ROOT = os.path.join(
    settings.MEDIA_ROOT, FOLDER_FILES
)


class UploadStatus(object):
    """Quick access for coupling variable with Log status string."""

    START = 'Start'
    RUNNING = 'Running'
    FAILED = 'Failed'
    SUCCESS = 'Success'


def generate_folder():
    """Generate folder."""
    return os.path.join(FOLDER_ROOT, id_generator())


class LayerUpload(AbstractResource):
    """Field of layer."""

    layer = models.ForeignKey(
        Layer,
        on_delete=models.CASCADE
    )
    progress = models.IntegerField(default=0)
    status = models.CharField(
        max_length=100,
        choices=(
            (UploadStatus.START, UploadStatus.START),
            (UploadStatus.RUNNING, UploadStatus.RUNNING),
            (UploadStatus.FAILED, UploadStatus.FAILED),
            (UploadStatus.SUCCESS, UploadStatus.SUCCESS),
        ),
        default=UploadStatus.START
    )
    note = models.TextField(blank=True, null=True)
    folder = models.TextField(default=generate_folder)

    @property
    def unique_id(self):
        """Return unique id."""
        return str(self.layer.unique_id)

    @property
    def files(self):
        """Return list of files in this layer."""
        if not os.path.exists(self.folder):
            return []
        return [
            f for f in os.listdir(self.folder) if
            os.path.isfile(os.path.join(self.folder, f))
        ]

    # ----------------------------------------------------
    # -------------------- FUNCTIONS ---------------------
    # ----------------------------------------------------
    def filepath(self, filename):
        """Return file path."""
        return os.path.join(self.folder, filename)

    def delete_folder(self):
        """Delete folder of the instance."""
        if os.path.exists(self.folder):
            shutil.rmtree(self.folder)

    def emptying_folder(self):
        """Delete content of the folder."""
        self.delete_folder()
        os.makedirs(self.folder)

    def update_status(self, status=None, progress=None, note=None):
        """Update status."""
        if status is not None:
            self.status = status
        if progress is not None:
            self.progress = progress
        if note is not None:
            self.note = note
        self.save()

    def import_data(self):
        """Import data to database."""
        if self.status == UploadStatus.RUNNING:
            return

        try:
            layer = self.layer
            layer.is_ready = False
            layer.save()

            # Need to extract first
            self.update_status(
                status=UploadStatus.RUNNING, note='Extract files', progress=20
            )
            for file in self.files:
                if file.endswith('.zip'):
                    with zipfile.ZipFile(self.filepath(file), 'r') as ref:
                        ref.extractall(self.folder)
                        ref.close()

            # Save the data
            for file in self.files:
                if FileType.guess_type(file):

                    # Save shapefile to database
                    self.update_status(
                        status=UploadStatus.RUNNING,
                        note='Save data to database',
                        progress=25
                    )
                    metadata = collection_to_postgis(
                        self.filepath(file),
                        table_name=layer.table_name,
                        schema_name=layer.schema_name
                    )

                    # Save fields to layer
                    self.update_status(
                        status=UploadStatus.RUNNING,
                        note='Save metadata to database',
                        progress=50
                    )
                    self.layer.layerattributes_set.all().delete()
                    for idx, field in enumerate(
                            fields(
                                layer.schema_name,
                                layer.table_name
                            )
                    ):
                        if field.name != 'geometry':
                            LayerAttributes.objects.create(
                                layer=layer,
                                attribute_name=field.name,
                                attribute_type=field.type,
                                attribute_order=idx
                            )

                    # Generate pmtiles
                    self.update_status(
                        status=UploadStatus.RUNNING,
                        note='Generate pmtiles',
                        progress=75
                    )
                    layer.generate_pmtiles()

                    layer.is_ready = True
                    layer.metadata = metadata

                    # Update default style
                    geometry_type = metadata['GEOMETRY TYPE'].lower()
                    if not layer.default_style_id:
                        default_style = POINT
                        if 'line' in geometry_type:
                            default_style = LINE
                        elif 'polygon' in geometry_type:
                            default_style = POLYGON
                        style, _ = Style.objects.get_or_create(
                            name=Style.default_style_name(geometry_type),
                            defaults={
                                'style': default_style
                            }
                        )
                        layer.update_default_style(style)
                    layer.save()

                    # stop when found first file
                    break
        except Exception as e:
            # Save fields to layer
            self.update_status(
                status=UploadStatus.FAILED,
                note=f'{e}'
            )
        else:
            # Save fields to layer
            self.update_status(
                status=UploadStatus.SUCCESS,
                note='',
                progress=100
            )
            # self.delete_folder()


@receiver(post_delete, sender=LayerUpload)
def layer_upload_on_delete(sender, instance: LayerUpload, using, **kwargs):
    """Delete folder when the layer deleted."""
    instance.delete_folder()


@receiver(post_save, sender=LayerUpload)
def run_layer_upload(sender, instance: LayerUpload, created, **kwargs):
    """Run import data when created."""
    if created:
        import_data.delay(instance.id)
