# coding=utf-8
# SPDX-FileCopyrightText: 2024 Kartoza <info@kartoza.com>
# SPDX-License-Identifier: AGPL-3.0-or-later
"""OGC API item-level views: collection_items and collection_item."""

import pygeoapi.api.itemtypes as itemtypes_api
from django.http import HttpRequest, HttpResponse
from django.views.decorators.csrf import csrf_exempt

from .base import get_resources, execute_with_config, ogc_authenticate

_CQL_JSON_TYPES = frozenset({'application/cql2+json', 'application/cql+json'})
_CQL_TEXT_TYPES = frozenset({'application/cql-text', 'text/plain'})


@csrf_exempt
@ogc_authenticate
def collection_items(
    request: HttpRequest,
    collection_id: str,
) -> HttpResponse:
    """
    List, filter, or create features in a collection.

    **GET** — return features as a GeoJSON FeatureCollection.  Supports the
    following query parameters:

    - ``limit`` / ``offset`` — pagination
    - ``bbox`` — spatial bounding-box filter
    - ``datetime`` — temporal filter
    - ``properties`` — comma-separated list of property names to include
    - ``filter`` — CQL text filter expression (e.g. ``name='kenya'``)

    **POST** — behaviour depends on ``Content-Type``:

    - ``application/geo+json`` — create a new feature; returns ``201 Created``
      with a ``Location`` header pointing to the new resource.
    - ``application/cql2+json`` — filter features using a CQL2-JSON expression
      in the request body; returns ``200 OK`` with a FeatureCollection.
    - ``application/cql-text`` — filter features using a CQL text expression
      in the request body; returns ``200 OK`` with a FeatureCollection.

    :param request: incoming Django HTTP request
    :type request: HttpRequest
    :param collection_id: local identifier of the collection
    :type collection_id: str
    :returns:
        GeoJSON FeatureCollection (GET / filter POST)
        or empty 201 (create POST)
    :rtype: HttpResponse
    """
    config = get_resources(request)

    if request.method == 'GET':
        # CQL text filter is passed via ?filter=<expr>
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
@ogc_authenticate
def collection_item(
    request: HttpRequest,
    collection_id: str,
    item_id: str,
) -> HttpResponse:
    """
    Retrieve, replace, or delete a single feature.

    **GET** — return the feature as a GeoJSON Feature object.

    **PUT** — replace the feature with the GeoJSON Feature supplied in the
    request body (``Content-Type: application/geo+json``);
    returns ``204 No Content`` on success.

    **DELETE** — remove the feature; returns ``200 OK`` on success.

    :param request: incoming Django HTTP request
    :type request: HttpRequest
    :param collection_id: local identifier of the collection
    :type collection_id: str
    :param item_id: local identifier of the feature
    :type item_id: str
    :returns: GeoJSON Feature (GET), empty 204 (PUT), or empty 200 (DELETE)
    :rtype: HttpResponse
    """
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
        exists = execute_with_config(
            itemtypes_api.get_collection_item,
            config, request, collection_id, item_id,
        )
        if exists.status_code == 404:
            return exists
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
