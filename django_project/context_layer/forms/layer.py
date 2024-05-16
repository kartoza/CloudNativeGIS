# coding=utf-8
"""Context Layer Management."""

from django import forms
from django.core.files.storage import FileSystemStorage

from context_layer.models import Layer


class MultipleFileInput(forms.ClearableFileInput):
    """Multiple file input."""

    allow_multiple_selected = True


class MultipleFileField(forms.FileField):
    """Multiple file field."""

    def __init__(self, *args, **kwargs):
        """Initialize the field."""
        kwargs.setdefault("widget", MultipleFileInput())
        super().__init__(*args, **kwargs)

    def clean(self, data, initial=None):
        """Clean data."""
        single_file_clean = super().clean
        if isinstance(data, (list, tuple)):
            result = [single_file_clean(d, initial) for d in data]
        else:
            result = [single_file_clean(data, initial)]
        return result


class LayerForm(forms.ModelForm):
    """Layer form."""

    files = MultipleFileField()

    def save(self, commit=True):
        """Save the data."""
        instance = super(LayerForm, self).save(commit=False)
        instance.created_by = self.user

        # Save files
        instance.emptying_folder()
        for file in self.files.getlist('files'):
            FileSystemStorage(location=instance.folder).save(file.name, file)

        self.instance.import_data()
        return instance

    class Meta:  # noqa: D106
        model = Layer
        exclude = ('unique_id',)
