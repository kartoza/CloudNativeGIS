"""Convert several GeoTIFF tiles into one mosaic, uploading every output.

Each tile becomes a COG (as a single TIFF does, see tiff_to_cog), then the
tiles together get:

- a GDAL VRT listing every tile's COG by a path relative to the VRT
  ("<tile id>/<tile id>.tif"), so it opens straight from the bucket the
  outputs are uploaded to;
- a web rendering: one merged EPSG:3857 COG, with embedded statistics,
  or - when the caller asks for no merge (a mosaic too big to merge) -
  each tile's own EPSG:3857 COG;
- a PNG thumbnail, drawn as a single raster's is.

Every output is uploaded to the presigned PUT URL the caller gives for it,
so the files go straight to the caller's bucket; the job reports each
one's size and SHA-256, and each tile's WGS84 bbox.
"""

import logging
import os
import shutil
import tempfile
from concurrent.futures import ThreadPoolExecutor
from typing import List, Optional

from app import jobs
from app.config import MOSAIC_TILE_WORKERS, TMP_DIR
from app.errors import ConversionError
from app.services.tiff_to_cog import (
    COG_OPTIONS,
    _check_embedded_statistics,
    _run,
    _translate_cog,
    _translate_cog_3857,
)
from app.utils import thumbnail
from app.utils.cog_info import read_cog_info
from app.utils.tiff_source import resolve_tiff_source
from app.utils.upload import upload_file

logger = logging.getLogger(__name__)

COG_MEDIA_TYPE = "image/tiff; application=geotiff; profile=cloud-optimized"
VRT_MEDIA_TYPE = "application/xml"


def _convert_tile(tile: dict, workdir: str) -> dict:
    """Download and convert one tile: its data and EPSG:3857 COGs, bbox."""
    tile_dir = os.path.join(workdir, "tiles", tile["id"])
    os.makedirs(tile_dir)
    source = resolve_tiff_source(tile["source"], tile_dir)
    data = os.path.join(tile_dir, f"{tile['id']}.tif")
    web = os.path.join(tile_dir, f"{tile['id']}_3857.tif")
    _translate_cog(source, data)
    _translate_cog_3857(source, web)
    os.remove(source)
    return {
        "id": tile["id"],
        "data": data,
        "web": web,
        "bbox": read_cog_info(data).get("bbox"),
    }


def _merge_web(web_paths: List[str], workdir: str, merged: str) -> str:
    """Merge the tiles' EPSG:3857 COGs; return the web VRT they were read by.

    Statistics are computed on the VRT first, so the thumbnail can be
    drawn from it too when there's no merged COG.
    """
    web_vrt = os.path.join(workdir, "web.vrt")
    _run(["gdalbuildvrt", "-resolution", "highest", web_vrt, *web_paths])
    _run(["gdalinfo", "-stats", web_vrt])
    if merged:
        _run(["gdal_translate", *COG_OPTIONS, web_vrt, merged])
        _check_embedded_statistics(merged)
    return web_vrt


def _build_vrt(workdir: str, name: str, tiles: List[dict]) -> str:
    """Build the VRT of every tile's COG, by paths relative to it.

    Built inside the tiles folder, so its paths ("<tile id>/<tile id>.tif")
    match where the tiles are uploaded, beside the VRT.
    """
    tiles_dir = os.path.join(workdir, "tiles")
    _run(
        [
            "gdalbuildvrt",
            "-resolution",
            "highest",
            name,
            *(f"{t['id']}/{t['id']}.tif" for t in tiles),
        ],
        cwd=tiles_dir,
    )
    return os.path.join(tiles_dir, name)


