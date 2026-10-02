"""Convert a vector source to PMTiles + GeoParquet.

Sources: a shapefile (zip), a GeoPackage, or a single GeoJSON, FlatGeobuf
or KML/KMZ file.

Each vector layer yields a pair: a GeoParquet file (the analysis-ready
data, in the source's own CRS) and a PMTiles file (the web-map rendering,
via ogr2ogr + tippecanoe) — the vector pairing the Portolan spec asks for.
"""

import logging
import os
import re
import subprocess
import tempfile
import time
from concurrent.futures import ThreadPoolExecutor
from typing import Callable, List, Optional

from app import jobs
from app.config import TMP_DIR
from app.errors import ConversionError
from app.utils.gpkg import (
    list_layers as list_gpkg_layers,
    sanitize_layer_filename,
)
from app.utils.parquet_info import read_parquet_info
from app.utils import thumbnail
from app.utils.pmtiles_info import read_pmtiles_info
from app.utils.shapefile_zip import validate_shapefile_zip
from app.utils.source import VECTOR_FILE_SUFFIXES, resolve_source
from app.utils.spatial_order import sort_spatially

logger = logging.getLogger(__name__)

# Guards against pathological geometry (e.g. a near-global polygon forced to
# a high zoom) turning one layer into a runaway process that never returns,
# while giving a big layer the time it genuinely needs: a base, plus time
# per GB of features, capped. (2.8 million buildings, 1.1 GB, take ~3
# minutes on 16 cores; a runaway is usually a small file.)
TIPPECANOE_BASE_TIMEOUT = 300
TIPPECANOE_TIMEOUT_PER_GB = 20 * 60
TIPPECANOE_MAX_TIMEOUT = 3 * 60 * 60

# A step's report of its progress: (what it's doing, fraction of it done).
Report = Callable[[str, float], None]

PMTILES_MEDIA_TYPE = "application/vnd.pmtiles"
PARQUET_MEDIA_TYPE = "application/vnd.apache.parquet"

