"""Convert a TIFF or raster GeoPackage to Cloud Optimized GeoTIFF(s) via gdal_translate."""  # noqa: E501

import json
import logging
import os
import subprocess
import tempfile
from typing import List, Optional

from app import jobs
from app.config import TMP_DIR
from app.errors import ConversionError
from app.utils.cog_info import read_cog_info
from app.utils.gpkg import list_raster_tables, sanitize_layer_filename
from app.utils.tiff_source import resolve_tiff_source

logger = logging.getLogger(__name__)

COG_OPTIONS = [
    "-of",
    "COG",
    "-co",
    "COMPRESS=DEFLATE",
    "-co",
    "BLOCKSIZE=512",
    "-co",
    "STATISTICS=YES",
]
STATISTICS_KEYS = (
    "STATISTICS_MINIMUM",
    "STATISTICS_MAXIMUM",
    "STATISTICS_MEAN",
    "STATISTICS_STDDEV",
)


def _run(cmd: list) -> None:
    logger.info("Running: %s", " ".join(cmd))
    try:
        subprocess.run(cmd, check=True, capture_output=True, text=True)
    except subprocess.CalledProcessError as e:
        raise ConversionError(502, f"{cmd[0]} failed: {e.stderr.strip() or e}")


def _check_embedded_statistics(path: str) -> None:
    """Fail unless every band carries its statistics inside the file."""
    try:
        output = subprocess.run(
            ["gdalinfo", "-json", path],
            check=True,
            capture_output=True,
            text=True,
            env={**os.environ, "GDAL_PAM_ENABLED": "NO"},
        ).stdout
        bands = json.loads(output).get("bands", [])
    except (subprocess.CalledProcessError, ValueError) as e:
        raise ConversionError(502, f"Could not inspect COG {path}: {e}")
    missing = [
        band.get("band")
        for band in bands
        if not all(
            key in band.get("metadata", {}).get("", {})
            for key in STATISTICS_KEYS
        )
    ]
    if not bands or missing:
        raise ConversionError(
            502,
            "COG was written without embedded band statistics "
            f"(bands {missing or 'none'}); this GDAL build may not "
            "support the COG driver's STATISTICS option (GDAL >= 3.8).",
        )


def _translate_cog(input_path: str, output_path: str) -> None:
    _run(["gdal_translate", *COG_OPTIONS, input_path, output_path])
    _check_embedded_statistics(output_path)


def _translate_cog_3857(input_path: str, output_path: str) -> None:
    """Reproject to EPSG:3857 while producing a COG.

    maplibre-cog-protocol (used by CloudBench's Map Explorer) only renders
    Web Mercator COGs, so every COG conversion also produces this variant
    alongside the original-CRS one.
    """
    _run(
        [
            "gdalwarp",
            "-t_srs",
            "EPSG:3857",
            *COG_OPTIONS,
            input_path,
            output_path,
        ]
    )
    _check_embedded_statistics(output_path)


def _convert_geopackage(
    gpkg_path: str,
    workdir: str,
    tables: Optional[List[str]],
    job_id: Optional[str],
) -> tuple:
    """Convert each requested raster table to its own COG file.

    Each raster table becomes its own file, since a GeoPackage may hold
    several independent rasters. A table that fails to convert is
    skipped rather than aborting the rest of the GeoPackage.
    """
    table_names = tables or [
        table["name"] for table in list_raster_tables(gpkg_path)
    ]
    if not table_names:
        raise ConversionError(
            400, "The GeoPackage has no raster tables to convert."
        )

    logger.info(
        "Job %s: converting %d GeoPackage raster table(s): %s",
        job_id,
        len(table_names),
        table_names,
    )
    files = []
    errors = []
    total = len(table_names)
    for i, table_name in enumerate(table_names):
        logger.info(
            "Job %s: converting raster %d/%d: %s",
            job_id,
            i + 1,
            total,
            table_name,
        )
        if job_id:
            jobs.update_detail(
                job_id,
                f"Converting raster {i + 1}/{total}: {table_name}",
                progress=i / total,
            )
        source = f"GPKG:{gpkg_path}:{table_name}"
        stem = sanitize_layer_filename(table_name)
        filename = f"{stem}_cog.tif"
        filename_3857 = f"{stem}_cog_3857.tif"
        cog_path = os.path.join(workdir, filename)
        cog_path_3857 = os.path.join(workdir, filename_3857)
        try:
            _translate_cog(source, cog_path)
            _translate_cog_3857(source, cog_path_3857)
        except ConversionError as e:
            logger.warning(
                "Skipping GeoPackage raster table %r (job %s): %s",
                table_name,
                job_id,
                e.message,
            )
            errors.append({"name": table_name, "error": e.message})
            continue
        logger.info(
            "Job %s: raster %s converted -> %s, %s",
            job_id,
            table_name,
            filename,
            filename_3857,
        )
        info = read_cog_info(cog_path)
        files.append(
            {
                "name": filename,
                "path": cog_path,
                "media_type": "image/tiff",
                "info": info,
            }
        )
        files.append(
            {
                "name": filename_3857,
                "path": cog_path_3857,
                "media_type": "image/tiff",
                "info": info,
            }
        )

    logger.info("Job %s: %d/%d rasters converted", job_id, len(files), total)
    if job_id:
        jobs.update_detail(
            job_id, f"Converted {len(files)}/{total} rasters", progress=1.0
        )
    if not files:
        raise ConversionError(
            400,
            "None of the GeoPackage raster tables could be converted: "
            + "; ".join(f"{e['name']}: {e['error']}" for e in errors),
        )
    return files, errors


def convert(
    source: str,
    tables: Optional[List[str]] = None,
    job_id: Optional[str] = None,
) -> tuple:
    """Convert source TIFF or raster GeoPackage (s3:// URI, URL, or path).

    `tables` (GeoPackage only) selects which raster tables to include;
    omit to include all of them — each becomes its own COG file, and one
    failing table is skipped rather than failing the whole conversion.

    Every raster (the plain TIFF, or each selected GeoPackage table)
    produces two COG files: the original-CRS one and an "_3857" suffixed
    EPSG:3857 reprojection, since maplibre-cog-protocol can only render
    Web Mercator COGs.

    Returns a tuple of ([{'name', 'path', 'media_type'}, ...],
    [{'name', 'error'}, ...], workdir) — the second list is any raster
    tables that were skipped (always empty for a plain TIFF). The caller
    is responsible for removing workdir once the response has been sent.
    """
    logger.info("Job %s: starting COG conversion of %s", job_id, source)
    os.makedirs(TMP_DIR, exist_ok=True)
    workdir = tempfile.mkdtemp(dir=TMP_DIR)

    input_path = resolve_tiff_source(source, workdir)
    if input_path.lower().endswith(".gpkg"):
        files, errors = _convert_geopackage(
            input_path, workdir, tables, job_id
        )
        return files, errors, workdir

    cog_path = os.path.join(workdir, "output_cog.tif")
    cog_path_3857 = os.path.join(workdir, "output_cog_3857.tif")
    _translate_cog(input_path, cog_path)
    _translate_cog_3857(input_path, cog_path_3857)
    info = read_cog_info(cog_path)
    return (
        [
            {
                "name": "output_cog.tif",
                "path": cog_path,
                "media_type": "image/tiff",
                "info": info,
            },
            {
                "name": "output_cog_3857.tif",
                "path": cog_path_3857,
                "media_type": "image/tiff",
                "info": info,
            },
        ],
        [],
        workdir,
    )
