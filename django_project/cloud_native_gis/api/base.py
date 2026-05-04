# coding=utf-8
# SPDX-FileCopyrightText: 2024 Kartoza <info@kartoza.com>
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Cloud Native GIS."""
import os
from datetime import datetime

from django.core.exceptions import (
    FieldError, ValidationError, SuspiciousOperation
)
from django.forms.models import model_to_dict
from django.http import HttpResponseForbidden, Http404, HttpResponse
from rest_framework import status
from rest_framework.response import Response
from rest_framework.viewsets import mixins, GenericViewSet

from cloud_native_gis.pagination import Pagination
from cloud_native_gis.utils.range_request import RangeRequestReader


class BaseReadApi(
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    GenericViewSet
):
    """Base Read API View."""

    form_class = None
    lookup_field = 'id'
    pagination_class = Pagination

    def filter_query(self, request, query, ignores: list, fields: list = None):
        """Return filter query."""
        for param, value in request.GET.items():
            field = param.split('__')[0]
            if field in ignores:
                continue

            if fields and field not in fields:
                continue

            if '_in' in param:
                value = value.split(',')

            if 'date' in param:
                try:
                    value = datetime.fromtimestamp(int(value))
                except (ValueError, TypeError):
                    pass
            try:
                if 'NaN' in value or 'None' in value or 'Null' in value:
                    param = f'{field}__isnull'
                    value = True
                    query = query.filter(**{param: value})
                else:
                    query = query.filter(**{param: value})
            except FieldError:
                raise SuspiciousOperation(f'Can not query param {param}')
            except ValidationError as e:
                raise SuspiciousOperation(e)
        return query

    def get_queryset(self):
        """Return queryset of API."""
        query = self.queryset
        return self.filter_query(
            self.request, query, ['page', 'page_size']
        )

    def get_serializer_context(self):
        """Extra context provided to the serializer class."""
        return {
            'request': self.request,
            'format': self.format_kwarg,
            'view': self,
            'user': self.request.user
        }

    def get_serializer(self, *args, **kwargs):
        """Return the serializer instance."""
        serializer_class = self.get_serializer_class()
        kwargs.setdefault('context', self.get_serializer_context())
        return serializer_class(*args, **kwargs)

    def retrieve(self, request, *args, **kwargs):
        """Retrive the detailed object."""
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        return Response(serializer.data)


class BaseApi(
    BaseReadApi,
    mixins.RetrieveModelMixin,
    mixins.DestroyModelMixin,
    GenericViewSet
):
    """Base API for Resource."""

    def create(self, request, *args, **kwargs):
        """Update an object."""
        data = request.data.copy()
        form = self.form_class(data)
        form.user = request.user
        if form.is_valid():
            instance = form.save()
            instance.save()
            serializer = self.get_serializer(instance)
            return Response(serializer.data, status=status.HTTP_201_CREATED)

        return Response(
            dict(form.errors.items()),
            status=status.HTTP_400_BAD_REQUEST
        )

    def update(self, request, *args, **kwargs):
        """Update an object."""
        partial = kwargs.pop('partial', False)
        data = request.data.copy()

        instance = self.get_object()
        if instance.created_by != request.user:
            return HttpResponseForbidden()

        # If it is partial, just save the data from POST
        if partial:
            initial_data = model_to_dict(instance)
            for key, value in data.items():
                initial_data[key] = value
        else:
            # If not partial, it will replace all data
            initial_data = data

        form = self.form_class(
            initial_data,
            instance=instance
        )
        form.user = request.user
        if form.is_valid():
            instance = form.save()
            serializer = self.get_serializer(instance)
            return Response(serializer.data)

        return Response(
            dict(form.errors.items()),
            status=status.HTTP_400_BAD_REQUEST
        )

    def partial_update(self, request, *args, **kwargs):
        """Partial update of object."""
        kwargs['partial'] = True
        return self.update(request, *args, **kwargs)

    def destroy(self, request, id=None):
        """Destroy an object."""
        instance = self.get_object()
        if instance.created_by != request.user:
            return HttpResponseForbidden()
        self.perform_destroy(instance)
        return Response(status=status.HTTP_204_NO_CONTENT)


def serve_bytes_range(request, full_path, content_type):
    """Serve file using bytes range request."""
    if not os.path.exists(full_path):
        raise Http404("PMTile file does not exist.")

    reader = RangeRequestReader(full_path)
    try:
        range_header = request.headers.get('Range')

        if not range_header:
            # Return entire file if no range is specified
            data = reader.read_all()
            response = HttpResponse(data)
            response['Content-Type'] = content_type
            response['Content-Length'] = len(data)
            response['Accept-Ranges'] = 'bytes'
            return response

        # Parse range header
        try:
            range_match = range_header.replace('bytes=', '').split('-')
            start = int(range_match[0])
            end = int(range_match[1]) if range_match[1] else None
        except (ValueError, IndexError):
            return HttpResponse(status=400)

        # Read the requested range
        length = (
            (end - start + 1) if end is not None else
            (os.path.getsize(full_path) - start)
        )
        data = reader.read_range(start, length)

        response = HttpResponse(data, status=206)
        response['Content-Type'] = content_type
        response['Content-Length'] = len(data)
        response['Content-Range'] = (
            f'bytes {start}-{start + len(data) - 1}/'
            f'{os.path.getsize(full_path)}'
        )
        response['Accept-Ranges'] = 'bytes'
        return response
    finally:
        reader.close()