def mosaic(
    tiles: List[dict],
    vrt: dict,
    merged: Optional[dict],
    thumbnail_output: Optional[dict],
    job_id: Optional[str] = None,
) -> dict:
    """Convert `tiles` into a mosaic and upload every output.

    `tiles` is [{'id', 'source', 'data_upload', 'web_upload'?}, ...]:
    each tile's source (s3:// URI, URL or path) and the PUT URLs its COG
    goes to - `web_upload` for its EPSG:3857 COG, needed only without a
    merged mosaic. `vrt` is {'name', 'upload'}; `merged` is {'name',
    'upload'} for the merged EPSG:3857 COG, or None for none;
    `thumbnail_output` is {'upload'}, or None for none.

    Returns {'tiles': [{'id', 'bbox', 'data': {'size', 'sha256'},
    'web'?: ...}], 'vrt': {...}, 'merged'?: {...}, 'thumbnail'?: {...}}.
    """
    if len(tiles) < 2:
        raise ConversionError(400, "A mosaic needs at least two tiles.")
    ids = [tile["id"] for tile in tiles]
    if len(set(ids)) != len(ids):
        raise ConversionError(400, "Tile ids must be unique.")
    if not merged and not all(tile.get("web_upload") for tile in tiles):
        raise ConversionError(
            400, "Without a merged mosaic, every tile needs a web_upload."
        )

    os.makedirs(TMP_DIR, exist_ok=True)
    workdir = tempfile.mkdtemp(dir=TMP_DIR)
    try:
        return _mosaic(tiles, vrt, merged, thumbnail_output, job_id, workdir)
    finally:
        shutil.rmtree(workdir, ignore_errors=True)


def _progress(job_id, detail, fraction):
    logger.info("Job %s: %s", job_id, detail)
    if job_id:
        jobs.update_detail(job_id, detail, progress=fraction)


def _mosaic(tiles, vrt, merged, thumbnail_output, job_id, workdir) -> dict:
    total = len(tiles)
    _progress(job_id, f"Converting {total} tiles", 0.0)
    converted = {}
    with ThreadPoolExecutor(max_workers=max(1, MOSAIC_TILE_WORKERS)) as pool:
        futures = [pool.submit(_convert_tile, t, workdir) for t in tiles]
        # In submission order, so the reported count follows the tile list.
        for done, future in enumerate(futures, start=1):
            result = future.result()
            converted[result["id"]] = result
            _progress(
                job_id,
                f"Converted tile {done} of {total}: {result['id']}",
                # The share of tiles done, so a caller can show which tile
                # is converting; the steps after keep it at 1.
                done / total,
            )
    ordered = [converted[tile["id"]] for tile in tiles]

    _progress(job_id, "Building the mosaic", 1.0)
    merged_path = os.path.join(workdir, merged["name"]) if merged else ""
    web_vrt = _merge_web([t["web"] for t in ordered], workdir, merged_path)
    vrt_path = _build_vrt(workdir, vrt["name"], ordered)
    thumbnail_path = os.path.join(workdir, "thumbnail.png")
    has_thumbnail = bool(thumbnail_output) and (
        thumbnail.render_raster_thumbnail(
            merged_path or web_vrt, thumbnail_path
        )
    )

    _progress(job_id, "Uploading the mosaic", 1.0)
    result: dict = {"tiles": []}
    for tile, spec in zip(ordered, tiles):
        entry = {
            "id": tile["id"],
            "bbox": tile["bbox"],
            "data": upload_file(
                tile["data"], spec["data_upload"], COG_MEDIA_TYPE
            ),
        }
        if not merged:
            entry["web"] = upload_file(
                tile["web"], spec["web_upload"], COG_MEDIA_TYPE
            )
        result["tiles"].append(entry)
    result["vrt"] = upload_file(vrt_path, vrt["upload"], VRT_MEDIA_TYPE)
    if merged:
        result["merged"] = upload_file(
            merged_path, merged["upload"], COG_MEDIA_TYPE
        )
    if has_thumbnail:
        result["thumbnail"] = upload_file(
            thumbnail_path, thumbnail_output["upload"], thumbnail.MEDIA_TYPE
        )
    _progress(job_id, f"Mosaic of {total} tiles uploaded", 1.0)
    return result
