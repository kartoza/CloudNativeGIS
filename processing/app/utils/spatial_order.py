"""Order a GeoParquet file's rows along a Hilbert curve.

Portolan requires spatially ordered rows (PTL-DAT-006): consecutive rows -
and so each row group - should cover one compact area, so a reader can
skip whole row groups by their bbox statistics. GDAL's SORT_BY_BBOX isn't
ordered closely enough for that. Ordering rows by the Hilbert index of
their bbox's centre is: the curve keeps nearby points next to each other.

A geometry column big enough to overflow `binary`'s 32-bit offsets while
being reordered (see _widen_binary_columns) is written back out as
`large_binary` rather than GDAL's original `binary` - geoparquet readers
(GDAL/pyogrio, geopandas, DuckDB spatial) accept either for WKB, so this
only changes the Arrow subtype of an already-exceptional file, not its
readability.
"""

import json
import os
from typing import Optional

import numpy as np
import pyarrow as pa
import pyarrow.parquet as pq

# Cells per side of the grid the curve runs through: 2^16, far finer than
# any row group needs.
HILBERT_ORDER = 16


def hilbert_index(
    x: np.ndarray, y: np.ndarray, order: int = HILBERT_ORDER
) -> np.ndarray:
    """Each (x, y) cell's distance along the Hilbert curve.

    `x`/`y` are integer cells in [0, 2^order).
    """
    n = 1 << order
    x = x.astype(np.int64)
    y = y.astype(np.int64)
    d = np.zeros(x.shape, dtype=np.int64)
    s = n >> 1
    while s > 0:
        rx = (x & s) > 0
        ry = (y & s) > 0
        d += s * s * ((3 * rx.astype(np.int64)) ^ ry.astype(np.int64))
        # Rotate the quadrant, so the curve stays continuous.
        flip = ~ry & rx
        x = np.where(flip, n - 1 - x, x)
        y = np.where(flip, n - 1 - y, y)
        x, y = np.where(~ry, y, x), np.where(~ry, x, y)
        s >>= 1
    return d


def _covering(schema) -> Optional[dict]:
    """Find the primary geometry's bbox covering: {'xmin': [column, field]}."""
    metadata = (schema.metadata or {}).get(b"geo")
    if not metadata:
        return None
    geo = json.loads(metadata)
    column = geo.get("columns", {}).get(geo.get("primary_column"), {})
    return column.get("covering", {}).get("bbox")


def _widen_binary_columns(table: pa.Table) -> pa.Table:
    """Cast any plain `binary` column (e.g. WKB geometry) to `large_binary`.

    Reordering a column this size - combine_chunks() below, or take()
    further down - can need to produce one array bigger than binary's
    32-bit offsets can address (~2GB of data): "offset overflow while
    concatenating arrays". large_binary's 64-bit offsets can't overflow
    on anything this reads.
    """
    fields = [
        field.with_type(pa.large_binary()) if pa.types.is_binary(field.type) else field
        for field in table.schema
    ]
    return table.cast(pa.schema(fields, metadata=table.schema.metadata))


def sort_spatially(path: str, row_group_size: int) -> None:
    """Rewrite the GeoParquet at `path` with its rows in Hilbert order.

    Reads the bbox covering column GDAL writes (WRITE_COVERING_BBOX), so
    no geometry is decoded; everything else - the GeoParquet metadata
    included - is kept as it is. Rows without a geometry go last. Leaves
    a file without a covering column as it is.
    """
    table = _widen_binary_columns(pq.read_table(path))
    covering = _covering(table.schema)
    if covering is None or table.num_rows < 2:
        return

    def side(name):
        column, field = covering[name]
        values = table.column(column).combine_chunks().field(field)
        return values.to_numpy(zero_copy_only=False).astype(np.float64)

    cx = (side("xmin") + side("xmax")) / 2
    cy = (side("ymin") + side("ymax")) / 2
    present = ~(np.isnan(cx) | np.isnan(cy))
    if not present.any():
        return
    cells = (1 << HILBERT_ORDER) - 1

    def to_cells(values):
        low, high = values[present].min(), values[present].max()
        span = (high - low) or 1.0
        scaled = np.nan_to_num((values - low) / span, nan=1.0)
        return np.clip(scaled * cells, 0, cells).astype(np.int64)

    index = hilbert_index(to_cells(cx), to_cells(cy))
    index[~present] = np.iinfo(np.int64).max
    order = np.argsort(index, kind="stable")

    temporary = f"{path}.sorting"
    pq.write_table(
        table.take(order),
        temporary,
        compression="zstd",
        row_group_size=row_group_size,
    )
    os.replace(temporary, path)
