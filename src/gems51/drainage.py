"""Real D8 flow routing on the official 100 m DEM, for the H52-A drainage-deflection test.

This module is this project's own construction. It is **not** a transcription of a published
drainage-offset/piercing-point algorithm; it operationalises the generic geomorphic observation
that a fault crossing a stream can deflect or kink the channel (e.g. Keller & Pinter, *Active
Tectonics*, Ch. 5) into a single, falsifiable, locally-computed field so it can be tested as an
independent corroborator of a topographic step, never as a stand-alone fault detector.

Inputs
------
`topo_u8.tif` band 9 (`dem_mean`) is the only elevation source used here. It is the
competition's own 10 m-aggregated-to-100 m DEM descriptor (see
`data/external/README.md`/`registry/sources.json` for provenance); no separate DEM is fetched.

Pipeline
--------
1. Decode `dem_mean` to metres with the project's standard `q_lo/q_hi` rule.
2. Route flow with `pysheds` (pit fill -> depression fill -> flat resolution -> D8 direction ->
   D8 accumulation). `pysheds==0.5.0` calls `numpy.in1d`, removed in NumPy >= 2.0; this module
   shims it to `numpy.isin` at import time (documented NumPy successor, identical result for the
   1-D membership test `pysheds` performs on the 8 direction codes) rather than silently failing
   or pinning an old NumPy for the whole project.
3. Threshold accumulation to a channel mask (`channel_area_cells`, preregistered below).
4. Build a **channel-deflection field**: at each channel cell, the circular mean resultant length
   R of the D8 flow-direction unit vectors in a local window, restricted to other channel cells.
   Deflection = 1 - R, i.e. 0 where the local channel runs in one direction (R=1), approaching 1
   where direction is highly variable in the window (a sharp bend, knickpoint, or confluence).
   This is the same resultant-length construction `gems51.structfield` calls "coherence" applied
   to a direction field instead of a gradient field, so it is internally consistent with the rest
   of the project's vocabulary, not a new ad hoc statistic.

Known confounders (documented, not fixed): river confluences and meanders also raise this field,
as do DEM aggregation artefacts and the flat-resolution heuristic in closed (endorheic) basins.
This is exactly why H52-A never uses the deflection field alone; it is required only to intersect
an independently measured topographic-step signal within a short radius.
"""
from __future__ import annotations

import numpy as np
import rasterio
from scipy import ndimage

from . import grid as g

CHANNEL_AREA_CELLS = 100          # 1 km^2 contributing area at 100 m cells (preregistered)
DEFLECTION_WINDOW_PX = 5          # 500 m window for the local circular-resultant statistic
MIN_CHANNEL_NEIGHBOURS = 3        # minimum weight before a deflection value is trusted


def _ensure_in1d_shim() -> None:
    if not hasattr(np, "in1d"):
        # NumPy >= 2.0 removed np.in1d; np.isin is the documented, behaviourally identical
        # successor for the 1-D membership test pysheds performs here. Recorded as an
        # irregularity: pysheds 0.5.0 (PyPI, 2022) predates NumPy's removal of in1d.
        np.in1d = np.isin  # type: ignore[attr-defined]


def load_dem_mean(topo_path: str) -> tuple[np.ndarray, np.ndarray, dict]:
    """Decode `topo_u8.tif` band 9 (`dem_mean`) to metres."""
    with rasterio.open(topo_path) as ds:
        band = ds.read(9).astype(np.float32)
        tags = dict(ds.tags(9))
        desc = ds.descriptions[8] if ds.descriptions else None
    if desc and desc != "dem_mean":
        raise ValueError(f"expected band 9 to be dem_mean, found {desc!r}")
    dem, valid = g.decode_quantised(band, tags)
    return dem.astype(np.float32), valid, {"q_lo": tags.get("q_lo"), "q_hi": tags.get("q_hi")}


def route_flow(dem: np.ndarray, valid: np.ndarray, nodata: float = -9999.0) -> dict:
    """Pit-fill, resolve flats, route D8 direction and accumulation with pysheds."""
    _ensure_in1d_shim()
    import tempfile
    from pathlib import Path

    from pysheds.grid import Grid

    out = np.where(valid, dem, nodata).astype(np.float32)
    profile = {
        "driver": "GTiff", "height": dem.shape[0], "width": dem.shape[1], "count": 1,
        "dtype": "float32", "crs": g.GRID["crs"],
        "transform": rasterio.transform.Affine(*g.GRID["transform"]), "nodata": nodata,
    }
    with tempfile.TemporaryDirectory() as td:
        path = Path(td) / "dem.tif"
        with rasterio.open(path, "w", **profile) as ds:
            ds.write(out, 1)
        grid = Grid.from_raster(str(path))
        raw = grid.read_raster(str(path))
        pit_filled = grid.fill_pits(raw)
        flooded = grid.fill_depressions(pit_filled)
        inflated = grid.resolve_flats(flooded)
        fdir = grid.flowdir(inflated)
        acc = grid.accumulation(fdir)
    return {"fdir": np.asarray(fdir), "acc": np.asarray(acc).astype(np.float64)}


# pysheds default D8 dirmap: (N, NE, E, SE, S, SW, W, NW) -> (64, 128, 1, 2, 4, 8, 16, 32)
_DIRMAP = (64, 128, 1, 2, 4, 8, 16, 32)
_ANGLES = {code: np.radians(90.0 - 45.0 * i) for i, code in enumerate(_DIRMAP)}


def direction_angle(fdir: np.ndarray) -> np.ndarray:
    """Map pysheds D8 codes to a flow-direction angle in radians (0 = east, CCW positive)."""
    angle = np.zeros(fdir.shape, dtype=np.float32)
    for code, theta in _ANGLES.items():
        angle = np.where(fdir == code, theta, angle)
    return angle


def channel_deflection(fdir: np.ndarray, acc: np.ndarray, valid: np.ndarray, *,
                        channel_area_cells: int = CHANNEL_AREA_CELLS,
                        window_px: int = DEFLECTION_WINDOW_PX,
                        min_neighbours: int = MIN_CHANNEL_NEIGHBOURS) -> dict:
    """Channel mask and the 1-R circular-deflection field, restricted to channel cells."""
    channel = valid & (acc >= channel_area_cells)
    angle = direction_angle(fdir)
    cos_a = np.where(channel, np.cos(angle), 0.0).astype(np.float32)
    sin_a = np.where(channel, np.sin(angle), 0.0).astype(np.float32)
    weight = channel.astype(np.float32)
    box = np.ones((window_px, window_px), dtype=np.float32)
    sum_cos = ndimage.convolve(cos_a, box, mode="constant")
    sum_sin = ndimage.convolve(sin_a, box, mode="constant")
    count = ndimage.convolve(weight, box, mode="constant")
    resultant = np.sqrt(sum_cos ** 2 + sum_sin ** 2) / np.maximum(count, 1.0)
    deflection = np.where(channel & (count >= min_neighbours), 1.0 - resultant, 0.0).astype(np.float32)
    return {
        "channel_mask": channel,
        "deflection": deflection,
        "channel_cells": int(np.count_nonzero(channel)),
        "channel_area_cells": channel_area_cells,
        "window_px": window_px,
    }
