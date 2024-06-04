# coding=utf-8
"""Context Layer Management."""

from django.contrib.auth import get_user_model
from django.db import models

from context_layer_management.models.general import (
    AbstractTerm, AbstractResource
)

User = get_user_model()


class Style(AbstractTerm, AbstractResource):
    """Model contains layer information."""

    created_by = models.ForeignKey(
        User, on_delete=models.CASCADE,
        editable=False, null=True, blank=True
    )

    style = models.JSONField(
        help_text=(
            'Contains mapbox style information.'
        )
    )

    @staticmethod
    def default_style_name(geometry_type):
        """Return default style name based on geometry type."""
        return f'Default {geometry_type.lower()}'

    @property
    def is_default_style(self):
        """Return default style."""
        return self.name in [
            Style.default_style_name('point'),
            Style.default_style_name('linestring'),
            Style.default_style_name('polygon'),
        ]


POINT = {
    "layers": [
        {
            "id": "<uuid>",
            "type": "circle",
            "paint": {
                "circle-color": "#ff7800",
                "circle-radius": 4,
                "circle-opacity": 1
            },
            "filter": ["==", "$type", "Point"],
            "source": "<uuid>",
            "source-layer": "default"
        }
    ]
}
LINE = {
    "layers": [
        {
            "id": "<uuid>",
            "type": "line",
            "source": "<uuid>",
            "source-layer": "default",
            "filter": ["==", "$type", "LineString"],
            "paint": {
                "line-color": "#ff7800",
                "line-width": 1
            },
        }
    ]
}

POLYGON = {
    "layers": [
        {
            "id": "<uuid>",
            "type": "fill",
            "source": "<uuid>",
            "source-layer": "default",
            "filter": ["==", "$type", "Polygon"],
            "paint": {
                "fill-color": "#ff7800",
                "fill-opacity": 0.8
            },
        }
    ]
}
