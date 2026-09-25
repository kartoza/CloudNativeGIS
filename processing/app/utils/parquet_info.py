"""GeoParquet schema/extent reader, via `ogrinfo -json`."""

import json
import logging
import subprocess

logger = logging.getLogger(__name__)

# OGR field types -> STAC table extension / Parquet-ish type names.
_TYPES = {
    "String": "string",
    "Integer": "int32",
    "Integer64": "int64",
    "Real": "double",
    "Date": "date32",
    "DateTime": "timestamp",
    "Time": "time",
    "Binary": "binary",
    "IntegerList": "list<int32>",
    "Integer64List": "list<int64>",
    "RealList": "list<double>",
    "StringList": "list<string>",
}


def read_parquet_info(path: str) -> dict:
    """Return {'columns', 'rowCount', 'bbox'} for a local GeoParquet file.

    `columns` is [{'name', 'type'}, ...] including the geometry column, as
    the STAC table extension's `table:columns` expects. `bbox` is in the
    file's own CRS, which isn't necessarily WGS84. Best-effort: returns {}
    if ogrinfo fails, since this only enriches the generated Portolan
    catalog rather than gating the conversion itself.
    """
    try:
        output = subprocess.run(
            ["ogrinfo", "-json", "-so", "-al", path],
            check=True,
            capture_output=True,
            text=True,
            timeout=30,
        ).stdout
        layer = json.loads(output)["layers"][0]
        columns = [
            {
                "name": field["name"],
                "type": _TYPES.get(field["type"], "string"),
            }
            for field in layer.get("fields", [])
        ]
        geometry = (layer.get("geometryFields") or [{}])[0]
        if geometry.get("name"):
            columns.append({"name": geometry["name"], "type": "binary"})
        return {
            "columns": columns,
            "rowCount": layer.get("featureCount"),
            "bbox": geometry.get("extent"),
        }
    except Exception:
        logger.warning(
            "Could not read GeoParquet info for %s", path, exc_info=True
        )
        return {}
