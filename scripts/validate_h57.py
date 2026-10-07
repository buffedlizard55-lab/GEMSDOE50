"""H57 validation — metric-exact scoring of the candidate on every available frame.

Reports, for the candidate and for matched controls:

* ``N`` (dots), ``T`` (credit), ``c_per_dot = T/N`` and the exact
  ``DTI = T / (0.2 T + 0.2 F + 0.8 G)`` on the F1 independent-population frame
  and on the F2 catalogue-holdout frame, with an 8 x 8 block bootstrap;
* matched-mass uniform controls (5 seeds) and 8 translation controls;
* the same statistics for the corpus anchors that have byte-verified supports,
  so the candidate's frame numbers sit next to the group's best;
* the modelled hidden DTI under the **corpus transfer factor**, which is the
  only bridge from a frame to the hidden truth available offline, and which is
  an assumption, not a measurement.

Usage
-----
    python scripts/validate_h57.py --tif docs/downloads/<candidate>-allfinite.tif
"""

from __future__ import annotations

import argparse
import glob
import json
import os
import sys
import time

import numpy as np
import rasterio

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from h57_frames import build_frames, load_grid

G_DEFAULT = 14088.75  # nested-pair solve, see docs/research/h57-verdict-20261007.md
TRANSFER_NOTE = (
    "hidden_c_per_dot / F1_c_per_dot, measured on the byte-verified well-spaced "
    "corpus artifacts with recorded scores; applying it to a different detector "
    "is an assumption, not a measurement."
)
DEFAULT_TRANSFER = 1.80


def load_pos(path: str) -> np.ndarray:
    with rasterio.open(path) as ds:
        a = ds.read(1)
    return np.isfinite(a) & (a > 0)


def stats(frame, sel, g):
    m = sel & frame.domain
    n = int(m.sum())
    if n == 0:
        return None
    credit = float(np.nansum(frame.K[m]))
    t = min(credit, float(frame.n_truth))
    d = 0.2 * t + 0.2 * (n - credit) + 0.8 * float(frame.n_truth)
    return {"n_dots": n, "credit": credit, "c_per_dot": credit / n,
            "coverage": t / frame.n_truth, "dti": t / d}


def _per_block(frame, sel, blocks):
    h, w = sel.shape
    bh, bw = h // blocks, w // blocks
    cred = np.zeros((blocks, blocks))
    cnt = np.zeros((blocks, blocks))
    for i in range(blocks):
        for j in range(blocks):
            sl = (slice(i * bh, (i + 1) * bh), slice(j * bw, (j + 1) * bw))
            mm = sel[sl] & frame.domain[sl]
            nn = int(mm.sum())
            cnt[i, j] = nn
            if nn:
                cred[i, j] = float(np.nansum(frame.K[sl][mm]))
    return cred, cnt


