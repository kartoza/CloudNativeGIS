"""LAS/LAZ -> Cloud Optimized Point Cloud (COPC) conversion endpoint."""

from typing import List, Optional

from fastapi import APIRouter
from pydantic import BaseModel

from app import jobs
from app.routers.uploads import LayerUploads, deliver
from app.services.las_to_copc import convert

router = APIRouter()


class COPCRequest(BaseModel):
    """Request body for the COPC conversion endpoint."""

    source: str
    thumbnail: bool = False
    # Upload the results here rather than keeping them to collect.
    uploads: Optional[List[LayerUploads]] = None


@router.post("/api/v1/copc", status_code=202)
def create_copc(body: COPCRequest):
    """Start converting a LAS or LAZ point cloud to COPC.

    Accepts a URL, local path, or S3 URI. Returns a job id right away;
    poll GET /api/v1/jobs/{job_id} for status. With `uploads`, the
    results go straight to those presigned URLs and the finished job
    reports them as `outputs`.
    """

    def work(job_id: str) -> dict:
        files, errors, workdir = convert(
            body.source, job_id=job_id, with_thumbnails=body.thumbnail
        )
        return deliver(files, errors, workdir, body.uploads, job_id)

    job_id = jobs.submit(work)
    return {"job_id": job_id, "status": "processing"}
