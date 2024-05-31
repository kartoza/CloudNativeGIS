# coding=utf-8
"""Context Layer Management."""

from django.urls import reverse

from context_layer_management.models.layer import Layer
from context_layer_management.models.style import Style


def layer_style_url(obj: Layer, style: Style, request) -> str:
    """Return layer style url."""
    return request.build_absolute_uri('/')[:-1] + reverse(
        'context-layer-management-style-view-set-detail',
        kwargs={
            'layer_id': obj.id,
            'id': style.id
        }
    )
