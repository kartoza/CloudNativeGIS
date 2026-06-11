# coding=utf-8
# SPDX-FileCopyrightText: 2024 Kartoza <info@kartoza.com>
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Cloud Native GIS."""

import os
import shutil
import uuid

from django.test import TestCase

from cloud_native_gis.models import (
    Layer, LayerUpload,
    UploadStatus
)
from cloud_native_gis.tests.model_factories import create_user
from cloud_native_gis.utils.connection import count_features
from cloud_native_gis.utils.main import ABS_PATH
from cloud_native_gis.utils.type import FileType


class TestLayerModel(TestCase):
    """Test class for layer models."""

    def setUp(self):
        """To setup test."""
        self.user = create_user()

    def test_export_layer(self):
        filepath = ABS_PATH(
            'cloud_native_gis', 'tests', '_fixtures',
            'capital_cities.zip'
        )

        layer = Layer.objects.create(
            unique_id=uuid.uuid4(),
            name='Test Layer',
            created_by=self.user
        )
        layer_upload = LayerUpload.objects.create(
            layer=layer,
            created_by=self.user
        )
        # copy to folder data
        layer_upload.emptying_folder()
        shutil.copy(filepath, layer_upload.folder)
        # import shapefile
        layer_upload.import_data()

        # assert layer
        layer.refresh_from_db()
        layer_upload.refresh_from_db()

        self.assertEqual(layer_upload.status, UploadStatus.SUCCESS)
        self.assertEqual(
            layer.attribute_names, ['CITY_NAME', 'CITY_TYPE', 'COUNTRY', 'id']
        )
        # Check count features
        self.assertEqual(
            count_features(layer.schema_name, layer.table_name),
            layer.metadata['FEATURE COUNT']
        )

        # try export
        export_path, msg = layer.export_layer(
            FileType.SHAPEFILE, '/tmp', f'{str(layer.unique_id)}.shp'
        )
        self.assertIsNotNone(export_path)
        self.assertEqual(
            export_path,
            os.path.join('/tmp', f'{str(layer.unique_id)}.zip')
        )
        self.assertEqual(msg, 'Success')

        os.remove(export_path)

        layer.delete()
        self.assertFalse(os.path.exists(layer_upload.folder))

    def _create_imported_layer(self):
        """Create a layer with imported data and return (layer, layer_upload)."""
        filepath = ABS_PATH(
            'cloud_native_gis', 'tests', '_fixtures',
            'capital_cities.zip'
        )
        layer = Layer.objects.create(
            unique_id=uuid.uuid4(),
            name='Test Layer',
            created_by=self.user
        )
        layer_upload = LayerUpload.objects.create(
            layer=layer,
            created_by=self.user
        )
        layer_upload.emptying_folder()
        shutil.copy(filepath, layer_upload.folder)
        layer_upload.import_data()
        layer.refresh_from_db()
        return layer, layer_upload

    def test_reset_attributes_includes_id(self):
        """reset_attributes should preserve the id attribute."""
        layer, _ = self._create_imported_layer()

        layer.reset_attributes()

        self.assertIn('id', layer.attribute_names)

        layer.delete()

    def _assert_id_sequence(self, layer):
        """Assert id column has a nextval DEFAULT and returns an integer on bare INSERT."""
        from django.db import connection
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT column_default
                FROM information_schema.columns
                WHERE table_schema = %s
                  AND table_name = %s
                  AND column_name = 'id'
                """,
                [layer.schema_name, layer.table_name],
            )
            row = cursor.fetchone()
        self.assertIsNotNone(row, 'id column not found')
        self.assertIsNotNone(row[0], 'id column has no DEFAULT')
        self.assertIn('nextval', row[0], 'DEFAULT is not a sequence nextval')

        with connection.cursor() as cursor:
            cursor.execute(
                f'INSERT INTO {layer.query_table_name} (geometry) '
                f"VALUES (ST_GeomFromText('POINT(0 0)', 4326)) "
                f'RETURNING id'
            )
            returned_id = cursor.fetchone()[0]
        self.assertIsNotNone(returned_id)
        self.assertIsInstance(returned_id, int)

    def test_add_id_new_column_creates_sequence(self):
        """add_id on a layer without an id column adds id and attaches a sequence."""
        layer, _ = self._create_imported_layer()
        # capital_cities has no id in source; add_id() was called by import_data
        self._assert_id_sequence(layer)
        layer.delete()

    def test_assign_extent_populates_field(self):
        """assign_extent should store [xmin, ymin, xmax, ymax] in EPSG:4326."""
        layer, _ = self._create_imported_layer()

        layer.extent = None
        layer.save(update_fields=['extent'])
        layer.assign_extent()
        layer.refresh_from_db()

        self.assertIsNotNone(layer.extent)
        self.assertEqual(len(layer.extent), 4)
        xmin, ymin, xmax, ymax = layer.extent
        self.assertLess(xmin, xmax)
        self.assertLess(ymin, ymax)
        # capital_cities is world data — bounds must be within WGS84 range
        self.assertGreaterEqual(xmin, -180)
        self.assertLessEqual(xmax, 180)
        self.assertGreaterEqual(ymin, -90)
        self.assertLessEqual(ymax, 90)

        layer.delete()

    def test_import_data_sets_extent(self):
        """import_data should automatically populate the extent field."""
        layer, _ = self._create_imported_layer()

        self.assertIsNotNone(layer.extent)
        self.assertEqual(len(layer.extent), 4)

        layer.delete()
