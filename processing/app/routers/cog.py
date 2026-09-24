"""TIFF/GeoPackage -> Cloud Optimized GeoTIFF (COG) conversion endpoint."""

from typing import List, Optional

from fastapi import APIRouter
from pydantic import BaseModel

from app import jobs
from app.services.tiff_to_cog import convert

router = APIRouter()


class COGRequest(BaseModel):
    """Request body for the COG conversion endpoint."""

    source: str
    # GeoPackage only: which raster tables to include (omit/None to
    # include all). Each table is converted to its own COG file.
    tables: Optional[List[str]] = None


@router.post("/api/v1/cog", status_code=202)
def create_cog(body: COGRequest):
    """Start converting a TIFF or raster GeoPackage to COG(s).

    Accepts a URL, local path, or S3 URI. Returns a job id right away;
    poll GET /api/v1/jobs/{job_id} for status.
    """

    def work(job_id: str) -> dict:
        files, errors, workdir = convert(
            body.source, tables=body.tables, job_id=job_id
        )
        return {"files": files, "errors": errors, "workdir": workdir}

    job_id = jobs.submit(work)
    return {"job_id": job_id, "status": "processing"}
