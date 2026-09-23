# CloudNativeGIS Lite

A standalone, database-free service that converts:

- a shapefile (zipped `.shp`/`.shx`/`.dbf`/...) into a
  [PMTiles](https://github.com/protomaps/PMTiles) file, using `ogr2ogr`
  and `tippecanoe`.
- a TIFF into a Cloud Optimized GeoTIFF (COG), using `gdal_translate`.

No Django, no PostGIS — just an HTTP API wrapped in a single Docker
container.

## Build

```bash
docker build -t cng-lite lite/
```

## Run

```bash
docker run --rm -p 8000:8000 cng-lite
```

To convert a shapefile from a local path instead of a URL, mount it into
the container and pass the in-container absolute path as `source`:

```bash
docker run --rm -p 8000:8000 -v /host/data:/data cng-lite
```

## Usage

Health check:

```bash
curl http://localhost:8000/health
```

Conversions run as background jobs, since shapefile/TIFF processing
can take a while: `POST /api/v1/pmtiles` or `/api/v1/cog` returns
immediately with a `job_id`, which you poll until it's done, then
collect the result. There's no Celery/broker involved — jobs run in a
thread pool inside the same process, so job state doesn't survive a
container restart and isn't shared across multiple replicas.

1. Submit the job:

    ```bash
    curl -X POST http://localhost:8000/api/v1/pmtiles \
        -H "Content-Type: application/json" \
        -d '{"source": "/data/my-shapefile.zip"}'
    # => {"job_id": "...", "status": "processing"}  (HTTP 202)
    ```

2. Poll its status:

    ```bash
    curl http://localhost:8000/api/v1/jobs/<job_id>
    ```

    - Still running: `{"job_id": "...", "status": "processing"}`
    - Failed: `{"job_id": "...", "status": "failed", "detail": "..."}`,
      with the same HTTP status the conversion would have returned
      (400 for bad/invalid input, 502 if `ogr2ogr`/`tippecanoe`/
      `gdal_translate` fail).
    - Done (streamed result): `{"job_id": "...", "status": "done", "result_url": "/api/v1/jobs/<job_id>/result"}`
    - Done (uploaded to S3, see `destination` below): `{"job_id": "...", "status": "done", "stored": "s3://..."}`

3. If `result_url` was given, fetch the file — this also discards the
   job and its temp files:

    ```bash
    curl http://localhost:8000/api/v1/jobs/<job_id>/result -o output.pmtiles
    ```

A finished job whose result is never collected is discarded
automatically after `LITE_JOB_RESULT_TTL` seconds (default 1 hour), so
temp files don't accumulate if a caller never polls.

`source` may be an `http(s)://` URL, an in-container local path, or an
`s3://bucket/key` reference — the server uses its own configured S3
credentials, so no bucket credentials need to be shared with the
caller:

```bash
curl -X POST http://localhost:8000/api/v1/pmtiles \
    -H "Content-Type: application/json" \
    -d '{"source": "s3://my-bucket/path/to/shapefile.zip"}'
```

...or directly to a loose `.shp` object — cng-lite lists and bundles
the sibling `.shx`/`.dbf`/etc. files sharing the same base name in the
same S3 "directory":

```bash
curl -X POST http://localhost:8000/api/v1/pmtiles \
    -H "Content-Type: application/json" \
    -d '{"source": "s3://my-bucket/path/to/shapefile.shp"}'
```

A non-S3 `source` must point to a `.zip` archive containing a complete
`.shp`/`.shx`/`.dbf` set.

By default the finished result is left for you to collect via
`result_url`. To have cng-lite upload it to S3 instead (e.g. writing
back into the same bucket), pass `destination` as an `s3://bucket/key`
URI — the job's `done` status then reports `stored` instead of a
`result_url`:

```bash
curl -X POST http://localhost:8000/api/v1/pmtiles \
    -H "Content-Type: application/json" \
    -d '{
          "source": "s3://my-bucket/path/to/shapefile.shp",
          "destination": "s3://my-bucket/path/to/shapefile.pmtiles"
        }'
```

### TIFF -> COG

Same request/job shape as `/api/v1/pmtiles`, on `/api/v1/cog`. `source`
may be a local path, an http(s) URL, or an `s3://bucket/key` reference
to a single TIFF object; `destination` works the same way:

```bash
curl -X POST http://localhost:8000/api/v1/cog \
    -H "Content-Type: application/json" \
    -d '{"source": "s3://my-bucket/path/to/raster.tif"}'
# => {"job_id": "...", "status": "processing"}

curl http://localhost:8000/api/v1/jobs/<job_id>
# => {"job_id": "...", "status": "done", "result_url": "/api/v1/jobs/<job_id>/result"}

curl http://localhost:8000/api/v1/jobs/<job_id>/result -o output_cog.tif
```

## S3 / MinIO configuration

`s3://bucket/key` sources require these environment variables (unset by
default, so `s3://` sources are rejected until configured):

| Variable                | Required | Default       | Notes                                              |
|--------------------------|----------|---------------|-----------------------------------------------------|
| `S3_ACCESS_KEY_ID`       | yes      | —             |                                                       |
| `S3_SECRET_ACCESS_KEY`   | yes      | —             |                                                       |
| `S3_ENDPOINT_URL`        | no       | AWS default   | Set to your MinIO endpoint, e.g. `http://minio:9000` |
| `S3_REGION`              | no       | `us-east-1`   |                                                       |
| `S3_ADDRESSING_STYLE`    | no       | `path`        | `path` works for MinIO and AWS alike                 |
| `S3_PRESIGN_EXPIRY`      | no       | `300`         | Seconds the presigned URL stays valid                |

## Authentication

Every endpoint except `/health` requires `Authorization: Bearer <token>` if
`LITE_API_TOKEN` is set — left unset (the default), no auth is enforced, so
only run without it in local dev. This is a single static shared secret for
now (it never expires); CloudBench's Django backend sends it as
`CLOUDNATIVEGIS_API_TOKEN`.

| Variable         | Default | Notes                                            |
|------------------|---------|---------------------------------------------------|
| `LITE_API_TOKEN` | unset   | Required bearer token; unset disables auth entirely |

## Job configuration

| Variable                | Default | Notes                                                        |
|--------------------------|---------|---------------------------------------------------------------|
| `LITE_JOB_MAX_WORKERS`   | `4`     | Max conversions running concurrently in background threads    |
| `LITE_JOB_RESULT_TTL`    | `3600`  | Seconds a finished, uncollected job's result is kept before being discarded |

Example run against a local MinIO instance:

```bash
docker run --rm -p 8000:8000 \
    -e S3_ENDPOINT_URL=http://minio:9000 \
    -e S3_ACCESS_KEY_ID=minioadmin \
    -e S3_SECRET_ACCESS_KEY=minioadmin \
    --network minio-net \
    cng-lite
```
