# coding=utf-8
"""Cloud Native GIS."""

import os
import tempfile
import uuid
from django.test import TestCase, RequestFactory
from unittest.mock import patch, MagicMock, mock_open
from django.http import Http404
from django.conf import settings
from django.urls import reverse

from cloud_native_gis.models.layer import Layer, LayerType
from cloud_native_gis.api.pmtile import PMTilesReader, serve_pmtiles
from cloud_native_gis.tests.model_factories import create_user


class TestPMTilesReader(TestCase):
    def setUp(self):
        # Create a temporary file with some test data
        self.temp_dir = tempfile.mkdtemp()
        self.test_file_path = os.path.join(self.temp_dir, 'test.pmtiles')

        # Create test data: 1000 bytes cycling through 0-255
        self.test_data = bytes([i % 256 for i in range(1000)])

        with open(self.test_file_path, 'wb') as f:
            f.write(self.test_data)

        self.reader = PMTilesReader(self.test_file_path)

    def tearDown(self):
        # Clean up
        self.reader.close()
        os.remove(self.test_file_path)
        os.rmdir(self.temp_dir)

    def test_read_range_normal(self):
        """Test reading specific byte ranges within file size."""
        # Test reading first 10 bytes
        data = self.reader.read_range(0, 10)
        self.assertEqual(data, bytes([i % 256 for i in range(10)]))

        # Test reading from middle of file
        data = self.reader.read_range(500, 10)
        self.assertEqual(data, bytes([i % 256 for i in range(500, 510)]))

    def test_read_range_at_end(self):
        """Test reading a range that extends beyond file size."""
        # Try to read 20 bytes from position 990 (file only has 10 more bytes)
        data = self.reader.read_range(990, 20)
        self.assertEqual(data, bytes([i % 256 for i in range(990, 1000)]))
        # Should only return remaining 10 bytes
        self.assertEqual(len(data), 10)

    def test_read_range_exact_size(self):
        """Test reading exactly to the end of file."""
        data = self.reader.read_range(900, 100)
        self.assertEqual(data, bytes([i % 256 for i in range(900, 1000)]))
        self.assertEqual(len(data), 100)

    def test_read_invalid_offset(self):
        """Test reading with invalid offsets."""
        # Test reading with negative offset
        with self.assertRaises(ValueError):
            self.reader.read_range(-1, 10)

        # Test reading with offset beyond file size
        with self.assertRaises(ValueError):
            self.reader.read_range(1001, 10)

    def test_read_all(self):
        """Test reading entire file."""
        data = self.reader.read_all()
        self.assertEqual(data, self.test_data)
        self.assertEqual(len(data), 1000)

    def test_close(self):
        """Test proper cleanup when closing."""
        reader = PMTilesReader(self.test_file_path)
        reader.close()
        self.assertTrue(reader.file.closed)
        self.assertTrue(reader.mmap.closed)

    @patch('mmap.mmap')
    def test_mmap_error_handling(self, mock_mmap):
        """Test handling of mmap errors."""
        mock_mmap.side_effect = OSError("Mock mmap error")
        with self.assertRaises(OSError):
            PMTilesReader(self.test_file_path)


