# coding=utf-8
"""Context Layer Management."""

import os

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test.testcases import TestCase

from context_layer.forms import LayerForm
from context_layer.models import Layer
from context_layer.tests.model_factories import create_user
from context_layer.utils.main import ABS_PATH


class LayerFormTest(TestCase):
    """Test for layer form."""

    def setUp(self):
        """To setup test."""
        self.user = create_user()

    def test_forms(self):
        """Test forms."""
        filepath = ABS_PATH(
            'context_layer', 'tests', '_fixtures', 'capital_cities.zip'
        )
        _file = open(filepath, 'rb')
        form_data = {'name': 'Test Layer'}
        form = LayerForm(
            initial={'unique_id': '00000000-0000-0000-0000-000000000000'},
            data=form_data,
            files={
                'files': [SimpleUploadedFile(_file.name, _file.read())]
            }
        )
        form.user = self.user
        self.assertTrue(form.is_valid())
        form.save()

        layer = Layer.objects.filter(name='Test Layer').first()
        _folder = layer.folder
        self.assertTrue(layer is not None)
        self.assertEqual(layer.created_by.pk, self.user.id)

        self.assertEqual(layer.fields, [])
        layer.import_data()
        self.assertEqual(
            layer.fields, ['CITY_TYPE', 'CITY_NAME', 'COUNTRY']
        )

        layer.delete()
        self.assertFalse(os.path.exists(_folder))
