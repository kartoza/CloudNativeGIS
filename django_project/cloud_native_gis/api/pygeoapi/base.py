# coding=utf-8
# SPDX-FileCopyrightText: 2024 Kartoza <info@kartoza.com>
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Base helpers for dynamic per-request pygeoapi config and request execution."""

import copy
from typing import Union

from django.conf import settings
from django.http import HttpRequest, HttpResponse
from pygeoapi.api import API, APIRequest
from pygeoapi.django_.views import apply_gzip

from cloud_native_gis.utils.pygeoapi_config import _layer_to_resource


def get_queryset(request: HttpRequest):
    """
    Return the Layer queryset exposed as OGC API resources.

    Override this function in a subclass or by monkey-patching to apply
    custom filtering or permission logic (e.g. restrict to layers owned
    by the authenticated user).

    :param request: the current Django HTTP request
    :type request: HttpRequest
    :returns: queryset of :class:`~cloud_native_gis.models.layer.Layer` objects
    :rtype: django.db.models.QuerySet
    """
    from cloud_native_gis.models.layer import Layer
    return Layer.objects.all()


def get_resources(request: HttpRequest) -> dict:
    """
    Build a pygeoapi config dict whose ``resources`` section is populated
    from :func:`get_queryset`.

    The returned dict is a deep copy of ``settings.PYGEOAPI_CONFIG`` with the
    ``resources`` key replaced by a mapping from collection ID to provider
    definition for every layer returned by :func:`get_queryset`.

    Override :func:`get_queryset` to control which layers are exposed without
    having to touch this function.

    :param request: the current Django HTTP request
    :type request: HttpRequest
    :returns: pygeoapi config dict with ``resources`` populated from the queryset
    :rtype: dict
    """
    from django.db import connection
    qs = get_queryset(request)

    db_settings = connection.settings_dict
    resources = {
        str(layer.unique_id).replace('-', '_'): _layer_to_resource(
            layer, db_settings
        )
        for layer in qs
    }

    config = copy.deepcopy(settings.PYGEOAPI_CONFIG)
    config['resources'] = resources
    return config


def execute_with_config(
    api_function,
    config: dict,
    request: HttpRequest,
    *args,
    skip_valid_check: bool = False,
) -> HttpResponse:
    """
    Execute a pygeoapi API function using an explicit config dict.

    Equivalent to pygeoapi's ``execute_from_django`` helper but accepts a
    pre-built config dict instead of reading from ``settings.PYGEOAPI_CONFIG``.
    This allows per-request dynamic resource configs (see :func:`get_resources`).

    :param api_function: callable with signature
        ``(api, request, *args) -> (headers, status, content)``
    :type api_function: callable
    :param config: pygeoapi config dict (e.g. from :func:`get_resources`)
    :type config: dict
    :param request: the current Django HTTP request
    :type request: HttpRequest
    :param args: additional positional arguments forwarded to ``api_function``
    :param skip_valid_check: when ``True`` skip the ``APIRequest.is_valid()``
        check; useful for endpoints that validate internally
    :type skip_valid_check: bool
    :returns: Django HTTP response with headers, status code, and body from
        the pygeoapi function
    :rtype: HttpResponse
    """
    api_: Union[API, object]
    if config['server'].get('admin'):
        from pygeoapi.admin import Admin
        api_ = Admin(config, settings.OPENAPI_DOCUMENT)
    else:
        api_ = API(config, settings.OPENAPI_DOCUMENT)

    if 'lang' in request.GET:
        request.GET = request.GET.copy()
        request.GET.pop('lang')

    api_request = APIRequest.from_django(request, api_.locales)

    if not skip_valid_check and not api_request.is_valid():
        headers, status, content = api_.get_format_exception(api_request)
    else:
        headers, status, content = api_function(api_, api_request, *args)
        content = apply_gzip(headers, content)

    response = HttpResponse(content, status=status)
    for key, value in headers.items():
        response[key] = value
    return response