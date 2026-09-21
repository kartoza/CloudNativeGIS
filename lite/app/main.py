"""Lite CloudNativeGIS service: shapefile -> PMTiles, TIFF -> COG."""

import logging

from fastapi import FastAPI

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
app.include_router(pmtiles.router)
app.include_router(cog.router)
app.include_router(gpkg.router)
app.include_router(jobs.router)


@app.get("/health")
def health() -> dict:
    """Health check endpoint."""
    return {"status": "ok"}
