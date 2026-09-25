"""GeoPackage layer introspection, via `ogrinfo -json`."""

import json
import re
import sqlite3
import subprocess

from app.errors import ConversionError


def list_layers(gpkg_path: str) -> list:
    """Return [{'name', 'geometryType', 'featureCount'}, ...] for a GeoPackage.

    Excludes non-spatial attribute tables (geometry type "None") such as
    QGIS's own `qgis_projects`/`layer_styles` bookkeeping tables, which
    ogrinfo reports as layers too but have nothing to tile.
    """
    try:
        output = subprocess.run(
            ["ogrinfo", "-json", "-so", gpkg_path],
            check=True,
            capture_output=True,
            text=True,
        ).stdout
    except subprocess.CalledProcessError as e:
        raise ConversionError(
            400, f"Could not read GeoPackage: {e.stderr.strip() or e}"
        )

    return [
        {
            "name": layer["name"],
            "geometryType": layer["geometryFields"][0]["type"],
            "featureCount": layer.get("featureCount", 0),
        }
        for layer in json.loads(output).get("layers", [])
        if layer.get("geometryFields")
    ]


def list_raster_tables(gpkg_path: str) -> list:
    """Return [{'name': ...}] for each raster ('tiles') table in a GeoPackage.

    A GeoPackage can hold vector layers and raster tile tables side by
    side; ogrinfo only reports the former, so this reads the raster ones
    straight out of the gpkg_contents bookkeeping table (a GeoPackage is
    itself just a SQLite database).
    """
    try:
        connection = sqlite3.connect(gpkg_path)
        try:
            rows = connection.execute(
                "SELECT table_name FROM gpkg_contents "
                "WHERE data_type IN ('tiles', '2d-gridded-coverage')"
            ).fetchall()
        finally:
            connection.close()
    except sqlite3.DatabaseError as e:
        raise ConversionError(400, f"Could not read GeoPackage: {e}")

    return [{"name": row[0]} for row in rows]


def sanitize_layer_filename(name: str) -> str:
    """Return a filesystem-safe stem for a layer name (its GeoJSON file)."""
    return re.sub(r"[^A-Za-z0-9_-]+", "_", name) or "layer"
