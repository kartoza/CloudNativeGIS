# coding=utf-8
"""Cloud Native GIS."""

import os
from django.test import TestCase
from django.core.files.uploadedfile import (
    InMemoryUploadedFile,
    TemporaryUploadedFile
)

from core.settings.utils import absolute_path
from cloud_native_gis.utils.fiona import (
    FileType,
    validate_shapefile_zip,
    open_fiona_collection,
    validate_collection_crs,
    delete_tmp_shapefile
)


class TestUtilsFiona(TestCase):
    """Test class for Fiona utility functions."""

    def test_validate_shapefile_zip(self):
        """Test validate shapefile."""
        # test incomplete zip
        shape_file_path = absolute_path(
            'cloud_native_gis',
            'tests',
            '_fixtures',
            'shp_no_shp.zip'
        )
        is_valid, error = validate_shapefile_zip(shape_file_path)
        self.assertFalse(is_valid)
        self.assertEqual(len(error), 1)
        self.assertEqual(error[0], 'shp_1_1.shp')
        shape_file_path = absolute_path(
            'cloud_native_gis',
            'tests',
            '_fixtures',
            'shp_no_dbf_shx.zip'
        )
        is_valid, error = validate_shapefile_zip(shape_file_path)
        self.assertFalse(is_valid)
        self.assertEqual(len(error), 2)
        self.assertEqual(error[0], 'test_2.shx')
        self.assertEqual(error[1], 'test_2.dbf')
        # test complete zip
        shape_file_path = absolute_path(
            'cloud_native_gis',
            'tests',
            '_fixtures',
            'shp.zip'
        )
        is_valid, error = validate_shapefile_zip(shape_file_path)
        self.assertTrue(is_valid)
        # test using in memory file
        file_stats = os.stat(shape_file_path)
        with open(shape_file_path, 'rb') as file:
            mem_file = InMemoryUploadedFile(
                file, None, 'shp.zip', 'application/zip',
                file_stats.st_size, None)
            is_valid, error = validate_shapefile_zip(mem_file)
            self.assertTrue(is_valid)
        # test using temporary uploaded file
        with open(shape_file_path, 'rb') as file:
            tmp_file = TemporaryUploadedFile(
                'shp.zip', 'application/zip', file_stats.st_size, 'utf-8')
            with open(tmp_file.temporary_file_path(), 'wb+') as wfile:
                wfile.write(file.read())
            is_valid, error = validate_shapefile_zip(tmp_file)
            self.assertTrue(is_valid)

    def test_open_fiona_collection_shp(self):
        """Test open fiona collection for shapefile."""
        shape_file_path = absolute_path(
            'cloud_native_gis',
            'tests',
            '_fixtures',
            'shp.zip'
        )
        file_stats = os.stat(shape_file_path)

        # test using filepath
        collection = open_fiona_collection(
            shape_file_path, FileType.SHAPEFILE)
        self.assertEqual(len(collection), 3)
        collection.close()

        # test using InMemoryUploadedFile
        with open(shape_file_path, 'rb') as file:
            mem_file = InMemoryUploadedFile(
                file, None, 'shp.zip', 'application/zip',
                file_stats.st_size, None)
            collection = open_fiona_collection(
                mem_file, FileType.SHAPEFILE)
            self.assertEqual(len(collection), 3)
            collection.close()
            delete_tmp_shapefile(collection.path)

        # test using TemporaryUploadedFile
        with open(shape_file_path, 'rb') as file:
            tmp_file = TemporaryUploadedFile(
                'shp.zip', 'application/zip', file_stats.st_size, 'utf-8')
            with open(tmp_file.temporary_file_path(), 'wb+') as wfile:
                wfile.write(file.read())
            collection = open_fiona_collection(
                tmp_file, FileType.SHAPEFILE)
            self.assertEqual(len(collection), 3)
            collection.close()
            delete_tmp_shapefile(collection.path)

    def test_open_fiona_collection_gpkg(self):
        """Test open fiona collection for gpkg."""
        gpkg_file_path = absolute_path(
            'cloud_native_gis',
            'tests',
            '_fixtures',
            'gpkg.gpkg'
        )
        file_stats = os.stat(gpkg_file_path)

        # test using filepath
        collection = open_fiona_collection(
            gpkg_file_path, FileType.GEOPACKAGE)
        self.assertEqual(len(collection), 3)
        collection.close()

        # test using InMemoryUploadedFile
        with open(gpkg_file_path, 'rb') as file:
            mem_file = InMemoryUploadedFile(
                file, None, 'gpkg.gpkg', 'application/geopackage+sqlite3',
                file_stats.st_size, None)
            collection = open_fiona_collection(
                mem_file, FileType.GEOPACKAGE)
            self.assertEqual(len(collection), 3)
        collection.close()

        # test using TemporaryUploadedFile
        with open(gpkg_file_path, 'rb') as file:
            tmp_file = TemporaryUploadedFile(
                'gpkg.gpkg', 'application/geopackage+sqlite3',
                file_stats.st_size, 'utf-8')
            with open(tmp_file.temporary_file_path(), 'wb+') as wfile:
                wfile.write(file.read())
            collection = open_fiona_collection(
                tmp_file, FileType.GEOPACKAGE)
            self.assertEqual(len(collection), 3)
        collection.close()

    def test_open_fiona_collection_geojson(self):
        """Test open fiona collection for geojson."""
        geojson_file_path = absolute_path(
            'cloud_native_gis',
            'tests',
            '_fixtures',
            'country.geojson'
        )
        file_stats = os.stat(geojson_file_path)

        # test using filepath
        collection = open_fiona_collection(
            geojson_file_path, FileType.GEOJSON)
        self.assertEqual(len(collection), 1)
        collection.close()

        # test using InMemoryUploadedFile
        with open(geojson_file_path, 'rb') as file:
            mem_file = InMemoryUploadedFile(
                file, None, 'country.geojson',
                'application/geo+json',
                file_stats.st_size, None)
            collection = open_fiona_collection(
                mem_file, FileType.GEOJSON)
            self.assertEqual(len(collection), 1)
        collection.close()

        # test using TemporaryUploadedFile
        with open(geojson_file_path, 'rb') as file:
            tmp_file = TemporaryUploadedFile(
                'country.geojson', 'application/geo+json',
                file_stats.st_size, 'utf-8')
            with open(tmp_file.temporary_file_path(), 'wb+') as wfile:
                wfile.write(file.read())
            collection = open_fiona_collection(
                tmp_file, FileType.GEOJSON)
            self.assertEqual(len(collection), 1)
        collection.close()

    def test_validate_collection_crs(self):
        """Test validate crs."""
        # test invalid crs shp
        shape_file_path = absolute_path(
            'cloud_native_gis',
            'tests',
            '_fixtures',
            'shp_3857.zip'
        )
        collection = open_fiona_collection(
            shape_file_path, FileType.SHAPEFILE)
        is_valid, crs = validate_collection_crs(collection)
        collection.close()
        self.assertFalse(is_valid)
        self.assertEqual(crs, 'epsg:3857')

        # test valid crs
        shape_file_path = absolute_path(
            'cloud_native_gis',
            'tests',
            '_fixtures',
            'gpkg.gpkg'
        )
        collection = open_fiona_collection(
            shape_file_path, FileType.GEOPACKAGE)
        is_valid, _ = validate_collection_crs(collection)
        collection.close()
        self.assertTrue(is_valid)

        shape_file_path = absolute_path(
            'cloud_native_gis',
            'tests',
            '_fixtures',
            'country.geojson'
        )
        collection = open_fiona_collection(
            shape_file_path, FileType.GEOJSON)
        is_valid, _ = validate_collection_crs(collection)
        collection.close()
        self.assertTrue(is_valid)
