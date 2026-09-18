"""Lite CloudNativeGIS service: shapefile -> PMTiles, TIFF -> COG."""

from fastapi import FastAPI

from app.errors import ConversionError, conversion_error_handler
from app.routers import cog, jobs, pmtiles

app = FastAPI(title='CloudNativeGIS Lite')

app.add_exception_handler(ConversionError, conversion_error_handler)
app.include_router(pmtiles.router)
app.include_router(cog.router)
app.include_router(jobs.router)


@app.get('/health')
def health() -> dict:
    """Health check endpoint."""
    return {'status': 'ok'}
