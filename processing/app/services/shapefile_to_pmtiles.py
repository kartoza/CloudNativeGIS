"""Convert a shapefile (zip) or GeoPackage to PMTiles + GeoParquet.

Each vector layer yields a pair: a GeoParquet file (the analysis-ready
data, in the source's own CRS) and a PMTiles file (the web-map rendering,
via ogr2ogr + tippecanoe) — the vector pairing the Portolan spec asks for.
"""

import logging
import os
import subprocess
import tempfile
from typing import List, Optional

from app import jobs
from app.config import TMP_DIR
from app.errors import ConversionError
from app.utils.gpkg import (
    list_layers as list_gpkg_layers,
    sanitize_layer_filename,
)
from app.utils.parquet_info import read_parquet_info
from app.utils.pmtiles_info import read_pmtiles_info
from app.utils.shapefile_zip import validate_shapefile_zip
from app.utils.source import resolve_source

logger = logging.getLogger(__name__)

# Guards against pathological geometry (e.g. a near-global polygon forced to
# a high zoom) turning one layer into a runaway process that never returns.
TIPPECANOE_TIMEOUT = 180

PMTILES_MEDIA_TYPE = "application/vnd.pmtiles"
PARQUET_MEDIA_TYPE = "application/vnd.apache.parquet"

# Portolan's GeoParquet requirements: GeoParquet 1.1 with a bbox covering
# column (per-row-group spatial stats), spatially ordered rows, row groups
# of at most 150k rows, zstd recommended.
GEOPARQUET_OPTIONS = [
    "-lco",
    "COMPRESSION=ZSTD",
    "-lco",
    "WRITE_COVERING_BBOX=YES",
    "-lco",
    "SORT_BY_BBOX=YES",
    "-lco",
    "ROW_GROUP_SIZE=100000",
]


def _run(cmd: list, timeout: Optional[int] = None) -> None:
    logger.info("Running: %s", " ".join(cmd))
    try:
        subprocess.run(
            cmd, check=True, capture_output=True, text=True, timeout=timeout
        )
    except subprocess.TimeoutExpired:
        raise ConversionError(502, f"{cmd[0]} timed out after {timeout}s")
    except subprocess.CalledProcessError as e:
        raise ConversionError(502, f"{cmd[0]} failed: {e.stderr.strip() or e}")


def _tile(pmtiles_path: str, layer_name: str, geojson_path: str) -> None:
    """Tiles geojson_path with an adaptively-guessed max zoom (-zg).

    Falls back to a low fixed zoom only for the one case -zg can't handle
    at all — too few distinct feature locations to guess from (e.g. a
    single point). A blanket fixed zoom is deliberately avoided otherwise:
    forcing a high zoom on a huge, simple feature (e.g. a near-world-sized
    polygon) makes tippecanoe try to tile it down to street level, which
    can run for hours — -zg picks a zoom that actually matches the data.
    """
    # --force: -zg can fail partway through after already creating
    # pmtiles_path, so a same-path retry (the -z0 fallback below) would
    # otherwise hit "tileset already exists" instead of actually retrying.
    base_cmd = [
        "tippecanoe",
        "--force",
        "--projection=EPSG:4326",
        "-o",
        pmtiles_path,
        "-l",
        layer_name,
        geojson_path,
    ]
    try:
        _run(base_cmd[:1] + ["-zg"] + base_cmd[1:], timeout=TIPPECANOE_TIMEOUT)
    except ConversionError as e:
        if "Can't guess maxzoom" not in e.message:
            raise
        _run(base_cmd[:1] + ["-z0"] + base_cmd[1:], timeout=TIPPECANOE_TIMEOUT)


def _write_geoparquet(
    parquet_path: str, source: str, layer_name: Optional[str] = None
) -> None:
    """Write one source layer as GeoParquet, keeping its original CRS.

    `layer_name` picks the layer out of a multi-layer source (GeoPackage);
    omit it for a single-layer source (shapefile).
    """
    cmd = ["ogr2ogr", "-f", "Parquet", *GEOPARQUET_OPTIONS, parquet_path, source]
    if layer_name:
        cmd.append(layer_name)
    _run(cmd)


def _layer_outputs(stem: str, pmtiles_path: str, parquet_path: str) -> list:
    return [
        {
            "name": f"{stem}.parquet",
            "path": parquet_path,
            "media_type": PARQUET_MEDIA_TYPE,
            "info": read_parquet_info(parquet_path),
        },
        {
            "name": f"{stem}.pmtiles",
            "path": pmtiles_path,
            "media_type": PMTILES_MEDIA_TYPE,
            "info": read_pmtiles_info(pmtiles_path),
        },
    ]


