"""Exact implementation of the official DOE GEMS distance-weighted Tversky index.

Source of the definition (read 2026-10-07 from the organizer's public problem page):
  https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/

Official text, transcribed verbatim from that page:

    Let p(x) in [0,1] denote the predicted probability of a fault at pixel x, and
    let g(x) denote the ground truth label of pixel x.

    TI(alpha,beta) = sum_x p(x)g(x) /
                     ( sum_x p(x)g(x) + alpha sum_x p(x)(1-g(x)) + beta sum_x (1-p(x))g(x) )

    k(d) = (1 - d/R)_+ = max(1 - d/R, 0),  R = 300 m (i.e. 3 pixels at 100 m)

    TP_w = sum_{g in G} max_{x: d(x,g) <= R} p(x) k(d(x,g))
    FP_w = sum_{x: p(x) > 0} p(x) [ 1 - max_{g in G} k(d(x,g)) ]
    FN_w = sum_{g in G} [ 1 - max_{x: d(x,g) <= R} p(x) k(d(x,g)) ]
    DTI(alpha,beta) = TP_w / (TP_w + alpha FP_w + beta FN_w + eps)

    alpha = 0.2, beta = 0.8

Everything below is a direct transcription of those five equations.  No tuning,
no re-weighting, no approximation is applied when ``exact=True``.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from scipy import ndimage

# Official constants (problem page 967).
ALPHA = 0.2
BETA = 0.8
R_PIXELS = 3.0  # 300 m at the competition's 100 m resolution
PIXEL_M = 100.0


def kernel(distance: np.ndarray | float, r: float = R_PIXELS) -> np.ndarray | float:
    """Triangular kernel k(d) = max(1 - d/R, 0) with R = 3 px (300 m)."""
    return np.maximum(1.0 - np.asarray(distance) / r, 0.0)


def _offset_kernels(r: float = R_PIXELS) -> list[tuple[int, int, float]]:
    """All integer pixel offsets with Euclidean distance <= r, with k(d) values."""
    n = int(np.floor(r))
    out: list[tuple[int, int, float]] = []
    for dy in range(-n, n + 1):
        for dx in range(-n, n + 1):
            d = float(np.hypot(dy, dx))
            if d <= r:
                out.append((dy, dx, float(kernel(d, r))))
    return out


def _shift(a: np.ndarray, dy: int, dx: int) -> np.ndarray:
    """Return b with b[r, c] = a[r + dy, c + dx], zero-filled at the border.

    For a truth pixel g at (r, c) this yields the prediction value at the
    pixel (r + dy, c + dx), which is what the ``max_x`` in TP_w needs.
    """
    b = np.zeros_like(a)
    h, w = a.shape
    ys0, ys1 = max(0, dy), min(h, h + dy)
    xs0, xs1 = max(0, dx), min(w, w + dx)
    yd0, yd1 = max(0, -dy), min(h, h - dy)
    xd0, xd1 = max(0, -dx), min(w, w - dx)
    if ys0 < ys1 and xs0 < xs1:
        b[yd0:yd1, xd0:xd1] = a[ys0:ys1, xs0:xs1]
    return b


@dataclass(frozen=True)
class DTIParts:
    """The five official quantities, plus the derived identity terms."""

    tp_w: float
    fp_w: float
    fn_w: float
    dti: float
    n_truth: int
    n_positive: int
    dot_credit: float  # A = sum_x p(x) max_g k(d(x,g));  FP_w = sum_x p(x) - A

    def as_dict(self) -> dict:
        return {
            "tp_w": self.tp_w,
            "fp_w": self.fp_w,
            "fn_w": self.fn_w,
            "dti": self.dti,
            "n_truth": self.n_truth,
            "n_positive": self.n_positive,
            "dot_credit": self.dot_credit,
            "alpha": ALPHA,
            "beta": BETA,
            "r_pixels": R_PIXELS,
        }


def evaluate(
    prediction: np.ndarray,
    truth: np.ndarray,
    *,
    alpha: float = ALPHA,
    beta: float = BETA,
    eps: float = 1e-11,
) -> DTIParts:
    """Distance-weighted Tversky index, transcribed from the official equations.

    Parameters
    ----------
    prediction
        2-D array of predicted probabilities in [0, 1].  Non-finite entries are
        treated as zero (they cannot be summed by the official equations).
    truth
        Boolean / 0-1 2-D array of ground-truth fault pixels.
    """
    p = np.asarray(prediction, dtype=np.float64)
    if p.ndim != 2:
        raise ValueError("prediction must be 2-D")
    p = np.where(np.isfinite(p), p, 0.0)
    if p.min() < 0.0 or p.max() > 1.0:
        raise ValueError("prediction must lie in [0, 1]")

    g = np.asarray(truth)
    if g.ndim != 2 or g.shape != p.shape:
        raise ValueError("truth must be 2-D and match prediction shape")
    g = g.astype(bool)

    n_truth = int(g.sum())
    n_positive = int((p > 0).sum())

    # ---- FP_w ----------------------------------------------------------
    # Nearest ground-truth pixel distance for every prediction pixel.
    dt_to_truth = ndimage.distance_transform_edt(~g)
    k_truth = kernel(dt_to_truth)
    dot_credit = float((p * k_truth).sum())
    fp_w = float(p.sum() - dot_credit)

    # ---- TP_w and FN_w -------------------------------------------------
    # per_truth[r, c] = max_{x: d(x, g) <= R} p(x) k(d(x, g)) evaluated at the
    # truth pixel g = (r, c).  For a truth pixel at (r, c) the candidate x are
    # (r + dy, c + dx).  Only truth pixels are summed, so the values are gathered
    # at the truth pixels instead of being materialised over the whole grid.
    rows, cols = np.nonzero(g)
    if rows.size == 0:
        return DTIParts(0.0, fp_w, 0.0, 0.0, 0, n_positive, dot_credit)
    r = R_PIXELS
    pad = int(np.floor(r)) + 1
    p_pad = np.zeros((p.shape[0] + 2 * pad, p.shape[1] + 2 * pad), dtype=p.dtype)
    p_pad[pad:-pad, pad:-pad] = p
    rr = rows + pad
    cc = cols + pad
    per_truth = np.zeros(rows.size, dtype=np.float64)
    for dy, dx, k in _offset_kernels():
        per_truth = np.maximum(per_truth, p_pad[rr + dy, cc + dx] * k)
    tp_w = float(per_truth.sum())
    fn_w = float(rows.size - tp_w)

    dti = tp_w / (tp_w + alpha * fp_w + beta * fn_w + eps)
    return DTIParts(tp_w, fp_w, fn_w, dti, n_truth, n_positive, dot_credit)


def binary_identity(
    prediction: np.ndarray, truth: np.ndarray, *, alpha: float = ALPHA, beta: float = BETA
) -> float:
    """Closed form for unit-height binary predictions.

    With p(x) in {0,1} the official equations reduce exactly to

        DTI = T / ( alpha(|S| - A) + beta|G| + (1 - beta)T )

    where S is the set of predicted pixels, T = TP_w and
    A = sum_{x in S} k(d(x, G)).  This is a cross-check of :func:`evaluate`.
    """
    p = np.asarray(prediction, dtype=np.float64)
    g = np.asarray(truth).astype(bool)
    s = p > 0
    if not np.allclose(p[s], 1.0):
        raise ValueError("binary_identity requires predictions in {0, 1}")
    dt = ndimage.distance_transform_edt(~g)
    a = float(kernel(dt)[s].sum())
    per_truth = np.zeros_like(p)
    for dy, dx, k in _offset_kernels():
        np.maximum(per_truth, _shift(p, dy, dx) * k, out=per_truth)
    t = float(per_truth[g].sum())
    n = int(s.sum())
    ng = int(g.sum())
    return t / (alpha * (n - a) + beta * ng + (1.0 - beta) * t + 1e-11)
