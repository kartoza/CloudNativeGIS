# coding=utf-8
"""Cloud Native GIS."""

import os
import uuid

from django.conf import settings
from django.contrib.auth import get_user_model
from django.db import connection, models
from django.db.models.signals import post_delete
from django.dispatch import receiver
from django.urls import reverse

from cloud_native_gis.models.general import (
    AbstractTerm, AbstractResource, License
)
from cloud_native_gis.models.style import Style
from cloud_native_gis.utils.connection import delete_table

FOLDER_FILES = 'cloud_native_gis_files'
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
    """Delete table when the layer deleted."""
    delete_table(instance.schema_name, instance.table_name)
