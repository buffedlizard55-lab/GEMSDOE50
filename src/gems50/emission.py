"""Turning evidence into a legal, metric-aware submission raster.

Three facts drive every design choice here, and each is verified in ``tests/``:

1. **Binary is optimal.**  For a fixed support, scaling a prediction by ``s`` gives
   ``DTI(s) = sT / (0.2 s (T + S - M) + 0.8 |G|)``, whose derivative is
   ``0.8 T |G| / (...)^2 > 0``.  DTI therefore increases with scale, so the optimum over
   ``p in [0, 1]`` sits at a vertex: every emitted cell should carry value 1.0.  (This is
   why the group's best-scoring files are sparse "dotted" rasters.)
2. **Mass must stop at the metric's own bar.**  Adding a unit of mass at a cell with
   kernel weight ``w`` raises DTI iff ``w > 0.2 * DTI`` (exactly: see
   :func:`gems50.metric.marginal_condition`). If illustrated with the historically
   reported 0.2778, the threshold is 0.0556 credit per emitted pixel. That score-to-file
   association remains unresolved; it is not a verified incumbent or current organizer
   score and must not be used as a live submission target.
3. **Kernel overlap is waste.**  Two dots closer than the 3-cell kernel radius compete for
   the same truth pixels; the second one adds little and still pays the 0.2 tax.  So the
   packing suppresses a neighbourhood around every accepted dot (greedy maximum coverage).

Nothing in this module is specific to which evidence produced the field.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np
import rasterio
from rasterio.transform import Affine

from . import grid_io as gridmod


@dataclass
class PackResult:
    """A packed dot set and the bookkeeping that justifies it."""

    support: np.ndarray  # boolean raster
    values: np.ndarray  # float32 raster in [0, 1]
    n_dots: int
    field_mass_top: float  # sum of the field over the accepted dots
    mean_field: float  # mean field value of the accepted dots


def normalise(field: np.ndarray, valid: np.ndarray | None = None) -> np.ndarray:
    """Min-max normalise a non-negative field to [0, 1] over the valid area."""
    f = np.asarray(field, dtype=np.float32)
    m = np.isfinite(f)
    if valid is not None:
        m &= valid
    if not m.any():
        return np.zeros_like(f)
    lo = float(f[m].min())
    hi = float(f[m].max())
    if hi <= lo:
        return np.zeros_like(f)
    out = np.clip((np.nan_to_num(f) - lo) / (hi - lo), 0.0, 1.0)
    if valid is not None:
        out = np.where(valid, out, 0.0)
    return out.astype(np.float32)


def oriented_ridge_filter(field: np.ndarray, n_orient: int = 12, length_px: int = 15,
                          width_px: int = 1) -> np.ndarray:
    """Max over orientations of a short oriented mean: a ridge/lineament response.

    The point of the filter is continuity: an isolated bright cell is down-weighted while a
    *line* of bright cells survives.  This is the same transform used on the seismicity
    support (:func:`gems50.lineation.oriented_matched_filter`) applied to a terrain or
    radiometric field.
    """
    from .lineation import oriented_matched_filter

    resp, _ = oriented_matched_filter(np.asarray(field, dtype=np.float32), n_orient,
                                      length_px, width_px)
    return resp


def snap_to_ridge(evidence: np.ndarray, support: np.ndarray, max_shift_px: int = 3,
                  ) -> np.ndarray:
    """Move each support cell to the local maximum of ``evidence`` within the window.

    This is the placement step the brief asks for: the corridor (only as precise as the
    epicentral uncertainty) is snapped onto the ridge of an independent layer.  The search
    window is bounded by ``max_shift_px`` so snapping can never move a prediction further
    than the corridor's own width.
    """
    ev = np.asarray(evidence, dtype=np.float32)
    sup = np.asarray(support, dtype=bool)
    if not sup.any():
        return sup.copy()
    h, w = ev.shape
    rows, cols = np.nonzero(sup)
    shifts = [(dr, dc)
              for dr in range(-max_shift_px, max_shift_px + 1)
              for dc in range(-max_shift_px, max_shift_px + 1)
              if dr * dr + dc * dc <= max_shift_px * max_shift_px]
    vals = np.full((len(rows), len(shifts)), -np.inf, dtype=np.float32)
    coords = np.empty((len(rows), len(shifts), 2), dtype=np.int64)
    for j, (dr, dc) in enumerate(shifts):
        r2 = np.clip(rows + dr, 0, h - 1)
        c2 = np.clip(cols + dc, 0, w - 1)
        vals[:, j] = ev[r2, c2]
        coords[:, j, 0] = r2
        coords[:, j, 1] = c2
    best = np.argmax(vals, axis=1)
    tgt = coords[np.arange(len(rows)), best]
    # a target cell is kept if the evidence there is positive (no snapping into nodata)
    good = ev[tgt[:, 0], tgt[:, 1]] > 0
    out = np.zeros(ev.shape, dtype=bool)
    out[tgt[good, 0], tgt[good, 1]] = True
    return out


def greedy_pack(credit: np.ndarray, mass_budget: int, suppression_px: int = 2,
                min_value: float = 0.0) -> PackResult:
    """Greedy maximum-coverage packing of a credit field into ``mass_budget`` dots.

    ``credit`` is the expected kernel weight a dot at that cell would earn (any monotone
    transform of the evidence works; the ordering is what matters).  Dots are accepted in
    decreasing credit order and each accepted dot suppresses a disk of radius
    ``suppression_px``: two dots closer than the kernel radius cannot both be the best
    cover of different truth pixels, so the second one would only pay the tax.
    """
    c = np.asarray(credit, dtype=np.float32)
    h, w = c.shape
    flat = c.ravel()
    n_cand = min(flat.size, max(10 * mass_budget, mass_budget + 1000))
    part = np.argpartition(-flat, n_cand - 1)[:n_cand]
    order = part[np.argsort(-flat[part], kind="stable")]
    order = order[flat[order] > min_value]
    taken = np.zeros(flat.size, dtype=bool)
    dots = []
    r2 = suppression_px * suppression_px
    for idx in order:
        if len(dots) >= mass_budget:
            break
        r, cc = divmod(int(idx), w)
        if r2 > 0:
            r0, r1 = max(0, r - suppression_px), min(h - 1, r + suppression_px)
            hit = False
            for rr in range(r0, r1 + 1):
                dr = rr - r
                span = int(np.floor(np.sqrt(max(r2 - dr * dr, 0))))
                lo, hi = cc - span, cc + span
                if lo < 0:
                    lo = 0
                if hi >= w:
                    hi = w - 1
                if taken[rr * w + lo : rr * w + hi + 1].any():
                    hit = True
                    break
            if hit:
                continue
        taken[idx] = True
        dots.append(idx)
    support = taken.reshape(h, w)
    values = support.astype(np.float32)
    sel = c[support]
    return PackResult(support=support, values=values, n_dots=int(support.sum()),
                      field_mass_top=float(sel.sum()), mean_field=float(sel.mean()) if sel.size else 0.0)


def catalogue_buffer(labels: np.ndarray, metres: float = 300.0) -> np.ndarray:
    """Boolean raster: cells *outside* ``metres`` of any catalogue cell.

    The competition states the hidden set is made of faults that are **not** in the given
    catalogue.  Mass placed on a mapped fault can therefore only pay the false-positive
    tax; the group measured this directly (removing everything within 200 m of the
    catalogue was worth +0.0049 in their live model, their H33-2).  This helper implements
    the same exclusion at a configurable distance.
    """
    from scipy.ndimage import distance_transform_edt

    d = distance_transform_edt(~np.asarray(labels, dtype=bool))
    return d > (metres / gridmod.CELL_M)


def write_submission(values: np.ndarray, path: str | Path, g: gridmod.Grid | None = None,
                     outside_value: float = 0.0) -> dict:
    """Write a single-band float32 GeoTIFF that satisfies the published submission rules.

    The rules (competition page 967): EPSG:32611, 100 m, identical bounds, single band,
    float32, values in [0, 1]; content outside the survey may be null or nan.  This writer
    never emits a nodata *tag* and never emits a value outside [0, 1] -- the two measured
    causes of the portal's "Predicted values must be in range [0, 1]" rejection -- so a
    download from this repository cannot fail for either reason.
    """
    g = g or gridmod.load_grid()
    a = np.asarray(values, dtype=np.float32)
    if a.shape != g.shape:
        raise ValueError(f"shape {a.shape} != grid {g.shape}")
    a = np.where(np.isfinite(a), a, outside_value)
    a = np.clip(a, 0.0, 1.0).astype(np.float32)
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with rasterio.open(path, "w", driver="GTiff", height=g.height, width=g.width,
                       count=1, dtype="float32", crs=g.crs, nodata=None,
                       transform=Affine(*g.transform), compress="deflate",
                       tiled=True, blockxsize=256, blockysize=256) as dst:
        dst.write(a, 1)
        dst.update_tags(AREA_OR_POINT="Area")
    return audit_submission(path)


def audit_submission(path: str | Path) -> dict:
    """Independent re-read of the written bytes: the format receipt shipped with the file."""
    import hashlib

    path = Path(path)
    with rasterio.open(path) as src:
        a = src.read(1)
        info = {
            "path": path.name,
            "bytes": path.stat().st_size,
            "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
            "driver": src.driver,
            "count": src.count,
            "dtype": src.dtypes[0],
            "crs": src.crs.to_string(),
            "width": src.width,
            "height": src.height,
            "transform": [float(v) for v in tuple(src.transform)[:6]],
            "nodata_tag": None if src.nodata is None else float(src.nodata),
            "res": [float(r) for r in src.res],
        }
    finite = np.isfinite(a)
    vals = a[finite]
    info.update({
        "cells_total": int(a.size),
        "cells_finite": int(finite.sum()),
        "cells_nan": int((~finite).sum()),
        "min": float(vals.min()) if vals.size else None,
        "max": float(vals.max()) if vals.size else None,
        "nonzero": int((vals > 0).sum()),
        "outside_0_1": int(((vals < 0) | (vals > 1)).sum()),
        "all_finite": bool(finite.all()),
        "values_in_unit_interval": bool(vals.size and (vals >= 0).all() and (vals <= 1).all()),
        "single_band": bool(src.count == 1) if False else True,
    })
    info["single_band"] = info["count"] == 1
    info["legal"] = bool(
        info["count"] == 1 and info["dtype"] == "float32" and info["crs"] == "EPSG:32611"
        and info["values_in_unit_interval"] and info["all_finite"]
    )
    return info
