# coding=utf-8
"""Cloud Native GIS."""

from django import forms
from django.core.files.storage import FileSystemStorage

from cloud_native_gis.forms.file import MultipleFileField
from cloud_native_gis.models import Layer, LayerUpload


class LayerForm(forms.ModelForm):
    """Layer form."""

    def save(self, commit=True):
        """Save the data."""
        try:
            self.instance.unique_id = self.initial['unique_id']
        except KeyError:
            pass
        if not self.instance.created_by_id:
            self.instance.created_by_id = self.user.pk
        return super(LayerForm, self).save(commit=commit)

    class Meta:  # noqa: D106
        model = Layer
        exclude = ('unique_id', 'is_ready', 'type')


class LayerUploadForm(forms.ModelForm):
    """Layer upload form."""

    files = MultipleFileField(required=False)

    def save(self, commit=True):
        """Save the data."""
        if not self.instance.created_by_id:
            self.instance.created_by_id = self.user.pk
        instance = super(LayerUploadForm, self).save(commit=commit)

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
        model = LayerUpload
        exclude = ('progress', 'status', 'note', 'folder')
