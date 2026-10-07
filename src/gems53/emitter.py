"""Expected-DTI greedy emitter: the mass and the spacing are *solved for*, not chosen.

First-order condition (exact, from the official formula; see :mod:`gems53.truthmodel`): with
``T`` the achieved true-positive weight, ``F`` the false-positive weight and ``N`` the truth size,
adding one pixel of credit ``dT`` and penalty ``dF`` raises the score iff

    dT / dF  >  k ,      k = 0.2 T / (0.2 F + 0.8 N) ,

i.e. the metric carries its own break-even credit bar, and ``k`` *rises* as the score rises.
So an emitter does not need a hand-picked budget: it needs the bar, evaluated at its own current
operating point.  ``emit_expected_dti`` iterates

    (1) rank every allowed cell by expected marginal credit minus the bar times its expected
        marginal penalty, (2) accept the batch above the bar with a suppression radius,
        (3) update ``T``, ``F``, the per-cell coverage, and therefore ``k``,

until the accepted batch is empty.  Convergence is guaranteed in practice because the marginal
credit is non-increasing (a maximum over an ever larger support) while ``k`` is non-decreasing.

Step (1) uses a first-order (uncorrelated-cells) estimate of the marginal credit; the accepted
set is then re-scored with the *exact* weighted evaluation, and Monte-Carlo-checked against drawn
binary truths in ``scripts/h53_validate.py``.
"""
from __future__ import annotations

from typing import Any

import numpy as np
from scipy import ndimage

from .truthmodel import ALPHA, BETA, EPS, credit_field, disc_footprint, expected_max_kernel, \
    kernel_weights


def _shifted_max_indicator(new: np.ndarray, kern: np.ndarray) -> np.ndarray:
    """``max_{x in new} kern(d)`` propagated onto the truth grid, by explicit offsets (no wrap)."""
    out = np.zeros(new.shape, dtype=np.float32)
    r = kern.shape[0] // 2
    h, w = new.shape
    src = new.astype(np.float32)
    for dy in range(-r, r + 1):
        for dx in range(-r, r + 1):
            k = float(kern[dy + r, dx + r])
            if k <= 0.0:
                continue
            ys0, ys1 = max(0, dy), min(h, h + dy)
            xs0, xs1 = max(0, dx), min(w, w + dx)
            if ys0 >= ys1 or xs0 >= xs1:
                continue
            band = np.zeros(new.shape, dtype=np.float32)
            band[ys0:ys1, xs0:xs1] = src[ys0 - dy:ys1 - dy, xs0 - dx:xs1 - dx] * k
            np.maximum(out, band, out=out)
    return out


