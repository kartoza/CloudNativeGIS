"""Upload a result file to a presigned (S3 or S3-compatible) PUT URL."""

import hashlib
import os

import httpx

from app.config import UPLOAD_TIMEOUT
from app.errors import ConversionError

CHUNK_SIZE = 1024 * 1024


def _hashed_chunks(path: str, digest):
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(CHUNK_SIZE), b""):
            digest.update(chunk)
            yield chunk


def upload_file(path: str, url: str, media_type: str) -> dict:
    """PUT path to url, returning {'size', 'sha256'} of the bytes sent.

    The caller presigns url for the object's final key, so this service
    writes straight to the caller's bucket without holding its
    credentials (as with presigned GET sources). The SHA-256 is computed
    from the very bytes uploaded, for the caller's checksums.
    """
    size = os.path.getsize(path)
    digest = hashlib.sha256()
    try:
        response = httpx.put(
            url,
            content=_hashed_chunks(path, digest),
            headers={"Content-Type": media_type, "Content-Length": str(size)},
            timeout=UPLOAD_TIMEOUT,
        )
    except httpx.HTTPError as e:
        raise ConversionError(502, f"Failed to upload result: {e}")
    if response.status_code >= 400:
        raise ConversionError(
            502,
            f"Failed to upload result: HTTP {response.status_code} "
            f"{response.text[:200]}",
        )
    return {"size": size, "sha256": digest.hexdigest()}
