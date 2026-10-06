"""The official competition metric, implemented literally from the problem statement.

Source (read 2026-10-06, quoted verbatim in docs/research/metric.md):
  https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/

Official definitions
--------------------
    k(d)   = max(1 - d/R, 0),   R = 300 m  (3 pixels at 100 m)

    TP_w   = sum_{g in G}  max_{x : d(x,g) <= R}  p(x) k(d(x,g))
    FP_w   = sum_{x : p(x) > 0}  p(x) [ 1 - max_{g in G} k(d(x,g)) ]
    FN_w   = sum_{g in G}  [ 1 - max_{x : d(x,g) <= R} p(x) k(d(x,g)) ]
    DTI    = TP_w / (TP_w + alpha FP_w + beta FN_w + eps),  alpha = 0.2, beta = 0.8

Two exact consequences used by the emitter (identities of the official formulas,
not approximations):

1.  TP_w + FN_w = |G|, because the same `max` appears in both sums.  Hence
        DTI = T / (0.8 G + 0.2 T + 0.2 F)          (alpha = 0.2, beta = 0.8)
    the "one-line form" of the metric.
2.  A dot that is the unique maximiser for one truth pixel changes the denominator
    by exactly alpha * (k + (1 - k)) = alpha = 0.2, giving the marginal-inclusion
    rule  k_marginal > alpha * s  (docs/research/metric.md).
"""

from __future__ import annotations

import numpy as np

ALPHA = 0.2
BETA = 0.8
RADIUS_M = 300.0
PIXEL_M = 100.0
RADIUS_PX = RADIUS_M / PIXEL_M  # 3.0
EPS = np.finfo(np.float64).eps


def kernel(d_px) -> np.ndarray:
    """Triangular kernel of the official metric, evaluated in pixel units."""
    return np.maximum(1.0 - np.asarray(d_px, dtype=np.float64) / RADIUS_PX, 0.0)


def tversky_index(tp_w: float, fp_w: float, fn_w: float,
                  alpha: float = ALPHA, beta: float = BETA) -> float:
    """DTI from the three weighted counts, exactly as published."""
    return tp_w / (tp_w + alpha * fp_w + beta * fn_w + EPS)


def score(pred: np.ndarray, truth: np.ndarray, domain: np.ndarray | None = None,
          max_truth: int = 200_000, rng: np.random.Generator | None = None) -> dict:
    """Distance-weighted Tversky index between a prediction raster and a truth mask.

    Parameters
    ----------
    pred : 2-D float array.  NaN outside the submission footprint is fine; NaNs are
        simply not predicted.  Values > 0 are predictions, weighted by their value.
    truth : 2-D bool/0-1 array of ground-truth pixels (already masked to the scored
        inventory: pass `truth = truth_all & ~known_catalogue`).
    domain : optional bool array.  Pixels outside it cannot contribute false
        positives (the organizers' rule that the known catalogue is removed from
        the scored domain).  Predictions outside `domain` are dropped.
    max_truth : Monte-Carlo cap on the number of truth pixels used (unbiased).

    Returns
    -------
    dict with tp_w, fp_w, fn_w, g, dti, the identity cross-check and counts.
    """
    from scipy.spatial import cKDTree

    pred = np.asarray(pred, dtype=np.float64)
    truth = np.asarray(truth).astype(bool)
    if domain is not None:
        truth = truth & np.asarray(domain, dtype=bool)

    pos = np.isfinite(pred) & (pred > 0)
    if domain is not None:
        pos &= np.asarray(domain, dtype=bool)

    t_idx = np.argwhere(truth)
    p_idx = np.argwhere(pos)
    g_total = float(truth.sum())
    if p_idx.size == 0:
        return dict(tp_w=0.0, fp_w=0.0, fn_w=g_total, g=g_total, dti=0.0,
                    dti_identity=0.0, n_truth=t_idx.shape[0], n_pred=0,
                    truth_subsampled=False)
    if t_idx.size == 0:
        return dict(tp_w=0.0, fp_w=float(pred[pos].sum()), fn_w=0.0, g=0.0, dti=0.0,
                    dti_identity=0.0, n_truth=0, n_pred=p_idx.shape[0],
                    truth_subsampled=False)

    rng = rng or np.random.default_rng(0)
    sampled = False
    if t_idx.shape[0] > max_truth:
        sel = rng.choice(t_idx.shape[0], max_truth, replace=False)
        t_idx = t_idx[np.sort(sel)]
        sampled = True
    scale = g_total / t_idx.shape[0]

    t_tree = cKDTree(t_idx)
    p_tree = cKDTree(p_idx)

    # --- TP_w = sum_g max_x p(x) k(d(x,g)) -------------------------------------
    # The published definition takes, for EACH ground-truth pixel g, the maximum over
    # ALL prediction pixels x within the kernel:
    #     TP_w = sum_g max_x p(x) k(d(x,g)).
    # A previous version of this function queried pred->nearest-truth instead, which
    # silently assigns each prediction to a single truth pixel and under-counts TP_w
    # (measured: 0.895 vs 0.941 exact on a 12-dot case; larger errors when truth pixels
    # are clustered, i.e. always on real data).  See tests/test_cross_metric.py.
    p_vals = pred[tuple(p_idx.T)]
    d_p2t, _ = t_tree.query(p_idx, k=1)          # needed for FP_w below
    cred = np.zeros(t_idx.shape[0], dtype=np.float64)
    for j, neighbours in enumerate(p_tree.query_ball_point(t_idx, r=RADIUS_PX + 1e-9)):
        if not neighbours:
            continue
        d = np.hypot(*(p_idx[neighbours] - t_idx[j]).T)
        w = p_vals[neighbours] * kernel(d)
        cred[j] = float(w.max())
    tp_w = float(cred.sum() * scale)

    # --- FN_w = the complement of the same max ---------------------------------
    fn_w = float((1.0 - cred).sum() * scale)

    # --- FP_w = sum_{p>0} p (1 - max_g k(d)) -----------------------------------
    near = kernel(d_p2t)
    fp_w = float((p_vals * (1.0 - near)).sum())

    dti = tversky_index(tp_w, fp_w, fn_w)
    dti_identity = tp_w / (BETA * g_total + (1.0 - BETA) * tp_w + ALPHA * fp_w + EPS)
    return dict(tp_w=tp_w, fp_w=fp_w, fn_w=fn_w, g=g_total, dti=dti,
                dti_identity=dti_identity, n_truth=int(truth.sum()),
                n_pred=int(p_idx.shape[0]), truth_subsampled=sampled,
                tp_plus_fn_minus_g=float(tp_w + fn_w - g_total))


def marginal_threshold(current_score: float, alpha: float = ALPHA) -> float:
    """Credit a new dot must earn to improve a file currently scoring s.

    Exact: a dot that is the unique maximiser for one truth pixel raises the
    denominator by exactly alpha, so it pays iff k > alpha * s.
    """
    return alpha * current_score


def max_distance_for_credit(credit: float) -> float:
    """Distance (metres) at which a dot still earns `credit`."""
    return RADIUS_M * (1.0 - credit)


def coverage_required(target: float, rho: float, alpha: float = ALPHA,
                      beta: float = BETA) -> float:
    """Invert DTI = s for weighted coverage x = T/G at false-positive ratio rho = F/G."""
    return target * (alpha * rho + beta) / (1.0 - alpha * target)
