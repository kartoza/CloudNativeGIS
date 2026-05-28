# coding=utf-8
# SPDX-FileCopyrightText: 2024 Kartoza <info@kartoza.com>
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Cloud Native GIS."""

import os
import uuid
from django.test import TestCase
import shutil

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
