---
title: Consuming a converted layer
summary: What CloudBench's S3 conversions actually hand you, and how to use each file
---

# Consuming a converted layer

CloudBench converts files already sitting in a bucket into web-ready layers, in the
background (see [CloudBench S3 conversion process](../developer/cloudbench-s3-conversions.md)
for how that conversion itself runs). This page is for whoever consumes the result -
a map developer, a data analyst, an AI agent exploring the bucket - not for maintaining
CloudBench itself.

## What you get, and where

Each converted layer lands in its own folder of the bucket, laid out as a
[Portolan](https://github.com/portolan-sdi/portolan-spec) "single-file collection" -
the same shape whether it came from a vector source or a raster one:

| File | For |
|---|---|
| `collection.json` | The layer's metadata: license, bounding box, and its **assets** - see below. The thing to fetch first; everything else is linked from it. |
| `README.md` | A human reading the bucket directly (e.g. browsing it in a file manager). |
| `AGENTS.md` | An AI agent exploring the bucket: which asset to actually query, and which are just for rendering. |
| `styles/default.json` | A ready-to-use [MapLibre](https://maplibre.org/) style - point a map straight at it, no styling work needed. |

Within `collection.json`, each **asset** is tagged with a `role` that tells you
*which file to use for what* - this is the main thing worth knowing, since every
layer produces more than one file and they are not interchangeable:

- **`data`** - the file to query or analyse (a GeoParquet for vector, the
  original-CRS COG for raster). Never the one to put on a map directly.
- **`visual`** - the file a map renders (PMTiles for vector, the `EPSG:3857` COG
  for raster).
- **`thumbnail`** - a small PNG preview.
- **`source`** (GeoPackage only) - the original upload, kept alongside its
  converted layers.

A GeoPackage's several layers are grouped under one sub-catalog folder (a shared
`catalog.json` linking each layer's own `collection.json`) rather than scattered at
the top level, so discovering the bucket shows them as one dataset, not loose files.

## Vector layers: PMTiles (render) + GeoParquet (query)

Both files are **static** - there is no tile server or query API behind them, only
the bucket (or a CDN in front of it):

- **PMTiles** packs every zoom/tile into one file with its own internal index, so a
  map library (`pmtiles` / `maplibre-gl` / `leaflet`) fetches exactly the tile(s) it
  needs with plain HTTP range requests - no backend to run, and nothing to pre-warm.
- **GeoParquet**'s bbox-covering column and row-group layout let a reader (`duckdb`,
  `geopandas`, `pyarrow`) skip straight to the row groups that overlap an area of
  interest, without downloading the whole file or needing a spatial database - a
  plain `duckdb` query against the object's URL (via its `httpfs`/`spatial`
  extensions) can filter spatially before a single row is parsed.

Querying the PMTiles for individual feature attributes isn't the intended use - tiles
are simplified per zoom level, and features can be split across tile boundaries. Use
the GeoParquet for that; use the PMTiles only to render.

## Raster layers: two COGs, for two different jobs

A COG is a regular GeoTIFF with its internal tiles and overviews laid out so a client
can read *just the part it needs* over plain HTTP (GDAL's `/vsicurl/`, `rasterio`,
`rio-tiler`, `titiler`, QGIS's "Add Layer from URL", ...) - never the whole file, even
for a single pixel value or a zoomed-out overview.

Pick the variant for what you're doing with it, not by habit - **don't download and
reproject the one you grabbed instead of fetching the right one**:

- The **original-CRS** COG (`data` asset) for anything that measures or analyses the
  raster (area, zonal statistics, sampling) - reprojecting first would distort those
  measurements.
- The **`_3857`** COG (`visual` asset) for a web map - most map libraries
  (MapLibre/Leaflet/OpenLayers) render in Web Mercator, and `maplibre-cog-protocol`
  specifically only accepts this one.

Both carry their band statistics (min/max/mean/stddev) embedded in the file's own
header, so a client can colour-stretch the raster sensibly straight from that - no
full-raster scan needed just to render it reasonably.

## A bulk upload's VRT

A bulk upload may also publish one GDAL VRT ("virtual raster") over all the GeoTIFFs
it converted that share a CRS, band count and data type - letting you open *one* file
and see the whole compatible set as a single continuous dataset, instead of
requesting and mosaicking each COG yourself.

A few things worth knowing before you reach for it:

- It's **metadata only** - an XML file referencing the underlying COGs, not a
  re-encoded copy. Opening it still reads pixels from the original COGs over HTTP;
  nothing is pre-rendered.
- It's linked from the bucket's root catalog (so it's discoverable), but it has no
  renderable asset of its own - open it with desktop GIS or GDAL tooling
  (`gdalinfo`, QGIS, `rasterio`), not CloudBench's own Map Explorer.
- Not every raster in the batch is necessarily covered - one with a different CRS,
  band count or data type is left out of the VRT (and told why), though it's still
  published as its own ordinary COG collection regardless.