def _convert_geopackage(
    gpkg_path: str,
    workdir: str,
    layers: Optional[List[str]],
    job_id: Optional[str],
) -> tuple:
    """Convert each requested layer to its own PMTiles + GeoParquet pair.

    Each vector layer becomes its own files (not merged), since each is
    independently useful as a map layer. A layer that fails (e.g. an
    unsupported geometry type) is skipped rather than aborting the rest
    of the GeoPackage.
    """
    layer_names = layers or [
        layer["name"] for layer in list_gpkg_layers(gpkg_path)
    ]
    if not layer_names:
        raise ConversionError(400, "The GeoPackage has no layers to convert.")

    logger.info(
        "Job %s: converting %d GeoPackage layer(s): %s",
        job_id,
        len(layer_names),
        layer_names,
    )
    files = []
    errors = []
    total = len(layer_names)
    for i, layer_name in enumerate(layer_names):
        logger.info(
            "Job %s: converting layer %d/%d: %s",
            job_id,
            i + 1,
            total,
            layer_name,
        )
        if job_id:
            jobs.update_detail(
                job_id,
                f"Converting layer {i + 1}/{total}: {layer_name}",
                progress=i / total,
            )
        try:
            stem = sanitize_layer_filename(layer_name)
            parquet_path = os.path.join(workdir, f"{stem}.parquet")
            _write_geoparquet(parquet_path, gpkg_path, layer_name)
            geojson_path = os.path.join(workdir, f"{stem}.geojson")
            _run(
                [
                    "ogr2ogr",
                    "-t_srs",
                    "EPSG:4326",
                    "-nln",
                    layer_name,
                    geojson_path,
                    gpkg_path,
                    layer_name,
                ]
            )
            pmtiles_path = os.path.join(workdir, f"{stem}.pmtiles")
            _tile(pmtiles_path, layer_name, geojson_path)
        except ConversionError as e:
            logger.warning(
                "Skipping GeoPackage layer %r (job %s): %s",
                layer_name,
                job_id,
                e.message,
            )
            errors.append({"name": layer_name, "error": e.message})
            continue
        logger.info(
            "Job %s: layer %s converted -> %s",
            job_id,
            layer_name,
            f"{stem}.pmtiles + {stem}.parquet",
        )
        files.extend(_layer_outputs(stem, pmtiles_path, parquet_path))

    converted = total - len(errors)
    logger.info("Job %s: %d/%d layers converted", job_id, converted, total)
    if job_id:
        jobs.update_detail(
            job_id, f"Converted {converted}/{total} layers", progress=1.0
        )
    if not files:
        raise ConversionError(
            400,
            "None of the GeoPackage layers could be converted: "
            + "; ".join(f"{e['name']}: {e['error']}" for e in errors),
        )
    return files, errors


def convert(
    source: str,
    layers: Optional[List[str]] = None,
    job_id: Optional[str] = None,
) -> tuple:
    """Convert source (shapefile zip or GeoPackage; URL or local path).

    `layers` (GeoPackage only) selects which layers to include; omit to
    include all of them — each becomes its own PMTiles + GeoParquet pair, and one
    failing layer is skipped rather than failing the whole conversion.
    `job_id`, if given, receives live per-layer progress via
    app.jobs.update_detail.

    Returns a tuple of ([{'name', 'path', 'media_type', 'info'}, ...],
    [{'name', 'error'}, ...], workdir) — the second list is any GeoPackage
    layers that were skipped (always empty for a shapefile). The caller is
    responsible for removing workdir once the response has been sent.
    """
    logger.info("Job %s: starting PMTiles conversion of %s", job_id, source)
    os.makedirs(TMP_DIR, exist_ok=True)
    workdir = tempfile.mkdtemp(dir=TMP_DIR)

    input_path = resolve_source(source, workdir)
    if input_path.lower().endswith(".gpkg"):
        files, errors = _convert_geopackage(
            input_path, workdir, layers, job_id
        )
        return files, errors, workdir

    validate_shapefile_zip(input_path)
    parquet_path = os.path.join(workdir, "output.parquet")
    _write_geoparquet(parquet_path, f"/vsizip/{input_path}")
    geojson_path = os.path.join(workdir, "output.geojson")
    _run(
        [
            "ogr2ogr",
            "-t_srs",
            "EPSG:4326",
            geojson_path,
            f"/vsizip/{input_path}",
        ]
    )

    pmtiles_path = os.path.join(workdir, "output.pmtiles")
    _tile(pmtiles_path, "default", geojson_path)

    return _layer_outputs("output", pmtiles_path, parquet_path), [], workdir
