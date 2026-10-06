"""Metric-optimal sparse emission.

Why emission is a separate problem from detection
-------------------------------------------------
The official metric (docs/research/metric.md) gives, for alpha = 0.2, beta = 0.8,

    DTI = T / (0.8 G + 0.2 T + 0.2 F)

with T = TP_w, F = FP_w, G = scored truth count.  Two properties follow directly:

* a *binary* support strictly dominates any graded version of itself, and
* a dot that is the unique maximiser for one truth pixel raises the denominator by
  exactly alpha = 0.2, so it pays for itself iff its expected credit exceeds
  alpha * s   (the marginal-inclusion rule).

`emit` places isolated unit dots greedily in order of *expected marginal credit*
against a belief field pi(x) = P(pixel x is a scored truth pixel):

    dT(x) = sum_delta pi(x + delta) * max(0, k(delta) - C(x + delta))

where C is the credit the accepted dots already deliver and delta runs over the
metric's own kernel support.  It stops at the marginal condition.  The bookkeeping is
verified against an independent brute-force implementation in tests/test_emitter.py.
"""

from __future__ import annotations

import heapq

import numpy as np

from . import metric

KERNEL_RADIUS = int(np.ceil(metric.RADIUS_PX))          # 3
UPDATE_RADIUS = 2 * KERNEL_RADIUS                       # 6


def kernel_offsets(radius_px: float = metric.RADIUS_PX) -> tuple:
    """All offsets inside the triangular kernel and their weights."""
    r = int(np.ceil(radius_px))
    dr, dc = [], []
    for i in range(-r, r + 1):
        for j in range(-r, r + 1):
            d = float(np.hypot(i, j))
            if d <= radius_px:
                dr.append(i)
                dc.append(j)
    off = np.array([dr, dc]).T
    w = metric.kernel(np.hypot(off[:, 0], off[:, 1])).astype(np.float32)
    keep = w > 0
    return off[keep].astype(np.int64), w[keep].astype(np.float32)


def delta_t(pi: np.ndarray, C: np.ndarray, off: np.ndarray, w: np.ndarray,
            rows: np.ndarray, cols: np.ndarray) -> np.ndarray:
    """Expected marginal credit for the pixels (rows, cols).  Vectorised."""
    H, W = pi.shape
    rr = rows[:, None] + off[None, :, 0]
    cc = cols[:, None] + off[None, :, 1]
    ok = (rr >= 0) & (rr < H) & (cc >= 0) & (cc < W)
    rrc = np.clip(rr, 0, H - 1)
    ccc = np.clip(cc, 0, W - 1)
    pi_g = pi[rrc, ccc]
    c_g = C[rrc, ccc]
    need = np.maximum(w[None, :] - c_g, 0.0) * pi_g
    need[~ok] = 0.0
    return need.sum(axis=1)


def expected_credit(pi: np.ndarray, dots: np.ndarray) -> float:
    """Expected TP_w of a dot support: sum_x pi(x) max_dot k(d(x, dot)).

    Independent of the greedy bookkeeping — used as a cross-check.
    """
    if not dots.any():
        return 0.0
    from scipy.ndimage import maximum_filter

    C = np.zeros(pi.shape, dtype=np.float32)
    idx = np.argwhere(dots)
    for r, c in idx:
        r0, r1 = max(0, r - KERNEL_RADIUS), min(pi.shape[0], r + KERNEL_RADIUS + 1)
        c0, c1 = max(0, c - KERNEL_RADIUS), min(pi.shape[1], c + KERNEL_RADIUS + 1)
        rr = np.arange(r0, r1)
        cc = np.arange(c0, c1)
        d = np.hypot(rr[:, None] - r, cc[None, :] - c)
        C[r0:r1, c0:c1] = np.maximum(C[r0:r1, c0:c1], metric.kernel(d).astype(np.float32))
    del maximum_filter
    return float((pi * C).sum())


