# coding=utf-8
"""Cloud Native GIS."""

from django import forms

from cloud_native_gis.models import Style


class StyleForm(forms.ModelForm):
    """Layer style form."""

    def save(self, commit=True):
        """Save the data."""
        if not self.instance.created_by_id:
            self.instance.created_by_id = self.user.pk
        return super(StyleForm, self).save(commit=commit)

    class Meta:  # noqa: D106
        model = Style
        exclude = ()
