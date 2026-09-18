"""TIFF -> Cloud Optimized GeoTIFF (COG) conversion endpoint."""

import shutil
from typing import Optional

from fastapi import APIRouter, BackgroundTasks
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel

from app.services.tiff_to_cog import convert
from app.utils.s3 import parse_s3_uri, upload_object

router = APIRouter()


class COGRequest(BaseModel):
    """Request body for the COG conversion endpoint."""

    source: str
    # Optional s3://bucket/key to upload the result to, instead of
    # streaming it back in the response.
    destination: Optional[str] = None


@router.post('/api/v1/cog')
def create_cog(body: COGRequest, background_tasks: BackgroundTasks):
    """Convert a TIFF (by URL, local path, or S3 URI) to a COG.

    If `destination` is given, the result is uploaded to that S3
    location and a JSON confirmation is returned instead of the file.
    """
    cog_path, workdir = convert(body.source)
    background_tasks.add_task(shutil.rmtree, workdir, ignore_errors=True)

    if body.destination:
        bucket, key = parse_s3_uri(body.destination)
        upload_object(bucket, key, cog_path)
        return JSONResponse(
            content={'stored': body.destination},
            background=background_tasks,
        )

    return FileResponse(
        cog_path,
        media_type='image/tiff',
        filename='output_cog.tif',
        background=background_tasks,
    )
