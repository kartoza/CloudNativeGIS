# coding=utf-8
"""Cloud Native GIS."""

import urllib.parse

from django.contrib.auth import get_user_model
from django.test.testcases import TestCase
from django.urls import reverse

from cloud_native_gis.models.layer import Layer, LayerType
from cloud_native_gis.tests.base import BaseTest
from cloud_native_gis.tests.model_factories import create_user

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
