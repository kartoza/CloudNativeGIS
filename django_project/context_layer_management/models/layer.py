# coding=utf-8
"""Context Layer Management."""

import os
import shutil
import uuid
import zipfile

from django.conf import settings
from django.db import models, connection
from django.db.models.signals import post_delete
from django.dispatch import receiver
from django.urls import reverse

from context_layer_management.models.general import (
    AbstractTerm, AbstractResource
)
from context_layer_management.utils.connection import delete_table, fields
from context_layer_management.utils.geopandas import shapefile_to_postgis

FOLDER_FILES = 'context_layer_management_files'
FOLDER_ROOT = os.path.join(
    settings.MEDIA_ROOT, FOLDER_FILES
)
FOLDER_URL = os.path.join(
    settings.MEDIA_URL, FOLDER_FILES
)


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
    is_ready = models.BooleanField(
        default=False,
        help_text='Indicates if the layer has been ready.'
    )
    type = models.CharField(
        max_length=256,
        default=LayerType.VECTOR_TILE,
        choices=(
            (LayerType.VECTOR_TILE, LayerType.VECTOR_TILE),
            (LayerType.RASTER_TILE, LayerType.RASTER_TILE),
        )
    )

    def __str__(self):
        """Return str."""
        return f'{self.name}'

    @property
    def folder(self) -> str:
        """Return folder path of this layer."""
        return os.path.join(FOLDER_ROOT, str(self.unique_id))

    @property
    def url(self) -> str:
        """Return url root of this layer."""
        return os.path.join(FOLDER_URL, str(self.unique_id))

    @property
    def files(self):
        """Return list of files in this layer."""
        if not os.path.exists(self.folder):
            return []
        return [
            f for f in os.listdir(self.folder) if
            os.path.isfile(os.path.join(self.folder, f))
        ]

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
            'context-layer-management-tile-api',
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
    def field_names(self):
        """Return list of field names in this layer."""
        return list(
            self.layerfield_set.all().values_list(
                'name', flat=True
            ).order_by('name')
        )

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

    def import_data(self):
        """Import data to database."""
        # Need to extract first
        self.is_ready = False
        self.save()

        for file in self.files:
            if file.endswith('.zip'):
                with zipfile.ZipFile(self.filepath(file), 'r') as ref:
                    ref.extractall(self.folder)
                    ref.close()

        # TODO:
        #  Handle when using tenant
        # Save the data
        for file in self.files:
            if file.endswith('.shp'):
                shapefile_to_postgis(
                    self.filepath(file), table_name=self.table_name,
                    schema_name=self.schema_name
                )
                self.layerfield_set.all().delete()
                for field in fields(
                        self.schema_name, self.table_name
                ):
                    LayerField.objects.create(
                        layer=self,
                        name=field.name,
                        type=field.type,
                    )

                self.is_ready = True
                self.save()


class LayerField(models.Model):
    """Field of layer."""

    layer = models.ForeignKey(
        Layer,
        on_delete=models.CASCADE
    )
    name = models.CharField(max_length=256)
    type = models.CharField(max_length=256)


@receiver(post_delete, sender=Layer)
def layer_on_delete(sender, instance: Layer, using, **kwargs):
    """Delete folder when the layer deleted."""
    instance.delete_folder()
    delete_table(instance.schema_name, instance.table_name)
