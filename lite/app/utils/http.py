"""Download a remote file over http(s)."""

import httpx

from app.config import DOWNLOAD_TIMEOUT, MAX_DOWNLOAD_SIZE
from app.errors import ConversionError


def download_url(url: str, dest_path: str) -> None:
    """Stream-download url to dest_path, enforcing a max size."""
    try:
        with httpx.stream(
            'GET', url, timeout=DOWNLOAD_TIMEOUT, follow_redirects=True
        ) as response:
            if response.status_code >= 400:
                raise ConversionError(
                    400,
                    f'Failed to download source: '
                    f'HTTP {response.status_code}'
                )
            written = 0
            with open(dest_path, 'wb') as f:
                for chunk in response.iter_bytes():
                    written += len(chunk)
                    if written > MAX_DOWNLOAD_SIZE:
                        raise ConversionError(
                            400,
                            'Source file exceeds max allowed size of '
                            f'{MAX_DOWNLOAD_SIZE} bytes'
                        )
                    f.write(chunk)
    except httpx.HTTPError as e:
        raise ConversionError(400, f'Failed to download source: {e}')
