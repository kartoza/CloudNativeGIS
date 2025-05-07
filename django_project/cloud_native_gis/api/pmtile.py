# coding=utf-8
"""Cloud Native GIS – PMTiles view."""
from __future__ import annotations

import os
import re
from pathlib import Path

from django.http import FileResponse, Http404, HttpResponse
from django.shortcuts import get_object_or_404

from cloud_native_gis.models import Layer

RANGE_RE = re.compile(r"bytes=(\d+)-(\d*)")

MIME_PMtiles = "application/vnd.pmtiles"


def _file_response(
    file_obj,
    status: int = 200,
    headers: dict[str, str] | None = None,
) -> HttpResponse:
    """Helper to build an HttpResponse with common headers."""
    resp = HttpResponse(file_obj, status=status)
    resp["Content-Type"] = MIME_PMtiles
    resp["Accept-Ranges"] = "bytes"
    if headers:
        for k, v in headers.items():
            resp[k] = v
    return resp


def serve_pmtiles(request, layer_uuid):
    """
    Serve a PMTiles archive with full Range‑request support.
    """
    layer = get_object_or_404(Layer, unique_id=layer_uuid)

    if not layer.pmtile:
        raise Http404("PMTiles file not found for this layer.")

    full_path = Path(layer.pmtile.path)
    if not full_path.is_file():
        raise Http404("PMTiles file does not exist.")

    file_size = full_path.stat().st_size
    range_header = request.headers.get("Range")

    if range_header:
        if match := RANGE_RE.fullmatch(range_header):
            start = int(match.group(1))
            end_raw = match.group(2)
            end = int(end_raw) if end_raw else file_size - 1

            if start >= file_size:
                return _file_response(
                    b"",
                    status=416,
                    headers={"Content-Range": f"bytes */{file_size}"},
                )

            end = min(end, file_size - 1)
            length = end - start + 1

            with open(full_path, "rb") as fh:
                fh.seek(start)
                data = fh.read(length)

            return _file_response(
                data,
                status=206,
                headers={
                    "Content-Length": str(length),
                    "Content-Range": f"bytes {start}-{end}/{file_size}",
                },
            )

    response = FileResponse(open(full_path, "rb"))
    response["Content-Type"] = MIME_PMtiles
    response["Accept-Ranges"] = "bytes"
    response["Content-Length"] = str(file_size)
    return response
