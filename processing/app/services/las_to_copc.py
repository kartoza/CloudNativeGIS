"""Convert a LAS/LAZ point cloud to Cloud Optimized Point Cloud (COPC).

COPC is a LAZ file whose points are organised in an octree, so a client
reads only the part (and the level of detail) it shows - Portolan's
cloud-native format for point clouds. The conversion is PDAL's
writers.copc; the thumbnail is the points' elevation gridded into a small
raster and coloured.
"""

import json
import logging
import os
import shutil
import subprocess
import tempfile
from typing import Optional

from pyproj import CRS, Transformer

from app import jobs
from app.config import TMP_DIR
from app.errors import ConversionError
from app.utils import thumbnail
from app.utils.http import download_url
from app.utils.s3 import download_object, parse_s3_uri

logger = logging.getLogger(__name__)

COPC_MEDIA_TYPE = "application/vnd.laszip+copc"
POINT_CLOUD_SUFFIXES = (".las", ".laz")
# Converting is PDAL reading every point: generous, as for tiling.
PDAL_TIMEOUT = 3 * 60 * 60
INFO_TIMEOUT = 300
# Elevation, low to high, for the thumbnail (gdaldem color-relief).
ELEVATION_RAMP = """nv 0 0 0 0
0% 43 131 186
25% 171 221 164
50% 255 255 191
75% 253 174 97
100% 215 25 28
"""


