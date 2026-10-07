"""Coincidence field + metric-aware emitter for the GEMSDOE50 H52 submission.

Pure functions only: no I/O, no randomness. Everything here is derived from the
competition's own rasters plus the free USGS products listed in the evidence file.
No previous submission's pixels are read.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from scipy.ndimage import distance_transform_edt

ALPHA = 0.2
BETA = 0.8
KERNEL_RADIUS_M = 300.0
PIXEL_M = 100.0
def bar_from_dti(dti: float) -> float:
    """Smallest expected gain at which a fresh pixel still pays for itself."""
    return ALPHA * dti / (1.0 - ALPHA * dti)


def coincidence_score(percentiles: np.ndarray, tau: float = 0.90) -> np.ndarray:
    """Weighted corroboration count across families.

    ``percentiles`` is (n_families, H, W) of within-family percentile ranks in
    [0, 1]. A family "agrees" at a cell when its percentile reaches ``tau``. The
    score is the number of agreeing families plus half the mean normalised
    excess over the threshold, so that (a) agreement dominates strength and
    (b) within the same agreement count, stronger agreement ranks first.
    """
    p = np.asarray(percentiles, dtype=np.float32)
    if p.ndim != 3:
        raise ValueError("percentiles must be (families, rows, cols)")
    if not 0.0 < tau < 1.0:
        raise ValueError("tau must be in (0, 1)")
    p = np.clip(p, 0.0, 1.0)
    agree = p >= tau
    count = agree.sum(axis=0).astype(np.float32)
    excess = np.where(agree, (p - tau) / (1.0 - tau), 0.0)
    denom = np.maximum(count, 1.0)
    strength = excess.sum(axis=0) / denom
    return count + 0.5 * strength


def greedy_isolated_emission(
    score: np.ndarray,
    allowed: np.ndarray,
    budget: int,
    block_radius_px: int = 2,
    order_key: np.ndarray | None = None,
) -> np.ndarray:
    """Take the highest-scoring allowed cells subject to a separation rule.

    A cell is accepted only when no already-accepted cell lies within
    ``block_radius_px`` in Chebyshev distance, so accepted dots are at least
    ``block_radius_px + 1`` pixels (>= 3 px = 300 m) apart. This is the
    geometry the metric's own 300 m kernel makes optimal: two dots closer than
    that re-cover the same truth pixels and pay the false-positive tax twice.
    """
    score = np.asarray(score, dtype=np.float64)
    allowed = np.asarray(allowed, dtype=bool)
    if score.shape != allowed.shape:
        raise ValueError("score and allowed shape mismatch")
    if order_key is None:
        order_key = score
    rows, cols = score.shape
    idx = np.flatnonzero(allowed.ravel())
    if idx.size == 0 or budget <= 0:
        return np.zeros(score.shape, dtype=bool)
    flat_score = score.ravel()
    flat_key = np.asarray(order_key, dtype=np.float64).ravel()
    # descending key, then descending score, then raster order -> deterministic
    order = idx[np.lexsort((idx, -flat_score[idx], -flat_key[idx]))]
    blocked = np.zeros((rows, cols), dtype=bool)
    out = np.zeros((rows, cols), dtype=bool)
    r = block_radius_px
    taken = 0
    for flat in order:
        i, j = divmod(int(flat), cols)
        if blocked[i, j]:
            continue
        out[i, j] = True
        taken += 1
        i0, i1 = max(0, i - r), min(rows, i + r + 1)
        j0, j1 = max(0, j - r), min(cols, j + r + 1)
        blocked[i0:i1, j0:j1] = True
        if taken >= budget:
            break
    return out


@dataclass(frozen=True)
class Particle:
    rows: np.ndarray
    cols: np.ndarray


def distance_to_mask(mask: np.ndarray, points: np.ndarray) -> np.ndarray:
    """Metres from every masked cell to the nearest ``True`` cell of ``mask``."""
    return distance_transform_edt(~mask, sampling=(PIXEL_M, PIXEL_M))[points[:, 0], points[:, 1]]
