# coding=utf-8
# SPDX-FileCopyrightText: 2024 Kartoza <info@kartoza.com>
# SPDX-License-Identifier: AGPL-3.0-or-later
"""OGC API collection-level views: list, detail, schema, and queryables."""

from typing import Optional

import pygeoapi.api as core_api
import pygeoapi.api.itemtypes as itemtypes_api
from django.http import HttpRequest, HttpResponse

from .base import get_resources, execute_with_config, ogc_authenticate


@ogc_authenticate
def collections(
    request: HttpRequest,
    collection_id: Optional[str] = None,
) -> HttpResponse:
    """
    List all available collections or return metadata for a single collection.

    When ``collection_id`` is ``None`` the response contains the full
    collection list.  When a value is provided only that collection's
    metadata is returned (404 if it does not exist).

    :param request: incoming Django HTTP request
    :type request: HttpRequest
    :param collection_id: optional local identifier of a collection
    :type collection_id: str or None
    :returns: collection list or single collection metadata as JSON
    :rtype: HttpResponse
    """
    config = get_resources(request)
    return execute_with_config(
        core_api.describe_collections, config, request, collection_id
    )


@ogc_authenticate
def collection_schema(
    request: HttpRequest,
    collection_id: Optional[str] = None,
) -> HttpResponse:
    """Return the JSON Schema describing the properties of a collection.

    :param request: incoming Django HTTP request
    :type request: HttpRequest
    :param collection_id: local identifier of the collection
    :type collection_id: str or None
    :returns: JSON Schema document for the collection
    :rtype: HttpResponse
    """
    config = get_resources(request)
    return execute_with_config(
        core_api.get_collection_schema, config, request, collection_id
    )


@ogc_authenticate
def collection_queryables(
    request: HttpRequest,
    collection_id: Optional[str] = None,
) -> HttpResponse:
    """
    Return the queryable properties for a collection.

    Queryables are the feature properties that can be referenced in CQL2
    filter expressions supplied to the items endpoint.

    :param request: incoming Django HTTP request
    :type request: HttpRequest
    :param collection_id: local identifier of the collection
    :type collection_id: str or None
    :returns: queryables document as JSON
    :rtype: HttpResponse
    """
    config = get_resources(request)
    return execute_with_config(
        itemtypes_api.get_collection_queryables, config, request, collection_id
    )
