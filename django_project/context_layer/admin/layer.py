"""Context Layer Management."""
import os

from django.contrib import admin
from django.utils.html import mark_safe  # Newer versions

from context_layer.forms.layer import LayerForm
from context_layer.models.layer import Layer


class LayerAdmin(admin.ModelAdmin):
    """Layer admin."""

    list_display = ('unique_id', 'name', 'created_by', 'created_at', 'files')
    form = LayerForm

    def get_form(self, request, *args, **kwargs):
        """Return form."""
        form = super(LayerAdmin, self).get_form(request, *args, **kwargs)
        form.user = request.user
        return form

    def files(self, obj: Layer):
        """Return files list."""
        return mark_safe(
            '<br/>'.join([
                f'<a href="{os.path.join(obj.url, f)}">{f}</a>'
                for f in os.listdir(obj.folder) if
                os.path.isfile(os.path.join(obj.folder, f))
            ])
        )


admin.site.register(Layer, LayerAdmin)
