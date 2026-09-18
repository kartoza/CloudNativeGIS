"""TIFF -> Cloud Optimized GeoTIFF (COG) conversion endpoint."""

import shutil
from typing import Optional

from fastapi import APIRouter
from pydantic import BaseModel

from app import jobs
from app.services.tiff_to_cog import convert
from app.utils.s3 import parse_s3_uri, upload_object

router = APIRouter()


class COGRequest(BaseModel):
    """Request body for the COG conversion endpoint."""

    source: str
    # Optional s3://bucket/key to upload the result to, instead of
    # streaming it back once the job is done.
    destination: Optional[str] = None


@router.post('/api/v1/cog', status_code=202)
def create_cog(body: COGRequest):
    """Start converting a TIFF (by URL, local path, or S3 URI) to a COG.

    Returns a job id right away; poll GET /api/v1/jobs/{job_id} for
    status. If `destination` is given, the job uploads the result to
    that S3 location instead of leaving it to be downloaded.
    """

    def work() -> dict:
        cog_path, workdir = convert(body.source)

        if body.destination:
            bucket, key = parse_s3_uri(body.destination)
            upload_object(bucket, key, cog_path)
            shutil.rmtree(workdir, ignore_errors=True)
            return {'stored': body.destination}

        return {
            'file': cog_path,
            'workdir': workdir,
            'media_type': 'image/tiff',
            'filename': 'output_cog.tif',
        }

    job_id = jobs.submit(work)
    return {'job_id': job_id, 'status': 'processing'}
