"""Inspect a GeoPackage's layers without converting them."""

import os
import shutil
import tempfile

from app.config import TMP_DIR
from app.utils.gpkg import list_layers, list_raster_tables
from app.utils.source import resolve_source


def inspect(source: str) -> dict:
    """Download source and list its vector layers and raster tables.

    source may be an s3:// URI, an http(s) URL, or a local path. A
    GeoPackage can hold either or both — the caller decides whether to
    route the file to PMTiles (vector) or COG (raster) conversion.
    """
    os.makedirs(TMP_DIR, exist_ok=True)
    workdir = tempfile.mkdtemp(dir=TMP_DIR)
    try:
        gpkg_path = resolve_source(source, workdir)
        return {
            "layers": list_layers(gpkg_path),
            "rasterTables": list_raster_tables(gpkg_path),
        }
    finally:
        shutil.rmtree(workdir, ignore_errors=True)
