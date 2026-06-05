# SPDX-FileCopyrightText: 2024 Kartoza <info@kartoza.com>
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Cloud Native GIS.

.. note:: Context Layer App.
"""

from __future__ import absolute_import, unicode_literals

from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class ContextLayerConfig(AppConfig):
    """Context Layer Config App."""

    name = 'cloud_native_gis'
    verbose_name = _('Cloud Native Layer')

    def ready(self):
        _patch_pygeoapi_sql_provider()


def _patch_pygeoapi_sql_provider():
    """Patch pygeoapi GenericSQLProvider._feature_to_sqlalchemy.

    OGC:CRS84 has no EPSG code, so pyproj's .to_epsg() returns None for it.
    The upstream method passes that None as the SRID to geoalchemy2's
    from_shape(), which then fails with a TypeError when formatting the EWKT
    string.  We fallback to SRID 4326 — safe because CRS84 and EPSG:4326
    share the same WGS84 datum; SRID is only a PostGIS metadata label and
    does not transform the coordinate values.
    """
    try:
        import pyproj
        import shapely.geometry
        from geoalchemy2.shape import from_shape
        from pygeoapi.provider.sql import GenericSQLProvider
        from pygeoapi.provider.base import ProviderInvalidDataError
    except ImportError:
        return

    def _feature_to_sqlalchemy(self, json_data, identifier=None):
        attributes = {**json_data['properties']}
        attributes.pop('identifier', None)
        attributes[self.geom] = from_shape(
            shapely.geometry.shape(json_data['geometry']),
            srid=pyproj.CRS.from_user_input(self.storage_crs).to_epsg() or 4326
        )
        attributes[self.id_field] = identifier
        try:
            return self.table_model(**attributes)
        except Exception as e:
            raise ProviderInvalidDataError(str(e))

    GenericSQLProvider._feature_to_sqlalchemy = _feature_to_sqlalchemy
