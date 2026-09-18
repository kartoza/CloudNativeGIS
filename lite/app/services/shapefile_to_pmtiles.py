"""Convert a shapefile (zip) to PMTiles via ogr2ogr + tippecanoe."""

import os
import subprocess
import tempfile

from app.config import TMP_DIR
from app.errors import ConversionError
from app.utils.shapefile_zip import validate_shapefile_zip
from app.utils.source import resolve_source


def _run(cmd: list) -> None:
    try:
        subprocess.run(cmd, check=True, capture_output=True, text=True)
    except subprocess.CalledProcessError as e:
        raise ConversionError(
            502, f'{cmd[0]} failed: {e.stderr.strip() or e}'
        )


def convert(source: str) -> tuple:
    """Convert source shapefile zip (URL or local path) to PMTiles.

    Returns a tuple of (pmtiles_path, workdir). The caller is responsible
    for removing workdir once the response has been sent.
    """
    os.makedirs(TMP_DIR, exist_ok=True)
    workdir = tempfile.mkdtemp(dir=TMP_DIR)

    zip_path = resolve_source(source, workdir)
    validate_shapefile_zip(zip_path)

    geojson_path = os.path.join(workdir, 'output.geojson')
    _run([
        'ogr2ogr',
        '-t_srs', 'EPSG:4326',
        geojson_path,
        f'/vsizip/{zip_path}',
    ])

    pmtiles_path = os.path.join(workdir, 'output.pmtiles')
    _run([
        'tippecanoe',
        '-zg',
        '--projection=EPSG:4326',
        '-o', pmtiles_path,
        '-l', 'default',
        geojson_path,
    ])

    return pmtiles_path, workdir
