"""Spatially blocked validation.

Two frames are used, and their limits are stated everywhere results are reported:

``catalogue``  — spatial folds of the published USGS/INGENIOUS catalogue.  The
    fold's catalogue pixels are the stand-in truth; every catalogue pixel outside
    the fold is masked out of the scored domain, exactly as the organizers remove
    the known inventory from the competition's scored domain.  This frame answers
    "does the prior find faults of the same system?"  It cannot answer "does it
    find faults the catalogue lacks?".

``sgmc`` — the same construction on an *independent* inventory (USGS State
    Geologic Map Compilation faults, `derived_sgmc_faults_100m_u8.tif`), which is
    largely non-Quaternary and therefore contains structures the Quaternary
    catalogue does not.  Truth = SGMC pixels that are **further than 1 km from the
    competition catalogue**, so this frame measures off-catalogue prediction.

Both frames are proxies.  The only official numbers are the leaderboard's.
"""

from __future__ import annotations

import numpy as np

from . import metric


def folds(shape, n_rows: int = 2, n_cols: int = 2, footprint: np.ndarray | None = None):
    """Spatial folds as a label raster (0..n-1, -1 outside)."""
    lab = np.full(shape, -1, dtype=np.int16)
    r_edges = np.linspace(0, shape[0], n_rows + 1).astype(int)
    c_edges = np.linspace(0, shape[1], n_cols + 1).astype(int)
    k = 0
    for i in range(n_rows):
        for j in range(n_cols):
            lab[r_edges[i]:r_edges[i + 1], c_edges[j]:c_edges[j + 1]] = k
            k += 1
    if footprint is not None:
        lab[~footprint] = -1
    return lab


def emit_dots_along(mask: np.ndarray, spacing_px: float = 2.83,
                    weight: np.ndarray | None = None, max_dots: int = 200_000) -> np.ndarray:
    """Place isolated unit dots on a metric-aligned spacing inside `mask`.

    Greedy: repeatedly take the highest-weight remaining pixel and delete every
    pixel within `spacing_px` of it.  This is the "dotted" family that owns the
    project's best recorded scores, with the spacing taken from the measured
    nearest-neighbour distribution of the 0.2600 artifact (median 3.0 px,
    p10 2.83 px).
    """
    from scipy.spatial import cKDTree

    idx = np.argwhere(mask)
    if idx.size == 0:
        return np.zeros_like(mask, dtype=bool)
    w = (np.ones(idx.shape[0]) if weight is None
         else np.asarray(weight)[mask].astype(np.float64))
    order = np.argsort(-w)
    idx = idx[order]
    tree = cKDTree(idx)
    taken = np.zeros(idx.shape[0], dtype=bool)
    deleted = np.zeros(idx.shape[0], dtype=bool)
    out = []
    for i in range(idx.shape[0]):
        if deleted[i]:
            continue
        taken[i] = True
        out.append(i)
        if len(out) >= max_dots:
            break
        for j in tree.query_ball_point(idx[i], r=spacing_px):
            deleted[j] = True
    res = np.zeros_like(mask, dtype=bool)
    res[idx[taken].T[0], idx[taken].T[1]] = True
    return res


def scored_truth_frame(cat: np.ndarray, fold_labels: np.ndarray, hold_fold: int,
                       min_distance_px: float = 10.0):
    """Truth = catalogue inside the held-out fold; domain = everything but the rest.

    `min_distance_px` removes truth pixels that are closer than this to a *known*
    catalogue pixel outside the fold — without it, the metric is dominated by
    boundary leakage across the seam of the block.
    """
    from scipy.ndimage import distance_transform_edt

    known = cat & (fold_labels != hold_fold)
    truth = cat & (fold_labels == hold_fold)
    if min_distance_px > 0:
        d = distance_transform_edt(~known)
        truth = truth & (d >= min_distance_px)
    domain = np.isfinite(fold_labels.astype(float)) & ~known
    return truth, domain


def evaluate(pred_mask: np.ndarray, truth: np.ndarray, domain: np.ndarray) -> dict:
    """Official DTI of a binary dot mask against a frame's truth/domain."""
    pred = np.where(pred_mask, 1.0, 0.0)
    pred[~domain] = np.nan
    r = metric.score(pred, truth, domain=domain)
    return {k: r[k] for k in ("tp_w", "fp_w", "fn_w", "g", "dti", "n_pred")}