# Portolan's GeoParquet requirements: GeoParquet 1.1 with a bbox covering
# column (per-row-group spatial stats), spatially ordered rows, row groups
# of at most 150k rows, zstd recommended. The rows are ordered afterwards
# (see sort_spatially): GDAL's SORT_BY_BBOX doesn't order them closely
# enough for Portolan.
GEOPARQUET_ROW_GROUP_SIZE = 100000
GEOPARQUET_OPTIONS = [
    "-lco",
    "COMPRESSION=ZSTD",
    "-lco",
    "WRITE_COVERING_BBOX=YES",
    "-lco",
    f"ROW_GROUP_SIZE={GEOPARQUET_ROW_GROUP_SIZE}",
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


def tippecanoe_timeout(geojson_path: str) -> int:
    """Seconds to allow tippecanoe for this input, scaled to its size."""
    gigabytes = os.path.getsize(geojson_path) / 1024**3
    scaled = TIPPECANOE_BASE_TIMEOUT + TIPPECANOE_TIMEOUT_PER_GB * gigabytes
    return int(min(scaled, TIPPECANOE_MAX_TIMEOUT))


# tippecanoe's progress on stderr: "Maxzoom: 42%" while it works out the
# zoom levels, then "13/4296/2912  85.0%" while it writes tiles.
_ZOOM_PROGRESS = re.compile(r"Maxzoom: (\d+)%")
_TILE_PROGRESS = re.compile(r"\d+/\d+/\d+\s+(\d+(?:\.\d+)?)%")


def _run_tippecanoe(cmd: list, timeout: int, report: Report) -> None:
    """Run tippecanoe, relaying its progress through report as it goes."""
    logger.info("Running: %s", " ".join(cmd))
    process = subprocess.Popen(
        cmd, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE
    )
    deadline = time.monotonic() + timeout
    tail = ""
    last = None
    # Progress lines end in "\r", so read chunks rather than lines.
    for chunk in iter(lambda: process.stderr.read1(4096), b""):
        if time.monotonic() > deadline:
            process.kill()
            process.wait()
            raise ConversionError(
                502, f"tippecanoe timed out after {timeout}s"
            )
        tail = (tail + chunk.decode(errors="replace"))[-4000:]
        zoom = _ZOOM_PROGRESS.findall(tail)
        tiles = _TILE_PROGRESS.findall(tail)
        if tiles:
            step = ("Generating vector tiles", float(tiles[-1]) / 100)
        elif zoom:
            step = ("Choosing zoom levels", float(zoom[-1]) / 100)
        else:
            continue
        # Only when the step or its whole percentage changes.
        key = (step[0], int(step[1] * 100))
        if key != last:
            last = key
            report(*step)
    remaining = deadline - time.monotonic()
    try:
        returncode = process.wait(timeout=max(remaining, 1))
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait()
        raise ConversionError(502, f"tippecanoe timed out after {timeout}s")
    if returncode != 0:
        # Just the messages, not the progress counters.
        message = _TILE_PROGRESS.sub("", _ZOOM_PROGRESS.sub("", tail))
        raise ConversionError(
            502, f"tippecanoe failed: {message.strip()[-800:]}"
        )


def _tile(
    pmtiles_path: str,
    layer_name: str,
    geojson_path: str,
    report: Report = lambda *_: None,
) -> None:
    """Tiles geojson_path with an adaptively-guessed max zoom (-zg).

    geojson_path is line-delimited GeoJSON (GeoJSONSeq), which tippecanoe
    reads in parallel (-P). Falls back to a low fixed zoom only for the
    one case -zg can't handle at all — too few distinct feature locations
    to guess from (e.g. a single point). A blanket fixed zoom is
    deliberately avoided otherwise: forcing a high zoom on a huge, simple
    feature (e.g. a near-world-sized polygon) makes tippecanoe try to tile
    it down to street level, which can run for hours — -zg picks a zoom
    that actually matches the data.
    """
    # --force: -zg can fail partway through after already creating
    # pmtiles_path, so a same-path retry (the -z0 fallback below) would
    # otherwise hit "tileset already exists" instead of actually retrying.
    base_cmd = [
        "tippecanoe",
        "--force",
        "-P",
        "--projection=EPSG:4326",
        "-o",
        pmtiles_path,
        "-l",
        layer_name,
        geojson_path,
    ]
    timeout = tippecanoe_timeout(geojson_path)
    try:
        _run_tippecanoe(base_cmd[:1] + ["-zg"] + base_cmd[1:], timeout, report)
    except ConversionError as e:
        if "Can't guess maxzoom" not in e.message:
            raise
        _run_tippecanoe(base_cmd[:1] + ["-z0"] + base_cmd[1:], timeout, report)


def _source_srs(source: str, layer_name: Optional[str]) -> list:
    """Options assuming WGS84 for a layer with no coordinate system.

    A shapefile without its .prj (or a layer without an SRS) has none,
    and reprojecting it fails outright; WGS84 is the usual case for such
    files, so it's assumed rather than refusing the upload.
    """
    import pyogrio

    try:
        crs = pyogrio.read_info(source, layer=layer_name).get("crs")
    except Exception:  # unreadable here: ogr2ogr will report it properly
        return []
    if crs:
        return []
    logger.info("%s has no coordinate system: assuming WGS84", source)
    return ["-s_srs", "EPSG:4326"]


def _single_layer(path: str, workdir: str) -> str:
    """Read path as one layer, merging a KML/KMZ's folders if several.

    LIBKML reads each <Folder> as its own layer, and GeoParquet holds one,
    so a multi-folder KML is merged into a GeoPackage layer first - each
    feature's folder kept in a "folder" column. Other sources (GeoJSON,
    FlatGeobuf, a single-folder KML) are read as they are.
    """
    import pyogrio

    try:
        layers = pyogrio.list_layers(path)
    except Exception as e:
        raise ConversionError(400, f"Could not read the file: {e}")
    if len(layers) == 0:
        raise ConversionError(
            400, "The file has no vector layers to convert."
        )
    if len(layers) == 1:
        return path
    merged_path = os.path.join(workdir, "merged.gpkg")
    _run(
        [
            "ogrmerge.py",
            "-single",
            "-f",
            "GPKG",
            "-o",
            merged_path,
            "-nln",
            "merged",
            # As every other source's GeoParquet names it (not "geom").
            "-lco",
            "GEOMETRY_NAME=geometry",
            "-src_layer_field_name",
            "folder",
            "-src_layer_field_content",
            "{LAYER_NAME}",
            path,
        ]
    )
    return merged_path


def _write_geoparquet(
    parquet_path: str,
    source: str,
    layer_name: Optional[str] = None,
    srs: Optional[list] = None,
) -> None:
    """Write one source layer as GeoParquet, keeping its original CRS.

    `layer_name` picks the layer out of a multi-layer source (GeoPackage);
    omit it for a single-layer source (shapefile). Its rows are then put in
    spatial order (see sort_spatially).
    """
    cmd = [
        "ogr2ogr",
        "-f",
        "Parquet",
        *GEOPARQUET_OPTIONS,
        # Without a CRS of its own, record the one assumed for the tiles.
        *(["-a_srs", "EPSG:4326"] if srs else []),
        parquet_path,
        source,
    ]
    if layer_name:
        cmd.append(layer_name)
    _run(cmd)
    sort_spatially(parquet_path, GEOPARQUET_ROW_GROUP_SIZE)


def _export_for_tiling(
    geojson_path: str,
    source: str,
    layer_name: Optional[str] = None,
    srs: Optional[list] = None,
) -> None:
    """Export a layer as line-delimited WGS84 GeoJSON, for tippecanoe."""
    cmd = ["ogr2ogr", "-f", "GeoJSONSeq", *(srs or []), "-t_srs", "EPSG:4326"]
    cmd += [geojson_path, source]
    if layer_name:
        cmd.append(layer_name)
    _run(cmd)


def _convert_layer(
    source: str,
    layer_name: Optional[str],
    tile_layer: str,
    stem: str,
    workdir: str,
    report: Report,
    with_thumbnail: bool = False,
) -> tuple:
    """Convert one layer: (pmtiles path, parquet path, thumbnail or None).

    The GeoParquet and the thumbnail only read the source, as the tiling
    does, so they're made alongside it rather than one after another.
    Progress never goes back: exporting features is 0-20%, tippecanoe
    choosing zoom levels 20-30%, writing tiles 30-100%; the GeoParquet's
    and thumbnail's states are noted as they go.
    """
    parquet_path = os.path.join(workdir, f"{stem}.parquet")
    geojson_path = os.path.join(workdir, f"{stem}.geojsonl")
    pmtiles_path = os.path.join(workdir, f"{stem}.pmtiles")
    thumbnail_path = os.path.join(workdir, f"{stem}_thumbnail.png")
    srs = _source_srs(source, layer_name)

    with ThreadPoolExecutor(max_workers=2) as pool:
        side = {
            "GeoParquet": pool.submit(
                _write_geoparquet, parquet_path, source, layer_name, srs
            )
        }
        if with_thumbnail:
            side["thumbnail"] = pool.submit(
                thumbnail.render_vector_thumbnail,
                source,
                thumbnail_path,
                layer=layer_name,
            )

        def note() -> str:
            return ", ".join(
                f"{name} ready" if task.done() else f"making {name}"
                for name, task in side.items()
            )

        report(f"Preparing features for the map · {note()}", 0.0)
        _export_for_tiling(geojson_path, source, layer_name, srs)

        phases = {"Choosing zoom levels": (0.2, 0.1)}
        best = {"fraction": 0.2, "percent": {}}

        def tiling(step: str, fraction: float) -> None:
            start, span = phases.get(step, (0.3, 0.7))
            # tippecanoe's percentages restart between its passes.
            percent = max(best["percent"].get(step, 0), int(fraction * 100))
            best["percent"][step] = percent
            best["fraction"] = max(best["fraction"], start + span * fraction)
            report(
                f"{step} (PMTiles): {percent}% · {note()}", best["fraction"]
            )

        _tile(pmtiles_path, tile_layer, geojson_path, tiling)
        os.remove(geojson_path)
        waiting = [name for name, task in side.items() if not task.done()]
        if waiting:
            report(f"Vector tiles ready · finishing {', '.join(waiting)}", 1.0)
        side["GeoParquet"].result()  # raises its error, if it failed
        if with_thumbnail:
            side["thumbnail"].result()  # best-effort: False if not drawn
    return (
        pmtiles_path,
        parquet_path,
        thumbnail_path if os.path.exists(thumbnail_path) else None,
    )


def _thumbnail_output(
    name: str, path: str, layer: Optional[str] = None
) -> list:
    """Return the thumbnail as a result file, or nothing if not rendered."""
    if not os.path.exists(path):
        return []
    return [
        {
            "name": name,
            "path": path,
            "media_type": thumbnail.MEDIA_TYPE,
            "info": {},
            "layer": layer,
            "role": "thumbnail",
        }
    ]


def _layer_outputs(
    stem: str,
    pmtiles_path: str,
    parquet_path: str,
    thumbnail_path: Optional[str] = None,
    layer: Optional[str] = None,
) -> list:
    """Return a converted layer's result files (the thumbnail, if drawn).

    Each is tagged with its layer (None for a single-layer source) and
    role - data (GeoParquet), visual (PMTiles), thumbnail - by which a
    caller's upload URLs are matched to it (see app.utils.upload).
    """
    thumbnail_files = (
        _thumbnail_output(f"{stem}_thumbnail.png", thumbnail_path, layer)
        if thumbnail_path
        else []
    )
    return thumbnail_files + [
        {
            "name": f"{stem}.parquet",
            "path": parquet_path,
            "media_type": PARQUET_MEDIA_TYPE,
            "info": read_parquet_info(parquet_path),
            "layer": layer,
            "role": "data",
        },
        {
            "name": f"{stem}.pmtiles",
            "path": pmtiles_path,
            "media_type": PMTILES_MEDIA_TYPE,
            "info": read_pmtiles_info(pmtiles_path),
            "layer": layer,
            "role": "visual",
        },
    ]


def _reporter(job_id: Optional[str], prefix: str, index: int, total: int):
    """Build the Report for layer `index` of `total`: the job's progress.

    The job's fraction is that layer's share of all of them; `prefix`
    (e.g. "Layer 2/5 (roads)") leads each message.
    """

    def report(step: str, fraction: float) -> None:
        if job_id:
            jobs.update_detail(
                job_id,
                f"{prefix}: {step}" if prefix else step,
                progress=(index + fraction) / total,
            )

    return report


def _convert_geopackage(
    gpkg_path: str,
    workdir: str,
    layers: Optional[List[str]],
    job_id: Optional[str],
    with_thumbnails: bool = False,
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
        report = _reporter(
            job_id, f"Layer {i + 1}/{total} ({layer_name})", i, total
        )
        try:
            stem = sanitize_layer_filename(layer_name)
            pmtiles_path, parquet_path, thumbnail_path = _convert_layer(
                gpkg_path,
                layer_name,
                layer_name,
                stem,
                workdir,
                report,
                with_thumbnails,
            )
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
        files.extend(
            _layer_outputs(
                stem, pmtiles_path, parquet_path, thumbnail_path, layer_name
            )
        )

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
    with_thumbnails: bool = False,
) -> tuple:
    """Convert source: a URL or local path.

    The source is a shapefile zip, GeoPackage, GeoJSON, FlatGeobuf or
    KML/KMZ.

    `layers` (GeoPackage only) selects which layers to include; omit to
    include all of them — each becomes its own PMTiles + GeoParquet pair,
    and one failing layer is skipped rather than failing the whole
    conversion.
    `job_id`, if given, receives live per-layer progress via
    app.jobs.update_detail. `with_thumbnails` also renders each layer's
    "{stem}_thumbnail.png" from its default style.

    Returns a tuple of ([{'name', 'path', 'media_type', 'info'}, ...],
    [{'name', 'error'}, ...], workdir) — the second list is any GeoPackage
    layers that were skipped (always empty for a single-layer source). The
    caller is responsible for removing workdir once the response has been
    sent.
    """
    logger.info("Job %s: starting PMTiles conversion of %s", job_id, source)
    os.makedirs(TMP_DIR, exist_ok=True)
    workdir = tempfile.mkdtemp(dir=TMP_DIR)

    if job_id:
        jobs.update_detail(job_id, "Downloading the source file", 0.0)
    input_path = resolve_source(source, workdir)
    if input_path.lower().endswith(".gpkg"):
        files, errors = _convert_geopackage(
            input_path, workdir, layers, job_id, with_thumbnails
        )
        return files, errors, workdir

    if input_path.lower().endswith(VECTOR_FILE_SUFFIXES):
        layer_source = _single_layer(input_path, workdir)
    else:
        validate_shapefile_zip(input_path)
        layer_source = f"/vsizip/{input_path}"
    report = _reporter(job_id, "", 0, 1)
    pmtiles_path, parquet_path, thumbnail_path = _convert_layer(
        layer_source,
        None,
        "default",
        "output",
        workdir,
        report,
        with_thumbnails,
    )
    files = _layer_outputs(
        "output", pmtiles_path, parquet_path, thumbnail_path
    )
    return files, [], workdir
