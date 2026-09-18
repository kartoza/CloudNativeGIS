"""Lite CloudNativeGIS service: shapefile -> PMTiles conversion."""

from fastapi import FastAPI

from app.errors import ConversionError, conversion_error_handler
from app.routers import pmtiles

app = FastAPI(title='CloudNativeGIS Lite')

app.add_exception_handler(ConversionError, conversion_error_handler)
app.include_router(pmtiles.router)


@app.get('/health')
def health() -> dict:
    """Health check endpoint."""
    return {'status': 'ok'}
