# coding=utf-8
"""Cloud Native GIS."""

import copy

from psycopg2 import sql
from django.db import connection
from django.core.exceptions import PermissionDenied
from django.core.files.storage import FileSystemStorage
from django.http import Http404
from rest_framework.views import APIView
from rest_framework.generics import get_object_or_404
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

from cloud_native_gis.api.base import BaseApi, BaseReadApi
from cloud_native_gis.forms.layer import LayerForm
from cloud_native_gis.forms.style import StyleForm
from cloud_native_gis.models.layer import Layer
from cloud_native_gis.models.layer_upload import LayerUpload
from cloud_native_gis.models.style import Style
from cloud_native_gis.serializer.layer import (
    LayerSerializer, LayerAttributeSerializer
)
from cloud_native_gis.serializer.layer_upload import LayerUploadSerializer
from cloud_native_gis.serializer.style import LayerStyleSerializer
from cloud_native_gis.utils.layer import layer_style_url, maputnik_url


class LayerViewSet(BaseApi):
    """API for layer."""

    form_class = LayerForm
    queryset = Layer.objects.all()
    serializer_class = LayerSerializer

    def get_serializer_context(self):
        """Extra context provided to the serializer class."""
        return {
            'request': self.request,
            'format': self.format_kwarg,
            'view': self,
            'user': self.request.user
        }


class LayerObjectViewSet(BaseReadApi):
    """Abstract base class for layer objects."""

    def _get_layer(self) -> Layer:  # noqa: D102
        layer_id = self.kwargs.get('layer_id')
        return get_object_or_404(
            Layer.objects.filter(pk=layer_id)
        )

    def get_serializer_context(self):
        """Extra context provided to the serializer class."""
        return {
            'request': self.request,
            'format': self.format_kwarg,
            'view': self,
            'user': self.request.user,
            'layer': self._get_layer()
        }

    def get_serializer(self, *args, **kwargs):
        """Return the serializer instance."""
        serializer_class = self.get_serializer_class()
        kwargs.setdefault('context', self.get_serializer_context())
        return serializer_class(*args, **kwargs)


class LayerStyleViewSet(LayerObjectViewSet):
    """API layer style."""

    form_class = StyleForm
    serializer_class = LayerStyleSerializer

    def get_queryset(self):
        """Return queryset of API."""
        layer = self._get_layer()
        return layer.styles.all()

    def list(self, request, *args, **kwargs):
        """Return just default style."""
        layer = self._get_layer()
        if layer.default_style:
            serializer = self.get_serializer(layer.default_style)
            return Response(serializer.data)
        else:
            raise Http404

    def update(self, request, *args, **kwargs):
        """Update style."""
        _id = int(self.kwargs.get('id'))
        layer = self._get_layer()
        is_default = request.data['isDefault']
        save_as = request.data['saveAs']

        style = None
        if layer.default_style and layer.default_style.pk == _id:
            style = layer.default_style
        if not style:
            try:
                style = layer.styles.get(id=_id)
            except Style.DoesNotExist:
                pass
        if not style:
            raise Http404

        # Clean style requests
        style_request = copy.deepcopy(request.data['style'])
        style_request['layers'] = []
        try:
            del style_request['sources']
        except KeyError:
            pass
        for index, style_layer in enumerate(request.data['style']['layers']):
            if style_layer['type'] != 'raster':
                style_layer['id'] = f'<uuid>-{index}'
                style_layer['source'] = '<uuid>'
                style_request['layers'].append(style_layer)

        # Save the style
        if style.is_default_style:
            style.id = None
        if save_as:
            style.id = None

        style.name = request.data['name']
        if style.name in Style.default_names():
            style.name = f'{style.name} ({layer.unique_id})'
        style.style = style_request
        style.save()

        # Save this as default style
        if is_default:
            layer.default_style = style
            layer.save()

        # Add style to styles
        layer.styles.add(style)

        return Response(
            f'{maputnik_url()}?styleUrl='
            f'{layer_style_url(layer, style, self.request)}'
        )


