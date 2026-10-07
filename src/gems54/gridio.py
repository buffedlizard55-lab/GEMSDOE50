"""Grid-checked raster I/O shared by the H53 scripts.

Every raster this project reads or writes is validated against the official competition grid taken
from ``data/grid/sample_submission.tif`` (the file the problem description tells competitors to use
as the template): EPSG:32611, 100 m, 3730 x 3292, transform (243350, 4508550) with -100 m rows.
A mismatch raises; nothing here resamples or "fixes up" a raster.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import rasterio
from scipy import ndimage

REPO = Path(__file__).resolve().parents[2]
GRID = {"width": 3292, "height": 3730, "crs": "EPSG:32611",
        "transform": (100.0, 0.0, 243350.0, 0.0, -100.0, 4508550.0), "pixel_m": 100.0}

_CACHE: dict[str, np.ndarray] = {}


def _check(path: Path, ds) -> None:
    if (ds.width, ds.height) != (GRID["width"], GRID["height"]):
        raise ValueError(f"{path.name}: shape {(ds.height, ds.width)} != {(GRID['height'], GRID['width'])}")
    if str(ds.crs) != GRID["crs"]:
        raise ValueError(f"{path.name}: CRS {ds.crs} != {GRID['crs']}")
    t = tuple(float(v) for v in ds.transform)[:6]
    if not np.allclose(t, GRID["transform"]):
        raise ValueError(f"{path.name}: transform {t} != {GRID['transform']}")


def read_band(path: str | Path, band: int = 1) -> np.ndarray:
    path = Path(path)
    with rasterio.open(path) as ds:
        _check(path, ds)
        return ds.read(band)


def _cached(key: str, build) -> np.ndarray:
    if key not in _CACHE:
        _CACHE[key] = build()
    return _CACHE[key]


def footprint() -> np.ndarray:
    def build():
        with rasterio.open(REPO / "data/grid/sample_submission.tif") as ds:
            _check(REPO / "data/grid/sample_submission.tif", ds)
            return np.isfinite(ds.read(1))
    return _cached("footprint", build)


def labels() -> np.ndarray:
    def build():
        a = read_band(REPO / "data/grid/labels.tif")
        return (a == 1) & footprint()
    return _cached("labels", build)


def catalogue_distance() -> np.ndarray:
    """Pixels to the nearest provided-catalogue trace cell (0 on a catalogue cell)."""
    return _cached("cat_dist", lambda: ndimage.distance_transform_edt(~labels()).astype(np.float32))


def load_binary_support(path: str | Path) -> dict:
    """Read a submission raster on the official grid and return its positive support + diagnostics."""
    path = Path(path)
    with rasterio.open(path) as ds:
        _check(path, ds)
        arr = ds.read(1)
        nodata = ds.nodatavals[0]
    finite = np.isfinite(arr)
    sup = finite & (arr > 0)
    vals = arr[finite & (arr != 0)]
    return {"support": sup, "values": arr, "finite": finite,
            "binary": bool(vals.size and np.allclose(vals, 1.0)),
            "n_distinct": int(np.unique(arr[finite]).size),
            "nan_cells": int((~finite).sum()), "outside_unit_interval": int(((arr < 0) | (arr > 1)).sum()),
            "cat_dist": catalogue_distance(), "nodata_tag": nodata, "path": str(path)}


def edge_distance_px() -> np.ndarray:
    """Distance in pixels from every cell to the nearest cell outside the data footprint.

    Every derivative filter in this project is contaminated at the boundary between data and
    no-data: the smoothed field steps to zero there, so a structure tensor computed on it reports
    a strong synthetic "lineament" ringing around the whole footprint outline.
    """
    key = ("edge_distance",)
    if key not in _CACHE:
        from scipy import ndimage
        _CACHE[key] = ndimage.distance_transform_edt(footprint()).astype(np.float32)
    return _CACHE[key]


def emission_domain(buffer_px: float = 2.0, edge_guard_px: float = 6.0) -> np.ndarray:
    """Where a dot is allowed at all: inside the footprint, far enough from the given catalogue,
    and far enough from the footprint edge (see :func:`edge_distance_px`)."""
    d = footprint() & (catalogue_distance() > buffer_px)
    if edge_guard_px > 0:
        d &= edge_distance_px() > edge_guard_px
    return d