def emit(belief: np.ndarray, target_score: float = 0.32, domain: np.ndarray | None = None,
         max_dots: int = 120_000, min_spacing_px: float = 2.0, verbose: bool = False) -> np.ndarray:
    """Greedy expected-marginal-credit emission of an isolated-dot support.

    Parameters
    ----------
    belief : 2-D float32.  Probability that a pixel is a scored truth pixel.  The
        *scale* sets the stopping point, so it must come from the calibration in
        docs/research/emission.md, not from an arbitrary rescaling.
    target_score : the operating score used in the marginal condition
        (dot pays iff expected credit > 0.2 * target_score).
    domain : optional submission footprint.
    max_dots : hard cap (safety only; the marginal rule normally binds first).
    min_spacing_px : minimum separation between accepted dots.
    """
    pi = np.asarray(belief, dtype=np.float32).copy()
    if domain is not None:
        pi = np.where(domain, pi, 0.0)
    pi[~np.isfinite(pi)] = 0.0
    np.maximum(pi, 0.0, out=pi)
    H, W = pi.shape

    off, w = kernel_offsets()
    thr = metric.ALPHA * target_score

    # --- initial expected marginal credit: correlation of pi with the kernel ----
    from scipy.ndimage import correlate

    kern = np.zeros((2 * KERNEL_RADIUS + 1, 2 * KERNEL_RADIUS + 1), dtype=np.float32)
    for (dy, dx), k in zip(off, w):
        kern[KERNEL_RADIUS + dy, KERNEL_RADIUS + dx] = k
    DT = correlate(pi, kern, mode="constant", cval=0.0).astype(np.float32)

    # a pixel just outside the domain can still see belief inside the kernel; the
    # submission must not contain such dots, so the support is clipped to the domain.
    support = DT > thr
    if domain is not None:
        support &= domain
    if verbose:
        print(f"  emitter: {int(support.sum()):,} pixels above the marginal bar "
              f"({thr:.4f}); max DT {DT.max():.4f}")
    if not support.any():
        return np.zeros((H, W), dtype=bool)

    rows_all, cols_all = np.nonzero(support)
    heap = [(-float(DT[r, c]), int(r), int(c)) for r, c in zip(rows_all, cols_all)]
    heapq.heapify(heap)

    C = np.zeros((H, W), dtype=np.float32)
    dots = np.zeros((H, W), dtype=bool)
    # Two dots closer than min_spacing_px are nearly redundant (the metric's TP term is
    # a max over predictions) while each still costs alpha, so their neighbourhood is
    # blocked once a dot is accepted.
    blocked = np.zeros((H, W), dtype=bool)
    sp = int(np.ceil(min_spacing_px))
    sr, sc = np.meshgrid(np.arange(-sp, sp + 1), np.arange(-sp, sp + 1), indexing="ij")
    smask = (np.hypot(sr, sc) <= min_spacing_px) & ((sr != 0) | (sc != 0))
    sr = sr[smask].ravel()
    sc = sc[smask].ravel()
    accepted = 0
    local = np.arange(-UPDATE_RADIUS, UPDATE_RADIUS + 1)
    lr, lc = np.meshgrid(local, local, indexing="ij")
    lr = lr.ravel()
    lc = lc.ravel()

    while heap and accepted < max_dots:
        negv, r, c = heapq.heappop(heap)
        if dots[r, c] or blocked[r, c]:
            continue
        v = float(delta_t(pi, C, off, w, np.array([r]), np.array([c]))[0])
        if v < thr:
            continue
        dots[r, c] = True
        accepted += 1
        for dr, dc in zip(sr, sc):
            rr, cc = r + dr, c + dc
            if 0 <= rr < H and 0 <= cc < W:
                blocked[rr, cc] = True
        # deliver credit
        for (dy, dx), k in zip(off, w):
            rr, cc = r + dy, c + dx
            if 0 <= rr < H and 0 <= cc < W and C[rr, cc] < k:
                C[rr, cc] = k
        # refresh the neighbourhood
        rr = r + lr
        cc = c + lc
        ok = (rr >= 0) & (rr < H) & (cc >= 0) & (cc < W)
        rr, cc = rr[ok], cc[ok]
        vals = delta_t(pi, C, off, w, rr, cc)
        for r2, c2, v2 in zip(rr, cc, vals):
            if v2 > thr and not dots[r2, c2]:
                heapq.heappush(heap, (-float(v2), int(r2), int(c2)))
    if verbose:
        print(f"  emitter: accepted {accepted} dots (threshold {thr:.4f})")
    return dots
