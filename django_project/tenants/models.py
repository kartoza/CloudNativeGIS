# coding=utf-8
"""Context Layer Management."""

import os

from django.contrib.auth import get_user_model
from django.db import models
from django_tenants.models import TenantMixin, DomainMixin
from django_tenants.utils import tenant_context


class Client(TenantMixin):
    """Client name for the tenant."""

    auto_create_schema = True
    name = models.CharField(max_length=100)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name

    def save(self, verbosity=1, *args, **kwargs):
        """Save client."""
        super().save(verbosity=verbosity, *args, **kwargs)
        self.create_superuser()

    def create_superuser(self, tenant=None):
        """Create superuser."""
        with tenant_context(self):
            print(
                f'Creating/updating superuser for '
                f'{tenant.schema_name if tenant else "public"}'
            )
            admin_username = os.getenv('ADMIN_USERNAME')
            admin_password = os.getenv('ADMIN_PASSWORD')
            admin_email = os.getenv('ADMIN_EMAIL')
            try:
                superuser = get_user_model().objects.get(
                    username=admin_username)
                superuser.set_password(admin_password)
                superuser.is_active = True
                superuser.email = admin_email
                superuser.save()
                print('superuser successfully updated')
            except get_user_model().DoesNotExist:
                get_user_model().objects.create_superuser(
                    admin_username,
                    admin_email,
                    admin_password
                )
                print('superuser successfully created')


class Domain(DomainMixin):
    """Client name for the tenant."""

    is_primary = models.BooleanField(
        default=True, db_index=True
    )

    @property
    def schema_name(self):
        """Return schema name of domain."""
        return self.tenant.schema_name
