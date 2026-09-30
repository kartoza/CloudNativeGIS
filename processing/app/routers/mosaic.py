"""Several GeoTIFF tiles -> one mosaic (COGs, VRT, web mosaic) endpoint."""

from typing import List, Optional

from fastapi import APIRouter
from pydantic import BaseModel

from app import jobs
from app.services.tiff_mosaic import mosaic

router = APIRouter()


class MosaicTile(BaseModel):
    """One tile: its source, and where its COG(s) are uploaded."""

    # Names the tile's folder in the VRT's relative paths.
    id: str
    source: str
    data_upload: str
    # Its EPSG:3857 COG's upload; only used without a merged mosaic.
    web_upload: Optional[str] = None


class MosaicOutput(BaseModel):
    """A whole-mosaic output: its filename and presigned PUT URL."""

    name: str = ""
    upload: str


class MosaicRequest(BaseModel):
    """Request body for the mosaic endpoint."""

    tiles: List[MosaicTile]
    vrt: MosaicOutput
    # The merged EPSG:3857 COG; omit for none (each tile's is uploaded).
    merged: Optional[MosaicOutput] = None
    thumbnail: Optional[MosaicOutput] = None


@router.post("/api/v1/mosaic", status_code=202)
def create_mosaic(body: MosaicRequest):
    """Start converting GeoTIFF tiles into one mosaic.

    Every output is uploaded to its presigned PUT URL. Returns a job id
    right away; poll GET /api/v1/jobs/{job_id}, whose `outputs` then give
    each file's size and SHA-256, and each tile's WGS84 bbox.
    """
    tiles = [tile.model_dump() for tile in body.tiles]
    merged = body.merged.model_dump() if body.merged else None
    thumbnail = body.thumbnail.model_dump() if body.thumbnail else None

    def work(job_id: str) -> dict:
        outputs = mosaic(
            tiles, body.vrt.model_dump(), merged, thumbnail, job_id=job_id
        )
        return {"files": [], "errors": [], "outputs": outputs}

    job_id = jobs.submit(work)
    return {"job_id": job_id, "status": "processing"}
