# coding=utf-8


from django.apps import AppConfig


class Config(AppConfig):
    """Documentation app."""

    name = 'tenants'
    verbose_name = "GeoSight tenant"


default_app_config = 'tenants.Config'
