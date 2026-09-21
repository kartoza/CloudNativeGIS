"""Inspect a GeoPackage's layers without converting them."""

import os
import shutil
import tempfile

from app.config import TMP_DIR
from app.utils.gpkg import list_layers
from app.utils.source import resolve_source


def inspect(source: str) -> list:
    """Download source (an s3:// URI, http(s) URL, or local path) and
    list its layers.
    """
    os.makedirs(TMP_DIR, exist_ok=True)
    workdir = tempfile.mkdtemp(dir=TMP_DIR)
    try:
        gpkg_path = resolve_source(source, workdir)
        return list_layers(gpkg_path)
    finally:
        shutil.rmtree(workdir, ignore_errors=True)
