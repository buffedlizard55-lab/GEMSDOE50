"""H59 - where does the sharpening exponent and the mass stop paying?

``h59_sharpen_sweep.py`` found the off-catalogue DTI and the lift over a matched-mass
uniform control both increasing monotonically in the sharpening exponent up to 8, and
the absolute DTI still rising at 120,000 dots.  This extension pushes both levers
until they turn over, on the same frozen frame, emitter, seed and pool, and reports the
per-macrofold breakdown for the winning cell so the choice is not a single pooled
number.

The transfer model used alongside is the repository's own
(``docs/research/h56-diagnosis.md`` sections 5-6), with the central calibrated hidden
mass ``G = 12,226 px`` and a per-dot credit transfer of 0.887.  Both readings are
printed because they disagree, and the disagreement is the honest state of knowledge:
the proxy says spend more, the model says the hidden truth is saturated.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from gems59 import features as FE
from gems59.frames import macrofolds
from gems59.metric import evaluate

WORK = ROOT / ".arena/h59"
MASSES = [90_000, 120_000, 180_000, 250_000]
EXPS = [8.0, 16.0, 32.0]
SEED = 20261007
TRANSFER = 0.887
G_CENTRAL = 12_226
G_GRID = [8_000, 12_226, 20_000]
LATTICE = 3
FLOOR = 1e-6


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(ROOT / "evidence/h59_sharpen_ext.json"))
    ap.add_argument("--uniform-seeds", type=int, default=3)
    args = ap.parse_args()

    import rasterio
    from scipy import ndimage

    footprint = np.load(WORK / "footprint.npy")
    truth = np.load(WORK / "truth_Smat.npy") & footprint
    fold_map, fold_names = macrofolds(footprint)
    with rasterio.open(ROOT / "data/grid/labels.tif") as ds:
        labels = ds.read(1)
    elig = footprint & ~ndimage.binary_dilation(labels == 1, np.ones((3, 3), bool))
    pool = np.flatnonzero(elig.ravel())

    meta = json.loads((WORK / "feature_names.json").read_text())
    idx = {n: i for i, n in enumerate(meta["names"])}
    cube = np.load(WORK / "features.npy", mmap_mode="r")

    def rank(nm):
        return FE.rank_normalise(np.asarray(cube[:, :, idx[nm]], np.float32), footprint)

    acc = np.zeros(footprint.shape, np.float32)
    cnt = np.zeros(footprint.shape, np.float32)
    for nm in [f"lidar{i:02d}" for i in range(2, 9)] + ["o19_gradmag"]:
        r = rank(nm)
        good = np.isfinite(r)
        acc[good] += r[good]
        cnt[good] += 1
    base = np.where(cnt > 0, acc / np.maximum(cnt, 1), np.nan).astype(np.float32)
    del acc, cnt

    out = {"frame": "S_matched", "truth_px": int(truth.sum()), "eligible_cells": int(elig.sum()),
           "lattice_px": LATTICE, "rng_seed": SEED, "transfer": TRANSFER,
           "G_central": G_CENTRAL, "G_grid": G_GRID, "cells": {}}

    a = np.asarray(base)
    good = np.isfinite(a)
    for exp in EXPS:
        v = np.clip(a[good], 0.0, None) ** exp
        f = np.full(base.shape, np.nan, np.float32)
        f[good] = (v / float(v.max())).astype(np.float32)
        del v
        rng = np.random.default_rng(SEED)
        h, w = f.shape
        bh, bw = h // LATTICE, w // LATTICE
        sub = np.where(elig[: bh * LATTICE, : bw * LATTICE],
                       np.nan_to_num(f[: bh * LATTICE, : bw * LATTICE], nan=-np.inf), -np.inf)
        view = sub.reshape(bh, LATTICE, bw, LATTICE).transpose(0, 2, 1, 3)
        view = view.reshape(bh, bw, LATTICE * LATTICE)
        mx, arg = view.max(axis=2), view.argmax(axis=2)
        flat = mx.ravel()
        bi = np.flatnonzero(np.isfinite(flat))
        vv = flat[bi]
        p = (vv - vv.min()) / (vv.max() - vv.min())
        p = (p + FLOOR) / (p + FLOOR).sum()
        order = rng.choice(bi, size=max(MASSES), replace=False, p=p)
        br, bc = np.unravel_index(order, (bh, bw))
        off = arg[br, bc]
        rr, cc = br * LATTICE + off // LATTICE, bc * LATTICE + off % LATTICE

        for n in MASSES:
            pred = np.zeros(f.shape, bool)
            pred[rr[:n], cc[:n]] = True
            parts = evaluate(pred.astype(np.float32), truth)
            uni = []
            for s in range(args.uniform_seeds):
                pick = np.random.default_rng(770 + 11 * s + n).choice(pool, size=n, replace=False)
                up = np.zeros(f.shape, bool)
                up.flat[pick] = True
                uni.append(evaluate(up.astype(np.float32), truth).dti)
            um = float(np.mean(uni))
            model = {str(G): min(TRANSFER * parts.tp_w, G) / (0.2 * n + 0.8 * G) for G in G_GRID}
            folds = {}
            for fi, fname in enumerate(fold_names):
                fm = fold_map == fi
                fp_ = evaluate(pred.astype(np.float32), truth & fm)
                folds[fname] = {"dti": fp_.dti, "truth_px": int((truth & fm).sum())}
            out["cells"][f"exp{int(exp)}|{n}"] = {
                "dti": parts.dti, "uniform": um, "lift": parts.dti / um,
                "tp_w": parts.tp_w, "credit_per_dot": parts.tp_w / n,
                "modelled": model, "modelled_central": model[str(G_CENTRAL)],
                "modelled_min_over_G": min(model.values()), "folds": folds,
                "fp_w": parts.fp_w,
            }
            fd = " ".join(f"{folds[k]['dti']:.4f}" for k in fold_names)
            print(f"exp{int(exp):2d} N={n:7,d} dti={parts.dti:.5f} lift={parts.dti / um:.3f} "
                  f"T/N={parts.tp_w / n:.4f} model_central={model[str(G_CENTRAL)]:.4f} folds={fd}")
        del f
    Path(args.out).write_text(json.dumps(out, indent=1), encoding="utf-8")
    best = max(out["cells"].items(), key=lambda kv: kv[1]["modelled_central"])
    best_proxy = max(out["cells"].items(), key=lambda kv: kv[1]["dti"])
    print(f"\nbest by central-G model: {best[0]} -> {best[1]['modelled_central']:.4f}")
    print(f"best by proxy DTI      : {best_proxy[0]} -> {best_proxy[1]['dti']:.5f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
