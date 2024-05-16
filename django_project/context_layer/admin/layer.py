"""Context Layer Management."""

from django.contrib import admin

from context_layer.forms.layer import LayerForm
from context_layer.models.layer import Layer


@admin.action(description='Import data')
def import_data(modeladmin, request, queryset):
    for upload_session in queryset:
        upload_session.import_data()


class LayerAdmin(admin.ModelAdmin):
    """Layer admin."""

    actions = [import_data, ]
    form = LayerForm
    list_display = ('unique_id', 'name', 'created_by', 'created_at')

    def get_form(self, request, *args, **kwargs):
        """Return form."""
        form = super(LayerAdmin, self).get_form(request, *args, **kwargs)
        form.user = request.user
        return form


admin.site.register(Layer, LayerAdmin)
