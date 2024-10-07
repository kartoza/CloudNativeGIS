from django.test import TestCase
from rest_framework.test import APIClient
from rest_framework import status
from unittest.mock import patch

from cloud_native_gis.models import Layer
from cloud_native_gis.tests.base import BaseTest
from cloud_native_gis.tests.model_factories import create_user


class ContextAPIViewTest(BaseTest, TestCase):

    def setUp(self):
        self.client = APIClient()

        self.user = create_user(password=self.password)

        # Create a mock Layer object for testing
        self.layer = Layer.objects.create(
            name='Test Layer 1',
            created_by=self.user,
            description='Test Layer 1',
        )

    def test_missing_required_parameters(self):
        # Test the case when required parameters are missing
        response = self.client.get('/api/context/')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('Required request argument', response.data)

    def test_invalid_coordinate_length(self):
        # Test when x and y have different lengths
        response = self.client.get('/api/context/', {'key': 'test-layer', 'x': '1,2', 'y': '1'})
        self.assertEqual(response.status_code, status.HTTP_500_INTERNAL_SERVER_ERROR)
        self.assertIn('The number of x and y coordinates must be the same', response.data)

    def test_invalid_coordinate_format(self):
        # Test when coordinates are not valid floats
        response = self.client.get('/api/context/', {'key': 'test-layer', 'x': 'a,b', 'y': 'c,d'})
        self.assertEqual(response.status_code, status.HTTP_500_INTERNAL_SERVER_ERROR)
        self.assertIn('All x and y values must be valid floats', response.data)

    def test_invalid_registry_value(self):
        # Test an invalid registry value
        response = self.client.get('/api/context/', {
            'key': 'test-layer',
            'x': '1,2',
            'y': '1,2',
            'registry': 'invalid'
        })
        self.assertEqual(response.status_code, status.HTTP_500_INTERNAL_SERVER_ERROR)
        self.assertIn('Registry should be "collection", "service" or "group".', response.data)

    def test_successful_native_query(self):
        # Patch the `query_features` function to return mock data
        with patch('cloud_native_gis.api.context.query_features') as mock_query_features:
            mock_query_features.return_value = [
                {'coordinates': (1.0, 1.0), 'feature': {'name': 'Test', 'type': 'Example'}}]

            response = self.client.get('/api/context/', {
                'key': self.layer.unique_id,
                'x': '1,2',
                'y': '1,2',
                'registry': 'native',
                'outformat': 'geojson',
                'tolerance': '10.0'
            })

            self.assertEqual(response.status_code, status.HTTP_200_OK)
            self.assertEqual(len(response.data), 1)
            self.assertIn('feature', response.data[0])
            self.assertEqual(response.data[0]['feature']['name'], 'Test')

    def test_layer_does_not_exist(self):
        # Test when the specified layer does not exist
        response = self.client.get('/api/context/', {
            'key': 'non-existent-layer',
            'x': '1,2',
            'y': '1,2',
            'registry': 'native'
        })
        self.assertEqual(response.status_code, status.HTTP_500_INTERNAL_SERVER_ERROR)
