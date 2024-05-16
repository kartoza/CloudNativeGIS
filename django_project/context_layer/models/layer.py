# coding=utf-8
"""Context Layer Management."""

import os
import shutil
import uuid
import zipfile

from django.conf import settings
from django.db import models
from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver
from django.urls import reverse

from context_layer.models.general import AbstractTerm, AbstractResource
from context_layer.utils.connection import delete_table, field_names
from context_layer.utils.geopandas import shapefile_to_postgis

FOLDER_ROOT = os.path.join(settings.MEDIA_ROOT, 'layer_files')
FOLDER_URL = os.path.join(settings.MEDIA_URL, 'layer_files')


class Layer(AbstractTerm, AbstractResource):
    """Model contains layer information."""

    unique_id = models.UUIDField(
        unique=True,
        default=uuid.uuid4,
        editable=False
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
        return 'public_gis'

    @property
    def field_names(self):
        """Return schema name of this layer."""
        return field_names(self.schema_name, self.table_name)

    @property
    def tile_url(self):
        """Return tile url of layer."""
        return reverse(
            'layer-tile-api',
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


@receiver(post_delete, sender=Layer)
def layer_on_delete(sender, instance: Layer, using, **kwargs):
    """Delete folder when the layer deleted."""
    instance.delete_folder()
    delete_table(instance.schema_name, instance.table_name)