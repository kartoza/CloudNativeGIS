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
from cloud_native_gis.models.layer_download import DownloadStatus
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

    def test_list_downloads(self):
        """Test listing user's downloads."""
        # Create a download
        layer_download = LayerDownload.export_layer(
            self.user,
            self.layer,
            FileType.GEOJSON,
            self.working_dir
        )

        # Get list
        url = reverse('cloud-native-gis-download-list')
        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertEqual(data['count'], 1)
        self.assertEqual(
            data['results'][0]['unique_id'],
            str(layer_download.unique_id)
        )

    def test_retrieve_download(self):
        """Test retrieving a specific download."""
        # Create a download
        layer_download = LayerDownload.export_layer(
            self.user,
            self.layer,
            FileType.GEOJSON,
            self.working_dir
        )

        # Get detail
        url = reverse(
            'cloud-native-gis-download-detail',
            kwargs={'id': layer_download.id}
        )
        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertEqual(data['unique_id'], str(layer_download.unique_id))
        self.assertEqual(data['file_type'], FileType.GEOJSON)
        self.assertEqual(data['layer_name'], self.layer.name)

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
            'cloud-native-gis-download-download-file',
            kwargs={'id': layer_download.id}
        )
        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.has_header('Content-Disposition'))

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
            'cloud-native-gis-download-download-file',
            kwargs={'id': layer_download.id}
        )
        response = self.client.get(url)

        self.assertEqual(response.status_code, 400)
        data = json.loads(response.content)
        self.assertIn('error', data)

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
            'cloud-native-gis-download-download-file',
            kwargs={'id': layer_download.id}
        )
        response = self.client.get(url)

        self.assertEqual(response.status_code, 403)

    def test_create_download_sync(self):
        """Test creating a synchronous download via API."""
        url = reverse(
            'cloud-native-gis-layer-download-create-download',
            kwargs={'layer_id': self.layer.id}
        )
        data = {
            'file_type': FileType.GEOJSON,
            'async': False
        }
        response = self.client.post(url, data, format='json')

        self.assertEqual(response.status_code, 200)
        result = json.loads(response.content)
        self.assertIn('download', result)
        self.assertEqual(
            result['download']['status'],
            DownloadStatus.SUCCESS
        )
        self.assertTrue(result['download']['is_ready'])

    def test_create_download_async(self):
        """Test creating an async download via API."""
        url = reverse(
            'cloud-native-gis-layer-download-create-download',
            kwargs={'layer_id': self.layer.id}
        )
        data = {
            'file_type': FileType.SHAPEFILE,
            'async': True
        }
        response = self.client.post(url, data, format='json')

        self.assertEqual(response.status_code, 200)
        result = json.loads(response.content)
        self.assertIn('download', result)
        self.assertIsNotNone(result['download']['task_id'])

    def test_create_download_invalid_file_type(self):
        """Test creating download with invalid file type."""
        url = reverse(
            'cloud-native-gis-layer-download-create-download',
            kwargs={'layer_id': self.layer.id}
        )
        data = {
            'file_type': 'invalid_type',
            'async': False
        }
        response = self.client.post(url, data, format='json')

        self.assertEqual(response.status_code, 400)
        result = json.loads(response.content)
        self.assertIn('error', result)

    def test_list_layer_downloads(self):
        """Test listing downloads for a specific layer."""
        # Create downloads
        LayerDownload.export_layer(
            self.user,
            self.layer,
            FileType.GEOJSON,
            self.working_dir
        )
        LayerDownload.export_layer(
            self.user,
            self.layer,
            FileType.SHAPEFILE,
            self.working_dir
        )

        # Get list
        url = reverse(
            'cloud-native-gis-layer-download-list',
            kwargs={'layer_id': self.layer.id}
        )
        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertEqual(data['count'], 2)