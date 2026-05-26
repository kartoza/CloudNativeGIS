"""Landing page and conformance views."""

from django.http import HttpRequest, HttpResponse
import pygeoapi.api as core_api

from .base import get_resources, execute_with_config


def landing_page(request: HttpRequest) -> HttpResponse:
    config = get_resources(request)
    return execute_with_config(core_api.landing_page, config, request)


def openapi(request: HttpRequest) -> HttpResponse:
    config = get_resources(request)
    return execute_with_config(core_api.openapi_, config, request)


def conformance(request: HttpRequest) -> HttpResponse:
    config = get_resources(request)
    return execute_with_config(core_api.conformance, config, request)