"""Render a layer's thumbnail.png from its default style.
"""

import json
import logging
import os
import subprocess
import sys
from typing import Optional

logger = logging.getLogger(__name__)

SIZE = 512
MEDIA_TYPE = "image/png"
# The default style's colours (see CloudBench's portolan.py).
BACKGROUND = "#f8f9fa"
FEATURE_COLOR = "#2d7d9b"
FILL_OPACITY = 0.5
VECTOR_TIMEOUT = 120
RASTER_TIMEOUT = 60


def render_vector_thumbnail(
    source: str, output_path: str, layer: Optional[str] = None
) -> bool:
    """Render a vector source (any OGR path, e.g. /vsizip/...) to PNG."""
    cmd = [sys.executable, "-m", "app.utils.thumbnail", source, output_path]
    if layer:
        cmd.append(layer)
    try:
        subprocess.run(
            cmd,
            check=True,
            capture_output=True,
            text=True,
            timeout=VECTOR_TIMEOUT,
            cwd=os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
        )
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired) as e:
        stderr = getattr(e, "stderr", "") or ""
        logger.warning(
            "Could not render thumbnail for %s: %s", source, stderr or e
        )
        return False
    return os.path.exists(output_path)


def _draw_vector(source: str, output_path: str, layer: Optional[str]):
    """Draw a vector layer (runs in the subprocess)."""
    import geopandas
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    frame = geopandas.read_file(source, layer=layer)
    frame = frame[frame.geometry.notna() & ~frame.geometry.is_empty]
    if frame.empty:
        raise ValueError("layer has no geometries")
    if frame.crs is None:
        frame = frame.set_crs("EPSG:4326")
    # Web Mercator can't represent the poles; clip to its valid latitudes.
    frame = frame.to_crs("EPSG:4326").clip((-180, -85.05, 180, 85.05))
    frame = frame.to_crs("EPSG:3857")
    if frame.empty:
        raise ValueError("layer has no geometries within Web Mercator bounds")

    minx, miny, maxx, maxy = frame.total_bounds
    width, height = max(maxx - minx, 1.0), max(maxy - miny, 1.0)
    # Fit the layer's aspect ratio into a SIZE x SIZE box.
    scale = SIZE / max(width, height)
    pixels = (max(int(width * scale), 64), max(int(height * scale), 64))
    dpi = 100
    figure = plt.figure(
        figsize=(pixels[0] / dpi, pixels[1] / dpi),
        dpi=dpi,
        facecolor=BACKGROUND,
    )
    axes = figure.add_axes((0.04, 0.04, 0.92, 0.92))
    axes.set_axis_off()
    axes.set_facecolor(BACKGROUND)

    geometry_types = frame.geometry.geom_type
    polygons = frame[geometry_types.str.contains("Polygon")]
    lines = frame[geometry_types.str.contains("LineString")]
    points = frame[geometry_types.str.contains("Point")]
    line_width = 72 / dpi  # 1 px, in points
    if not polygons.empty:
        polygons.plot(
            ax=axes,
            facecolor=FEATURE_COLOR,
            alpha=FILL_OPACITY,
            edgecolor="none",
        )
        polygons.boundary.plot(
            ax=axes, color=FEATURE_COLOR, linewidth=line_width
        )
    if not lines.empty:
        lines.plot(ax=axes, color=FEATURE_COLOR, linewidth=line_width)
    if not points.empty:
        points.plot(ax=axes, color=FEATURE_COLOR, markersize=6)
    axes.set_xlim(minx, maxx)
    axes.set_ylim(miny, maxy)
    axes.set_aspect("equal")
    figure.savefig(output_path, dpi=dpi, facecolor=BACKGROUND)
    plt.close(figure)


def render_raster_thumbnail(cog_path: str, output_path: str) -> bool:
    """Render a (Web Mercator) COG to PNG, reading its overviews.

    RGB(A) bytes are drawn as-is, a paletted band through its palette,
    and anything else as greyscale stretched between the band's embedded
    min/max statistics; nodata/masked pixels come out transparent.
    """
    try:
        info = json.loads(
            subprocess.run(
                ["gdalinfo", "-json", cog_path],
                check=True,
                capture_output=True,
                text=True,
                timeout=RASTER_TIMEOUT,
            ).stdout
        )
        width, height = info["size"]
        scale = SIZE / max(width, height, 1)
        size = [
            str(max(int(width * scale), 1)),
            str(max(int(height * scale), 1)),
        ]
        bands = info.get("bands", [])
        first = bands[0] if bands else {}
        options: list = []
        if len(bands) >= 3 and first.get("type") == "Byte":
            options = ["-b", "1", "-b", "2", "-b", "3"]
            alpha = bands[3] if len(bands) >= 4 else {}
            # Keep an existing alpha band, else derive one from the mask
            # (nodata/masked pixels transparent, like on the map).
            if alpha.get("colorInterpretation") == "Alpha":
                options += ["-b", "4"]
            else:
                options += ["-b", "mask"]
        elif first.get("colorInterpretation") == "Palette":
            options = ["-expand", "rgba"]
        else:
            stats = first.get("metadata", {}).get("", {})
            low = float(stats.get("STATISTICS_MINIMUM", 0))
            high = float(stats.get("STATISTICS_MAXIMUM", 255))
            if low == high:
                # A constant raster: mid-grey, rather than a stretch of
                # nothing that turns it (and its nodata) all white.
                low, high = low - 1, high + 1
            options = [
                "-b",
                "1",
                "-b",
                "mask",
                "-ot",
                "Byte",
                "-scale_1",
                str(low),
                str(high),
                "0",
                "255",
            ]
        subprocess.run(
            [
                "gdal_translate",
                "-q",
                "-of",
                "PNG",
                "-outsize",
                *size,
                "-r",
                "average",
                *options,
                cog_path,
                output_path,
            ],
            check=True,
            capture_output=True,
            text=True,
            timeout=RASTER_TIMEOUT,
        )
    except Exception:
        logger.warning(
            "Could not render thumbnail for %s", cog_path, exc_info=True
        )
        return False
    # gdal_translate may leave a PAM sidecar next to the PNG; not needed.
    if os.path.exists(f"{output_path}.aux.xml"):
        os.remove(f"{output_path}.aux.xml")
    return os.path.exists(output_path)


if __name__ == "__main__":
    _draw_vector(
        sys.argv[1], sys.argv[2], sys.argv[3] if len(sys.argv) > 3 else None
    )
