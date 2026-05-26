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
    """Remove unused OGC API paths and their tags from the OpenAPI document."""
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
    Replace hardcoded collection IDs in paths with a {collectionId} parameter.

    pygeoapi generates one path entry per layer (e.g. /collections/uuid_a/items,
    /collections/uuid_b/items). This function collapses them into a single
    parameterised path (/collections/{collectionId}/items) so Swagger UI shows
    one entry per endpoint pattern instead of one per layer.
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


def _group_collections_tag(openapi: dict) -> dict:
    """
    Ensure every path under /collections uses the 'collections' tag so that
    Swagger UI groups them together, including the /collections list endpoint
    which pygeoapi places under a different tag by default.
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
                _parameterize_collection_ids(
                    _filter_openapi(get_oas(config))
                )
            )
        finally:
            os.unlink(tmp_path)

        with open(openapi_path, 'w') as f:
            yaml.dump(openapi, f, default_flow_style=False, allow_unicode=True)

        self.stdout.write(
            self.style.SUCCESS(f'OpenAPI document written to: {openapi_path}')
        )