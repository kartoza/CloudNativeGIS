"""Errors raised during conversion pipelines."""

from fastapi import Request
from fastapi.responses import JSONResponse


class ConversionError(Exception):
    """Raised when a conversion step fails.

    status_code is 400 for bad/invalid input, 502 for a failure in an
    underlying tool (ogr2ogr, tippecanoe, gdal_translate, ...).
    """

    def __init__(self, status_code: int, message: str):
        """Store the HTTP status code and message for the handler."""
        self.status_code = status_code
        self.message = message
        super().__init__(message)


async def conversion_error_handler(
    request: Request, exc: ConversionError
) -> JSONResponse:
    """Convert a ConversionError into a JSON error response."""
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.message},
    )
