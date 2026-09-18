"""Resolve a request 'source' (URL or local path) to a local file."""

import os
import shutil
import zipfile

from app.errors import ConversionError
from app.utils.http import download_url
from app.utils.s3 import (
    download_object,
    list_sibling_keys,
    parse_s3_uri,
    presign_get_url,
)


def _bundle_s3_shapefile_parts(bucket: str, key: str, workdir: str) -> str:
    """Bundle loose shapefile part objects into a local zip.

    Downloads all S3 objects sharing key's base name.
    """
    sibling_keys = list_sibling_keys(bucket, key)
    if not sibling_keys:
        raise ConversionError(400, f'No S3 objects found matching {key}')

    parts_dir = os.path.join(workdir, 'parts')
    os.makedirs(parts_dir, exist_ok=True)
    for sibling_key in sibling_keys:
        filename = sibling_key.rsplit('/', 1)[-1]
        download_object(bucket, sibling_key, os.path.join(parts_dir, filename))

    dest_path = os.path.join(workdir, 'input.zip')
    with zipfile.ZipFile(dest_path, 'w', zipfile.ZIP_DEFLATED) as archive:
        for filename in os.listdir(parts_dir):
            archive.write(os.path.join(parts_dir, filename), arcname=filename)
    return dest_path


def resolve_source(source: str, workdir: str) -> str:
    """Resolve source to a local zip path.

    source may be an s3:// URI, an http(s) URL, or a local path.
    Returns the local filesystem path to the (now local) source file.
    """
    if source.startswith('s3://'):
        bucket, key = parse_s3_uri(source)

        if key.lower().endswith('.zip'):
            presigned_url = presign_get_url(bucket, key)
            dest_path = os.path.join(workdir, 'input.zip')
            download_url(presigned_url, dest_path)
            return dest_path

        # Not a .zip: treat as loose shapefile parts (.shp/.shx/.dbf/...)
        # sharing the same base name in the same S3 "directory".
        return _bundle_s3_shapefile_parts(bucket, key, workdir)

    if source.startswith('http://') or source.startswith('https://'):
        dest_path = os.path.join(workdir, 'input.zip')
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

    dest_path = os.path.join(workdir, 'input.zip')
    shutil.copyfile(source, dest_path)
    return dest_path
