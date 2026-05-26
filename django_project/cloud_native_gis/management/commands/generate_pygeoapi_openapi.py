# coding=utf-8
# SPDX-FileCopyrightText: 2024 Kartoza <info@kartoza.com>
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Management command to generate pygeoapi OpenAPI document."""

import copy
import re

from django.core.management.base import BaseCommand
from django.conf import settings

# Path prefixes to exclude from the generated OpenAPI spec.
_EXCLUDED_PATH_PREFIXES = (
    '/processes',
    '/jobs',
    '/stac',
    '/stac-api',
    '/TileMatrixSets',
    '/asyncapi',
)

# Path suffixes/substrings to exclude (collection sub-resources we don't use).
_EXCLUDED_PATH_SUBSTRINGS = (
    '/coverage',
    '/map',
    '/tiles',
    '/position',
    '/area',
    '/cube',
    '/radius',
    '/trajectory',
    '/corridor',
    '/instances',
    '/locations',
    '/edr',
)


def _filter_openapi(openapi: dict) -> dict:
    """
    Remove unused OGC API paths and their tags from the OpenAPI document.

    Paths matching any prefix in ``_EXCLUDED_PATH_PREFIXES`` or any substring
    in ``_EXCLUDED_PATH_SUBSTRINGS`` are dropped.  The ``lang`` query parameter
    is also stripped from every remaining operation.  Tag definitions that are
    no longer referenced are pruned accordingly.

    :param openapi: OpenAPI dict produced by ``pygeoapi.openapi.get_oas``
    :type openapi: dict
    :returns: filtered OpenAPI dict (mutated in place and returned)
    :rtype: dict
    """
    paths = openapi.get('paths', {})

    def _excluded(path: str) -> bool:
        for prefix in _EXCLUDED_PATH_PREFIXES:
            if path.startswith(prefix):
                return True
        for sub in _EXCLUDED_PATH_SUBSTRINGS:
            if sub in path:
                return True
        return False

    filtered = {
        path: item for path, item in paths.items()
        if not _excluded(path)
    }

    # Remove 'lang' parameter from all operations
    for item in filtered.values():
        for operation in item.values():
            if isinstance(operation, dict) and 'parameters' in operation:
                operation['parameters'] = [
                    p for p in operation['parameters']
                    if not (isinstance(p, dict) and p.get('name') == 'lang')
                ]

    openapi['paths'] = filtered

    # Collect tags still referenced by remaining paths
    used_tags = set()
    for item in openapi['paths'].values():
        for operation in item.values():
            if isinstance(operation, dict):
                used_tags.update(operation.get('tags', []))

    if 'tags' in openapi:
        openapi['tags'] = [
            t for t in openapi['tags'] if t.get('name') in used_tags
        ]

    return openapi


# Key used for the single dummy resource injected during spec generation.
# The fixed ID is replaced with {collectionId} by _parameterize_collection_ids.
_TEMPLATE_COLLECTION_ID = 'collection'

# Matches /collections/<id> or /collections/<id>/anything
# where <id> is not already a {template} variable.
_COLLECTION_PATH_RE = re.compile(r'^(/collections/)([^/{][^/]*)(/.*)?$')

_COLLECTION_ID_PARAM = {
    'name': 'collectionId',
    'in': 'path',
    'required': True,
    'schema': {'type': 'string'},
    'description': 'Local identifier of a collection',
}


def _parameterize_collection_ids(openapi: dict) -> dict:
    """
    Replace hardcoded collection IDs in paths with a ``{collectionId}`` parameter.

    pygeoapi generates one path entry per configured layer
    (e.g. ``/collections/uuid_a/items``, ``/collections/uuid_b/items``).
    This function collapses them into a single parameterised path
    (``/collections/{collectionId}/items``) so Swagger UI shows one entry per
    endpoint pattern instead of one per layer.

    Any existing ``collectionId`` path parameter is de-duplicated and a
    canonical definition is inserted at position 0.

    :param openapi: OpenAPI dict (after ``_filter_openapi``)
    :type openapi: dict
    :returns: OpenAPI dict with parameterised collection paths (mutated in place
        and returned)
    :rtype: dict
    """
    paths = openapi.get('paths', {})
    new_paths = {}

    for path, item in paths.items():
        match = _COLLECTION_PATH_RE.match(path)
        if match:
            suffix = match.group(3) or ''
            new_path = f'/collections/{{collectionId}}{suffix}'
            if new_path in new_paths:
                # Already added from a previous layer – skip duplicate.
                continue
            item = copy.deepcopy(item)
            for operation in item.values():
                if not isinstance(operation, dict):
                    continue
                params = [
                    p for p in operation.get('parameters', [])
                    if not (isinstance(p, dict) and p.get('name') == 'collectionId')
                ]
                params.insert(0, copy.deepcopy(_COLLECTION_ID_PARAM))
                operation['parameters'] = params
            new_paths[new_path] = item
        else:
            new_paths[path] = item

    openapi['paths'] = new_paths
    return openapi


_COLLECTION_ID_PARAM_REF = {
    'name': 'collectionId',
    'in': 'path',
    'required': True,
    'schema': {'type': 'string'},
    'description': 'Local identifier of a collection',
}

_FEATURE_ID_PARAM = {
    'name': 'featureId',
    'in': 'path',
    'required': True,
    'schema': {'type': 'string'},
    'description': 'Local identifier of a feature',
}

_GEOJSON_FEATURE_BODY = {
    'required': True,
    'description': 'A GeoJSON feature',
    'content': {
        'application/geo+json': {
            'schema': {
                '$ref': (
                    'https://schemas.opengis.net/ogcapi/features/part1/1.0'
                    '/openapi/ogcapi-features-1.yaml'
                    '#/components/schemas/featureGeoJSON'
                ),
            }
        }
    },
}

_STD_RESPONSES = {
    '400': {
        '$ref': (
            'https://schemas.opengis.net/ogcapi/features/part1/1.0'
            '/openapi/ogcapi-features-1.yaml'
            '#/components/responses/InvalidParameter'
        )
    },
    '404': {
        '$ref': (
            'https://schemas.opengis.net/ogcapi/features/part1/1.0'
            '/openapi/ogcapi-features-1.yaml'
            '#/components/responses/NotFound'
        )
    },
    '500': {
        '$ref': (
            'https://schemas.opengis.net/ogcapi/features/part1/1.0'
            '/openapi/ogcapi-features-1.yaml'
            '#/components/responses/ServerError'
        )
    },
}


def _add_write_operations(openapi: dict) -> dict:
    """
    Inject write operations that pygeoapi omits for read-only providers.

    Adds or updates the following operations in the OpenAPI paths:

    - ``POST /collections/{collectionId}/items`` — create a feature
      (``application/geo+json``) or filter with CQL2-JSON /
      CQL text.  If pygeoapi already generated a ``post`` entry for CQL2,
      it is extended with the GeoJSON content type and an updated description.
    - ``PUT /collections/{collectionId}/items/{featureId}`` — replace a feature.
    - ``DELETE /collections/{collectionId}/items/{featureId}`` — delete a feature.

    :param openapi: OpenAPI dict (after ``_parameterize_collection_ids``)
    :type openapi: dict
    :returns: OpenAPI dict with write operations added (mutated in place and
        returned)
    :rtype: dict
    """
    paths = openapi.setdefault('paths', {})

    # POST /collections/{collectionId}/items — create feature OR CQL filter.
    # pygeoapi already generates a 'post' for CQL2-JSON; extend its requestBody
    # to also accept application/geo+json so Swagger shows both uses.
    items_path = paths.setdefault('/collections/{collectionId}/items', {})
    post_op = items_path.setdefault('post', {
        'operationId': 'postCollectionFeatures',
        'tags': ['collections'],
        'parameters': [copy.deepcopy(_COLLECTION_ID_PARAM_REF)],
        'responses': {},
    })
    post_op['summary'] = 'Create feature or filter with CQL2'
    post_op['description'] = (
        'This endpoint serves two purposes depending on the `Content-Type`:\n\n'
        '---\n\n'
        '### 1. Create a new feature\n'
        '**Content-Type:** `application/geo+json`\n\n'
        'Send a GeoJSON Feature in the request body. '
        'Returns `201 Created` with a `Location` header pointing to the new feature.\n\n'
        '**Example body:**\n'
        '```json\n'
        '{\n'
        '  "type": "Feature",\n'
        '  "geometry": {\n'
        '    "type": "Point",\n'
        '    "coordinates": [36.8, -1.3]\n'
        '  },\n'
        '  "properties": {\n'
        '    "name": "Nairobi"\n'
        '  }\n'
        '}\n'
        '```\n\n'
        '---\n\n'
        '### 2. Filter features with CQL2-JSON\n'
        '**Content-Type:** `application/cql2+json`\n\n'
        'Send a CQL2 filter expression as JSON. '
        'Returns `200 OK` with a GeoJSON FeatureCollection of matching features.\n\n'
        '**Example body:**\n'
        '```json\n'
        '{\n'
        '  "op": "=",\n'
        '  "args": [{"property": "name"}, "kenya"]\n'
        '}\n'
        '```\n\n'
        '---\n\n'
        '### 3. Filter features with CQL text\n'
        '**Content-Type:** `application/cql-text`\n\n'
        'Send a CQL text filter expression as plain text. '
        'Returns `200 OK` with a GeoJSON FeatureCollection of matching features.\n\n'
        '**Example body:**\n'
        '```\n'
        "name = 'kenya'\n"
        '```'
    )
    post_op['responses']['200'] = {'description': 'GeoJSON FeatureCollection (CQL filter result)'}
    post_op['responses']['201'] = {'description': 'Feature created — Location header contains the new feature URL'}
    for k, v in copy.deepcopy(_STD_RESPONSES).items():
        post_op['responses'].setdefault(k, v)

    request_body = post_op.setdefault('requestBody', {'required': True, 'content': {}})
    request_body['description'] = (
        'Use `application/geo+json` to create a feature, '
        '`application/cql2+json` or `application/cql-text` to filter.'
    )
    request_body['content']['application/geo+json'] = {
        'schema': {
            '$ref': (
                'https://schemas.opengis.net/ogcapi/features/part1/1.0'
                '/openapi/ogcapi-features-1.yaml'
                '#/components/schemas/featureGeoJSON'
            )
        },
        'example': {
            'type': 'Feature',
            'geometry': {
                'type': 'Point',
                'coordinates': [36.8, -1.3],
            },
            'properties': {'name': 'Nairobi'},
        },
    }
    request_body['content']['application/cql2+json'] = {
        'schema': {'$ref': 'https://schemas.opengis.net/cql2/1.0/cql2.json'},
        'example': {
            'op': '=',
            'args': [{'property': 'name'}, 'kenya'],
        },
    }
    request_body['content']['application/cql-text'] = {
        'schema': {'type': 'string'},
        'example': "name = 'kenya'",
    }

    # PUT /collections/{collectionId}/items/{featureId} — replace a feature
    item_path = paths.setdefault(
        '/collections/{collectionId}/items/{featureId}', {}
    )
    if 'put' not in item_path:
        item_path['put'] = {
            'summary': 'Replace a feature',
            'operationId': 'replaceCollectionFeature',
            'tags': ['collections'],
            'parameters': [
                copy.deepcopy(_COLLECTION_ID_PARAM_REF),
                copy.deepcopy(_FEATURE_ID_PARAM),
            ],
            'requestBody': copy.deepcopy(_GEOJSON_FEATURE_BODY),
            'responses': {
                '200': {'description': 'Feature replaced successfully'},
                **copy.deepcopy(_STD_RESPONSES),
            },
        }

    # DELETE /collections/{collectionId}/items/{featureId} — delete a feature
    if 'delete' not in item_path:
        item_path['delete'] = {
            'summary': 'Delete a feature',
            'operationId': 'deleteCollectionFeature',
            'tags': ['collections'],
            'parameters': [
                copy.deepcopy(_COLLECTION_ID_PARAM_REF),
                copy.deepcopy(_FEATURE_ID_PARAM),
            ],
            'responses': {
                '204': {'description': 'Feature deleted successfully'},
                **copy.deepcopy(_STD_RESPONSES),
            },
        }

    return openapi


def _group_collections_tag(openapi: dict) -> dict:
    """
    Ensure every path under ``/collections`` uses the ``collections`` tag.

    pygeoapi places the ``/collections`` list endpoint under a different tag
    by default.  This function overrides all ``/collections*`` operations to
    use ``collections`` so that Swagger UI groups them together under one
    section.  Unused tag definitions are pruned and a ``collections`` tag
    entry is created if one does not already exist.

    :param openapi: OpenAPI dict (after ``_add_write_operations``)
    :type openapi: dict
    :returns: OpenAPI dict with unified tag grouping (mutated in place and
        returned)
    :rtype: dict
    """
    for path, item in openapi.get('paths', {}).items():
        if not path.startswith('/collections'):
            continue
        for operation in item.values():
            if isinstance(operation, dict):
                operation['tags'] = ['collections']

    # Keep the 'collections' tag definition; remove any now-empty tag entries.
    used_tags = {'collections'}
    for item in openapi.get('paths', {}).values():
        for operation in item.values():
            if isinstance(operation, dict):
                used_tags.update(operation.get('tags', []))

    if 'tags' in openapi:
        openapi['tags'] = [
            t for t in openapi['tags'] if t.get('name') in used_tags
        ]
        if not any(t.get('name') == 'collections' for t in openapi['tags']):
            openapi['tags'].insert(0, {'name': 'collections'})

    return openapi


class Command(BaseCommand):
    help = 'Generate pygeoapi OpenAPI document from pygeoapi-config.yml'

    def handle(self, *args, **options):
        import json
        import os
        import tempfile
        import yaml
        from pygeoapi.openapi import get_oas

        # get_oas() instantiates the provider to inspect its schema, so we
        # give it a GeoJSON file provider backed by a temp file — no DB needed.
        geojson = {
            'type': 'FeatureCollection',
            'features': [{
                'type': 'Feature',
                'id': '1',
                'geometry': {'type': 'Point', 'coordinates': [0, 0]},
                'properties': {'id': 1},
            }],
        }
        with tempfile.NamedTemporaryFile(
            mode='w', suffix='.geojson', delete=False
        ) as tmp:
            json.dump(geojson, tmp)
            tmp_path = tmp.name

        try:
            template_resource = {
                'type': 'collection',
                'title': {'en': 'Collection'},
                'description': {'en': 'A feature collection'},
                'keywords': {'en': ['geospatial']},
                'links': [],
                'extents': {
                    'spatial': {
                        'bbox': [-180, -90, 180, 90],
                        'crs': 'http://www.opengis.net/def/crs/OGC/1.3/CRS84',
                    }
                },
                'providers': [{
                    'type': 'feature',
                    'name': 'GeoJSON',
                    'data': tmp_path,
                    'id_field': 'id',
                }],
            }
            config = copy.deepcopy(settings.PYGEOAPI_CONFIG)
            config['resources'] = {_TEMPLATE_COLLECTION_ID: template_resource}
            openapi_path = settings.PYGEOAPI_OPENAPI

            openapi = _group_collections_tag(
                _add_write_operations(
                    _parameterize_collection_ids(
                        _filter_openapi(get_oas(config))
                    )
                )
            )
        finally:
            os.unlink(tmp_path)

        with open(openapi_path, 'w') as f:
            yaml.dump(openapi, f, default_flow_style=False, allow_unicode=True)

        self.stdout.write(
            self.style.SUCCESS(f'OpenAPI document written to: {openapi_path}')
        )