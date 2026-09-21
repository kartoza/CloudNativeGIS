"""GeoPackage layer introspection, via ogrinfo (this image's GDAL predates
`ogrinfo -json` and has no `osgeo` Python bindings, so its stable plain-text
summary format is parsed instead)."""

import re
import sqlite3
import subprocess

from app.errors import ConversionError

_LAYER_BLOCK = re.compile(
    r"^Layer name:\s*(?P<name>.+)$\n"
    r"Geometry:\s*(?P<geometry>.+)$\n"
    r"Feature Count:\s*(?P<count>\d+)$",
    re.MULTILINE,
)


def list_layers(gpkg_path: str) -> list:
    """Return [{'name', 'geometryType', 'featureCount'}, ...] for a GeoPackage.

    Excludes non-spatial attribute tables (geometry type "None") such as
    QGIS's own `qgis_projects`/`layer_styles` bookkeeping tables, which
    ogrinfo reports as layers too but have nothing to tile.
    """
    try:
        output = subprocess.run(
            ["ogrinfo", "-al", "-so", gpkg_path],
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
            "name": match.group("name").strip(),
            "geometryType": match.group("geometry").strip(),
            "featureCount": int(match.group("count")),
        }
        for match in _LAYER_BLOCK.finditer(output)
        if match.group("geometry").strip().lower() != "none"
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
    """A filesystem-safe stem for a layer name (used for its GeoJSON file)."""
    return re.sub(r"[^A-Za-z0-9_-]+", "_", name) or "layer"
