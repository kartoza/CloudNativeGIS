# coding=utf-8
# SPDX-FileCopyrightText: 2024 Kartoza <info@kartoza.com>
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Tests for OGC API (pygeoapi) endpoints and base helpers."""

from django.core.files.storage import FileSystemStorage
from django.test import TestCase, TransactionTestCase
from django.urls import reverse
from rest_framework.test import APIRequestFactory

from core.settings.utils import absolute_path
from cloud_native_gis.models.layer import Layer
from cloud_native_gis.models.layer_upload import LayerUpload
from cloud_native_gis.tests.base import BaseTest
from cloud_native_gis.tests.model_factories import create_user


def _cid(layer):
    """Return the OGC collection ID string for a layer."""
    return str(layer.unique_id)


def _url(name, **kwargs):
    """Resolve a URL by name and append ?f=json."""
    return reverse(name, kwargs=kwargs or None) + '?f=json'


# ---------------------------------------------------------------------------
# Unit tests – base helpers
# ---------------------------------------------------------------------------

class BaseHelpersTest(TestCase):
    """Unit tests for get_queryset and get_resources."""

    def setUp(self):
        self.factory = APIRequestFactory()
        self.user = create_user()

    def _get(self, path='/'):
        req = self.factory.get(path)
        req.user = self.user
        return req

    def test_get_queryset_returns_all_layers(self):
        """get_queryset returns every Layer object without filtering."""
        from cloud_native_gis.api.pygeoapi.base import get_queryset
        Layer.objects.create(name='L1', created_by=self.user)
        Layer.objects.create(name='L2', created_by=self.user)
        self.assertEqual(get_queryset(self._get()).count(), 2)

    def test_get_resources_returns_config_dict(self):
        """get_resources returns a dict with 'server' and 'resources' keys."""
        from cloud_native_gis.api.pygeoapi.base import get_resources
        config = get_resources(self._get())
        self.assertIn('server', config)
        self.assertIn('resources', config)

    def test_get_resources_includes_layer_in_resources(self):
        """get_resources includes each layer from get_queryset in resources."""
        from cloud_native_gis.api.pygeoapi.base import get_resources
        layer = Layer.objects.create(name='L', created_by=self.user)
        config = get_resources(self._get())
        self.assertIn(_cid(layer), config['resources'])

# ---------------------------------------------------------------------------
# Landing, OpenAPI, Conformance  (no layer data required)
# ---------------------------------------------------------------------------

class OGCLandingTest(BaseTest, TestCase):
    """Tests for the OGC API landing page, OpenAPI document, and conformance."""

    def test_landing_page(self):
        """GET /ogc/ returns a valid OGC API landing page."""
        response = self.assertRequestGetView(_url('landing-page'), 200)
        self.assertIn('links', response.json())

    def test_openapi(self):
        """GET /ogc/openapi returns an OpenAPI 3.x document."""
        response = self.assertRequestGetView(_url('openapi'), 200)
        self.assertIn('openapi', response.json())

    def test_conformance(self):
        """GET /ogc/conformance lists OGC conformance classes."""
        response = self.assertRequestGetView(_url('conformance'), 200)
        self.assertIn('conformsTo', response.json())


# ---------------------------------------------------------------------------
# Collections – no layer configured
# ---------------------------------------------------------------------------

class OGCEmptyCollectionsTest(BaseTest, TestCase):
    """Endpoint behaviour when no layers are available."""

    def test_collections_list_empty(self):
        """GET /ogc/collections returns an empty collections array."""
        data = self.assertRequestGetView(_url('collections'), 200).json()
        self.assertIn('collections', data)
        self.assertEqual(data['collections'], [])

    def test_collection_detail_not_found(self):
        """GET /ogc/collections/{id} returns 404 for an unknown collection."""
        self.assertRequestGetView(
            _url('collection-detail', collection_id='nonexistent'), 404
        )

    def test_collection_schema_not_found(self):
        """GET /ogc/collections/{id}/schema returns 404 for an unknown collection."""
        self.assertRequestGetView(
            _url('collection-schema', collection_id='nonexistent'), 404
        )

    def test_collection_queryables_not_found(self):
        """GET /ogc/collections/{id}/queryables returns 404 for unknown collection."""
        self.assertRequestGetView(
            _url('collection-queryables', collection_id='nonexistent'), 404
        )

    def test_items_list_not_found(self):
        """GET /ogc/collections/{id}/items returns 404 for an unknown collection."""
        self.assertRequestGetView(
            _url('collection-items', collection_id='nonexistent'), 404
        )

    def test_item_detail_not_found(self):
        """GET /ogc/collections/{id}/items/{item_id} returns 404 for unknown collection."""
        self.assertRequestGetView(
            _url('collection-item', collection_id='nonexistent', item_id='1'),
            404,
        )


# ---------------------------------------------------------------------------
# Full integration – real PostGIS layer (polygons_import.zip: 2 features,
# columns: id, name, geometry)
# ---------------------------------------------------------------------------

class OGCCollectionTest(BaseTest, TransactionTestCase):
    """
    Integration tests for collection, schema, queryables, and items endpoints.

    Each test imports the polygons_import.zip fixture into a temporary PostGIS
    table and tears it down afterwards.
    """

    def setUp(self):
        self.user = create_user(password=self.password)
        self.layer = Layer.objects.create(
            name='Test Layer',
            created_by=self.user,
            is_ready=True,
        )
        self.layer_upload = LayerUpload.objects.create(
            created_by=self.user, layer=self.layer
        )
        fixture = absolute_path(
            'cloud_native_gis', 'tests', '_fixtures', 'polygons_import.zip'
        )
        with open(fixture, 'rb') as fh:
            FileSystemStorage(
                location=self.layer_upload.folder
            ).save('polygons_import.zip', fh)
        self.layer_upload.save()
        self.layer_upload.import_data()
        self.layer.refresh_from_db()
        self.cid = _cid(self.layer)

    def tearDown(self):
        self.layer_upload.delete_folder()
        self.layer.delete()

    # -- Collections list & detail --

    def test_collections_list(self):
        """GET /ogc/collections includes the imported layer."""
        data = self.assertRequestGetView(_url('collections'), 200).json()
        ids = [c['id'] for c in data['collections']]
        self.assertIn(self.cid, ids)

    def test_collection_detail(self):
        """GET /ogc/collections/{id} returns the collection metadata."""
        data = self.assertRequestGetView(
            _url('collection-detail', collection_id=self.cid), 200
        ).json()
        self.assertEqual(data['id'], self.cid)
        self.assertIn('links', data)

    # -- Sub-resources --

    def test_collection_schema(self):
        """GET /ogc/collections/{id}/schema returns JSON Schema properties."""
        data = self.assertRequestGetView(
            _url('collection-schema', collection_id=self.cid), 200
        ).json()
        self.assertIn('properties', data)

    def test_collection_queryables(self):
        """GET /ogc/collections/{id}/queryables lists queryable properties."""
        data = self.assertRequestGetView(
            _url('collection-queryables', collection_id=self.cid), 200
        ).json()
        self.assertIn('properties', data)

    # -- Items list --

    def test_items_list_type(self):
        """GET /ogc/collections/{id}/items returns a GeoJSON FeatureCollection."""
        data = self.assertRequestGetView(
            _url('collection-items', collection_id=self.cid), 200
        ).json()
        self.assertEqual(data['type'], 'FeatureCollection')

    def test_items_list_count(self):
        """items response numberMatched and numberReturned reflect fixture size."""
        data = self.assertRequestGetView(
            _url('collection-items', collection_id=self.cid), 200
        ).json()
        self.assertIn('numberMatched', data)
        self.assertEqual(data['numberMatched'], 2)
        self.assertEqual(data['numberReturned'], 2)

    def test_items_list_feature_structure(self):
        """Each feature has type, geometry, and properties."""
        features = self.assertRequestGetView(
            _url('collection-items', collection_id=self.cid), 200
        ).json()['features']
        for feature in features:
            self.assertEqual(feature['type'], 'Feature')
            self.assertIn('geometry', feature)
            self.assertIn('properties', feature)

    def test_items_limit(self):
        """GET …/items?limit=1 returns exactly 1 feature."""
        data = self.assertRequestGetView(
            _url('collection-items', collection_id=self.cid) + '&limit=1', 200
        ).json()
        self.assertEqual(data['numberReturned'], 1)
        self.assertEqual(len(data['features']), 1)

    def test_items_offset(self):
        """GET …/items?offset=1 skips the first feature."""
        data = self.assertRequestGetView(
            _url('collection-items', collection_id=self.cid) + '&offset=1', 200
        ).json()
        self.assertEqual(data['numberReturned'], 1)

    def test_items_options(self):
        """OPTIONS /ogc/collections/{id}/items is supported."""
        from django.test.client import Client
        url = reverse('collection-items', kwargs={'collection_id': self.cid})
        response = Client().options(url)
        self.assertIn(response.status_code, (200, 204))

    # -- Item detail --

    def test_item_detail(self):
        """GET /ogc/collections/{id}/items/1 returns a single GeoJSON Feature."""
        data = self.assertRequestGetView(
            _url('collection-item', collection_id=self.cid, item_id='1'), 200
        ).json()
        self.assertEqual(data['type'], 'Feature')
        self.assertIn('geometry', data)
        self.assertIn('properties', data)
        self.assertEqual(data['id'], 1)

    def test_item_detail_not_found(self):
        """GET /ogc/collections/{id}/items/99999 returns 404."""
        self.assertRequestGetView(
            _url('collection-item', collection_id=self.cid, item_id='99999'),
            404,
        )

    def test_item_options(self):
        """OPTIONS /ogc/collections/{id}/items/{id} is supported."""
        from django.test.client import Client
        url = reverse(
            'collection-item',
            kwargs={'collection_id': self.cid, 'item_id': '1'},
        )
        response = Client().options(url)
        self.assertIn(response.status_code, (200, 204))

    # -- CQL filter – GET --

    def test_cql_get_filter_by_id(self):
        """GET …/items?filter=id=1 returns 1 feature."""
        url = (
            _url('collection-items', collection_id=self.cid)
            + '&filter=id%3D1'
        )
        data = self.assertRequestGetView(url, 200).json()
        self.assertEqual(data['numberReturned'], 1)
        self.assertEqual(data['features'][0]['properties']['name'], 'kenya')

    def test_cql_get_filter_by_name(self):
        """GET …/items?filter=name='somalia' returns 1 feature."""
        url = (
            _url('collection-items', collection_id=self.cid)
            + "&filter=name%3D'somalia'"
        )
        data = self.assertRequestGetView(url, 200).json()
        self.assertEqual(data['numberReturned'], 1)
        self.assertEqual(data['features'][0]['properties']['name'], 'somalia')

    # -- CQL filter – POST CQL2-JSON --

    def test_cql_post_json_filter_by_id(self):
        """POST …/items with CQL2-JSON body filters by id."""
        import json
        from django.test.client import Client
        url = reverse('collection-items', kwargs={'collection_id': self.cid})
        body = json.dumps({
            'op': '=',
            'args': [{'property': 'id'}, 1],
        })
        response = Client().post(
            url, data=body, content_type='application/cql2+json'
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data['numberReturned'], 1)
        self.assertEqual(data['features'][0]['properties']['name'], 'kenya')

    def test_cql_post_json_filter_by_name(self):
        """POST …/items with CQL2-JSON body filters by name."""
        import json
        from django.test.client import Client
        url = reverse('collection-items', kwargs={'collection_id': self.cid})
        body = json.dumps({
            'op': '=',
            'args': [{'property': 'name'}, 'somalia'],
        })
        response = Client().post(
            url, data=body, content_type='application/cql2+json'
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data['numberReturned'], 1)
        self.assertEqual(data['features'][0]['properties']['name'], 'somalia')

    # -- CQL filter – POST CQL text --

    def test_cql_post_text_filter_by_id(self):
        """POST …/items with CQL text body filters by id."""
        from django.test.client import Client
        url = reverse('collection-items', kwargs={'collection_id': self.cid})
        response = Client().post(
            url, data='id = 1', content_type='application/cql-text'
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data['numberReturned'], 1)
        self.assertEqual(data['features'][0]['properties']['name'], 'kenya')

    # -- Write operations --

    _NEW_FEATURE = {
        'type': 'Feature',
        'id': 3,
        'geometry': {
            'type': 'Polygon',
            'coordinates': [[[0, 0], [1, 0], [1, 1], [0, 1], [0, 0]]],
        },
        'properties': {'name': 'new_country'},
    }

    def test_create_feature(self):
        """POST …/items with GeoJSON body creates a new feature (201)."""
        import json
        from django.test.client import Client
        url = reverse('collection-items', kwargs={'collection_id': self.cid})
        response = Client().post(
            url,
            data=json.dumps(self._NEW_FEATURE),
            content_type='application/geo+json',
        )
        self.assertEqual(response.status_code, 201)
        # Total count increased to 3
        data = self.assertRequestGetView(
            _url('collection-items', collection_id=self.cid), 200
        ).json()
        self.assertEqual(data['numberMatched'], 3)

    def test_replace_feature(self):
        """PUT …/items/{id} replaces an existing feature (204)."""
        import json
        from django.test.client import Client
        url = reverse(
            'collection-item',
            kwargs={'collection_id': self.cid, 'item_id': '1'},
        )
        updated = dict(self._NEW_FEATURE)
        updated['id'] = 1
        updated['properties'] = {'name': 'updated_country'}
        response = Client().put(
            url,
            data=json.dumps(updated),
            content_type='application/geo+json',
        )
        self.assertEqual(response.status_code, 204)
        # Verify the name changed
        data = self.assertRequestGetView(
            _url('collection-item', collection_id=self.cid, item_id='1'), 200
        ).json()
        self.assertEqual(data['properties']['name'], 'updated_country')

    def test_delete_feature(self):
        """DELETE …/items/{id} removes a feature (200)."""
        from django.test.client import Client
        url = reverse(
            'collection-item',
            kwargs={'collection_id': self.cid, 'item_id': '1'},
        )
        response = Client().delete(url)
        self.assertEqual(response.status_code, 200)
        # Total count decreased to 1
        data = self.assertRequestGetView(
            _url('collection-items', collection_id=self.cid), 200
        ).json()
        self.assertEqual(data['numberMatched'], 1)

    def test_delete_feature_not_found(self):
        """DELETE …/items/99999 returns 404."""
        from django.test.client import Client
        url = reverse(
            'collection-item',
            kwargs={'collection_id': self.cid, 'item_id': '99999'},
        )
        response = Client().delete(url)
        self.assertEqual(response.status_code, 404)

    def test_create_feature_without_id(self):
        """POST …/items with no 'id' in body returns 201 with a valid Location."""
        import json
        from django.test.client import Client
        feature_without_id = {
            'type': 'Feature',
            'geometry': {
                'type': 'Polygon',
                'coordinates': [[[0, 0], [1, 0], [1, 1], [0, 1], [0, 0]]],
            },
            'properties': {'name': 'auto_id_country'},
        }
        url = reverse('collection-items', kwargs={'collection_id': self.cid})
        response = Client().post(
            url,
            data=json.dumps(feature_without_id),
            content_type='application/geo+json',
        )
        self.assertEqual(response.status_code, 201)
        location = response.get('Location', '')
        # Location must end with an integer id, not 'None'
        item_id = location.rstrip('/').split('/')[-1]
        self.assertNotEqual(item_id, 'None')
        self.assertTrue(item_id.isdigit(), f'Expected integer id in Location, got: {location}')
        # Feature count increased
        data = self.assertRequestGetView(
            _url('collection-items', collection_id=self.cid), 200
        ).json()
        self.assertEqual(data['numberMatched'], 3)
