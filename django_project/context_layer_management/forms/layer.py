# coding=utf-8
"""Context Layer Management."""

from django import forms
from django.core.files.storage import FileSystemStorage

from context_layer_management.forms.file import MultipleFileField
from context_layer_management.models import Layer


class LayerForm(forms.ModelForm):
    """Layer form."""

    files = MultipleFileField()

    def save(self, commit=True):
        """Save the data."""
        try:
            self.instance.unique_id = self.initial['unique_id']
        except KeyError:
            pass
        if not self.instance.created_by_id:
            self.instance.created_by_id = self.user.pk
        instance = super(LayerForm, self).save(commit=commit)

        # Save files
        try:
            _files = self.files.getlist('files')
        except AttributeError:
            _files = self.files['files']
        if len(_files):
            instance.emptying_folder()
            for file in _files:
                FileSystemStorage(
                    location=instance.folder
                ).save(file.name, file)

        return instance

    class Meta:  # noqa: D106
        model = Layer
        exclude = ('unique_id', 'is_ready')
