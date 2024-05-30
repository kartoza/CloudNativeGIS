# coding=utf-8
"""Context Layer Management."""

from django import forms

from context_layer_management.models import LayerStyle


class LayerStyleForm(forms.ModelForm):
    """Layer style form."""

    def save(self, commit=True):
        """Save the data."""
        if not self.instance.created_by_id:
            self.instance.created_by_id = self.user.pk
        return super(LayerStyleForm, self).save(commit=commit)

    class Meta:  # noqa: D106
        model = LayerStyle
        exclude = ()
