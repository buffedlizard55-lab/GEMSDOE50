"""The official metric written as a decision objective over a probabilistic truth set.

Official definition (https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/,
retrieved 2026-10-07, verified verbatim against this module's ``dti_exact``):

    k(d)          = max(1 - d/R, 0),  R = 300 m
    TP_w          = sum_{g in G} max_{x: d(x,g)<=R} p(x) k(d(x,g))
    FP_w          = sum_{x: p(x)>0} p(x) [1 - max_{g in G} k(d(x,g))]
    FN_w          = sum_{g in G} [1 - max_{x: d(x,g)<=R} p(x) k(d(x,g))]
    DTI           = TP_w / (TP_w + 0.2 FP_w + 0.8 FN_w + eps)

Two structural facts drive everything in this repository and both follow from the equations
above without approximation:

1. ``FN_w = |G| - TP_w``, so ``DTI = TP_w / (0.2 (TP_w + FP_w) + 0.8 |G|)``: the truth size
   ``|G|`` enters the denominator as an additive constant that no submission can change, and
   only ``0.2 TP_w + 0.2 FP_w`` is ours to move.
2. Every predicted pixel is *bounded* by 1 in its contribution to ``TP_w`` (the maximum over
   ``x`` is taken per truth pixel), while ``FP_w`` is linear in ``p(x)``.  Therefore, for a
   fixed support, ``p(x) = 1`` dominates every ``p(x) < 1``: the optimal submission is binary
   on its support.  This is verified numerically in ``tests/test_h53_truthmodel.py``.

Because the support is what we choose, we can work with an expected truth: a weight field
``w(x) >= 0`` with ``sum(w) = |G|``.  ``TP_w`` is then exact under linearity of expectation (the
inner maximum is over *our own* deterministic support), while ``FP_w`` needs
``E[max_g k]``; that expectation is computed with a Poisson (independent-cell) closure over the
nested disc sums of ``w``, which is exact in the limit of small weights and conservative
otherwise.  ``dti_exact`` re-scores any candidate against a *drawn binary* truth with the
independent reference implementation, so the approximation is measured, not assumed.
"""
from __future__ import annotations

from dataclasses import dataclass, field as dc_field
from typing import Any

import numpy as np
from scipy import ndimage

PIXEL_M = 100.0
RADIUS_M = 300.0
ALPHA = 0.2
BETA = 0.8
EPS = 1e-9

# Distinct kernel levels for integer pixel offsets inside the 3 px support, sorted by descending
# weight: d = 0, 1, sqrt2, 2, sqrt5, sqrt8 (3.0 gives k = 0 and is excluded).
_LEVELS: tuple[tuple[float, float], ...] = (
    (0.0, 1.0),
    (1.0, 1.0 - 1.0 / 3.0),
    (np.sqrt(2.0), 1.0 - np.sqrt(2.0) / 3.0),
    (2.0, 1.0 - 2.0 / 3.0),
    (np.sqrt(5.0), 1.0 - np.sqrt(5.0) / 3.0),
    (np.sqrt(8.0), 1.0 - np.sqrt(8.0) / 3.0),
)


def disc_footprint(radius_px: float) -> np.ndarray:
    r = int(np.floor(radius_px + 1e-9))
    yy, xx = np.ogrid[-r:r + 1, -r:r + 1]
    return (yy * yy + xx * xx) <= radius_px * radius_px + 1e-9


def kernel_weights(radius_px: float = RADIUS_M / PIXEL_M) -> np.ndarray:
    r = int(np.ceil(radius_px))
    yy, xx = np.meshgrid(np.arange(-r, r + 1), np.arange(-r, r + 1), indexing="ij")
    d = np.hypot(yy, xx)
    return np.maximum(1.0 - d / radius_px, 0.0).astype(np.float32)


def support_coverage(support: np.ndarray) -> np.ndarray:
    """``b[g] = max_{x in support} k(d(x, g))`` for a binary support (layer-cake form).

    ``max_x k(d) = sum_j (k_j - k_{j+1}) * 1[exists a dot within radius_j]``.  Each indicator is
    one binary dilation with a disc footprint, so this is exact and costs six filters.
    """
    s = np.asarray(support, dtype=np.float32)
    out = np.zeros(s.shape, dtype=np.float32)
    weights = np.array([k for _, k in _LEVELS], dtype=np.float64)
    radii = np.array([d for d, _ in _LEVELS], dtype=np.float64)
    for j in range(len(weights)):
        nxt = float(weights[j + 1]) if j + 1 < len(weights) else 0.0
        reach = ndimage.binary_dilation(s > 0, structure=disc_footprint(radii[j])).astype(np.float32)
        out += (float(weights[j]) - nxt) * reach
    return out.astype(np.float32)


