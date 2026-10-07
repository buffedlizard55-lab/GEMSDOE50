"""Validate the H59 candidate and write the evidence file.

Reported instruments (all frozen; none is the hidden test set):

  frame ``S-matched``  SGMC fault pixels inside the study footprint, more than
                       300 m from the supplied catalogue, and belonging to a
                       connected component smaller than the largest component ever
                       drawn in the supplied catalogue (< 500 px).  The component
                       filter matters: the raw proxy has 40 components >= 200 px
                       while the supplied catalogue has 10 components >= 200 px and
                       none >= 500 px, so the raw proxy over-represents long
                       bedrock traces (see docs/research/h59-proxy-gap.md).
  frame ``S-raw``      the repository's standard off-catalogue proxy, for
                       comparability with earlier artifacts only.
  frame ``L``          the supplied catalogue itself.  The candidate is *designed*
                       to avoid it, so a value near zero here is expected and is a
                       positive control on the catalogue-exclusion step, not a
                       performance number.

Controls: matched-mass uniform scatter (5 seeds), and four fixed translations of
the candidate.  Uncertainty: paired block bootstrap over 32 x 32 px subtiles.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from gems59 import frames as FR
from gems59.metric import evaluate

SUBTILE = 32
N_BOOT = 400
UNIFORM_SEEDS = (101, 202, 303, 404, 505)
TRANSLATIONS = [(3, 0), (-3, 0), (0, 3), (0, -3), (7, 7)]


def matched_frame() -> np.ndarray:
    from scipy import ndimage

    truth = FR.load_sgmc_offcatalogue()
    lab, _ = ndimage.label(truth, structure=np.ones((3, 3), int))
    sizes = np.bincount(lab.ravel())
    sizes[0] = 0
    keep = np.flatnonzero((sizes > 0) & (sizes < 500))
    return np.isin(lab, keep)


def shift(mask: np.ndarray, dy: int, dx: int) -> np.ndarray:
    out = np.zeros_like(mask)
    h, w = mask.shape
    ys0, ys1 = max(0, dy), min(h, h + dy)
    xs0, xs1 = max(0, dx), min(w, w + dx)
    out[ys0:ys1, xs0:xs1] = mask[max(0, -dy) : h - max(0, dy), max(0, -dx) : w - max(0, dx)][
        : ys1 - ys0, : xs1 - xs0
    ]
    return out


def subtile_credits(pred: np.ndarray, truth: np.ndarray, footprint: np.ndarray):
    """Per-subtile (TP_w, FP_w, FN_w), summed exactly as the official metric does."""
    out = []
    h, w = pred.shape
    step = SUBTILE
    for r0 in range(0, h, step):
        for c0 in range(0, w, step):
            p = pred[r0 : r0 + step, c0 : c0 + step]
            g = truth[r0 : r0 + step, c0 : c0 + step]
            if not g.any() and not p.any():
                continue
            parts = evaluate(p, g)
            out.append((parts.tp_w, parts.fp_w, parts.fn_w))
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--tif", required=True)
    ap.add_argument("--out", default="evidence/h59_validation.json")
    ap.add_argument("--boot", type=int, default=N_BOOT)
    args = ap.parse_args()

    import rasterio

    with rasterio.open(args.tif) as src:
        arr = src.read(1)
    pred = (np.nan_to_num(arr, nan=0.0) > 0)

    labels, footprint = FR.load_labels()
    positives = labels == 1
    truth_m = matched_frame()
    truth_raw = FR.load_sgmc_offcatalogue()
    fold, fold_names = FR.macrofolds(footprint)

    res: dict[str, object] = {
        "raster": args.tif,
        "positive_cells": int(pred.sum()),
        "frames": {},
        "controls": {},
    }

    for name, truth in [("S_matched", truth_m), ("S_raw", truth_raw), ("L", positives)]:
        d = evaluate(pred.astype(np.float32), truth & footprint).dti
        folds = []
        for k, fn in enumerate(fold_names):
            m = fold == k
            folds.append(
                {
                    "fold": fn,
                    "truth_px": int((truth & m).sum()),
                    "dti": evaluate((pred & m).astype(np.float32), truth & m).dti,
                }
            )
        res["frames"][name] = {"truth_px": int(truth.sum()), "dti": d, "folds": folds}
        print(f"{name:10s} truth={int(truth.sum()):>6d} DTI={d:.5f} folds="
              + ",".join(f"{f['dti']:.4f}" for f in folds))

    # ---- matched-mass uniform control ---------------------------------------
    rng_pool = np.flatnonzero(footprint.ravel())
    uni_vals = []
    for s in UNIFORM_SEEDS:
        rng = np.random.default_rng(9100 + s)
        idx = rng.choice(rng_pool, int(pred.sum()), replace=False)
        u = np.zeros(footprint.size, bool)
        u[idx] = True
        u = u.reshape(footprint.shape)
        uni_vals.append(evaluate(u.astype(np.float32), truth_m & footprint).dti)
    res["controls"]["matched_mass_uniform_matched_frame"] = {
        "values": [round(v, 5) for v in uni_vals],
        "mean": float(np.mean(uni_vals)),
        "lift_of_candidate": float(res["frames"]["S_matched"]["dti"] / np.mean(uni_vals)),
    }
    print("uniform control:", [round(v, 4) for v in uni_vals])

    # ---- fair control: uniform inside the artifact's own eligible pool ---------
    # The candidate is barred from the registered prior-artifact positive union and
    # from the pixel-exact catalogue, so the apples-to-apples control is a uniform
    # scatter of the same count inside the *same* pool.  The pool is re-derived here
    # from the frozen build constants and its size is cross-checked against the
    # receipt, so a drifted constant cannot silently change the control.
    from scipy import ndimage as _nd

    cat = positives
    d_cat = _nd.distance_transform_edt(~cat)
    z = np.load("registry/prior_positive_union.npz")
    shape = tuple(int(x) for x in z["shape"])
    prior_u = np.unpackbits(z["packed"])[: shape[0] * shape[1]].reshape(shape).astype(bool)
    elig = footprint & (d_cat > 1) & ~prior_u
    receipt = json.loads(Path("evidence/h59_build.json").read_text())
    assert int(elig.sum()) == int(receipt["eligible_cells"]), (
        f"eligible pool {int(elig.sum())} != receipt {receipt['eligible_cells']}"
    )
    pool_idx = np.flatnonzero(elig.ravel())
    fr_vals = []
    for s in UNIFORM_SEEDS:
        rng = np.random.default_rng(9200 + s)
        idx = rng.choice(pool_idx, int(pred.sum()), replace=False)
        u = np.zeros(elig.size, bool)
        u[idx] = True
        u = u.reshape(elig.shape)
        fr_vals.append(evaluate(u.astype(np.float32), truth_m & footprint).dti)
    res["controls"]["matched_mass_uniform_frozen_pool"] = {
        "eligible_cells": int(elig.sum()),
        "values": [round(v, 5) for v in fr_vals],
        "mean": float(np.mean(fr_vals)),
        "lift_of_candidate": float(res["frames"]["S_matched"]["dti"] / np.mean(fr_vals)),
    }
    print("frozen-pool uniform control:", [round(v, 4) for v in fr_vals],
          "lift", round(res["frames"]["S_matched"]["dti"] / float(np.mean(fr_vals)), 3))

    # ---- translation control -------------------------------------------------
    tr = {}
    for dy, dx in TRANSLATIONS:
        t = shift(pred, dy, dx) & footprint
        tr[f"dy{dy}_dx{dx}"] = evaluate(t.astype(np.float32), truth_m & footprint).dti
    res["controls"]["translations"] = {k: round(v, 5) for k, v in tr.items()}
    res["controls"]["translation_max"] = float(max(tr.values()))
    print("translations:", {k: round(v, 4) for k, v in tr.items()})

    # ---- paired block bootstrap ---------------------------------------------
    b = min(args.boot, 400)
    sub_p = subtile_credits((pred & footprint).astype(np.float32), truth_m & footprint, footprint)
    deltas = []
    rng = np.random.default_rng(20261007)
    arr_p = np.array(sub_p)
    for s in UNIFORM_SEEDS[:1]:
        rngu = np.random.default_rng(9100 + s)
        idx = rngu.choice(rng_pool, int(pred.sum()), replace=False)
        u = np.zeros(footprint.size, bool)
        u[idx] = True
        u = u.reshape(footprint.shape)
        arr_u = np.array(subtile_credits((u & footprint).astype(np.float32), truth_m & footprint, footprint))

        def dti_of(a):
            tp = a[:, 0].sum()
            fp = a[:, 1].sum()
            fn = a[:, 2].sum()
            return tp / (tp + 0.2 * fp + 0.8 * fn + 1e-11)

        n = len(arr_p)
        for _ in range(b):
            pick = rng.integers(0, n, n)
            deltas.append(dti_of(arr_p[pick]) - dti_of(arr_u[pick]))
    res["controls"]["paired_bootstrap_candidate_minus_uniform"] = {
        "n": len(deltas),
        "mean": float(np.mean(deltas)),
        "ci95": [float(np.quantile(deltas, 0.025)), float(np.quantile(deltas, 0.975))],
        "positive_fraction": float(np.mean(np.array(deltas) > 0)),
    }
    print("bootstrap:", res["controls"]["paired_bootstrap_candidate_minus_uniform"])

    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out).write_text(json.dumps(res, indent=1))
    print("wrote", args.out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
