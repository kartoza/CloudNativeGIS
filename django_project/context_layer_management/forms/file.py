# coding=utf-8
"""Context Layer Management."""

from django import forms


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
