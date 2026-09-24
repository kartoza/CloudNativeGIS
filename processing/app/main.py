"""Lite CloudNativeGIS service: shapefile -> PMTiles, TIFF -> COG."""

import logging

from fastapi import Depends, FastAPI

from app.auth import require_api_token
from app.errors import ConversionError, conversion_error_handler
from app.routers import cog, gpkg, jobs, pmtiles

# Conversion jobs run in background threads (see app.jobs) — without this,
# their success/failure/skip logging (docker logs) would be invisible,
# since uvicorn only configures its own access/error loggers by default.
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)

app = FastAPI(title="CloudNativeGIS Lite")

app.add_exception_handler(ConversionError, conversion_error_handler)
# /health is intentionally excluded — docker's healthcheck calls it with no
# token (see deployment/docker-compose.cng-lite.yml).
_auth = [Depends(require_api_token)]
app.include_router(pmtiles.router, dependencies=_auth)
app.include_router(cog.router, dependencies=_auth)
app.include_router(gpkg.router, dependencies=_auth)
app.include_router(jobs.router, dependencies=_auth)


@app.get("/health")
def health() -> dict:
    """Health check endpoint."""
    return {"status": "ok"}
