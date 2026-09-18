"""Resolve a request source to a local TIFF file.

source may be an s3:// URI, an http(s) URL, or a local path.
"""

import os
import shutil

from app.errors import ConversionError
from app.utils.http import download_url
from app.utils.s3 import download_object, parse_s3_uri


def resolve_tiff_source(source: str, workdir: str) -> str:
    """Resolve source to a local .tif path.

    Returns the local filesystem path to the (now local) source file.
    """
    dest_path = os.path.join(workdir, 'input.tif')

    if source.startswith('s3://'):
        bucket, key = parse_s3_uri(source)
        download_object(bucket, key, dest_path)
        return dest_path

    if source.startswith('http://') or source.startswith('https://'):
        download_url(source, dest_path)
        return dest_path

    if not os.path.isabs(source):
        raise ConversionError(
            400, 'Local source path must be absolute'
        )
    if not os.path.isfile(source):
        raise ConversionError(
            400, f'Source file does not exist: {source}'
        )

    shutil.copyfile(source, dest_path)
    return dest_path
