"""Grid, catalogue, footprint and auxiliary rasters on the official competition grid.

All rasters here are EPSG:32611, 100 m, 3292 x 3730, transform (243350, 4508550) with
-100 m rows, matching ``sample_submission.tif`` exactly.  Nothing in this module rewrites
or resamples a source raster: a mismatch is an error, not a fix-up.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import rasterio

REPO = Path(__file__).resolve().parents[2]
GRID = {
    "width": 3292,
    "height": 3730,
    "crs": "EPSG:32611",
    "transform": (100.0, 0.0, 243350.0, 0.0, -100.0, 4508550.0),
    "pixel_m": 100.0,
}
LEFT, TOP = 243350.0, 4508550.0


def load_raster(path: str | Path, band: int = 1) -> tuple[np.ndarray, dict]:
    with rasterio.open(path) as ds:
        if ds.crs is None or str(ds.crs) != GRID["crs"]:
            raise ValueError(f"{path}: CRS {ds.crs} != {GRID['crs']}")
        if (ds.width, ds.height) != (GRID["width"], GRID["height"]):
            raise ValueError(f"{path}: shape {(ds.width, ds.height)} != grid")
        t = tuple(float(v) for v in ds.transform)[:6]
        if not np.allclose(t, GRID["transform"]):
            raise ValueError(f"{path}: transform {t} != grid")
        data = ds.read(band)
        info = {"path": str(path), "count": ds.count, "dtype": ds.dtypes[band - 1],
                "nodata": ds.nodata,
                "description": ds.descriptions[band - 1] if ds.descriptions else None,
                "tags": dict(ds.tags(band))}
    return data, info


def decode_quantised(band: np.ndarray, tags: dict) -> tuple[np.ndarray, np.ndarray]:
    """Decode the owner-mirrored u8 rasters: 0 = nodata, else lo+(q-1)/254*(hi-lo)."""
    q = band.astype(np.float32)
    valid = q > 0
    if "q_lo" in tags and "q_hi" in tags:
        lo, hi = float(tags["q_lo"]), float(tags["q_hi"])
        out = np.where(valid, lo + (q - 1.0) / 254.0 * (hi - lo), np.nan)
    else:
        out = np.where(valid, (q - 1.0) / 254.0, np.nan)
    return out.astype(np.float32), valid


def col_row(x: np.ndarray, y: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Projected metres -> integer (col, row).  No clipping: callers test bounds."""
    col = np.floor((np.asarray(x, dtype=np.float64) - LEFT) / GRID["pixel_m"]).astype(np.int64)
    row = np.floor((TOP - np.asarray(y, dtype=np.float64)) / GRID["pixel_m"]).astype(np.int64)
    return col, row


def load_labels(path: str | Path | None = None) -> np.ndarray:
    """The official catalogue raster: 1 = mapped trace, 0 = mapped absence, -1 = nodata."""
    p = Path(path) if path else REPO / "data" / "grid" / "labels.tif"
    data, _ = load_raster(p)
    return data == 1


def load_footprint(path: str | Path | None = None) -> np.ndarray:
    """The scoring footprint: finite cells of the official example submission."""
    p = Path(path) if path else REPO / "data" / "grid" / "sample_submission.tif"
    data, _ = load_raster(p)
    return np.isfinite(data)
