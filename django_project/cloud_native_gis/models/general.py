# coding=utf-8
"""Cloud Native GIS."""
from django.contrib.auth import get_user_model
from django.db import models
from django.utils import timezone

User = get_user_model()


class AbstractTerm(models.Model):
    """Abstract model for Term."""

    name = models.CharField(
        max_length=512,
        help_text='The name of data.'
    )
    description = models.TextField(
        null=True, blank=True
    )

    def __str__(self):
        return self.name

    class Meta:  # noqa: D106
        abstract = True


class AbstractResource(models.Model):
    """Abstract model with Resource."""

    created_by = models.ForeignKey(
        User, on_delete=models.CASCADE,
        editable=False,
        related_name="%(app_label)s_%(class)s_related",
        related_query_name="%(app_label)s_%(class)ss",
    )
    created_at = models.DateTimeField(
        default=timezone.now,
        editable=False
    )

    class Meta:  # noqa: D106
        abstract = True


class License(AbstractTerm):
    """License model."""

    pass