def suppressible(allowed: np.ndarray, taken: np.ndarray, radius_px: float) -> np.ndarray:
    """Cells still selectable: allowed, and not within ``radius_px`` of an accepted dot."""
    if radius_px <= 0:
        return allowed & ~taken
    foot = disc_footprint(radius_px)
    foot = np.array(foot, dtype=bool)
    foot[foot.shape[0] // 2, foot.shape[1] // 2] = False      # the dot cell itself
    blocked = ndimage.binary_dilation(taken, structure=foot)
    return allowed & ~blocked & ~taken


def emit_expected_dti(belief_or_weight: np.ndarray, w: np.ndarray, allowed: np.ndarray,
                      *, fixed_mass: int | None = None, batch: int = 700, max_rounds: int = 90,
                      suppression_px: float = 1.0, bar_margin: float = 1.0,
                      verbose: bool = False) -> tuple[np.ndarray, dict[str, Any]]:
    """Greedily emit a binary support that maximises the expected official DTI.

    Parameters
    ----------
    belief_or_weight:
        unused ranking hint kept for API symmetry; the ranking is computed from ``w`` itself.
    w:
        probabilistic truth weight field (``sum(w) = N``).
    allowed:
        cells the emitter may use (footprint, outside the catalogue buffer, ...).
    fixed_mass:
        if given, stop after exactly this many dots instead of at the bar (used to build
        matched-mass comparators on the holdout, where a budget difference would confound the test).
    """
    w = np.asarray(w, dtype=np.float32)
    allowed = np.asarray(allowed, dtype=bool) & (w >= 0)
    n = float(w.sum())
    if n <= 0:
        raise ValueError("empty truth weight field")
    if float(np.max(w)) > 1.0 + 1e-6:
        raise ValueError("w must be a probability field (cells in [0,1]) whose sum is N")
    kern = kernel_weights()
    discount = expected_max_kernel(w)                    # per-candidate FP discount
    taken = np.zeros(w.shape, dtype=bool)
    coverage = np.zeros(w.shape, dtype=np.float32)       # b[g] : best kernel credit so far
    t_weight = 0.0
    f_weight = 0.0
    history: list[dict[str, Any]] = []
    for rnd in range(max_rounds):
        residual = w * np.clip(1.0 - coverage, 0.0, 1.0)
        credit = credit_field(residual)                   # dT per candidate cell
        penalty = np.clip(1.0 - discount, 0.0, 1.0)       # dF per candidate cell
        k_bar = ALPHA * t_weight / (ALPHA * f_weight + BETA * n + EPS)
        gain = credit - k_bar * penalty * bar_margin
        selectable = suppressible(allowed, taken, suppression_px)
        g = np.where(selectable, gain, -np.inf).ravel()
        room = None if fixed_mass is None else int(fixed_mass) - int(taken.sum())
        if room is not None and room <= 0:
            break
        limit = batch if room is None else min(batch, room)
        order = np.argsort(-g, kind="stable")[:limit]
        order = order[np.isfinite(g[order])]                  # drop the -inf (unselectable) tail
        cand = order if room is not None else order[g[order] > 0.0]
        if cand.size == 0:
            break
        new = np.zeros(w.size, dtype=bool)
        new[cand] = True
        new = new.reshape(w.shape) & selectable
        if not new.any():
            break
        # exact updates
        add_cov = _shifted_max_indicator(new, kern)
        gain_t = float(np.sum(w * np.clip(add_cov - coverage, 0.0, None)))
        coverage = np.maximum(coverage, add_cov)
        taken |= new
        add_f = float(np.sum(np.clip(1.0 - discount[new], 0.0, 1.0)))
        f_weight += add_f
        t_weight += gain_t
        mass = int(taken.sum())
        score = t_weight / (ALPHA * (t_weight + f_weight) + BETA * n + EPS)
        history.append({"round": rnd, "accepted": int(new.sum()), "mass": mass,
                        "k_bar": float(k_bar), "dT": gain_t, "dF": add_f,
                        "predicted_dti": float(score)})
        if verbose:
            print(f"   r{rnd:02d} +{int(new.sum()):5d} mass={mass:7d} k={k_bar:.5f} "
                  f"dT={gain_t:8.2f} dF={add_f:8.2f} predDTI={score:.4f}", flush=True)
        if fixed_mass is not None and mass >= fixed_mass:
            break
    info = {"history": history, "mass": int(taken.sum()), "tp": t_weight, "fp": f_weight,
            "n_truth": n, "predicted_dti": t_weight / (ALPHA * (t_weight + f_weight) + BETA * n + EPS),
            "final_k_bar": float(ALPHA * t_weight / (ALPHA * f_weight + BETA * n + EPS)),
            "rounds": len(history), "suppression_px": suppression_px,
            "fixed_mass": fixed_mass, "bar_margin": bar_margin}
    return taken, info


def emit_stratified(field: np.ndarray, allowed: np.ndarray, mass: int, block: int = 12,
                    rng_seed: int | None = None) -> tuple[np.ndarray, dict[str, Any]]:
    """Space-filling emission: at most one dot per ``block``-pixel square per round, best-first.

    Why this exists, and why it is not a cosmetic change.  ``TPw`` is a **maximum over predicted
    cells** within each truth pixel's kernel: once a truth pixel is claimed by one dot, every other
    dot within 300 m of it adds no true-positive weight but still adds its own false-positive
    penalty ``p(x)(1 - max_g k)``.  A field's top-N cells are a union of dense blobs (the top 40,000
    cells of this project's belief field form 2,108 connected components, the largest 3,420 px), so
    most of them are *duplicate claims*: on the off-catalogue SGMC instrument they earn 0.026 credit
    per dot against 0.108 for a uniform-random control at the same mass.  Taking one dot per spatial
    block before any block may claim a second makes each dot contest a *distinct* neighbourhood
    first, and lifts the identical field to 0.105 credit per dot at ``block = 12``
    (``evidence/h53_validation.json``, table ``layout_ablation``).

    Round ``r`` places each block's ``r``-th best cell, ordered by value; the support therefore
    degrades gracefully into plain top-N once ``mass`` exceeds the number of occupied blocks.
    Cells in the trailing partial block strip (``height % block``) are filled in a final pass, so the
    emission still covers the whole domain when the mass is large.
    """
    field = np.asarray(field, dtype=np.float32)
    allowed = np.asarray(allowed, dtype=bool) & np.isfinite(field)
    h, w = field.shape
    H, W = h // block, w // block
    if H < 1 or W < 1:
        raise ValueError("block larger than the grid")
    # a cell with no belief is not a candidate: the layout rule ranks *evidence*, and filling a
    # block with a zero-belief cell would silently spend budget on nothing
    view = np.where(allowed[:H * block, :W * block] & (field[:H * block, :W * block] > 0.0),
                    field[:H * block, :W * block], -np.inf)
    view = view.reshape(H, block, W, block).transpose(0, 2, 1, 3).reshape(H * W, block * block)
    order = np.argsort(-view, axis=1, kind="stable")
    ranked_v = np.take_along_axis(view, order, axis=1)
    sup = np.zeros((h, w), dtype=bool)
    taken = 0
    rounds = 0
    rng = np.random.default_rng(rng_seed) if rng_seed is not None else None
    for r in range(block * block):
        if taken >= mass:
            break
        col = ranked_v[:, r]
        good = np.isfinite(col)
        if not good.any():
            break
        vals = np.where(good, col, -np.inf)
        blk = np.argsort(-vals, kind="stable") if rng is None else rng.permutation(H * W)
        for bi in blk:
            if taken >= mass:
                break
            v = vals[bi]
            if not np.isfinite(v):
                break
            cell = int(order[bi, r])
            rr, cc = (bi // W) * block + cell // block, (bi % W) * block + cell % block
            if not sup[rr, cc]:
                sup[rr, cc] = True
                taken += 1
        rounds += 1
    if taken < mass:                                # trailing strip / partial blocks
        rest = allowed & ~sup & (field > 0)
        idx = np.flatnonzero(rest.ravel())
        if idx.size:
            keep = idx[np.argsort(-field.ravel()[idx], kind="stable")[:mass - taken]]
            sup.ravel()[keep] = True
            taken += int(keep.size)
    info = {"mass": int(sup.sum()), "mass_requested": int(mass), "block": block, "rounds": rounds,
            "blocks_occupied": int(np.count_nonzero(
                sup[:H * block, :W * block].reshape(H, block, W, block).any(axis=(1, 3)))),
            "blocks_in_trimmed_view": int(np.isfinite(ranked_v[:, 0]).sum())}
    return sup, info