def disc_sums(w: np.ndarray) -> list[np.ndarray]:
    """Nested disc sums ``S_j(x) = sum_{g: d(x,g) <= radius_j} w[g]`` (one per kernel level)."""
    return [ndimage.correlate(w, disc_footprint(r), mode="constant", cval=0.0)
            for r, _ in _LEVELS]


def probability_from_prior(prior: np.ndarray, n_truth: float) -> tuple[np.ndarray, dict]:
    """Turn an unnormalised preference field into per-cell probabilities with ``sum(q) = N``.

    ``q = min(1, lambda * prior)`` with ``lambda`` found by bisection.  The cap at 1 is what makes
    the closure below exact for independent Bernoulli cells; a pure Poisson rescaling
    ``q = N * prior / sum(prior)`` would overstate coverage wherever the prior concentrates.
    """
    pr = np.clip(np.asarray(prior, dtype=np.float64), 0.0, None)
    total = float(pr.sum())
    if total <= 0 or n_truth <= 0:
        raise ValueError("prior field and n_truth must be positive")
    lo, hi = 0.0, max(1e-12, 4.0 * n_truth / max(float(pr.max()), 1e-12))
    def mass(lam: float) -> float:
        return float(np.minimum(1.0, lam * pr).sum())
    for _ in range(80):
        mid = 0.5 * (lo + hi)
        if mass(mid) < n_truth:
            lo = mid
        else:
            hi = mid
    lam = 0.5 * (lo + hi)
    q = np.minimum(1.0, lam * pr).astype(np.float32)
    return q, {"lambda": lam, "target_n": float(n_truth), "achieved_n": float(q.sum()),
               "saturated_cells": int((q >= 0.999).sum())}


def expected_max_kernel(q: np.ndarray) -> np.ndarray:
    """``E[ max_{g in G} k(d(x, g)) ]`` for independent Bernoulli truth cells with probability ``q``.

    Layer-cake over the kernel levels, with the "no truth cell inside disc_j" probability written
    as ``exp(sum_{disc_j} log(1 - q))`` - exact under independence, unlike a Poisson closure.
    """
    weights = np.array([k for _, k in _LEVELS], dtype=np.float64)
    # clip in float64: 1 - 1e-12 is *exactly* 1.0 in float32, which would send log1p to -inf and
    # print a divide-by-zero warning for a perfectly ordinary saturated cell
    logq = np.log1p(-np.clip(np.asarray(q, dtype=np.float64), 0.0, 1.0 - 1e-9)).astype(np.float32)
    out = np.zeros(q.shape, dtype=np.float64)
    for j, (r, _) in enumerate(_LEVELS):
        none = np.exp(ndimage.correlate(logq, disc_footprint(r), mode="constant", cval=0.0))
        nxt = weights[j + 1] if j + 1 < len(weights) else 0.0
        out += (weights[j] - nxt) * (1.0 - none)
    return out.astype(np.float32)


def credit_field(w: np.ndarray) -> np.ndarray:
    """``c[x] = sum_g w[g] k(d(x, g))`` - the *unconstrained* expected credit of a dot at ``x``."""
    return ndimage.correlate(w, kernel_weights(), mode="constant", cval=0.0).astype(np.float32)


def dti_weighted(support: np.ndarray, w: np.ndarray,
                 *, coverage: np.ndarray | None = None,
                 discount: np.ndarray | None = None) -> dict[str, Any]:
    """Expected official DTI of a binary support against the probabilistic truth ``w``.

    ``coverage``/``discount`` may be supplied by a caller that has already computed them (both are
    the expensive parts); they are pure functions of ``support`` and ``w`` respectively.
    """
    support = np.asarray(support, dtype=bool)
    w = np.asarray(w, dtype=np.float32)
    n = float(w.sum())
    if n <= 0:
        raise ValueError("truth weight field is empty")
    cov = support_coverage(support) if coverage is None else coverage
    disc = expected_max_kernel(w) if discount is None else discount
    tp = float(np.sum(w * cov))
    mass = int(support.sum())
    fp = float(mass - np.minimum(disc[support], 1.0).sum()) if mass else 0.0
    score = tp / (ALPHA * (tp + fp) + BETA * n + EPS)
    return {"dti": score, "tp": tp, "fp": fp, "n_truth": n, "mass": mass,
            "break_even_k": ALPHA * tp / (ALPHA * fp + BETA * n)}


