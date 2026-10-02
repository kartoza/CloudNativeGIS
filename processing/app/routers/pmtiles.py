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
    """

    def work(job_id: str) -> dict:
        files, errors, workdir = convert(
            body.source,
            layers=body.layers,
            job_id=job_id,
            with_thumbnails=body.thumbnail,
        )
        return deliver(files, errors, workdir, body.uploads, job_id)

    job_id = jobs.submit(work)
    return {"job_id": job_id, "status": "processing"}
