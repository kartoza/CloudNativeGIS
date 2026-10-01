"""Upload result files to presigned (S3 or S3-compatible) PUT URLs."""

import hashlib
import os
from typing import List, Optional, Tuple

import httpx

from app import jobs
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


def upload_outputs(
    files: List[dict], uploads: List[dict], job_id: Optional[str] = None
) -> Tuple[dict, List[dict]]:
    """Upload a conversion's result files to the caller's presigned URLs.

    `files` are a conversion's results, each tagged with its `layer` (None
    for a single-layer source) and `role` (data, visual, thumbnail).
    `uploads` is [{'layer', 'files': {role: {'url', 'content_type'}}}]:
    where the caller wants each layer's files - straight into its bucket,
    under their final keys - and the content type each URL was signed for.
    A role the caller asked nothing for (e.g. no thumbnail) isn't sent.

    Returns ({'layers': [{'layer', 'files': {role: {'size', 'sha256',
    'info'}}}]}, errors) - an error for each layer converted that the
    caller gave no URLs for.
    """
    targets = {
        (spec.get("layer"), role): target
        for spec in uploads
        for role, target in spec["files"].items()
    }
    wanted = [f for f in files if (f.get("layer"), f.get("role")) in targets]
    layers: dict = {}
    for index, file in enumerate(wanted):
        if job_id:
            jobs.update_detail(
                job_id,
                f"Uploading the results ({index + 1} of {len(wanted)})",
                progress=1.0,
            )
        target = targets[(file["layer"], file["role"])]
        sent = upload_file(file["path"], target["url"], target["content_type"])
        layers.setdefault(file["layer"], {})[file["role"]] = {
            **sent,
            "info": file.get("info") or {},
        }
    requested = {spec.get("layer") for spec in uploads}
    errors = [
        {
            "name": layer,
            "error": "converted, but no upload URL was given for it",
        }
        for layer in {f.get("layer") for f in files} - requested
    ]
    return (
        {
            "layers": [
                {"layer": layer, "files": roles}
                for layer, roles in layers.items()
            ]
        },
        errors,
    )
