"""H51 — off-catalogue lineament corridors and metric-optimal dot emission.

Design summary (see ``docs/hypotheses-preregistered.md`` and ``docs/research/``):

* The scored truth of this competition is the set of *new* expert-mapped faults; pixels
  belonging to the published USGS/INGENIOUS catalogue are **masked out of every term** of
  the distance-weighted Tversky index (DrivenData staff, community thread 11516).
* With ``k(d) = max(1 - d/300 m, 0)``, ``DTI = T / (0.2*(T + F) + 0.8*G)`` where
  ``T = TP_w``, ``F = FP_w`` and ``G`` is the scored truth mass. A unit prediction whose
  best kernel credit is ``k`` raises ``T`` by ``k`` and the denominator by exactly ``0.2``,
  so it pays iff ``k > 0.2*s/(1 - 0.2*s)`` -- i.e. it must land within ~280 m of truth.
* Therefore the emission must be *binary*, *sparse*, *off-catalogue*, and concentrated
  where the belief field is high. Everything here is deterministic and seed-free.

Functions are written to be importable and unit-testable without the competition rasters.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass

import numpy as np
from scipy.ndimage import (
    distance_transform_edt,
    gaussian_filter,
    maximum_filter,
    median_filter,
    sobel,
)

RADIUS_M = 300.0
ALPHA = 0.2
BETA = 0.8
PIXEL_M = 100.0

# --- grid constants of the competition raster (verified from sample_submission.tif) -----
GRID_SHAPE = (3730, 3292)
GRID_TRANSFORM = (100.0, 0.0, 243350.0, 0.0, -100.0, 4508550.0)
GRID_CRS = "EPSG:32611"


# --------------------------------------------------------------------------------------
# raster helpers
# --------------------------------------------------------------------------------------
def utm_to_rowcol(x: np.ndarray, y: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Convert EPSG:32611 easting/northing to (row, col) floats of the competition grid."""
    col = (np.asarray(x, float) - GRID_TRANSFORM[2]) / GRID_TRANSFORM[0]
    row = (np.asarray(y, float) - GRID_TRANSFORM[5]) / GRID_TRANSFORM[4]
    return row, col


