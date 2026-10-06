"""The official competition metric, implemented exactly as published, with its algebra.

Published definition (competition page 967, fetched 2026-10-06):

    k(d)  = max(1 - d/R, 0)                     triangular kernel, R = 300 m = 3 cells
    TPw   = sum_{g in G} max_{x: d(x,g)<=R} p(x) k(d(x,g))
    FPw   = sum_{x: p(x)>0} p(x) [1 - max_{g in G} k(d(x,g))]
    FNw   = sum_{g in G} [1 - max_{x: d(x,g)<=R} p(x) k(d(x,g))]
    DTI   = TPw / (TPw + alpha FPw + beta FNw + eps),   alpha = 0.2, beta = 0.8

Two exact consequences are used throughout this repository and are *tested* here rather
than trusted:

    (identity)  FNw = |G| - TPw                          (holds for any p, any raster)
    (algebra)   DTI = T / (0.2 (T + S - M) + 0.8 |G|)
                with T = TPw, S = sum_x p(x)  (emitted mass),
                     M = sum_x p(x) max_g k(d(x,g))

and the first-order condition that follows from the algebra:

    (marginal rule)  adding one unit of mass at a cell whose kernel weight toward
                     truth is w raises DTI  <=>  w > 0.2 * DTI

for the single-truth-pixel case; :func:`marginal_condition` is the exact multi-pixel form.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from scipy.ndimage import distance_transform_edt

ALPHA = 0.2
BETA = 0.8


@dataclass(frozen=True)
class DTI:
    """All components of the metric for one (prediction, truth) pair."""

    tpw: float
    fpw: float
    fnw: float
    mass: float  # S = sum of predicted values
    best_cover: float  # M = sum_x p(x) max_g k
    truth_cells: int  # |G|
    value: float  # DTI

    def as_dict(self) -> dict:
        return {
            "tpw": self.tpw,
            "fpw": self.fpw,
            "fnw": self.fnw,
            "mass": self.mass,
            "best_cover": self.best_cover,
            "truth_cells": self.truth_cells,
            "dti": self.value,
        }


def _as_float(a) -> np.ndarray:
    out = np.asarray(a, dtype=np.float32)
    return np.nan_to_num(out, nan=0.0, posinf=0.0, neginf=0.0)


def kernel_offsets(offsets: int = 3) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """(dcol, drow, weight) for every offset inside the triangular support."""
    rr, cc = np.mgrid[-offsets : offsets + 1, -offsets : offsets + 1]
    d = np.sqrt(rr.astype(np.float64) ** 2 + cc.astype(np.float64) ** 2)
    keep = d <= offsets
    return cc[keep], rr[keep], np.maximum(1.0 - d[keep] / offsets, 0.0)


def dti_parts(pred, truth, offsets: int = 3, alpha: float = ALPHA, beta: float = BETA,
              eps: float = 0.0) -> DTI:
    """Exact components of the published metric.

    ``pred`` holds probability mass in [0, 1]; ``truth`` is a boolean raster.  TPw is the
    exact max-plus convolution over the (2R+1)^2 kernel support (zero-padded, so no
    wrap-around), FPw = S - M with M obtained from an exact Euclidean distance transform,
    and FNw = |G| - TPw.  No approximation is used anywhere.
    """
    p = _as_float(pred)
    g = np.asarray(truth).astype(bool)
    if p.shape != g.shape:
        raise ValueError(f"shape mismatch: pred {p.shape} vs truth {g.shape}")

    pad = offsets
    pp = np.pad(p, pad, mode="constant")
    dcol, drow, w = kernel_offsets(offsets)
    acc = np.zeros_like(p)
    for dc, dr, wk in zip(dcol, drow, w):
        # offset (dr, dc) of the prediction relative to the truth cell
        sl = pp[pad + dr : pad + dr + p.shape[0], pad + dc : pad + dc + p.shape[1]]
        if wk == 1.0:
            np.maximum(acc, sl, out=acc)
        else:
            np.maximum(acc, sl * np.float32(wk), out=acc)
    tpw = float(acc[g].sum(dtype=np.float64))

    if g.any():
        d = distance_transform_edt(~g)
        best = np.maximum(1.0 - d / offsets, 0.0).astype(np.float32)
    else:
        best = np.zeros(p.shape, dtype=np.float32)
    mass = float(p.sum(dtype=np.float64))
    m = float((p * best).sum(dtype=np.float64))
    fpw = mass - m
    truth_cells = int(g.sum())
    fnw = truth_cells - tpw
    denom = tpw + alpha * fpw + beta * fnw + eps
    value = 0.0 if denom <= 0 else tpw / denom
    return DTI(tpw=tpw, fpw=fpw, fnw=fnw, mass=mass, best_cover=m,
               truth_cells=truth_cells, value=value)


def dti(pred, truth, offsets: int = 3, alpha: float = ALPHA, beta: float = BETA) -> float:
    """The scalar published metric."""
    return dti_parts(pred, truth, offsets, alpha, beta).value


def algebra_rhs(t: float, s: float, m: float, truth_cells: int, alpha: float = ALPHA) -> float:
    """DTI = T / (0.2 (T + S - M) + 0.8 |G|), the closed form used for decision rules."""
    return t / (alpha * (t + s - m) + (1.0 - alpha) * truth_cells)


def credit_bar(current_dti: float, spec: float = 1.0, alpha: float = ALPHA) -> float:
    """Kernel weight a new unit of mass must reach to raise DTI (single-truth-pixel case)."""
    return alpha * current_dti * spec


def marginal_condition(w_new: float, delta_t: float, current_dti: float,
                       alpha: float = ALPHA) -> bool:
    """Exact test: does adding one unit of mass at this cell raise DTI?

    ``delta_t`` = increase of TPw (sum of kernel weights over the truth cells for which
    this cell becomes the best cover), ``w_new`` = increase of M (= the kernel weight
    toward the cell's nearest truth cell).
    """
    return delta_t > alpha * current_dti * (delta_t + 1.0 - w_new)


def brute_force(pred, truth, offsets: int = 3, alpha: float = ALPHA, beta: float = BETA) -> dict:
    """O(|G| * N) transcription of the published equations, for tests only."""
    p = _as_float(pred)
    g = np.asarray(truth).astype(bool)
    gc = np.argwhere(g)
    pc = np.argwhere(p > 0)
    tpw = 0.0
    for r, c in gc:
        best = 0.0
        for r2, c2 in pc:
            d = float(np.hypot(r - r2, c - c2))
            if d <= offsets:
                best = max(best, float(p[r2, c2]) * max(1.0 - d / offsets, 0.0))
        tpw += best
    fpw = 0.0
    for r2, c2 in pc:
        bestk = 0.0
        if len(gc):
            dmin = float(np.min(np.hypot(gc[:, 0] - r2, gc[:, 1] - c2)))
            bestk = max(1.0 - dmin / offsets, 0.0)
        fpw += float(p[r2, c2]) * (1.0 - bestk)
    fnw = float(len(gc)) - tpw
    denom = tpw + alpha * fpw + beta * fnw
    return {"tpw": tpw, "fpw": fpw, "fnw": fnw,
            "dti": 0.0 if denom <= 0 else tpw / denom}
