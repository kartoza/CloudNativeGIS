"""Shapefile/GeoPackage -> PMTiles conversion endpoint."""

from typing import List, Optional

from fastapi import APIRouter
from pydantic import BaseModel

from app import jobs
from app.services.shapefile_to_pmtiles import convert

router = APIRouter()


class PMTilesRequest(BaseModel):
    """Request body for the pmtiles conversion endpoint."""

    source: str
    # GeoPackage only: which layers to include (omit/None to include all).
    # Each layer is converted to its own PMTiles file.
    layers: Optional[List[str]] = None


@router.post("/api/v1/pmtiles", status_code=202)
def create_pmtiles(body: PMTilesRequest):
    """Start converting a shapefile (zip) or GeoPackage to PMTiles.

    Accepts a URL or local path. Returns a job id right away; poll
    GET /api/v1/jobs/{job_id} for status.
    """

    def work(job_id: str) -> dict:
        files, errors, workdir = convert(
            body.source, layers=body.layers, job_id=job_id
        )
        return {"files": files, "errors": errors, "workdir": workdir}

    job_id = jobs.submit(work)
    return {"job_id": job_id, "status": "processing"}