def rowcol_to_utm(row: np.ndarray, col: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    a, b, c, d, e, f = GRID_TRANSFORM
    x = c + a * np.asarray(col, float) + b * np.asarray(row, float)
    y = f + d * np.asarray(col, float) + e * np.asarray(row, float)
    return x, y


def distance_to_mask(mask: np.ndarray) -> np.ndarray:
    """Euclidean distance (in pixels) from every cell to the nearest True cell of ``mask``."""
    return distance_transform_edt(~np.asarray(mask, bool))


def credit_field(dots: np.ndarray) -> np.ndarray:
    """``C(g) = max over dots x of k(d(x, g))`` — the credit a truth pixel at ``g`` earns.

    The metric's triangular kernel is radially decreasing, so the maximum equals the kernel
    of the distance to the nearest dot.
    """
    dots = np.asarray(dots, bool)
    if not dots.any():
        return np.zeros(dots.shape, np.float32)
    d = distance_transform_edt(~dots)
    return np.maximum(0.0, 1.0 - (d * PIXEL_M) / RADIUS_M).astype(np.float32)


def support_field(dots: np.ndarray) -> np.ndarray:
    """``S(g) = sum over dots x of k(d(x, g))`` — matched prediction mass at a truth pixel.

    Computed as a convolution with the 7x7 triangular kernel (support = 300 m = 3 px).
    """
    from scipy.ndimage import convolve

    r = int(np.ceil(RADIUS_M / PIXEL_M))
    yy, xx = np.mgrid[-r:r + 1, -r:r + 1]
    ker = np.maximum(0.0, 1.0 - (np.hypot(yy, xx) * PIXEL_M) / RADIUS_M).astype(np.float32)
    return convolve(np.asarray(dots, np.float32), ker, mode="constant", cval=0.0)


def normalize01(x: np.ndarray, mask: np.ndarray | None = None, clip_q: float = 0.999) -> np.ndarray:
    """Robustly rescale to [0, 1] using the 0/``clip_q`` quantiles of the masked values."""
    x = np.asarray(x, float)
    v = x[mask] if mask is not None else x.ravel()
    v = v[np.isfinite(v)]
    if v.size == 0:
        return np.zeros_like(x)
    lo = float(np.min(v))
    hi = float(np.quantile(v, clip_q))
    if hi <= lo:
        return np.zeros_like(x)
    return np.clip((x - lo) / (hi - lo), 0.0, 1.0)


# --------------------------------------------------------------------------------------
# layer 1: geophysical gradient lineaments (magnetic / radiometric)
# --------------------------------------------------------------------------------------
def gradient_lineament_response(
    band: np.ndarray,
    valid: np.ndarray,
    sigmas: Iterable[float] = (1.5, 3.0),
    ridge_window: int = 9,
) -> np.ndarray:
    """Thin, coherent lineament response of a geophysical band.

    A fault that offsets or juxtaposes magnetised / radiometrically distinct rock produces a
    *linear* gradient in the band. Two ingredients separate such lineaments from broad
    gradients:

    1. multi-scale corroboration -- the geometric mean of the gradient magnitudes at two
       smoothing scales suppresses single-scale noise and broad regional gradients;
    2. ridge enhancement -- subtraction of a moving median, which keeps thin ridges and
       removes the broad component of a gradient zone.

    Returns a non-negative float array, 0 where the band is invalid.
    """
    band = np.asarray(band, float)
    valid = np.asarray(valid, bool)
    filled = np.where(valid, band, 0.0)
    responses = []
    for s in sigmas:
        sm = gaussian_filter(filled, s)
        gx = sobel(sm, axis=0, mode="nearest")
        gy = sobel(sm, axis=1, mode="nearest")
        responses.append(np.hypot(gx, gy))
    # geometric mean: a lineament must be visible at both scales
    gm = np.exp(np.mean([np.log(r + 1e-6) for r in responses], axis=0))
    ridge = gm - median_filter(gm, size=ridge_window)
    ridge = np.maximum(ridge, 0.0)
    ridge[~valid] = 0.0
    return ridge


def _selfmasked_ridge(x: np.ndarray, window: int = 25) -> np.ndarray:
    """Keep only local maxima ridges of ``x`` (1 where x equals the local max)."""
    m = maximum_filter(x, size=window)
    return np.where(x >= m, x, 0.0)


# --------------------------------------------------------------------------------------
# layer 2: seismicity lineament corridors (2-D adaptation of the Ouillon-type method)
# --------------------------------------------------------------------------------------
@dataclass(frozen=True)
class CorridorParams:
    neighbour_radius_m: float = 5000.0
    min_events: int = 8
    min_linearity: float = 0.80          # lambda1/sum(lambda) of the 2-D covariance
    min_length_m: float = 2000.0         # 5th-95th percentile extent along the axis
    min_depth_km: float = 0.0
    max_depth_km: float = 20.0
    min_magnitude: float = 1.0
    width_floor_m: float = 300.0         # never narrower than the metric's kernel
    time_window_years: float = 1.0       # one observation per event cell per window
    seed_cell_m: float = 1000.0


def decluster_catalog(
    time_years: np.ndarray,
    mag: np.ndarray,
    row: np.ndarray,
    col: np.ndarray,
    cell_m: float = 250.0,
    window_years: float = 1.0,
) -> np.ndarray:
    """Keep at most one event per (250 m cell, 1-year window); the largest magnitude wins.

    This is the point-pattern de-duplication used to stop a single aftershock sequence from
    dominating a neighbourhood (the preregistered H50-S1 rule, 2-D adaptation).
    """
    cell = round(cell_m / PIXEL_M)
    key_cell = (row // cell).astype(np.int64) * 100000 + (col // cell).astype(np.int64)
    key_win = (time_years / window_years).astype(np.int64)
    key = key_cell * 1000 + key_win
    order = np.lexsort((-mag, key))
    _, first = np.unique(key[order], return_index=True)
    keep = order[np.sort(first)]
    return keep


def seismicity_corridors(
    row: np.ndarray,
    col: np.ndarray,
    depth_km: np.ndarray,
    mag: np.ndarray,
    width_m: np.ndarray | None = None,
    params: CorridorParams | None = None,
    shape: tuple[int, int] = GRID_SHAPE,
) -> tuple[np.ndarray, dict]:
    """Accumulate straight corridor evidence from linear, well-sampled epicentre neighbourhoods.

    For every seed event the local neighbourhood is fitted with a 2-D PCA. A neighbourhood is
    accepted when it is *linear*, *long* and *well sampled*; the accepted corridor is painted
    with the metric's own triangular kernel across its local width (never below 300 m because
    the catalogue's own horizontal error is of that order).

    Returns ``(raster, audit)``.
    """
    from scipy.spatial import cKDTree

    params = params or CorridorParams()
    n = len(row)
    if n == 0:
        return np.zeros(shape, np.float32), {"n_events": 0, "n_seeds": 0, "n_corridors": 0}
    pts = np.column_stack([row * PIXEL_M, col * PIXEL_M])
    tree = cKDTree(pts)
    seed_cell = max(1, round(params.seed_cell_m / PIXEL_M))
    seed_keys = np.unique((row // seed_cell).astype(np.int64) * 100000 + (col // seed_cell).astype(np.int64))
    seed_rows = (seed_keys // 100000) * seed_cell + seed_cell // 2
    seed_cols = (seed_keys % 100000) * seed_cell + seed_cell // 2

    out = np.zeros(shape, np.float32)
    n_corridors = 0
    n_seeds_with_events = 0
    half = RADIUS_M / PIXEL_M  # kernel support in px
    half_i = int(np.ceil(half))
    yy, xx = np.mgrid[-half_i:half_i + 1, -half_i:half_i + 1]
    kd = np.sqrt(yy * yy + xx * xx) * PIXEL_M
    ker = np.maximum(0.0, 1.0 - kd / RADIUS_M)
    for sr, sc in zip(seed_rows, seed_cols):
        idx = tree.query_ball_point([sr * PIXEL_M + PIXEL_M / 2, sc * PIXEL_M + PIXEL_M / 2],
                                    r=params.neighbour_radius_m)
        if len(idx) < params.min_events:
            continue
        idx = np.asarray(idx)
        p = pts[idx]
        mu = p.mean(axis=0)
        q = p - mu
        cov = q.T @ q / len(idx)
        w, v = np.linalg.eigh(cov)
        l1, l2 = float(w[-1]), float(w[0])
        if l1 <= 0 or (l1 / (l1 + l2)) < params.min_linearity:
            continue
        axis = v[:, -1]
        t = q @ axis
        length = float(np.percentile(t, 95) - np.percentile(t, 5))
        if length < params.min_length_m:
            continue
        if width_m is not None:
            lidx = idx
            loc_err = float(np.median(width_m[lidx][np.isfinite(width_m[lidx])])) if np.any(
                np.isfinite(width_m[lidx])) else params.width_floor_m
        else:
            loc_err = params.width_floor_m
        width = max(params.width_floor_m, loc_err)
        n_seeds_with_events += 1
        # paint the corridor: sample points along +-length/2 of the axis, kernel-blurred
        n_samp = int(max(2, np.ceil(length / 50.0)))
        s = np.linspace(-length / 2, length / 2, n_samp)
        along = mu[None, :] + s[:, None] * axis[None, :]
        # widen perpendicular to the axis to the local width
        perp = v[:, 0]
        offs = np.array([-1.0, -0.5, 0.0, 0.5, 1.0]) * (width / 2.0)
        samples = (along[:, None, :] + offs[None, :, None] * perp[None, None, :]).reshape(-1, 2)
        rr = samples[:, 0] / PIXEL_M
        cc = samples[:, 1] / PIXEL_M
        ri = np.round(rr).astype(np.int64)
        ci = np.round(cc).astype(np.int64)
        ok = (ri >= 0) & (ri < shape[0]) & (ci >= 0) & (ci < shape[1])
        for r0, c0 in zip(ri[ok], ci[ok]):
            r1, r2 = max(0, r0 - int(np.ceil(half))), min(shape[0], r0 + int(np.ceil(half)) + 1)
            c1, c2 = max(0, c0 - int(np.ceil(half))), min(shape[1], c0 + int(np.ceil(half)) + 1)
            kr1 = int(np.ceil(half)) - (r0 - r1)
            kr2 = kr1 + (r2 - r1)
            kc1 = int(np.ceil(half)) - (c0 - c1)
            kc2 = kc1 + (c2 - c1)
            np.maximum(out[r1:r2, c1:c2], ker[kr1:kr2, kc1:kc2], out=out[r1:r2, c1:c2])
        n_corridors += 1
    return out, {"n_events": int(n), "n_seeds": len(seed_keys),
                     "n_seeds_with_events": n_seeds_with_events, "n_corridors": n_corridors}


# --------------------------------------------------------------------------------------
# layer 3: point-feature alignment (thermal springs / wells)
# --------------------------------------------------------------------------------------
def point_alignment(rows: np.ndarray, cols: np.ndarray, shape: tuple[int, int],
                    radius_px: float = 8.0) -> np.ndarray:
    """Blurred alignment field of point features (scale ~ a few pixels)."""
    m = np.zeros(shape, np.float32)
    r = np.round(np.asarray(rows, float)).astype(int)
    c = np.round(np.asarray(cols, float)).astype(int)
    ok = (r >= 0) & (r < shape[0]) & (c >= 0) & (c < shape[1])
    m[r[ok], c[ok]] = 1.0
    return gaussian_filter(m, radius_px / 2.0)


# --------------------------------------------------------------------------------------
# emission: greedy max-belief dots with suppression (metric-aware)
# --------------------------------------------------------------------------------------
@dataclass(frozen=True)
class EmissionParams:
    spacing_px: float = 2.8
    belief_floor: float = 0.02
    budget: int = 45000
    catalogue_clearance_px: int = 0
    # The greedy scan only sees the ``pool_factor * budget`` highest-belief cells, but it
    # *rejects* most of them (neighbours blocked by an accepted dot). On a sharply peaked
    # belief field the acceptance rate is ~0.11, so a small pool silently caps the accepted
    # count and collapses the dot set onto the peaks. Keep the pool generous; acceptance
    # order is prefix-stable, so changing the pool does not change any accepted prefix.
    pool_factor: int = 4


def place_dots_ordered(
    belief: np.ndarray,
    allowed: np.ndarray,
    params: EmissionParams | None = None,
) -> np.ndarray:
    """Flat indices of the greedily accepted dots, in acceptance order.

    The accepted set of any budget is a prefix of this sequence, so one call yields the
    whole score-vs-budget frontier without re-running the packer.
    """
    params = params or EmissionParams()
    b = np.asarray(belief, float)
    flat = np.where(allowed, b, -np.inf).ravel()
    ok = np.isfinite(flat) & (flat >= params.belief_floor)
    n_ok = int(ok.sum())
    if n_ok == 0:
        return np.zeros(0, np.int64)
    pf = max(int(params.pool_factor), 1)
    k = int(min(n_ok, max(pf * params.budget, params.budget + 1)))
    cand = np.argpartition(-flat, k - 1)[:k] if k < flat.size else np.flatnonzero(ok)
    cand = cand[np.isfinite(flat[cand])]
    order = np.argsort(-flat[cand], kind="stable")
    cand = cand[order]

    blocked = np.zeros(allowed.shape, bool)
    r = int(np.ceil(params.spacing_px * np.sqrt(2.0)))
    yy, xx = np.mgrid[-r:r + 1, -r:r + 1]
    disk = (yy * yy + xx * xx) <= (params.spacing_px ** 2)
    kept = []
    for idx in cand:
        if len(kept) >= params.budget:
            break
        rr, cc = divmod(int(idx), b.shape[1])
        if blocked[rr, cc]:
            continue
        kept.append(int(idx))
        r1, r2 = max(0, rr - r), min(b.shape[0], rr + r + 1)
        c1, c2 = max(0, cc - r), min(b.shape[1], cc + r + 1)
        dr1 = r - (rr - r1)
        dc1 = r - (cc - c1)
        blocked[r1:r2, c1:c2] |= disk[dr1:dr1 + (r2 - r1), dc1:dc1 + (c2 - c1)]
    return np.asarray(kept, np.int64)


def place_dots(
    belief: np.ndarray,
    allowed: np.ndarray,
    params: EmissionParams | None = None,
) -> np.ndarray:
    """Greedy belief-ordered dot placement with a hard minimum-separation suppression.

    Each accepted dot suppresses a disc of radius ``spacing_px`` around itself, so the output
    is a Poisson-disk-like packing whose density follows the belief field. This is the
    emission geometry that the metric pays for: at 100 m pixels, a ~2.8 px lattice is the
    group's measured optimum for coverage retention per unit of false-positive mass.
    """
    order = place_dots_ordered(belief, allowed, params)
    out = np.zeros(belief.shape, bool)
    if order.size:
        out.ravel()[order] = True
    return out


# --------------------------------------------------------------------------------------
# scoring (mirrors the official equations; see src/gemsdoe50/metric.py)
# --------------------------------------------------------------------------------------
def kernel_from_distance(d_px: np.ndarray) -> np.ndarray:
    return np.maximum(0.0, 1.0 - (d_px * PIXEL_M) / RADIUS_M)


def score_components(truth: np.ndarray, pred: np.ndarray, mask: np.ndarray,
                     truth_mass_hint: float | None = None) -> dict:
    """Distance-weighted Tversky components on ``mask`` (the scored domain).

    ``truth`` and ``pred`` are binary; ``mask`` marks the pixels that enter scoring (the
    competition masks out known-catalogue pixels).
    """
    truth = np.asarray(truth, bool) & mask
    pred = np.asarray(pred, bool) & mask
    tp = fp = fn = 0.0
    if not truth.any():
        return {"dti": 0.0, "tp": 0.0, "fp": float(pred.sum()), "fn": 0.0,
                "truth_cells": 0, "pred_cells": int(pred.sum())}
    d_pred = distance_transform_edt(~pred) if pred.any() else None
    d_truth = distance_transform_edt(~truth)
    if d_pred is not None:
        tp = float(kernel_from_distance(d_pred[truth]).sum())
    if pred.any():
        fp = float((1.0 - kernel_from_distance(d_truth[pred])).sum())
    fn = float(truth.sum()) - tp
    denom = tp + ALPHA * fp + BETA * fn
    dti = float(tp / denom) if denom > 0 else 0.0
    return {"dti": dti, "tp": tp, "fp": fp, "fn": fn, "truth_cells": int(truth.sum()),
            "pred_cells": int(pred.sum())}


def predicted_score(tp: float, fp: float, truth_mass: float) -> float:
    """DTI from components, using the exact identity TP_w + FN_w = G."""
    denom = tp + ALPHA * fp + BETA * (truth_mass - tp)
    return float(tp / denom) if denom > 0 else 0.0