class LayerUploadViewSet(LayerObjectViewSet):
    """API layer upload style."""

    serializer_class = LayerUploadSerializer

    def get_queryset(self):
        """Return queryset of API."""
        layer = self._get_layer()
        return layer.layerupload_set.all().order_by('-pk')

    def post(self, request, layer_id):
        """Post file."""
        layer = get_object_or_404(Layer, id=layer_id)
        if layer.created_by != self.request.user:
            raise PermissionDenied

        instance = LayerUpload(
            created_by=request.user, layer=layer
        )
        instance.emptying_folder()

        # Save files
        file = request.FILES['file']
        FileSystemStorage(
            location=instance.folder
        ).save(file.name, file)
        instance.save()
        return Response('Uploaded')


class LayerAttributesViewSet(LayerObjectViewSet):
    """API layer attributes."""

    serializer_class = LayerAttributeSerializer

    def get_queryset(self):
        """Return queryset of API."""
        layer = self._get_layer()
        return layer.layerattributes_set.all()


class DataPreviewAPI(APIView):
    """API to preview data."""

    permission_classes = [IsAuthenticated]

    def _get_search_query(self, layer: Layer, search):
        text_attributes = layer.layerattributes_set.filter(
            attribute_type='text'
        ).values_list('attribute_name', flat=True)
        search_query = []
        params = []
        attrs = []
        for attr in text_attributes:
            attrs.append(sql.Identifier(attr))
            search_query.append("{} ILIKE %s")
            params.append(f"%{search}%")
        return ' OR '.join(search_query), params, attrs

    def _get_count(self, layer: Layer, search=None):
        """Get count of features in layer."""
        if search is None or search == '':
            return layer.metadata['FEATURE COUNT']

        search_cond, params, attrs = self._get_search_query(layer, search)
        if search_cond == '':
            return layer.metadata['FEATURE COUNT']
        query = sql.SQL("SELECT COUNT(*) FROM {}.{} WHERE {}").format(
            sql.Identifier(layer.schema_name),
            sql.Identifier(layer.table_name),
            sql.SQL(search_cond).format(*attrs)
        )
        with connection.cursor() as cursor:
            cursor.execute(query, params)
            return cursor.fetchone()[0]

    def get(self, request, *args, **kwargs):
        """Get data from layer table."""
        layer = get_object_or_404(
            Layer,
            id=kwargs.get('layer_id')
        )

        page_size = int(request.GET.get('page_size', 10))
        page = int(request.GET.get('page', 1))
        search = request.GET.get('search', None)
        total_count = self._get_count(layer, search)
        columns = layer.layerattributes_set.all().values_list(
            'attribute_name', flat=True
        ).order_by('attribute_order')
        id_col = 'id'
        if id_col not in columns:
            id_col = columns[0]
        search_cond = sql.SQL('')
        params = []
        if search is not None and search != '':
            search_cond, params, attrs = self._get_search_query(layer, search)
            if search_cond != '':
                search_cond = sql.SQL('WHERE {}').format(
                    sql.SQL(search_cond).format(*attrs)
                )
        query = sql.SQL("""
            SELECT {} FROM {}.{}
            {}
            ORDER BY {} ASC
            OFFSET %s LIMIT %s
        """).format(
            sql.SQL(',').join(map(sql.Identifier, columns)),
            sql.Identifier(layer.schema_name),
            sql.Identifier(layer.table_name),
            search_cond,
            sql.Identifier(id_col)
        )
        rows = []
        with connection.cursor() as cursor:
            cursor.execute(
                query,
                params + [(int(page) - 1) * int(page_size), int(page_size)]
            )
            _rows = cursor.fetchall()
            for _row in _rows:
                _data = {}
                for i, col in enumerate(columns):
                    _data[col] = _row[i]
                rows.append(_data)

        return Response(data={
            'layer_id': layer.id,
            'page': page,
            'page_size': page_size,
            'count': total_count,
            'data': rows,
            'columns': columns
        })
