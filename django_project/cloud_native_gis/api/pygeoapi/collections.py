"""Collection-level views: list, schema, queryables."""

from typing import Optional

from django.http import HttpRequest, HttpResponse
import pygeoapi.api as core_api
import pygeoapi.api.itemtypes as itemtypes_api

from .base import get_resources, execute_with_config


def collections(
    request: HttpRequest,
    collection_id: Optional[str] = None,
) -> HttpResponse:
    config = get_resources(request)
    return execute_with_config(
        core_api.describe_collections, config, request, collection_id
    )


def collection_schema(
    request: HttpRequest,
    collection_id: Optional[str] = None,
) -> HttpResponse:
    config = get_resources(request)
    return execute_with_config(
        core_api.get_collection_schema, config, request, collection_id
    )


def collection_queryables(
    request: HttpRequest,
    collection_id: Optional[str] = None,
) -> HttpResponse:
    config = get_resources(request)
    return execute_with_config(
        itemtypes_api.get_collection_queryables, config, request, collection_id
    )