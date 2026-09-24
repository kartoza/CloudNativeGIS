"""Shared-secret auth for every route except /health.

CloudBench's Django backend is the only intended caller — see
apps.s3.cng_lite.cng_lite_headers on that side.
"""

import secrets

from fastapi import Header, HTTPException

from app import config


def require_api_token(authorization: str = Header(default="")) -> None:
    """Reject requests missing/mismatching the configured bearer token.

    No-op if config.API_TOKEN isn't set (local dev without one configured).
    """
    if not config.API_TOKEN:
        return

    scheme, _, token = authorization.partition(" ")
    valid = scheme.lower() == "bearer" and secrets.compare_digest(
        token, config.API_TOKEN
    )
    if not valid:
        raise HTTPException(
            status_code=401, detail="Missing or invalid API token"
        )