def _run(
    cmd: list, timeout: int = PDAL_TIMEOUT, stdin: Optional[str] = None
) -> str:
    logger.info("Running: %s", " ".join(cmd))
    try:
        result = subprocess.run(
            cmd,
            input=stdin,
            check=True,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
    except subprocess.CalledProcessError as e:
        raise ConversionError(
            500, f"{cmd[0]} failed: {(e.stderr or e.stdout or '').strip()}"
        )
    except subprocess.TimeoutExpired:
        raise ConversionError(504, f"{cmd[0]} timed out")
    return result.stdout


def _resolve_source(source: str, workdir: str) -> str:
    """Fetch source (s3:// URI, URL or absolute path) as a local file.

    Keeps its .las/.laz suffix, which is how PDAL picks the reader.
    """
    path = source.split("?", 1)[0].lower()
    suffix = next((s for s in POINT_CLOUD_SUFFIXES if path.endswith(s)), "")
    if not suffix:
        raise ConversionError(400, "The source must be a .las or .laz file.")
    dest_path = os.path.join(workdir, f"input{suffix}")
    if source.startswith("s3://"):
        bucket, key = parse_s3_uri(source)
        download_object(bucket, key, dest_path)
    elif source.startswith(("http://", "https://")):
        download_url(source, dest_path)
    else:
        if not os.path.isabs(source):
            raise ConversionError(400, "Local source path must be absolute")
        if not os.path.isfile(source):
            raise ConversionError(
                400, f"Source file does not exist: {source}"
            )
        shutil.copyfile(source, dest_path)
    return dest_path


def _header(path: str) -> dict:
    """Read a point cloud's header: bounds, point count, CRS (no points)."""
    output = _run(["pdal", "info", "--metadata", path], INFO_TIMEOUT)
    return json.loads(output)["metadata"]


def _horizontal_crs(header: dict) -> CRS:
    """Return the point cloud's horizontal CRS; fail if it has none.

    LAS coordinates are almost always projected, so - unlike a shapefile
    without a .prj - assuming WGS84 would put the data in the wrong place.
    """
    wkt = (header.get("srs") or {}).get("wkt") or header.get(
        "comp_spatialreference", ""
    )
    if not wkt:
        raise ConversionError(
            400,
            "The point cloud has no coordinate system, so it can't be "
            "placed on a map. Assign one (e.g. pdal translate with "
            "--writers.las.a_srs) and upload it again.",
        )
    return CRS.from_wkt(wkt).to_2d()


def _wgs84_bbox(header: dict, crs: CRS) -> list:
    """Return the header's bounds, reprojected to WGS84 (west, south, ...)."""
    transformer = Transformer.from_crs(
        crs, CRS.from_epsg(4326), always_xy=True
    )
    return list(
        transformer.transform_bounds(
            header["minx"],
            header["miny"],
            header["maxx"],
            header["maxy"],
            densify_pts=21,
        )
    )


def _dimensions(path: str) -> list:
    """List the point cloud's dimensions: [{'name', 'size', 'type'}, ...]."""
    output = _run(["pdal", "info", "--schema", path], INFO_TIMEOUT)
    dimensions = json.loads(output)["schema"]["dimensions"]
    return [
        {"name": d["name"], "size": d["size"], "type": d["type"]}
        for d in dimensions
    ]


def _crs_id(crs: CRS) -> Optional[str]:
    authority = crs.to_authority()
    return f"{authority[0]}:{authority[1]}" if authority else None


def _thumbnail(copc_path: str, workdir: str, header: dict) -> list:
    """Render the points' elevation as the thumbnail (nothing on failure).

    Gridded in Web Mercator at about thumbnail size from a coarse level of
    the COPC octree, so even a huge cloud reads only a sample.
    """
    grid = os.path.join(workdir, "thumbnail_grid.tif")
    coloured = os.path.join(workdir, "thumbnail_rgba.tif")
    ramp = os.path.join(workdir, "elevation_ramp.txt")
    path = os.path.join(workdir, "output_thumbnail.png")
    try:
        crs = _horizontal_crs(header)
        west, south, east, north = Transformer.from_crs(
            crs, CRS.from_epsg(3857), always_xy=True
        ).transform_bounds(
            header["minx"], header["miny"], header["maxx"], header["maxy"]
        )
        resolution = max(east - west, north - south) / thumbnail.SIZE
        pipeline = [
            {
                "type": "readers.copc",
                "filename": copc_path,
                "resolution": resolution,
            },
            {"type": "filters.reprojection", "out_srs": "EPSG:3857"},
            {
                "type": "writers.gdal",
                "filename": grid,
                "resolution": resolution,
                "output_type": "max",
                "dimension": "Z",
                "data_type": "float32",
                # Fills the odd empty cell between sparse points.
                "window_size": 3,
                "gdaldriver": "GTiff",
            },
        ]
        _run(
            ["pdal", "pipeline", "--stdin"], INFO_TIMEOUT, json.dumps(pipeline)
        )
        with open(ramp, "w") as f:
            f.write(ELEVATION_RAMP)
        _run(
            ["gdaldem", "color-relief", "-alpha", grid, ramp, coloured],
            INFO_TIMEOUT,
        )
        if not thumbnail.render_raster_thumbnail(coloured, path):
            return []
    except Exception:
        logger.warning(
            "Could not render a point cloud thumbnail", exc_info=True
        )
        return []
    return [
        {
            "name": "output_thumbnail.png",
            "path": path,
            "media_type": thumbnail.MEDIA_TYPE,
            "info": {},
            "layer": None,
            "role": "thumbnail",
        }
    ]


def convert(
    source: str,
    job_id: Optional[str] = None,
    with_thumbnails: bool = False,
) -> tuple:
    """Convert source LAS/LAZ (s3:// URI, URL, or absolute path) to COPC.

    The COPC's info is its WGS84 `bbox`, point `count`, `crs` (e.g.
    "EPSG:2992") and `dimensions`. Returns ([{'name', 'path',
    'media_type', 'info', 'layer', 'role'}, ...], [], workdir); the caller
    removes workdir once the results are delivered.
    """
    logger.info("Job %s: starting COPC conversion of %s", job_id, source)
    os.makedirs(TMP_DIR, exist_ok=True)
    workdir = tempfile.mkdtemp(dir=TMP_DIR)
    input_path = _resolve_source(source, workdir)

    header = _header(input_path)
    crs = _horizontal_crs(header)
    if job_id:
        jobs.update_detail(job_id, "Building the COPC octree", 0.1)
    copc_path = os.path.join(workdir, "output.copc.laz")
    _run(
        [
            "pdal",
            "translate",
            input_path,
            copc_path,
            "--writer",
            "writers.copc",
            # Keep the source's header fields (scale, offset, ...) and VLRs.
            "--writers.copc.forward=all",
        ]
    )
    info = {
        "bbox": _wgs84_bbox(header, crs),
        "count": header.get("count"),
        "crs": _crs_id(crs),
        "dimensions": _dimensions(copc_path),
    }
    files = [
        {
            "name": "output.copc.laz",
            "path": copc_path,
            "media_type": COPC_MEDIA_TYPE,
            "info": info,
            "layer": None,
            "role": "data",
        }
    ]
    if with_thumbnails:
        if job_id:
            jobs.update_detail(job_id, "Rendering the thumbnail", 0.9)
        files += _thumbnail(copc_path, workdir, header)
    return files, [], workdir
