"""Shapefile -> PMTiles conversion endpoint."""

import shutil
from typing import Optional

from fastapi import APIRouter, BackgroundTasks
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel

from app.services.shapefile_to_pmtiles import convert
from app.utils.s3 import parse_s3_uri, upload_object

router = APIRouter()


class PMTilesRequest(BaseModel):
    """Request body for the pmtiles conversion endpoint."""

    source: str
    # Optional s3://bucket/key to upload the result to, instead of
    # streaming it back in the response.
    destination: Optional[str] = None


@router.post('/api/v1/pmtiles')
def create_pmtiles(body: PMTilesRequest, background_tasks: BackgroundTasks):
    """Convert a shapefile (zip, by URL or local path) to PMTiles.

    If `destination` is given, the result is uploaded to that S3
    location and a JSON confirmation is returned instead of the file.
    """
    pmtiles_path, workdir = convert(body.source)
    background_tasks.add_task(shutil.rmtree, workdir, ignore_errors=True)

    if body.destination:
        bucket, key = parse_s3_uri(body.destination)
        upload_object(bucket, key, pmtiles_path)
        return JSONResponse(
            content={'stored': body.destination},
            background=background_tasks,
        )

    return FileResponse(
        pmtiles_path,
        media_type='application/octet-stream',
        filename='output.pmtiles',
        background=background_tasks,
    )
