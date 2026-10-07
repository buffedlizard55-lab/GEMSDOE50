"""Metric-matched sparse emission.

The metric (verified against the competition page's worked example in
``tests/test_metric.py``) gives, for a binary support with weighted credit T and penalty
F and hidden truth size G,

    DTI = T / (0.2*T + 0.2*F + 0.8*G) = T / (0.8*G + 0.2*(T + F))

so adding one dot of kernel credit k changes the score by

    sign(k*(0.8*G + 0.2*(T+F)) - 0.2*T) = sign(k - 0.2*DTI).

Two consequences drive this module:

* a dot *pays* only if its kernel credit clears ``0.2 * DTI``, i.e. it must sit within
  ``300 m * (1 - 0.2*DTI)`` of scored truth (~283 m at DTI = 0.28);
* two dots closer than the kernel radius are nearly redundant - the numerator is a maximum
  over predictions - while each still costs the 0.2 term, so accepted dots are separated by
  at least ``suppression_px``.
"""
from __future__ import annotations

import numpy as np
from scipy import ndimage

KERNEL_RADIUS_PX = 3.0


def kernel_weights(radius_px: float = KERNEL_RADIUS_PX) -> np.ndarray:
    r = int(np.ceil(radius_px))
    yy, xx = np.meshgrid(np.arange(-r, r + 1), np.arange(-r, r + 1), indexing="ij")
    d = np.hypot(yy, xx)
    k = np.maximum(1.0 - d / radius_px, 0.0)
    return k.astype(np.float32)


def expected_credit_field(belief: np.ndarray, radius_px: float = KERNEL_RADIUS_PX) -> np.ndarray:
    """Kernel correlation: expected marginal credit of a dot placed at each cell."""
    kern = kernel_weights(radius_px)
    return ndimage.correlate(np.asarray(belief, dtype=np.float32), kern, mode="constant").astype(np.float32)


def pack(
    belief: np.ndarray,
    mass: int,
    *,
    valid: np.ndarray | None = None,
    suppression_px: float = 3.0,
    seed: int = 51,
) -> tuple[np.ndarray, dict]:
    """Greedy packing of up to ``mass`` dots by descending expected marginal credit."""
    score = expected_credit_field(np.nan_to_num(belief, nan=0.0, posinf=0.0, neginf=0.0))
    allowed = np.isfinite(belief)
    if valid is not None:
        allowed = allowed & valid
    score = np.where(allowed & (score > 0), score, 0.0)
    order = np.argsort(-score.ravel(), kind="stable")
    height, width = score.shape
    dot = np.zeros(height * width, dtype=bool)
    blocked = np.zeros(height * width, dtype=bool)
    sp = int(np.ceil(suppression_px))
    offsets = [(dy, dx) for dy in range(-sp, sp + 1) for dx in range(-sp, sp + 1)
               if 0 < np.hypot(dy, dx) <= suppression_px]
    taken = 0
    tie_break = None
    for flat in order:
        if taken >= mass:
            break
        if score.flat[flat] <= 0 or blocked[flat]:
            continue
        if tie_break is None:
            tie_break = np.random.default_rng(seed)
        dot[flat] = True
        taken += 1
        r, c = divmod(int(flat), width)
        for dy, dx in offsets:
            rr, cc = r + dy, c + dx
            if 0 <= rr < height and 0 <= cc < width:
                blocked[rr * width + cc] = True
    support = dot.reshape(height, width)
    return support, {"mass": int(taken), "suppression_px": suppression_px,
                     "belief_max": float(np.max(belief)) if np.isfinite(belief).any() else 0.0}


def sweep(
    belief: np.ndarray,
    masses: list[int],
    truths: dict[str, np.ndarray],
    *,
    valid: np.ndarray | None = None,
    suppression_px: float = 3.0,
) -> dict:
    """Emit at each mass in the sweep and score it on every instrument."""
    from .instruments import all_instruments

    out = {}
    for m in masses:
        support, pack_info = pack(belief, m, valid=valid, suppression_px=suppression_px)
        scores = all_instruments(support, truths)
        out[int(m)] = {"n_dots": pack_info["mass"], "instruments": scores}
    return out


def choose_mass(sweep_results: dict, *, target_dti: float, min_instruments: int = 2) -> dict:
    """Pick the largest swept mass whose *marginal* proxy credit still clears the bar.

    The bar is the metric's own first-order condition ``k > 0.2 * target_dti`` applied to the
    measured per-dot credit on the off-catalogue instruments.  ``target_dti`` is preregistered
    (see ``docs/hyporheses-preregistered.md``), never tuned on a holdout score.
    """
    masses = sorted(sweep_results)
    chosen = masses[0]
    table = []
    for i, m in enumerate(masses):
        if i == 0:
            table.append({"mass": m, "marginal": None, "kept": False})
            continue
        prev = masses[i - 1]
        margins = []
        for name, score in sweep_results[m]["instruments"].items():
            if name == "catalogue":
                continue
            n_now, n_prev = sweep_results[m]["n_dots"], sweep_results[prev]["n_dots"]
            if n_now == n_prev:
                continue
            delta_t = (score["tp_weight"] - sweep_results[prev]["instruments"][name]["tp_weight"])
            margins.append(delta_t / (n_now - n_prev))
        if not margins:
            break
        marginal = float(min(margins))
        keeps = marginal > 0.2 * target_dti
        table.append({"mass": m, "marginal": marginal, "bar": 0.2 * target_dti, "kept": keeps})
        if keeps:
            chosen = m
    return {"chosen_mass": int(chosen), "target_dti": target_dti, "table": table}
