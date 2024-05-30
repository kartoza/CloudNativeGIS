# coding=utf-8
"""Context Layer Management."""

import os
import uuid

from django.conf import settings
from django.db import models, connection
from django.db.models.signals import post_delete
from django.dispatch import receiver
from django.urls import reverse

from context_layer_management.models.general import (
    AbstractTerm, AbstractResource
)
from context_layer_management.utils.connection import delete_table

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


class LayerStyle(AbstractTerm, AbstractResource):
    """Model contains layer information."""

    style = models.JSONField(
        help_text=(
            'Contains mapbox style information.'
        )
    )


class Layer(AbstractTerm, AbstractResource):
    """Model contains layer information."""

    unique_id = models.UUIDField(
        unique=True,
        default=uuid.uuid4,
        editable=False
    )
    is_ready = models.BooleanField(
        default=False,
        help_text='Indicates if the layer is ready.'
    )
    type = models.CharField(
        max_length=256,
        default=LayerType.VECTOR_TILE,
        choices=(
            (LayerType.VECTOR_TILE, LayerType.VECTOR_TILE),
            (LayerType.RASTER_TILE, LayerType.RASTER_TILE),
        )
    )
    metadata = models.JSONField(
        null=True, blank=True
    )

    default_style = models.ForeignKey(
        LayerStyle, null=True, blank=True, on_delete=models.SET_NULL,
        help_text='Default layer style',
        related_name='default_style'
    )
    styles = models.ManyToManyField(
        LayerStyle, blank=True,
        help_text='Style list for the layer.'
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
    """Delete table when the layer deleted."""
    delete_table(instance.schema_name, instance.table_name)
