# coding=utf-8
"""Context Layer Management."""

import os
import shutil
import zipfile

from django.conf import settings
from django.db import models
from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver

from context_layer_management.models.general import AbstractResource
from context_layer_management.models.layer import Layer, LayerField, LayerStyle
from context_layer_management.models.style_defaults import (
    LINE, POINT, POLYGON
)
from context_layer_management.tasks import import_data
from context_layer_management.utils.connection import fields
from context_layer_management.utils.geopandas import shapefile_to_postgis
from context_layer_management.utils.main import id_generator

FOLDER_FILES = 'context_layer_management_files'
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
                if file.endswith('.shp'):

                    # Save shapefile to database
                    self.update_status(
                        status=UploadStatus.RUNNING,
                        note='Save data to database',
                        progress=50
                    )
                    metadata = shapefile_to_postgis(
                        self.filepath(file),
                        table_name=layer.table_name,
                        schema_name=layer.schema_name
                    )

                    # Save fields to layer
                    self.update_status(
                        status=UploadStatus.RUNNING,
                        note='Save metadata to database',
                        progress=70
                    )
                    self.layer.layerfield_set.all().delete()
                    for field in fields(
                            layer.schema_name,
                            layer.table_name
                    ):
                        if field.name != 'geometry':
                            LayerField.objects.create(
                                layer=layer,
                                name=field.name,
                                type=field.type,
                            )

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
                        style, _ = LayerStyle.objects.get_or_create(
                            name=f'Default {geometry_type}',
                            defaults={
                                'style': default_style
                            }
                        )
                        layer.default_style = style
                        layer.styles.add(style)
                    layer.save()
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
            self.delete_folder()


@receiver(post_delete, sender=LayerUpload)
def layer_upload_on_delete(sender, instance: LayerUpload, using, **kwargs):
    """Delete folder when the layer deleted."""
    instance.delete_folder()


@receiver(post_save, sender=LayerUpload)
def run_layer_upload(sender, instance: LayerUpload, created, **kwargs):
    """Run import data when created."""
    if created:
        import_data.delay(instance.id)
