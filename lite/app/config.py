"""Configuration for the lite service."""

import os

# Directory under which per-request temp working dirs are created.
TMP_DIR = os.environ.get("LITE_TMP_DIR", "/tmp/cng-lite")

# Timeout (seconds) for downloading a remote source file.
DOWNLOAD_TIMEOUT = float(os.environ.get("LITE_DOWNLOAD_TIMEOUT", "60"))

# Max allowed size (bytes) for a downloaded source file. Default 500MB.
MAX_DOWNLOAD_SIZE = int(
    os.environ.get("LITE_MAX_DOWNLOAD_SIZE", str(500 * 1024 * 1024))
)

# S3 (or S3-compatible, e.g. MinIO) credentials used to presign GET URLs
# for `s3://bucket/key` sources. Left unset, s3:// sources are rejected.
S3_ENDPOINT_URL = os.environ.get("S3_ENDPOINT_URL") or None
S3_ACCESS_KEY_ID = os.environ.get("S3_ACCESS_KEY_ID")
S3_SECRET_ACCESS_KEY = os.environ.get("S3_SECRET_ACCESS_KEY")
S3_REGION = os.environ.get("S3_REGION", "us-east-1")
# 'path' works for MinIO and AWS S3 alike; set to 'virtual' if needed.
S3_ADDRESSING_STYLE = os.environ.get("S3_ADDRESSING_STYLE", "path")
# How long (seconds) a generated presigned URL stays valid.
S3_PRESIGN_EXPIRY = int(os.environ.get("S3_PRESIGN_EXPIRY", "300"))

# Max number of conversions that may run concurrently in background
# job threads.
JOB_MAX_WORKERS = int(os.environ.get("LITE_JOB_MAX_WORKERS", "4"))

# How long (seconds) a finished job's result is kept for collection
# via GET /api/v1/jobs/{job_id} before being discarded. Default 1 hour.
JOB_RESULT_TTL = int(os.environ.get("LITE_JOB_RESULT_TTL", str(60 * 60)))
