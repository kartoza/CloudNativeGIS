"""Item-level views: collection_items and collection_item."""

from django.http import HttpRequest, HttpResponse
from django.views.decorators.csrf import csrf_exempt
import pygeoapi.api.itemtypes as itemtypes_api

from .base import get_resources, execute_with_config

# Content-types that signal a CQL filter POST rather than a feature-create POST.
_CQL_JSON_TYPES = frozenset({'application/cql2+json', 'application/cql+json'})
_CQL_TEXT_TYPES = frozenset({'application/cql-text', 'text/plain'})


@csrf_exempt
def collection_items(
    request: HttpRequest,
    collection_id: str,
) -> HttpResponse:
    config = get_resources(request)

    if request.method == 'GET':
        # CQL text filter is passed via ?filter=<expr>&filter-lang=cql-text
        return execute_with_config(
            itemtypes_api.get_collection_items,
            config, request, collection_id,
            skip_valid_check=True,
        )

    if request.method == 'POST':
        content_type = (request.content_type or '').split(';')[0].strip()

        if content_type == 'application/geo+json':
            return execute_with_config(
                itemtypes_api.manage_collection_item,
                config, request, 'create', collection_id,
                skip_valid_check=True,
            )

        if content_type in _CQL_TEXT_TYPES:
            # Inject the CQL text body as the ?filter query parameter so
            # pygeoapi's get_collection_items picks it up via parse_ecql_text.
            request.GET = request.GET.copy()
            request.GET['filter'] = request.body.decode()

        # CQL2-JSON body (application/cql2+json) or plain CQL text (above):
        # pygeoapi reads request.data when no ?filter= param is present.
        return execute_with_config(
            itemtypes_api.get_collection_items,
            config, request, collection_id,
            skip_valid_check=True,
        )

    if request.method == 'OPTIONS':
        return execute_with_config(
            itemtypes_api.manage_collection_item,
            config, request, 'options', collection_id,
            skip_valid_check=True,
        )


@csrf_exempt
def collection_item(
    request: HttpRequest,
    collection_id: str,
    item_id: str,
) -> HttpResponse:
    config = get_resources(request)

    if request.method == 'GET':
        return execute_with_config(
            itemtypes_api.get_collection_item,
            config, request, collection_id, item_id,
        )
    if request.method == 'PUT':
        return execute_with_config(
            itemtypes_api.manage_collection_item,
            config, request, 'update', collection_id, item_id,
            skip_valid_check=True,
        )
    if request.method == 'DELETE':
        return execute_with_config(
            itemtypes_api.manage_collection_item,
            config, request, 'delete', collection_id, item_id,
            skip_valid_check=True,
        )
    if request.method == 'OPTIONS':
        return execute_with_config(
            itemtypes_api.manage_collection_item,
            config, request, 'options', collection_id, item_id,
            skip_valid_check=True,
        )