def dti_exact(truth: np.ndarray, prediction: np.ndarray, *, pixel_size_m: float = PIXEL_M,
              radius_m: float = RADIUS_M) -> dict[str, float]:
    """Independent reference: the official metric on a *binary* truth raster.

    Deliberately re-derived here (not imported) so that a mistake in one implementation cannot
    validate the other; ``tests/test_h53_truthmodel.py`` compares both against the repository's
    long-tested ``gemsdoe50.metric`` implementation and the competition's published worked
    example (TP=3.00, FP=1.89, FN=2.00 -> 0.60).
    """
    truth = np.asarray(truth, dtype=bool)
    prediction = np.clip(np.asarray(prediction, dtype=np.float64), 0.0, 1.0)
    gy, gx = np.nonzero(truth)
    if gx.size == 0:
        raise ValueError("empty truth")
    kern = kernel_weights(radius_m / pixel_size_m)
    r = kern.shape[0] // 2
    padded = np.pad(prediction, r)
    off = [(dy, dx) for dy in range(-r, r + 1) for dx in range(-r, r + 1)
           if kern[dy + r, dx + r] > 0]
    # per-truth-pixel maximum of p(x) * k(d): scan the kernel support once per offset
    best = np.zeros(gx.size, dtype=np.float64)
    for dy, dx in off:
        np.maximum(best, padded[gy + r + dy, gx + r + dx] * float(kern[dy + r, dx + r]), out=best)
    tp = float(best.sum())
    fn = float(gx.size - tp)
    # per-predicted-pixel discount: 1 - max over truth cells of k(d), evaluated on the full grid
    full = np.zeros(truth.shape, dtype=np.float64)
    for dy, dx in off:
        k = float(kern[dy + r, dx + r])
        shifted = np.zeros_like(truth, dtype=np.float64)
        src = truth
        # shifted[y, x] = k * truth[y - dy, x - dx] with no wrap-around
        ys0, ys1 = max(0, dy), min(truth.shape[0], truth.shape[0] + dy)
        xs0, xs1 = max(0, dx), min(truth.shape[1], truth.shape[1] + dx)
        shifted[ys0:ys1, xs0:xs1] = truth[ys0 - dy:ys1 - dy, xs0 - dx:xs1 - dx]
        full[shifted > 0] = np.maximum(full[shifted > 0], k)
    pos = prediction > 0
    fp = float(np.sum(prediction[pos] * (1.0 - full[pos])))
    score = tp / (tp + ALPHA * fp + BETA * fn + EPS)
    return {"dti": float(score), "tp": tp, "fp": fp, "fn": fn, "n_truth": float(gx.size),
            "mass": float(np.count_nonzero(pos))}


@dataclass
class TruthModel:
    """A generative description of the *hidden* label set: ``w = N * (1-u) * prior + u/N_u``.

    ``prior`` is ``belief ** gamma`` restricted to the emission domain (footprint, outside the
    catalogue buffer of ``buffer_px`` pixels).  ``u`` is a uniform floor over that same domain:
    the fraction of the hidden truth the field is *not* told about.  All four numbers are fitted
    to the group's own scored submissions in ``scripts/h53_calibrate.py``; none is hand-picked.
    """
    n_truth: float = 12226.0
    gamma: float = 1.0
    buffer_px: float = 0.0
    uniform_floor: float = 0.0

    def weights(self, belief: np.ndarray, domain: np.ndarray) -> tuple[np.ndarray, dict]:
        """Probability field ``q`` supported on ``domain`` with ``sum(q) = n_truth``."""
        b = np.clip(np.asarray(belief, dtype=np.float64), 0.0, 1.0)
        dom = np.asarray(domain, dtype=bool)
        u = float(np.clip(self.uniform_floor, 0.0, 0.95))
        prior = np.where(dom, b ** self.gamma, 0.0)
        if float(prior.sum()) <= 0:
            prior = dom.astype(np.float64)
        peak = float(prior.max()) or 1.0
        prior = prior / peak
        if u > 0 and dom.any():                      # mix in a uniform floor over the domain
            prior = (1.0 - u) * prior + u * dom.astype(np.float64) / max(float(dom.sum()), 1.0) * peak
        q, info = probability_from_prior(prior, self.n_truth)
        return q.astype(np.float32), info

    def as_dict(self) -> dict[str, float]:
        return {"n_truth": self.n_truth, "gamma": self.gamma, "buffer_px": self.buffer_px,
                "uniform_floor": self.uniform_floor}


def marginal_gain(tp: float, fp: float, n: float) -> float:
    """Break-even per-dot kernel credit ``0.2 TP / (0.2 FP + 0.8 N)`` at the current operating point."""
    return ALPHA * tp / (ALPHA * fp + BETA * n + EPS)


@dataclass
class Calibration:
    params: dict[str, float]
    rmse: float
    per_file: list[dict[str, Any]] = dc_field(default_factory=list)

    def as_dict(self) -> dict[str, Any]:
        return {"params": self.params, "rmse": self.rmse, "per_file": self.per_file}