class TestServePMTiles(TestCase):
    def setUp(self):
        self.user = create_user(password='test')
        self.layer_1 = Layer.objects.create(
            name='Test Layer 1',
            created_by=self.user,
            description='Test Layer 1',
            is_ready=True
        )
        # Create a temporary file with some test data
        self.temp_dir = tempfile.mkdtemp()
        self.test_file_path = os.path.join(self.temp_dir, 'test.pmtiles')
        # Create test data: 1000 bytes cycling through 0-255
        self.test_data = bytes([i % 256 for i in range(1000)])

        with open(self.test_file_path, 'wb') as f:
            f.write(self.test_data)

        self.layer_1.pmtile.save('test.pmtiles', open(self.test_file_path, 'rb'))
        self.layer_1.save()
        self.factory = RequestFactory()

    def tearDown(self):
        os.remove(self.test_file_path)
        os.rmdir(self.temp_dir)

    @patch('cloud_native_gis.api.pmtile.os.path.exists')
    @patch('cloud_native_gis.api.pmtile.PMTilesReader')
    def test_file_not_found(self, mock_reader, mock_exists):
        """Test 404 response when file doesn't exist."""
        mock_exists.return_value = False
        layer_uuid = str(uuid.uuid4())
        url = reverse('serve-pmtiles', kwargs={'layer_uuid': layer_uuid})
        request = self.factory.get(url)

        with self.assertRaises(Http404):
            serve_pmtiles(request, layer_uuid)

        layer_uuid = str(self.layer_1.unique_id)
        url = reverse('serve-pmtiles', kwargs={'layer_uuid': layer_uuid})
        request = self.factory.get(url)

        with self.assertRaises(Http404):
            serve_pmtiles(request, layer_uuid)

    @patch('cloud_native_gis.api.pmtile.os.path.exists')
    @patch('cloud_native_gis.api.pmtile.PMTilesReader')
    def test_serve_full_file(self, mock_reader, mock_exists):
        """Test serving entire file when no range header is present."""
        mock_exists.return_value = True

        # Setup mock reader
        mock_reader_instance = MagicMock()
        mock_reader_instance.read_all.return_value = self.test_data
        mock_reader.return_value = mock_reader_instance

        layer_uuid = str(self.layer_1.unique_id)
        url = reverse('serve-pmtiles', kwargs={'layer_uuid': layer_uuid})
        request = self.factory.get(url)
        response = serve_pmtiles(request, layer_uuid)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'application/octet-stream')
        self.assertEqual(response['Content-Length'], '1000')
        self.assertEqual(response['Accept-Ranges'], 'bytes')
        self.assertEqual(response.content, self.test_data)

    @patch('cloud_native_gis.api.pmtile.os.path.exists')
    @patch('cloud_native_gis.api.pmtile.os.path.getsize')
    @patch('cloud_native_gis.api.pmtile.PMTilesReader')
    def test_serve_partial_content(
        self, mock_reader, mock_getsize, mock_exists
    ):
        """Test serving partial content with range header."""
        mock_exists.return_value = True
        mock_getsize.return_value = 1000

        # Setup mock reader
        mock_reader_instance = MagicMock()
        mock_reader_instance.read_range.return_value = self.test_data[0:100]
        mock_reader.return_value = mock_reader_instance

        layer_uuid = str(self.layer_1.unique_id)
        url = reverse('serve-pmtiles', kwargs={'layer_uuid': layer_uuid})
        request = self.factory.get(url)
        request.headers = {'Range': 'bytes=0-99'}
        response = serve_pmtiles(request, layer_uuid)

        self.assertEqual(response.status_code, 206)
        self.assertEqual(response['Content-Type'], 'application/octet-stream')
        self.assertEqual(response['Content-Length'], '100')
        self.assertEqual(response['Content-Range'], 'bytes 0-99/1000')
        self.assertEqual(response['Accept-Ranges'], 'bytes')
        self.assertEqual(response.content, self.test_data[0:100])

    @patch('cloud_native_gis.api.pmtile.os.path.exists')
    @patch('cloud_native_gis.api.pmtile.PMTilesReader')
    def test_invalid_range_header(self, mock_reader, mock_exists):
        """Test handling of invalid range header."""
        mock_exists.return_value = True

        layer_uuid = str(self.layer_1.unique_id)
        url = reverse('serve-pmtiles', kwargs={'layer_uuid': layer_uuid})
        request = self.factory.get(url)
        request.headers = {'Range': 'bytes=invalid'}
        response = serve_pmtiles(request, layer_uuid)

        self.assertEqual(response.status_code, 400)

    @patch('cloud_native_gis.api.pmtile.os.path.exists')
    @patch('cloud_native_gis.api.pmtile.os.path.getsize')
    @patch('cloud_native_gis.api.pmtile.PMTilesReader')
    def test_range_end_omitted(self, mock_reader, mock_getsize, mock_exists):
        """Test range request where end byte is omitted."""
        mock_exists.return_value = True
        mock_getsize.return_value = 1000

        # Setup mock reader
        mock_reader_instance = MagicMock()
        mock_reader_instance.read_range.return_value = self.test_data[500:]
        mock_reader.return_value = mock_reader_instance

        layer_uuid = str(self.layer_1.unique_id)
        url = reverse('serve-pmtiles', kwargs={'layer_uuid': layer_uuid})
        request = self.factory.get(url)
        request.headers = {'Range': 'bytes=500-'}
        response = serve_pmtiles(request, layer_uuid)

        self.assertEqual(response.status_code, 206)
        self.assertEqual(response['Content-Length'], '500')
        self.assertEqual(response['Content-Range'], 'bytes 500-999/1000')

    @patch('cloud_native_gis.api.pmtile.os.path.exists')
    @patch('cloud_native_gis.api.pmtile.PMTilesReader')
    def test_reader_cleanup(self, mock_reader, mock_exists):
        """Test that PMTilesReader is properly closed."""
        mock_exists.return_value = True

        mock_reader_instance = MagicMock()
        mock_reader_instance.read_all.return_value = self.test_data
        mock_reader.return_value = mock_reader_instance

        layer_uuid = str(self.layer_1.unique_id)
        url = reverse('serve-pmtiles', kwargs={'layer_uuid': layer_uuid})
        request = self.factory.get(url)
        serve_pmtiles(request, layer_uuid)

        mock_reader_instance.close.assert_called_once()

    @patch('cloud_native_gis.api.pmtile.os.path.exists')
    @patch('cloud_native_gis.api.pmtile.PMTilesReader')
    def test_reader_cleanup_on_error(self, mock_reader, mock_exists):
        """Test that PMTilesReader is closed even if an error occurs."""
        mock_exists.return_value = True

        mock_reader_instance = MagicMock()
        mock_reader_instance.read_range.side_effect = Exception("Test error")
        mock_reader.return_value = mock_reader_instance

        layer_uuid = str(self.layer_1.unique_id)
        url = reverse('serve-pmtiles', kwargs={'layer_uuid': layer_uuid})
        request = self.factory.get(url)
        request.headers = {'Range': 'bytes=0-99'}
        
        with self.assertRaises(Exception):
            serve_pmtiles(request, layer_uuid)

        mock_reader_instance.close.assert_called_once()
