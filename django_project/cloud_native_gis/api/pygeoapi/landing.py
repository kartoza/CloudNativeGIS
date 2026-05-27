# coding=utf-8
# SPDX-FileCopyrightText: 2024 Kartoza <info@kartoza.com>
# SPDX-License-Identifier: AGPL-3.0-or-later
"""OGC API landing page, OpenAPI document, and conformance views."""

import pygeoapi.api as core_api
from django.http import HttpRequest, HttpResponse

from .base import get_resources, execute_with_config


def landing_page(request: HttpRequest) -> HttpResponse:
    """
    Return the OGC API landing page.

    Provides links to the API capabilities including the OpenAPI document,
    conformance classes, and available collections.

    :param request: incoming Django HTTP request
    :type request: HttpRequest
    :returns: OGC API landing page as JSON or HTML
    :rtype: HttpResponse
    """
    config = get_resources(request)
    return execute_with_config(core_api.landing_page, config, request)


def openapi(request: HttpRequest) -> HttpResponse:
    """
    Return the OpenAPI 3.x document describing this OGC API instance.

    :param request: incoming Django HTTP request
    :type request: HttpRequest
    :returns: OpenAPI document as JSON or YAML
    :rtype: HttpResponse
    """
    config = get_resources(request)
    return execute_with_config(core_api.openapi_, config, request)


def conformance(request: HttpRequest) -> HttpResponse:
    """
    Return the list of OGC conformance classes implemented by this API.

    :param request: incoming Django HTTP request
    :type request: HttpRequest
    :returns: conformance declaration as JSON
    :rtype: HttpResponse
    """
    config = get_resources(request)
    return execute_with_config(core_api.conformance, config, request)
