# coding=utf-8
# SPDX-FileCopyrightText: 2024 Kartoza <info@kartoza.com>
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Utilities for building pygeoapi provider config from Django Layer models."""

import copy
import logging

logger = logging.getLogger(__name__)

_ID_FIELD_CANDIDATES = ('id', 'ogc_fid', 'fid', 'gid')


def _detect_id_field(layer):
    """
    Detect the primary-key column name for a layer's PostGIS table.

    Checks ``_ID_FIELD_CANDIDATES`` in order and returns the first match
    found in the table's columns.  Falls back to the first non-geometry
    column when none of the candidates exist.

    :param layer: Layer instance whose table is inspected
    :type layer: cloud_native_gis.models.layer.Layer
    :returns: column name to use as the pygeoapi ``id_field``
    :rtype: str
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
    """
    Build a pygeoapi collection resource dict from a Layer instance.

    The returned dict is suitable for use as a value in the ``resources``
    section of a pygeoapi config.  Write operations (POST / PUT / DELETE)
    are enabled via ``editable: True``.

    :param layer: Layer instance to expose as an OGC API collection
    :type layer: cloud_native_gis.models.layer.Layer
    :param db_settings: Django database settings dict
        (typically ``django.db.connection.settings_dict``)
    :type db_settings: dict
    :returns: pygeoapi resource definition dict
    :rtype: dict
    """
    return {
        'type': 'collection',
        'title': {'en': layer.name},
        'description': {'en': layer.abstract or layer.name},
        'keywords': {'en': ['geospatial', 'cloudnative-gis']},
        'links': [],
        'extents': {
            'spatial': {
                'bbox': [-180, -90, 180, 90],
                'crs': 'http://www.opengis.net/def/crs/EPSG/0/4326',
            }
        },
        'crs': [
            'http://www.opengis.net/def/crs/OGC/1.3/CRS84',
            'http://www.opengis.net/def/crs/EPSG/0/4326',
        ],
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
            'storage_crs': 'http://www.opengis.net/def/crs/EPSG/0/4326',
            'crs': [
                'http://www.opengis.net/def/crs/OGC/1.3/CRS84',
                'http://www.opengis.net/def/crs/EPSG/0/4326',
            ],
            'editable': True,
        }],
    }


def refresh_pygeoapi_config():
    """Rebuild settings.PYGEOAPI_CONFIG resources from all ready Layer objects.

    Iterates over every :class:`~cloud_native_gis.models.layer.Layer` with
    ``is_ready=True`` and replaces the ``resources`` section of
    ``settings.PYGEOAPI_CONFIG`` in-place.

    Safe to call at any time — individual layer failures are caught and logged
    so a missing table or DB error never crashes the server.

    :returns: None
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
