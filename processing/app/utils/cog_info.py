"""COG bounding box reader, via `gdalinfo -json`."""

import json
import logging
import subprocess

logger = logging.getLogger(__name__)


def read_cog_info(path: str) -> dict:
    """Return {'bbox': [west, south, east, north]} (WGS84) for a local COG.

    Best-effort: returns {} if gdalinfo fails or the output is unreadable,
    since this only enriches the generated Portolan catalog rather than
    gating the conversion itself.
    """
    try:
        output = subprocess.run(
            ["gdalinfo", "-json", path],
            check=True,
            capture_output=True,
            text=True,
            timeout=30,
        ).stdout
        info = json.loads(output)
        coordinates = info["wgs84Extent"]["coordinates"][0]
        lons = [point[0] for point in coordinates]
        lats = [point[1] for point in coordinates]
        return {"bbox": [min(lons), min(lats), max(lons), max(lats)]}
    except Exception:
        logger.warning("Could not read COG bounds for %s", path, exc_info=True)
        return {}
