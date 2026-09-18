"""Convert a TIFF to a Cloud Optimized GeoTIFF (COG) via gdal_translate."""

import os
import subprocess
import tempfile

from app.config import TMP_DIR
from app.errors import ConversionError
from app.utils.tiff_source import resolve_tiff_source


def _run(cmd: list) -> None:
    try:
        subprocess.run(cmd, check=True, capture_output=True, text=True)
    except subprocess.CalledProcessError as e:
        raise ConversionError(
            502, f'{cmd[0]} failed: {e.stderr.strip() or e}'
        )


def convert(source: str) -> tuple:
    """Convert source TIFF (s3:// URI, URL, or local path) to a COG.

    Returns a tuple of (cog_path, workdir). The caller is responsible
    for removing workdir once the response has been sent.
    """
    os.makedirs(TMP_DIR, exist_ok=True)
    workdir = tempfile.mkdtemp(dir=TMP_DIR)

    tiff_path = resolve_tiff_source(source, workdir)

    cog_path = os.path.join(workdir, 'output_cog.tif')
    _run([
        'gdal_translate',
        '-of', 'COG',
        '-co', 'COMPRESS=DEFLATE',
        tiff_path,
        cog_path,
    ])

    return cog_path, workdir
