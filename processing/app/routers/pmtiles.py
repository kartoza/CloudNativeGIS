"""Vector -> PMTiles conversion endpoint.

Sources: a shapefile (zip), GeoPackage, GeoJSON, FlatGeobuf or KML/KMZ.
"""

from typing import List, Optional

from fastapi import APIRouter
from pydantic import BaseModel

from app import jobs
from app.routers.uploads import LayerUploads, deliver
from app.services.shapefile_to_pmtiles import convert

router = APIRouter()


class PMTilesRequest(BaseModel):
    """Request body for the pmtiles conversion endpoint."""

    source: str
    # GeoPackage only: which layers to include (omit/None to include all).
    # Each layer is converted to its own PMTiles file.
    layers: Optional[List[str]] = None
    thumbnail: bool = False
    # The zoom tippecanoe's maxzoom guess (-zg) is floored to, so a layer of
    # many small, densely-packed features (e.g. neighbourhood polygons) isn't
    # left looking coarse at the zoom it's actually viewed at - see
    # shapefile_to_pmtiles.DEFAULT_MIN_MEANINGFUL_ZOOM for the default and the
    # trade-off (a higher floor means bigger files and longer tiling, floored
    # only when the data's own guess is lower).
    min_meaningful_zoom: Optional[int] = None
    # Upload each layer's results here rather than keeping them to collect.
    uploads: Optional[List[LayerUploads]] = None


@router.post("/api/v1/pmtiles", status_code=202)
def create_pmtiles(body: PMTilesRequest):
    """Start converting a vector source to PMTiles + GeoParquet.

    The source is a shapefile (zip), GeoPackage, GeoJSON, FlatGeobuf or
    KML/KMZ.

    Accepts a URL or local path. Returns a job id right away; poll
    GET /api/v1/jobs/{job_id} for status. With `uploads`, each layer's
    results go straight to those presigned URLs and the finished job
    reports them as `outputs`.

    `min_meaningful_zoom` (optional): see PMTilesRequest - raise it if a
    layer of small, densely-packed polygons (e.g. admin boundaries) still
    looks too simplified at the zoom it's actually viewed at.
    """

    def work(job_id: str) -> dict:
        files, errors, workdir = convert(
            body.source,
            layers=body.layers,
            job_id=job_id,
            with_thumbnails=body.thumbnail,
            min_meaningful_zoom=body.min_meaningful_zoom,
        )
        return deliver(files, errors, workdir, body.uploads, job_id)

    job_id = jobs.submit(work)
    return {"job_id": job_id, "status": "processing"}
