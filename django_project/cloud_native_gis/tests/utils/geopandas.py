# coding=utf-8
"""Cloud Native GIS."""

import uuid

from django.test import TransactionTestCase
from psycopg2.errors import InvalidParameterValue, UndefinedColumn

from cloud_native_gis.models import Layer
from cloud_native_gis.tests.model_factories import create_user
from cloud_native_gis.utils.connection import get_features
from cloud_native_gis.utils.geopandas import geojson_to_geopanda, Mode


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