def block_bootstrap(frame, sel, n_boot=400, blocks=8, seed=7):
    """Paired spatial-block bootstrap of DTI(candidate) - DTI(matched uniform)."""
    rng = np.random.default_rng(seed)
    m = sel & frame.domain
    n = int(m.sum())
    if n == 0:
        return None
    idx = np.nonzero(frame.domain.ravel())[0]
    uni = np.zeros(sel.size, dtype=bool)
    uni[rng.choice(idx, size=min(n, idx.size), replace=False)] = True
    uni = uni.reshape(sel.shape)
    ca, na = _per_block(frame, m, blocks)
    cu, nu = _per_block(frame, uni, blocks)
    g_tot = float(frame.n_truth)
    flat_i, flat_j = np.meshgrid(np.arange(blocks), np.arange(blocks), indexing="ij")
    fi, fj = flat_i.ravel(), flat_j.ravel()
    deltas = []
    for _ in range(n_boot):
        k = rng.integers(0, fi.size, size=fi.size)
        n_a, c_a = na[fi[k], fj[k]].sum(), ca[fi[k], fj[k]].sum()
        n_u, c_u = nu[fi[k], fj[k]].sum(), cu[fi[k], fj[k]].sum()
        if n_a == 0 or n_u == 0:
            continue
        d_a = 0.2 * min(c_a, g_tot) + 0.2 * (n_a - c_a) + 0.8 * g_tot
        d_u = 0.2 * min(c_u, g_tot) + 0.2 * (n_u - c_u) + 0.8 * g_tot
        deltas.append(min(c_a, g_tot) / d_a - min(c_u, g_tot) / d_u)
    if not deltas:
        return None
    d = np.asarray(deltas)
    return {"mean_delta": float(d.mean()), "lo95": float(np.percentile(d, 2.5)),
            "hi95": float(np.percentile(d, 97.5)),
            "positive_frac": float((d > 0).mean()), "n_boot": int(d.size)}


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--tif", required=True)
    ap.add_argument("--prior", default=".arena/prior")
    ap.add_argument("--inputs", default=".arena/inputs")
    ap.add_argument("--labels", default="data/grid/labels.tif")
    ap.add_argument("--sgmc", default="data/external/derived_sgmc_faults_100m_u8.tif")
    ap.add_argument("--out", default="evidence/h57_validation.json")
    ap.add_argument("--g", type=float, default=G_DEFAULT)
    ap.add_argument("--transfer", type=float, default=DEFAULT_TRANSFER)
    args = ap.parse_args(argv)

    footprint, catalogue, _, _ = load_grid(args.labels)
    with rasterio.open(args.sgmc) as ds:
        sgmc = ds.read(1) == 1
    with rasterio.open(os.path.join(args.inputs, "lidar_scarp_features_u8.tif")) as ds:
        valid = ds.read(12) > 0
    allf = build_frames(footprint, catalogue, sgmc, valid)
    f1 = allf["F1_sgmc_off"]
    f2 = {k: v for k, v in allf.items() if k.startswith("F2_")}

    cand = load_pos(args.tif)
    rep = {"generated_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
           "candidate": args.tif, "G": args.g, "transfer_note": TRANSFER_NOTE,
           "n_candidate_dots": int(cand.sum())}

    rep["F1"] = stats(f1, cand, args.g)
    rng = np.random.default_rng(11)
    idx = np.nonzero(f1.domain.ravel())[0]
    n = int((cand & f1.domain).sum())
    uni = []
    for _ in range(5):
        u = np.zeros(cand.size, dtype=bool)
        u[rng.choice(idx, size=min(n, idx.size), replace=False)] = True
        s = stats(f1, u.reshape(cand.shape), args.g)
        if s:
            uni.append(s["c_per_dot"])
    rep["F1_uniform_mean_c_per_dot"] = float(np.mean(uni))
    rep["F1_lift"] = (rep["F1"]["c_per_dot"] / rep["F1_uniform_mean_c_per_dot"]
                      if rep["F1"] else None)
    shifts = []
    for dr, dc in ((-7, 0), (7, 0), (0, -7), (0, 7), (-5, -5), (5, 5), (-5, 5), (5, -5)):
        s = stats(f1, np.roll(np.roll(cand, dr, 0), dc, 1), args.g)
        if s:
            shifts.append(s["c_per_dot"])
    rep["F1_translation_mean_c_per_dot"] = float(np.mean(shifts))
    rep["F1_beats_translations"] = bool(rep["F1"] and rep["F1"]["c_per_dot"] > np.mean(shifts))
    rep["F1_block_bootstrap_vs_uniform"] = block_bootstrap(f1, cand)

    folds = {k: stats(fr, cand, args.g) for k, fr in f2.items()}
    rep["F2"] = folds
    ws = {k: v for k, v in folds.items() if k.startswith("F2_cat")}
    cred = sum(v["credit"] for v in ws.values() if v)
    dots = sum(v["n_dots"] for v in ws.values() if v)
    gsum = sum(f2[k].n_truth for k in ws)
    t = min(cred, gsum)
    d = 0.2 * t + 0.2 * (dots - cred) + 0.8 * gsum
    rep["F2_summary"] = {"folds": len(ws),
                         "folds_with_dots": sum(1 for v in ws.values() if v),
                         "pooled_c_per_dot": (cred / dots) if dots else None,
                         "pooled_dti": (t / d) if dots else None}

    anchors = []
    for p in sorted(glob.glob(os.path.join(args.prior, "*.tif"))):
        pos_ = load_pos(p)
        s1 = stats(f1, pos_, args.g)
        if not s1:
            continue
        anchors.append({"file": os.path.basename(p), "n_dots": int(pos_.sum()),
                        "F1_c_per_dot": s1["c_per_dot"], "F1_dti": s1["dti"]})
    rep["F1_corpus_anchors"] = anchors

    rep["transfer_factor"] = args.transfer
    if rep["F1"]:
        h = rep["F1"]["c_per_dot"] * args.transfer
        nn = int(cand.sum())
        t = min(h * nn, args.g)
        d = 0.2 * t + 0.2 * (nn - h * nn) + 0.8 * args.g
        rep["modelled_hidden"] = {"assumed_hidden_c_per_dot": h, "N": nn, "T": t,
                                  "coverage": t / args.g, "dti": t / d}

    os.makedirs(os.path.dirname(args.out) or ".", exist_ok=True)
    with open(args.out, "w") as fh:
        json.dump(rep, fh, indent=1)
    print(json.dumps({k: v for k, v in rep.items() if k != "F1_corpus_anchors"}, indent=1))
    print("\nF1 corpus anchors (c_per_dot is the quantity a detector is ranked on):")
    for a in sorted(anchors, key=lambda z: -z["F1_c_per_dot"])[:12]:
        print(f"  {a['file']:26s} N={a['n_dots']:8d} c/dot={a['F1_c_per_dot']:.4f} "
              f"DTI={a['F1_dti']:.4f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
