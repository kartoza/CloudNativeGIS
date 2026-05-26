# coding=utf-8
# SPDX-FileCopyrightText: 2024 Kartoza <info@kartoza.com>
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Utilities for building pygeoapi config from Django Layer model."""

import copy
import logging

logger = logging.getLogger(__name__)


_ID_FIELD_CANDIDATES = ('id', 'ogc_fid', 'fid', 'gid')


def _detect_id_field(layer):
    """
    Return the first available id_field candidate from the layer table.
    Falls back to the first non-geometry attribute, or None if table is empty.
    """
    from cloud_native_gis.utils.connection import fields
    col_names = [
        f.name for f in fields(layer.schema_name, layer.table_name)
        if f.name.lower() != 'geometry'
    ]
    for candidate in _ID_FIELD_CANDIDATES:
        if candidate in col_names:
            return candidate
    return col_names[0] if col_names else 'id'


def _layer_to_resource(layer, db_settings):
    """Build a pygeoapi collection resource dict from a Layer instance."""
    return {
        'type': 'collection',
        'title': {'en': layer.name},
        'description': {'en': layer.abstract or layer.name},
        'keywords': {'en': ['geospatial', 'cloudnative-gis']},
        'links': [],
        'extents': {
            'spatial': {
                'bbox': [-180, -90, 180, 90],
                'crs': 'http://www.opengis.net/def/crs/OGC/1.3/CRS84',
            }
        },
        'providers': [{
            'type': 'feature',
            'name': 'PostgreSQL',
            'data': {
                'host': db_settings['HOST'] or 'localhost',
                'port': int(db_settings.get('PORT') or 5432),
                'dbname': db_settings['NAME'],
                'user': db_settings['USER'],
                'password': db_settings['PASSWORD'],
                'search_path': [layer.schema_name],
            },
            'id_field': _detect_id_field(layer),
            'table': layer.table_name,
            'geom_field': 'geometry',
        }],
    }


def refresh_pygeoapi_config():
    """
    Rebuild settings.PYGEOAPI_CONFIG resources from all ready Layer objects.

    Safe to call at any time — failures are caught and logged so a missing
    table or DB error never crashes the server.
    """
    from django.conf import settings
    from django.db import connection

    try:
        from cloud_native_gis.models.layer import Layer

        db_settings = connection.settings_dict
        resources = {}

        for layer in Layer.objects.filter(is_ready=True):
            resource_id = str(layer.unique_id).replace('-', '_')
            resources[resource_id] = _layer_to_resource(layer, db_settings)

        config = copy.deepcopy(settings.PYGEOAPI_CONFIG)
        config['resources'] = resources
        settings.PYGEOAPI_CONFIG = config

    except Exception as exc:
        logger.warning('Could not refresh pygeoapi config: %s', exc)
