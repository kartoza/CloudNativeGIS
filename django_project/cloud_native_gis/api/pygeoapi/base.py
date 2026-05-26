"""Base helpers for dynamic per-user pygeoapi config and request execution."""

import copy
from typing import Union

from django.conf import settings
from django.http import HttpRequest, HttpResponse
from pygeoapi.api import API, APIRequest
from pygeoapi.django_.views import apply_gzip

from cloud_native_gis.utils.pygeoapi_config import _layer_to_resource


def get_queryset(
    request: HttpRequest
):
    """
    Return the Layer queryset exposed as OGC API resources.

    Override this function to apply custom filtering or permission logic.

    :param request: the current Django request
    :returns: Layer queryset
    """
    from cloud_native_gis.models.layer import Layer
    return Layer.objects.all()


def get_resources(
    request: HttpRequest
) -> dict:
    """
    Build a pygeoapi config dict whose resources come from get_queryset().

    Override get_queryset() to control which layers are exposed.

    :param request: the current Django request
    :returns: pygeoapi config dict with resources populated from the queryset
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
    Equivalent to pygeoapi's execute_from_django but accepts an explicit
    config dict instead of reading from settings.PYGEOAPI_CONFIG.
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
