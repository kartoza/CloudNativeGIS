"""Presign S3 (or S3-compatible, e.g. MinIO) GET URLs."""

import os
from urllib.parse import urlparse

import boto3
from botocore.client import Config
from botocore.exceptions import BotoCoreError, ClientError

from app.config import (
    S3_ACCESS_KEY_ID,
    S3_ADDRESSING_STYLE,
    S3_ENDPOINT_URL,
    S3_PRESIGN_EXPIRY,
    S3_REGION,
    S3_SECRET_ACCESS_KEY,
)
from app.errors import ConversionError


def parse_s3_uri(uri: str) -> tuple:
    """Parse an s3://bucket/key URI into (bucket, key).

    Raises ConversionError(400, ...) if the URI is malformed.
    """
    parsed = urlparse(uri)
    bucket = parsed.netloc
    key = parsed.path.lstrip('/')
    if not bucket or not key:
        raise ConversionError(
            400, f'Invalid s3:// URI, expected s3://<bucket>/<key>: {uri}'
        )
    return bucket, key


def _client():
    if not S3_ACCESS_KEY_ID or not S3_SECRET_ACCESS_KEY:
        raise ConversionError(
            400,
            'S3 access is not configured on this server '
            '(S3_ACCESS_KEY_ID / S3_SECRET_ACCESS_KEY missing)'
        )
    return boto3.client(
        's3',
        endpoint_url=S3_ENDPOINT_URL,
        region_name=S3_REGION,
        aws_access_key_id=S3_ACCESS_KEY_ID,
        aws_secret_access_key=S3_SECRET_ACCESS_KEY,
        config=Config(
            signature_version='s3v4',
            s3={'addressing_style': S3_ADDRESSING_STYLE},
        ),
    )


def presign_get_url(bucket: str, key: str) -> str:
    """Generate a short-lived presigned GET URL for an S3 object."""
    try:
        return _client().generate_presigned_url(
            'get_object',
            Params={'Bucket': bucket, 'Key': key},
            ExpiresIn=S3_PRESIGN_EXPIRY,
        )
    except (BotoCoreError, ClientError) as e:
        raise ConversionError(400, f'Failed to presign S3 URL: {e}')


def list_sibling_keys(bucket: str, key: str) -> list:
    """List object keys in the same S3 "directory" as key that share
    its base name (e.g. for 'dir/name.shp', finds 'dir/name.shx',
    'dir/name.dbf', ...).
    """
    prefix = key.rsplit('/', 1)[0] + '/' if '/' in key else ''
    base_name = os.path.splitext(key.rsplit('/', 1)[-1])[0].lower()

    client = _client()
    try:
        paginator = client.get_paginator('list_objects_v2')
        keys = []
        for page in paginator.paginate(Bucket=bucket, Prefix=prefix):
            for obj in page.get('Contents', []):
                obj_key = obj['Key']
                obj_basename = obj_key.rsplit('/', 1)[-1]
                if os.path.splitext(obj_basename)[0].lower() == base_name:
                    keys.append(obj_key)
        return keys
    except (BotoCoreError, ClientError) as e:
        raise ConversionError(400, f'Failed to list S3 objects: {e}')


def download_object(bucket: str, key: str, dest_path: str) -> None:
    """Download an S3 object directly to dest_path."""
    try:
        _client().download_file(bucket, key, dest_path)
    except (BotoCoreError, ClientError) as e:
        raise ConversionError(
            400, f'Failed to download S3 object {key}: {e}'
        )


def upload_object(bucket: str, key: str, file_path: str) -> None:
    """Upload a local file to an S3 object."""
    try:
        _client().upload_file(file_path, bucket, key)
    except (BotoCoreError, ClientError) as e:
        raise ConversionError(
            400, f'Failed to upload result to S3 object {key}: {e}'
        )
