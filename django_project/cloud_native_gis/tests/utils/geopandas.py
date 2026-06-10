# coding=utf-8
# SPDX-FileCopyrightText: 2024 Kartoza <info@kartoza.com>
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Cloud Native GIS."""

import uuid

from django.db import connection
from django.test import TransactionTestCase
from psycopg2.errors import InvalidParameterValue, UndefinedColumn

from cloud_native_gis.models import Layer
from cloud_native_gis.tests.model_factories import create_user
from cloud_native_gis.utils.connection import get_features
from cloud_native_gis.utils.geopandas import (
    create_id_field, geojson_to_geopanda, geopanda_to_postgis, Mode
)


class TestGeopandas(TransactionTestCase):
    """Test class for Geopandas utility functions."""

    def setUp(self):
        """To setup test."""
        self.user = create_user()

    def test_geojson_injection(self):
        """Test validate shapefile."""
        layer = Layer.objects.create(
            unique_id=uuid.uuid4(),
            name='Test Layer',
            created_by=self.user
        )
        with self.assertRaises(KeyError):
            geojson_to_geopanda(
                {}, layer.schema_name, layer.table_name
            )

        geojson_to_geopanda(
            {
                "type": "FeatureCollection",
                "features": [
                    {
                        "type": "Feature",
                        "properties": {
                            "id": 1,
                            "name": "Alice's Home",
                            "category": "residence"
                        },
                        "geometry": {
                            "type": "Point",
                            "coordinates": [
                                106.827153,
                                -6.17511
                            ]
                        }
                    }
                ]
            }, layer.schema_name, layer.table_name
        )
        layer.reset_attributes()
        features = get_features(layer.schema_name, layer.table_name)
        self.assertEqual(len(features), 1)
        self.assertEqual(features[0][1], 1)
        self.assertEqual(features[0][2], "Alice's Home")
        self.assertEqual(features[0][3], "residence")

        with self.assertRaises(InvalidParameterValue):
            geojson_to_geopanda(
                {
                    "type": "FeatureCollection",
                    "features": [
                        {
                            "type": "Feature",
                            "properties": {
                                "id": 10,
                                "name": "New shop",
                                "category": "shop"
                            },
                            "geometry": {
                                "type": "Polygon",
                                "coordinates": [
                                    [
                                        [0, 0],
                                        [0, 1],
                                        [1, 1],
                                        [1, 0],
                                        [0, 0]
                                    ]
                                ]
                            }
                        }
                    ]
                }, layer.schema_name, layer.table_name,
                mode=Mode.APPEND
            )
        with self.assertRaises(UndefinedColumn):
            geojson_to_geopanda(
                {
                    "type": "FeatureCollection",
                    "features": [
                        {
                            "type": "Feature",
                            "properties": {
                                "id": 10,
                                "name": "New shop",
                                "category": "shop",
                                "new_field": "new_field"
                            },
                            "geometry": {
                                "type": "Point",
                                "coordinates": [
                                    106.827153,
                                    -6.17511
                                ]
                            }
                        }
                    ]
                }, layer.schema_name, layer.table_name,
                mode=Mode.APPEND
            )

        self.assertEqual(
            ['category', 'id', 'name'], layer.attribute_names
        )
        ids = list(
            layer.layerattributes_set.values_list('id', flat=True)
        )
        # Replace
        geojson_to_geopanda(
            {
                "type": "FeatureCollection",
                "features": [
                    {
                        "type": "Feature",
                        "properties": {
                            "id": 10,
                            "name": "New shop",
                            "category": "shop"
                        },
                        "geometry": {
                            "type": "Point",
                            "coordinates": [
                                106.827153,
                                -6.17511
                            ]
                        }
                    }
                ]
            }, layer.schema_name, layer.table_name
        )
        layer.reset_attributes()
        self.assertEqual(
            ['category', 'id', 'name'], layer.attribute_names
        )
        new_ids = list(
            layer.layerattributes_set.values_list('id', flat=True)
        )
        self.assertEqual(ids, new_ids)

        # Replace with different attributes
        geojson_to_geopanda(
            {
                "type": "FeatureCollection",
                "features": [
                    {
                        "type": "Feature",
                        "properties": {
                            "id": 10,
                            "name": "New shop",
                            "category": "shop",
                            "new_field": "value"
                        },
                        "geometry": {
                            "type": "Point",
                            "coordinates": [
                                106.827153,
                                -6.17511
                            ]
                        }
                    }
                ]
            }, layer.schema_name, layer.table_name
        )
        layer.reset_attributes()
        self.assertEqual(
            ['category', 'id', 'name', 'new_field'],
            layer.attribute_names
        )
        new_ids = list(
            layer.layerattributes_set.values_list('id', flat=True)
        )
        self.assertNotEqual(ids, new_ids)

        features = get_features(layer.schema_name, layer.table_name)
        self.assertEqual(len(features), 1)
        self.assertEqual(features[0][1], 10)
        self.assertEqual(features[0][2], 'New shop')
        self.assertEqual(features[0][3], 'shop')

        geojson_to_geopanda(
            {
                "type": "FeatureCollection",
                "features": [
                    {
                        "type": "Feature",
                        "properties": {
                            "id": 1,
                            "name": "Alice's Home",
                            "category": "residence"
                        },
                        "geometry": {
                            "type": "Point",
                            "coordinates": [
                                106.827153,
                                -6.17511
                            ]
                        }
                    }
                ]
            }, layer.schema_name, layer.table_name,
            mode=Mode.APPEND
        )
        features = get_features(layer.schema_name, layer.table_name)
        self.assertEqual(len(features), 2)
        self.assertEqual(features[0][1], 10)
        self.assertEqual(features[0][2], 'New shop')
        self.assertEqual(features[0][3], 'shop')
        self.assertEqual(features[1][1], 1)
        self.assertEqual(features[1][2], "Alice's Home")
        self.assertEqual(features[1][3], "residence")


class TestGeopandaToPostgisIdValidation(TransactionTestCase):
    """Test id column validation in geopanda_to_postgis."""

    def setUp(self):
        self.user = create_user()
        self.layer = Layer.objects.create(
            unique_id=uuid.uuid4(),
            name='Id Validation Test',
            created_by=self.user,
        )

    def tearDown(self):
        self.layer.delete()

    def _make_gdf(self, id_value):
        import geopandas as gpd
        import pandas as pd
        from shapely.geometry import Point
        return gpd.GeoDataFrame(
            {'id': [id_value], 'name': ['Test']},
            geometry=[Point(106.8, -6.2)],
            crs='EPSG:4326'
        )

    def test_string_id_raises_value_error(self):
        """geopanda_to_postgis raises ValueError when id is a string."""
        gdf = self._make_gdf('SOM')
        with self.assertRaises(ValueError) as ctx:
            geopanda_to_postgis(
                gdf, self.layer.table_name, self.layer.schema_name
            )
        self.assertIn("'id'", str(ctx.exception))
        self.assertIn('integer', str(ctx.exception))

    def test_float_id_raises_value_error(self):
        """geopanda_to_postgis raises ValueError when id is a float."""
        import geopandas as gpd
        import pandas as pd
        from shapely.geometry import Point
        gdf = gpd.GeoDataFrame(
            {'id': [1.5], 'name': ['Test']},
            geometry=[Point(106.8, -6.2)],
            crs='EPSG:4326'
        )
        with self.assertRaises(ValueError):
            geopanda_to_postgis(
                gdf, self.layer.table_name, self.layer.schema_name
            )

    def test_integer_id_succeeds(self):
        """geopanda_to_postgis accepts an integer id column."""
        import geopandas as gpd
        from shapely.geometry import Point
        gdf = gpd.GeoDataFrame(
            {'id': [1], 'name': ['Test']},
            geometry=[Point(106.8, -6.2)],
            crs='EPSG:4326'
        )
        geopanda_to_postgis(
            gdf, self.layer.table_name, self.layer.schema_name
        )

    def test_no_id_column_succeeds(self):
        """geopanda_to_postgis works fine when there is no id column."""
        import geopandas as gpd
        from shapely.geometry import Point
        gdf = gpd.GeoDataFrame(
            {'name': ['Test']},
            geometry=[Point(106.8, -6.2)],
            crs='EPSG:4326'
        )
        geopanda_to_postgis(
            gdf, self.layer.table_name, self.layer.schema_name
        )

    def test_geojson_string_id_raises_value_error(self):
        """geojson_to_geopanda raises ValueError when id is a string."""
        with self.assertRaises(ValueError):
            geojson_to_geopanda(
                {
                    'type': 'FeatureCollection',
                    'features': [{
                        'type': 'Feature',
                        'properties': {'id': 'SOM', 'name': 'Somalia'},
                        'geometry': {
                            'type': 'Point',
                            'coordinates': [46.0, 6.0]
                        }
                    }]
                },
                self.layer.schema_name, self.layer.table_name
            )


class TestCreateIdField(TransactionTestCase):
    """Test create_id_field utility."""

    def setUp(self):
        self.user = create_user()
        self.layer = Layer.objects.create(
            unique_id=uuid.uuid4(),
            name='Id Field Test',
            created_by=self.user,
        )
        with connection.cursor() as cursor:
            cursor.execute(
                f'CREATE SCHEMA IF NOT EXISTS {self.layer.schema_name}'
            )
            cursor.execute(
                f'CREATE TABLE {self.layer.query_table_name} ('
                f'  geometry geometry(Geometry, 4326)'
                f')'
            )
            cursor.execute(
                f"INSERT INTO {self.layer.query_table_name} (geometry) "
                f"VALUES (ST_GeomFromText('POINT(1 1)', 4326)), "
                f"       (ST_GeomFromText('POINT(2 2)', 4326))"
            )

    def tearDown(self):
        self.layer.delete()

    def _get_column_default(self):
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT column_default
                FROM information_schema.columns
                WHERE table_schema = %s
                  AND table_name = %s
                  AND column_name = 'id'
                """,
                [self.layer.schema_name, self.layer.table_name],
            )
            row = cursor.fetchone()
        return row[0] if row else None

    def test_creates_id_column_when_missing(self):
        """create_id_field adds id column and fills it with row numbers."""
        create_id_field(self.layer.schema_name, self.layer.table_name)

        with connection.cursor() as cursor:
            cursor.execute(
                f'SELECT id FROM {self.layer.query_table_name} ORDER BY id'
            )
            ids = [row[0] for row in cursor.fetchall()]

        self.assertEqual(ids, [1, 2])

    def test_attaches_sequence_as_default(self):
        """create_id_field sets nextval sequence as the id column DEFAULT."""
        create_id_field(self.layer.schema_name, self.layer.table_name)

        default = self._get_column_default()
        self.assertIsNotNone(default)
        self.assertIn('nextval', default)

    def test_sequence_continues_from_max_id(self):
        """Inserting after create_id_field uses the next sequence value."""
        create_id_field(self.layer.schema_name, self.layer.table_name)

        with connection.cursor() as cursor:
            cursor.execute(
                f'INSERT INTO {self.layer.query_table_name} (geometry) '
                f"VALUES (ST_GeomFromText('POINT(3 3)', 4326)) RETURNING id"
            )
            new_id = cursor.fetchone()[0]

        self.assertEqual(new_id, 3)

    def test_idempotent_on_existing_id_column(self):
        """create_id_field does not overwrite existing id values."""
        with connection.cursor() as cursor:
            cursor.execute(
                f'ALTER TABLE {self.layer.query_table_name} ADD COLUMN id INTEGER'
            )
            cursor.execute(
                f'UPDATE {self.layer.query_table_name} t '
                f'SET id = sub.rn '
                f'FROM (SELECT ctid, ROW_NUMBER() OVER () AS rn '
                f'      FROM {self.layer.query_table_name}) sub '
                f'WHERE t.ctid = sub.ctid'
            )

        create_id_field(self.layer.schema_name, self.layer.table_name)

        with connection.cursor() as cursor:
            cursor.execute(
                f'SELECT id FROM {self.layer.query_table_name} ORDER BY id'
            )
            ids = [row[0] for row in cursor.fetchall()]

        self.assertEqual(ids, [1, 2])
        self.assertIn('nextval', self._get_column_default())
