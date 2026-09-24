"""Minimal PMTiles v3 header/metadata reader.

Only what Portolan collection generation needs: the tile bounding box,
zoom range, and vector layer ids. No dependency beyond the standard
library — the header is a fixed 127-byte binary layout, and the JSON
metadata block (optionally gzip-compressed) sits at an offset it names.
See https://github.com/protomaps/PMTiles/blob/main/spec/v3/spec.md
"""

import gzip
import json
import struct

_HEADER_SIZE = 127
_MAGIC = b"PMTiles"


def read_pmtiles_info(path: str) -> dict:
    """Return bbox/minzoom/maxzoom/layers for a local PMTiles file.

    `bbox` is [west, south, east, north] in WGS84. `layers` lists the
    vector_layers ids from the JSON metadata block (empty for a tileset
    that has none, e.g. raster tiles). Returns an empty dict if the file
    can't be parsed — this is best-effort catalog enrichment, not a
    validity check (validate_pmtiles already confirmed the magic bytes).
    """
    try:
        with open(path, "rb") as f:
            header = f.read(_HEADER_SIZE)
            if len(header) < _HEADER_SIZE or header[:7] != _MAGIC:
                return {}
            (
                _root_dir_offset,
                _root_dir_length,
                json_metadata_offset,
                json_metadata_length,
                *_rest,
            ) = struct.unpack_from("<QQQQQQQQQQQ", header, 8)
            internal_compression = header[97]
            min_zoom = header[100]
            max_zoom = header[101]
            min_lon_e7, min_lat_e7, max_lon_e7, max_lat_e7 = (
                struct.unpack_from("<iiii", header, 102)
            )

            layers = []
            if json_metadata_length:
                f.seek(json_metadata_offset)
                raw = f.read(json_metadata_length)
                if internal_compression == 2:
                    raw = gzip.decompress(raw)
                metadata = json.loads(raw)
                layers = [
                    layer["id"]
                    for layer in metadata.get("vector_layers", [])
                    if layer.get("id")
                ]

        return {
            "bbox": [
                min_lon_e7 / 1e7,
                min_lat_e7 / 1e7,
                max_lon_e7 / 1e7,
                max_lat_e7 / 1e7,
            ],
            "minzoom": min_zoom,
            "maxzoom": max_zoom,
            "layers": layers,
        }
    except Exception:
        return {}
