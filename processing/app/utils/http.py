"""Download a remote file over http(s)."""

import os
import shutil

import httpx

from app.config import DOWNLOAD_TIMEOUT
from app.errors import ConversionError

GB = 1024**3
# Re-check free space after every this many bytes written.
CHECK_EVERY = 64 * 1024**2


def disk_reserve(path: str) -> int:
    """Bytes a download must leave free on path's disk.

    10% of the disk, or 1 GB if that's less: room for the conversion's
    outputs, and for other jobs, so one download can't fill the disk.
    """
    return min(GB, shutil.disk_usage(path).total // 10)


def _check_space(path: str, needed: int = 0) -> None:
    """Refuse to go on if `needed` more bytes would eat into the reserve."""
    free = shutil.disk_usage(path).free
    reserve = disk_reserve(path)
    if free - needed >= reserve:
        return
    mb = 1024**2
    if needed:
        message = (
            "Not enough disk space to download the source: it is "
            f"{needed // mb} MB, and {free // mb} MB is free "
            f"({reserve // mb} MB of which is kept in reserve)."
        )
    else:
        message = (
            "The disk ran low while downloading the source: "
            f"{free // mb} MB is left, and {reserve // mb} MB is kept in "
            "reserve."
        )
    raise ConversionError(507, message)


def download_url(url: str, dest_path: str) -> None:
    """Stream-download url to dest_path, stopping before the disk fills.

    There's no fixed size limit: the disk is. A source that says how big
    it is (Content-Length) is refused up front if it won't fit; any source
    is stopped if, while it streams in, free space falls to the reserve
    (see disk_reserve). A partial download is removed.
    """
    directory = os.path.dirname(dest_path) or "."
    try:
        with httpx.stream(
            "GET", url, timeout=DOWNLOAD_TIMEOUT, follow_redirects=True
        ) as response:
            if response.status_code >= 400:
                raise ConversionError(
                    400,
                    f"Failed to download source: "
                    f"HTTP {response.status_code}",
                )
            declared = response.headers.get("Content-Length")
            if declared and declared.isdigit():
                _check_space(directory, int(declared))
            unchecked = 0
            with open(dest_path, "wb") as f:
                for chunk in response.iter_bytes():
                    f.write(chunk)
                    unchecked += len(chunk)
                    if unchecked >= CHECK_EVERY:
                        unchecked = 0
                        _check_space(directory)
    except httpx.HTTPError as e:
        _remove(dest_path)
        raise ConversionError(400, f"Failed to download source: {e}")
    except ConversionError:
        _remove(dest_path)
        raise


def _remove(path: str) -> None:
    try:
        os.remove(path)
    except OSError:
        pass
