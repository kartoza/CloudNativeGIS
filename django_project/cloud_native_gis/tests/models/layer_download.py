# coding=utf-8
"""Cloud Native GIS."""

import os
import shutil
import tempfile
import uuid

from django.test import TestCase

from cloud_native_gis.models import (
    Layer, LayerDownload, LayerUpload
)
from cloud_native_gis.models.layer_download import DownloadStatus
from cloud_native_gis.tests.model_factories import create_user
from cloud_native_gis.utils.main import ABS_PATH
from cloud_native_gis.utils.type import FileType


class TestLayerDownloadModel(TestCase):
    """Test class for LayerDownload model."""

    def setUp(self):
        """Set up test."""
        self.user = create_user()
        self.working_dir = tempfile.mkdtemp()

        # Create a test layer with data
        filepath = ABS_PATH(
            'cloud_native_gis', 'tests', '_fixtures',
            'capital_cities.zip'
        )

        self.layer = Layer.objects.create(
            unique_id=uuid.uuid4(),
            name='Test Layer',
            created_by=self.user
        )
        self.layer_upload = LayerUpload.objects.create(
            layer=self.layer,
            created_by=self.user
        )
        # Copy to folder data
        self.layer_upload.emptying_folder()
        shutil.copy(filepath, self.layer_upload.folder)
        # Import shapefile
        self.layer_upload.import_data()

        # Refresh to get updated status
        self.layer.refresh_from_db()
        self.layer_upload.refresh_from_db()

    def tearDown(self):
        """Clean up after test."""
        # Clean up working directory
        if os.path.exists(self.working_dir):
            shutil.rmtree(self.working_dir)

        # Clean up layer (will cascade delete upload)
        self.layer.delete()

    def test_export_layer_static_method(self):
        """Test the export_layer static method."""
        layer_download = LayerDownload.export_layer(
            self.user,
            self.layer,
            FileType.GEOJSON,
            self.working_dir
        )

        self.assertIsNotNone(layer_download)
        self.assertEqual(layer_download.created_by, self.user)
        self.assertEqual(layer_download.layer, self.layer)
        self.assertEqual(layer_download.file_type, FileType.GEOJSON)
        self.assertEqual(layer_download.working_dir, self.working_dir)
        self.assertEqual(layer_download.status, DownloadStatus.START)

    def test_download_original_file_success(self):
        """Test downloading original file."""
        layer_download = LayerDownload.export_layer(
            self.user,
            self.layer,
            FileType.ORIGINAL,
            self.working_dir
        )

        # Run the download
        layer_download.run()

        # Refresh from database
        layer_download.refresh_from_db()

        # Assert success
        self.assertEqual(layer_download.status, DownloadStatus.SUCCESS)
        self.assertIsNotNone(layer_download.path)
        self.assertTrue(os.path.exists(layer_download.path))
        self.assertTrue(
            layer_download.path.endswith('.zip') or
            os.path.isdir(layer_download.path)
        )

    def test_download_geojson_success(self):
        """Test downloading layer as GeoJSON."""
        layer_download = LayerDownload.export_layer(
            self.user,
            self.layer,
            FileType.GEOJSON,
            self.working_dir
        )

        # Run the download
        layer_download.run()

        # Refresh from database
        layer_download.refresh_from_db()

        # Assert success
        self.assertEqual(layer_download.status, DownloadStatus.SUCCESS)
        self.assertIsNotNone(layer_download.path)
        self.assertTrue(os.path.exists(layer_download.path))
        self.assertTrue(layer_download.path.endswith('.geojson'))

    def test_download_shapefile_success(self):
        """Test downloading layer as Shapefile."""
        layer_download = LayerDownload.export_layer(
            self.user,
            self.layer,
            FileType.SHAPEFILE,
            self.working_dir
        )

        # Run the download
        layer_download.run()

        # Refresh from database
        layer_download.refresh_from_db()

        # Assert success
        self.assertEqual(layer_download.status, DownloadStatus.SUCCESS)
        self.assertIsNotNone(layer_download.path)
        self.assertTrue(os.path.exists(layer_download.path))
        self.assertTrue(layer_download.path.endswith('.zip'))

    def test_download_geopackage_success(self):
        """Test downloading layer as GeoPackage."""
        layer_download = LayerDownload.export_layer(
            self.user,
            self.layer,
            FileType.GEOPACKAGE,
            self.working_dir
        )

        # Run the download
        layer_download.run()

        # Refresh from database
        layer_download.refresh_from_db()

        # Assert success
        self.assertEqual(layer_download.status, DownloadStatus.SUCCESS)
        self.assertIsNotNone(layer_download.path)
        self.assertTrue(os.path.exists(layer_download.path))
        self.assertTrue(layer_download.path.endswith('.gpkg'))

    def test_download_kml_success(self):
        """Test downloading layer as KML."""
        layer_download = LayerDownload.export_layer(
            self.user,
            self.layer,
            FileType.KML,
            self.working_dir
        )

        # Run the download
        layer_download.run()

        # Refresh from database
        layer_download.refresh_from_db()

        # Assert success
        self.assertEqual(layer_download.status, DownloadStatus.SUCCESS)
        self.assertIsNotNone(layer_download.path)
        self.assertTrue(os.path.exists(layer_download.path))
        self.assertTrue(layer_download.path.endswith('.kml'))

    def test_download_original_file_not_found(self):
        """Test downloading original file when it doesn't exist."""
        # Create layer without upload
        layer_no_upload = Layer.objects.create(
            unique_id=uuid.uuid4(),
            name='Layer Without Upload',
            created_by=self.user
        )

        layer_download = LayerDownload.export_layer(
            self.user,
            layer_no_upload,
            FileType.ORIGINAL,
            self.working_dir
        )

        # Run the download
        layer_download.run()

        # Refresh from database
        layer_download.refresh_from_db()

        # Assert failure
        self.assertEqual(layer_download.status, DownloadStatus.FAILED)
        self.assertIsNotNone(layer_download.note)
        self.assertIn('Original file does not found', layer_download.note)

        # Clean up
        layer_no_upload.delete()

    def test_download_status_transitions(self):
        """Test that status transitions work correctly."""
        layer_download = LayerDownload.export_layer(
            self.user,
            self.layer,
            FileType.GEOJSON,
            self.working_dir
        )

        # Initial status should be START
        self.assertEqual(layer_download.status, DownloadStatus.START)

        # Run the download
        layer_download.run()

        # Refresh from database
        layer_download.refresh_from_db()

        # Status should be SUCCESS
        self.assertEqual(layer_download.status, DownloadStatus.SUCCESS)

    def test_unique_id_generated(self):
        """Test that unique_id is automatically generated."""
        layer_download = LayerDownload.export_layer(
            self.user,
            self.layer,
            FileType.GEOJSON,
            self.working_dir
        )

        self.assertIsNotNone(layer_download.unique_id)
        self.assertIsInstance(layer_download.unique_id, uuid.UUID)

    def test_multiple_downloads_for_same_layer(self):
        """Test that multiple downloads can be created for the same layer."""
        download1 = LayerDownload.export_layer(
            self.user,
            self.layer,
            FileType.GEOJSON,
            self.working_dir
        )

        download2 = LayerDownload.export_layer(
            self.user,
            self.layer,
            FileType.SHAPEFILE,
            self.working_dir
        )

        # Both should exist
        self.assertIsNotNone(download1)
        self.assertIsNotNone(download2)

        # They should be different instances
        self.assertNotEqual(download1.id, download2.id)
        self.assertNotEqual(download1.unique_id, download2.unique_id)

        # Both should reference the same layer
        self.assertEqual(download1.layer, download2.layer)