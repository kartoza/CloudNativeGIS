# coding=utf-8
"""Context Layer Management."""

import os

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test.testcases import TestCase

from context_layer_management.forms import LayerForm, LayerUploadForm
from context_layer_management.models import Layer, LayerType, LayerUpload
from context_layer_management.tests.model_factories import create_user
from context_layer_management.utils.connection import count_features
from context_layer_management.utils.main import ABS_PATH


class LayerFormTest(TestCase):
    """Test for layer form."""

    def setUp(self):
        """To setup test."""
        self.user = create_user()

    def test_forms(self):
        """Test forms."""
        form_data = {'name': 'Test Layer', 'type': LayerType.VECTOR_TILE}
        form = LayerForm(data=form_data)
        form.user = self.user
        self.assertTrue(form.is_valid())
        form.save()

        layer = Layer.objects.filter(name='Test Layer').first()
        self.assertTrue(layer is not None)
        self.assertEqual(layer.created_by.pk, self.user.id)
        self.assertEqual(layer.field_names, [])

        # Run the upload form
        filepath = ABS_PATH(
            'context_layer_management', 'tests', '_fixtures',
            'capital_cities.zip'
        )
        _file = open(filepath, 'rb')
        upload_form = LayerUploadForm(
            data={
                'layer': layer.id
            },
            files={
                'files': [SimpleUploadedFile(_file.name, _file.read())]
            }
        )
        upload_form.user = self.user
        self.assertTrue(upload_form.is_valid())
        upload_form.save()
        layer_upload = LayerUpload.objects.filter(layer=layer).first()

        # IMPORT DATA
        # Check table is deleted
        layer_upload.import_data()
        layer.refresh_from_db()

        # Check folder is deleted
        self.assertFalse(os.path.exists(layer_upload.folder))

        # Check fields
        self.assertEqual(
            layer.field_names, ['CITY_NAME', 'CITY_TYPE', 'COUNTRY']
        )
        # Check count features
        self.assertEqual(
            count_features(layer.schema_name, layer.table_name),
            layer.metadata['FEATURE COUNT']
        )

        # DELETE LAYER
        # Check table is deleted
        layer.delete()
        self.assertEqual(
            count_features(layer.schema_name, layer.table_name),
            None
        )
