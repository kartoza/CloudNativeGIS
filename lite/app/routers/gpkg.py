"""GeoPackage layer inspection endpoint (list layers without converting)."""

from fastapi import APIRouter
from pydantic import BaseModel

from app.services.gpkg_inspect import inspect

router = APIRouter()


class GpkgLayersRequest(BaseModel):
    """Request body for the GeoPackage layer-listing endpoint."""

    source: str


@router.post("/api/v1/gpkg/layers")
def get_gpkg_layers(body: GpkgLayersRequest):
    """Report a GeoPackage's layers (name, geometry, feature count)."""
    return {"layers": inspect(body.source)}
