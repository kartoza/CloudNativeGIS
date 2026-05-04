# SPDX-FileCopyrightText: 2024 Kartoza <info@kartoza.com>
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Cloud Native GIS.

.. note:: Context Layer App.
"""

from __future__ import absolute_import, unicode_literals

from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class ContextLayerConfig(AppConfig):
    """Context Layer Config App."""

    name = 'cloud_native_gis'
    verbose_name = _('Cloud Native Layer')
