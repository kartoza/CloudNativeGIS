# coding=utf-8
"""Cloud Native GIS."""

import urllib.parse

from django.contrib.auth import get_user_model
from django.test.testcases import TestCase
from django.urls import reverse
from rest_framework.test import APIRequestFactory
from django.core.files.storage import FileSystemStorage

from core.settings.utils import absolute_path
from cloud_native_gis.models.layer import Layer, LayerType
from cloud_native_gis.models.layer_upload import LayerUpload
from cloud_native_gis.tests.base import BaseTest
from cloud_native_gis.tests.model_factories import create_user
from cloud_native_gis.api.layer import DataPreviewAPI

User = get_user_model()


class LayerTest(BaseTest, TestCase):
    """Test for Layer API."""

    def setUp(self):
        """To setup test."""
        self.user = create_user(password=self.password)
        self.user_1 = create_user(password=self.password)
        self.layer_1 = Layer.objects.create(
            name='Test Layer 1',
            created_by=self.user,
            description='Test Layer 1',
        )
        Layer.objects.create(
            name='Test Layer 2',
            created_by=self.user,
            description='Test Layer 2',
        )

    def test_list_api(self):
        """Test List API."""
        url = reverse('cloud-native-gis-layer-list')
        response = self.assertRequestGetView(url, 200, user=self.user)
        self.assertEqual(len(response.json()['results']), 2)

    def test_list_api_by_filter(self):
        """Test list API with filter."""
        params = urllib.parse.urlencode(
            {
                'name__contains': 'Layer 2'
            }
        )
        url = reverse('cloud-native-gis-layer-list') + '?' + params
        response = self.assertRequestGetView(url, 200, user=self.user)
        self.assertEqual(len(response.json()['results']), 1)

    def test_create_api(self):
        """Test POST API."""
        url = reverse('cloud-native-gis-layer-list')
        response = self.assertRequestPostView(
            url, 201,
            user=self.user,
            data={
                "name": 'Test new layer',
                'type': LayerType.VECTOR_TILE
            },
            content_type=self.JSON_CONTENT
        ).json()
        obj = Layer.objects.get(id=response['id'])
        self.assertEqual(obj.name, 'Test new layer')
        self.assertEqual(response['name'], 'Test new layer')
        self.assertEqual(obj.created_by, self.user)
        self.assertEqual(response['created_by'], self.user.username)

    def test_detail_api(self):
        """Test GET detail api."""
        url = reverse('cloud-native-gis-layer-list', args=[0])
        self.assertRequestGetView(url, 404)

        url = reverse(
            'cloud-native-gis-layer-detail',
            kwargs={'id': self.layer_1.id}
        )
        response = self.assertRequestGetView(url, 200, user=self.user).json()

        self.assertEqual(response['name'], self.layer_1.name)
        self.assertEqual(response['description'], self.layer_1.description)
        self.assertEqual(
            response['created_by'], self.user.username
        )

    def test_update_api(self):
        """Test PUT API."""
        url = reverse('cloud-native-gis-layer-list', args=[0])
        self.assertRequestPutView(url, 404, data={})

        url = reverse(
            'cloud-native-gis-layer-detail',
            kwargs={'id': self.layer_1.id}
        )
        self.assertRequestPutView(url, 403, data={})
        self.assertRequestPutView(
            url, 403,
            user=self.user_1,
            data={},
            content_type=self.JSON_CONTENT
        )
        response = self.assertRequestPutView(
            url, 200,
            user=self.user,
            data={
                "name": 'Test Layer 1 Updated',
                'type': LayerType.VECTOR_TILE
            },
            content_type=self.JSON_CONTENT
        ).json()
        obj = Layer.objects.get(id=response['id'])
        self.assertEqual(obj.name, 'Test Layer 1 Updated')
        self.assertEqual(response['name'], 'Test Layer 1 Updated')
        self.assertEqual(obj.created_by, self.user)
        self.assertEqual(response['created_by'], self.user.username)

    def test_delete_api(self):
        """Test DELETE API."""
        _id = self.layer_1.id
        url = reverse('cloud-native-gis-layer-detail', args=[0])
        self.assertRequestDeleteView(url, 404)
        url = reverse(
            'cloud-native-gis-layer-detail', kwargs={'id': _id}
        )
        self.assertRequestDeleteView(url, 403)
        self.assertRequestDeleteView(url, 403, user=self.user_1)
        self.assertRequestDeleteView(url, 204, user=self.user)
        self.assertFalse(Layer.objects.filter(id=_id).first())


class DataPreviewAPITest(TestCase):

    def setUp(self):
        """Init test class."""
        self.factory = APIRequestFactory()

        # add superuser
        self.superuser = create_user(
            is_staff=True,
            is_superuser=True,
            is_active=True
        )

        # add normal user
        self.user = create_user(
            is_active=True
        )

        self.layer = Layer.objects.create(
            created_by=self.user,
            is_ready=True
        )
        self.layer_upload = LayerUpload.objects.create(
            created_by=self.user, layer=self.layer
        )
        file_path = absolute_path(
            'cloud_native_gis',
            'tests',
            '_fixtures',
            'polygons_import.zip'
        )
        with open(file_path, 'rb') as data:
            FileSystemStorage(
                location=self.layer_upload.folder
            ).save(f'polygons_import.zip', data)
        self.layer_upload.save()
        self.layer_upload.import_data()

        self.layer.refresh_from_db()

    def tearDown(self):
        """Clean up after tests."""
        self.layer_upload.delete_folder()
        self.layer.delete()

    def test_data_preview_api(self):
        """Test data preview API."""
        view = DataPreviewAPI.as_view()
        request = self.factory.get(
            reverse('data-preview', kwargs={
                'layer_id': self.layer.id
            }),
            data={
                'page_size': 10,
                'page': 1
            }
        )
        request.user = self.superuser
        response = view(request, layer_id=self.layer.id)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['count'], 2)
        self.assertEqual(len(response.data['data']), 2)
        self.assertEqual(response.data['data'][0]['id'], 1)
        self.assertEqual(response.data['data'][0]['name'], 'kenya')

    def test_data_preview_api_with_search(self):
        """Test data preview API with search."""
        view = DataPreviewAPI.as_view()

        request = self.factory.get(
            reverse('data-preview', kwargs={
                'layer_id': self.layer.id
            }),
            data={
                'page_size': 10,
                'page': 1,
                'search': 'KENY'
            }
        )
        request.user = self.superuser
        response = view(request, layer_id=self.layer.id)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['count'], 1)
        self.assertEqual(len(response.data['data']), 1)
        self.assertEqual(response.data['data'][0]['id'], 1)
        self.assertEqual(response.data['data'][0]['name'], 'kenya')

    def test_data_preview_api_no_features(self):
        """Test data preview API with no features."""
        view = DataPreviewAPI.as_view()

        request = self.factory.get(
            reverse('data-preview', kwargs={
                'layer_id': self.layer.id
            }),
            data={
                'page_size': 10,
                'page': 1,
                'search': 'FEATURE_NOT_FOUND'
            }
        )
        request.user = self.superuser
        response = view(request, layer_id=self.layer.id)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['count'], 0)
        self.assertEqual(len(response.data['data']), 0)
