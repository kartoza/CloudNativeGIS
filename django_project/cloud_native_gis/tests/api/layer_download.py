# coding=utf-8
"""Cloud Native GIS."""

import json
import os
import shutil
import tempfile
import uuid

from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient

from cloud_native_gis.models import Layer, LayerDownload, LayerUpload
from cloud_native_gis.tests.model_factories import create_user
from cloud_native_gis.utils.main import ABS_PATH
from cloud_native_gis.utils.type import FileType


class TestLayerDownloadAPI(TestCase):
    """Test class for LayerDownload API."""

    def setUp(self):
        """Set up test."""
        self.client = APIClient()
        self.user = create_user()
        self.other_user = create_user(username='other_user')
        self.client.force_authenticate(user=self.user)
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

    def test_download_file_success(self):
        """Test downloading a ready file."""
        # Create and run download
        layer_download = LayerDownload.export_layer(
            self.user,
            self.layer,
            FileType.GEOJSON,
            self.working_dir
        )
        layer_download.run()

        # Download file
        url = reverse(
            'download-file',
            kwargs={'unique_id': layer_download.unique_id}
        )
        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.has_header('Content-Disposition'))
        self.assertIn(
            f'{self.layer.name}.geojson',
            response['Content-Disposition']
        )

    def test_download_file_not_ready(self):
        """Test downloading a file that's not ready."""
        # Create download without running it
        layer_download = LayerDownload.export_layer(
            self.user,
            self.layer,
            FileType.GEOJSON,
            self.working_dir
        )

        # Try to download
        url = reverse(
            'download-file',
            kwargs={'unique_id': layer_download.unique_id}
        )
        response = self.client.get(url)

        self.assertEqual(response.status_code, 400)
        data = json.loads(response.content)
        self.assertIn('error', data)
        self.assertEqual(data['error'], 'Download is not ready yet.')

    def test_download_file_permission_denied(self):
        """Test downloading someone else's file."""
        # Create download as user
        layer_download = LayerDownload.export_layer(
            self.user,
            self.layer,
            FileType.GEOJSON,
            self.working_dir
        )
        layer_download.run()

        # Try to download as other user
        self.client.force_authenticate(user=self.other_user)
        url = reverse(
            'download-file',
            kwargs={'unique_id': layer_download.unique_id}
        )
        response = self.client.get(url)

        self.assertEqual(response.status_code, 403)

    def test_download_file_not_found(self):
        """Test downloading a non-existent file."""
        # Try to download with invalid UUID
        url = reverse(
            'download-file',
            kwargs={'unique_id': uuid.uuid4()}
        )
        response = self.client.get(url)

        self.assertEqual(response.status_code, 404)

    def test_download_different_file_types(self):
        """Test downloading different file types."""
        file_types = [
            (FileType.GEOJSON, '.geojson'),
            (FileType.SHAPEFILE, '.zip'),
            (FileType.GEOPACKAGE, '.gpkg'),
            (FileType.KML, '.kml'),
        ]

        for file_type, extension in file_types:
            # Create and run download
            layer_download = LayerDownload.export_layer(
                self.user,
                self.layer,
                file_type,
                self.working_dir
            )
            layer_download.run()

            # Download file
            url = reverse(
                'download-file',
                kwargs={'unique_id': layer_download.unique_id}
            )
            response = self.client.get(url)

            self.assertEqual(response.status_code, 200)
            self.assertIn(
                f'{self.layer.name}{extension}',
                response['Content-Disposition']
            )