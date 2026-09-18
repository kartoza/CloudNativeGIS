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

Convert a shapefile zip by URL:

```bash
curl -X POST http://localhost:8000/api/v1/pmtiles \
    -H "Content-Type: application/json" \
    -d '{"source": "https://example.com/data.zip"}' \
    -o output.pmtiles
```

Convert a shapefile zip by local (in-container) path:

```bash
curl -X POST http://localhost:8000/api/v1/pmtiles \
    -H "Content-Type: application/json" \
    -d '{"source": "/data/my-shapefile.zip"}' \
    -o output.pmtiles
```

Convert a shapefile stored in S3 (or an S3-compatible store, e.g.
MinIO) by object reference — the server uses its own configured
credentials, so no bucket credentials need to be shared with the
caller. `source` can point to a `.zip`:

```bash
curl -X POST http://localhost:8000/api/v1/pmtiles \
    -H "Content-Type: application/json" \
    -d '{"source": "s3://my-bucket/path/to/shapefile.zip"}' \
    -o output.pmtiles
```

...or directly to a loose `.shp` object — cng-lite lists and bundles
the sibling `.shx`/`.dbf`/etc. files sharing the same base name in the
same S3 "directory":

```bash
curl -X POST http://localhost:8000/api/v1/pmtiles \
    -H "Content-Type: application/json" \
    -d '{"source": "s3://my-bucket/path/to/shapefile.shp"}' \
    -o output.pmtiles
```

By default the result is streamed back in the response. To have
cng-lite upload the result to S3 instead (e.g. writing back into the
same bucket), pass `destination` as an `s3://bucket/key` URI — the
response is then a small JSON confirmation instead of the file itself:

```bash
curl -X POST http://localhost:8000/api/v1/pmtiles \
    -H "Content-Type: application/json" \
    -d '{
          "source": "s3://my-bucket/path/to/shapefile.shp",
          "destination": "s3://my-bucket/path/to/shapefile.pmtiles"
        }'
# => {"stored": "s3://my-bucket/path/to/shapefile.pmtiles"}
```

A non-S3 `source` must point to a `.zip` archive containing a complete
`.shp`/`.shx`/`.dbf` set. Errors return a JSON body `{"detail": "..."}`
with HTTP 400 for invalid/unreachable input, or 502 if `ogr2ogr`/
`tippecanoe` fail during conversion.

### TIFF -> COG

Same request shape as `/api/v1/pmtiles`, on `/api/v1/cog`. `source` may
be a local path, an http(s) URL, or an `s3://bucket/key` reference to a
single TIFF object:

```bash
curl -X POST http://localhost:8000/api/v1/cog \
    -H "Content-Type: application/json" \
    -d '{"source": "s3://my-bucket/path/to/raster.tif"}' \
    -o output_cog.tif
```

Pass `destination` (an `s3://bucket/key` URI) to have cng-lite upload
the COG to S3 instead of streaming it back:

```bash
curl -X POST http://localhost:8000/api/v1/cog \
    -H "Content-Type: application/json" \
    -d '{
          "source": "s3://my-bucket/path/to/raster.tif",
          "destination": "s3://my-bucket/path/to/raster_cog.tif"
        }'
# => {"stored": "s3://my-bucket/path/to/raster_cog.tif"}
```

Errors follow the same convention: HTTP 400 for invalid/unreachable
input, 502 if `gdal_translate` fails during conversion.

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

Example run against a local MinIO instance:

```bash
docker run --rm -p 8000:8000 \
    -e S3_ENDPOINT_URL=http://minio:9000 \
    -e S3_ACCESS_KEY_ID=minioadmin \
    -e S3_SECRET_ACCESS_KEY=minioadmin \
    --network minio-net \
    cng-lite
```
