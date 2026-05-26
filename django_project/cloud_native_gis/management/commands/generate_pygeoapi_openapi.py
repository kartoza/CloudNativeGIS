# coding=utf-8
# SPDX-FileCopyrightText: 2024 Kartoza <info@kartoza.com>
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Management command to generate pygeoapi OpenAPI document."""

from django.core.management.base import BaseCommand
from django.conf import settings


class Command(BaseCommand):
    help = 'Generate pygeoapi OpenAPI document from pygeoapi-config.yml'

    def handle(self, *args, **options):
        import os
        import yaml
        from pygeoapi.openapi import get_oas

        config = settings.PYGEOAPI_CONFIG
        openapi_path = settings.PYGEOAPI_OPENAPI

        self.stdout.write(
            f'Reading config from: {os.environ.get("PYGEOAPI_CONFIG")}'
        )

        openapi = get_oas(config)

        with open(openapi_path, 'w') as f:
            yaml.dump(openapi, f, default_flow_style=False, allow_unicode=True)

        self.stdout.write(
            self.style.SUCCESS(f'OpenAPI document written to: {openapi_path}')
        )