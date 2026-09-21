"""Validate a shapefile .zip contains the required sibling files."""

import os
import zipfile

from app.errors import ConversionError

REQUIRED_EXTENSIONS = (".shp", ".shx", ".dbf")


def validate_shapefile_zip(zip_path: str) -> None:
    """Validate zip_path is a zip containing a complete .shp/.shx/.dbf set.

    Raises ConversionError(400, ...) if invalid.
    """
    if not zipfile.is_zipfile(zip_path):
        raise ConversionError(400, "Source file is not a valid zip file")

    with zipfile.ZipFile(zip_path, "r") as archive:
        names = archive.namelist()

    shp_names = {
        os.path.splitext(n)[0] for n in names if n.lower().endswith(".shp")
    }
    if not shp_names:
        raise ConversionError(400, "No .shp file found inside the zip archive")

    lower_names = {n.lower() for n in names}
    missing = []
    for base in shp_names:
        for ext in REQUIRED_EXTENSIONS:
            if f"{base.lower()}{ext}" not in lower_names:
                missing.append(f"{base}{ext}")

    if missing:
        raise ConversionError(
            400,
            "Shapefile zip is missing required files: "
            + ", ".join(sorted(missing)),
        )
