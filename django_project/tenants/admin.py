# coding=utf-8
"""Context Layer Management."""


from django.contrib import admin
from django_tenants.admin import TenantAdminMixin

from tenants.models import Client, Domain


@admin.register(Client)
class ClientAdmin(TenantAdminMixin, admin.ModelAdmin):
    """Tenant admin."""

    list_display = ('name', 'schema_name')


@admin.register(Domain)
class DomainAdmin(TenantAdminMixin, admin.ModelAdmin):
    """Domain admin."""

    list_display = ('domain', 'tenant', 'schema_name', 'is_primary')
