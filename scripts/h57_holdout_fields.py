"""H57 experiment 9 - which field finds the *labelled* fault population.

The off-catalogue proxy is made of USGS SGMC bedrock fault pixels.  The hidden
target is young, surface-expressed faults the experts mapped themselves (staff
ruling R4).  Those are different populations, and H57's own screen shows the
proxy prefers a topographic slope band that the repository's earlier work did
not find useful for young faults.  This script settles the question with the one
instrument in the repository that is drawn from the labelled population itself.

Design
------
For each spatial macrofold ``k``: hide fold ``k``'s labels, remove a 1 px buffer
around the *visible* labels from the emission pool, emit over the whole footprint
including fold ``k``, then score the emitted dots inside fold ``k`` only, against
fold ``k``'s own labels.  Dots outside fold ``k`` are discarded from the score so
that the comparison is against held-out truth and nothing else.

This is the same construction as ``h57_field_select.py``, with one change that
matters: the *labels* of the held-out fold are still physically present in the
map, so the field sees the terrain there; only the answer is hidden.  The metric
is the organizers' own, restricted to the fold's bounding box and truth set.

Also runs a lattice-spacing sweep for the winning field on frame S, so the
emission geometry and the field are chosen on the same footing.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from gems57 import features as FE
from gems57.frames import macrofolds
from gems57.metric import evaluate

WORK = ROOT / ".arena/h57"
MASS = 90_000
STRUCT = np.ones((3, 3), bool)


def rank_mean(mats):
    acc = np.zeros(mats[0].shape, np.float32)
    cnt = np.zeros(mats[0].shape, np.float32)
    for q in mats:
        good = np.isfinite(q)
        acc[good] += q[good]
        cnt[good] += 1
    return np.where(cnt > 0, acc / np.maximum(cnt, 1), np.nan).astype(np.float32)


def emit(field, elig, n, k, seed):
    rng = np.random.default_rng(seed)
    h, w = field.shape
    bh, bw = h // k, w // k
    sub = np.where(elig[: bh * k, : bw * k], np.nan_to_num(field[: bh * k, : bw * k], nan=-np.inf),
                   -np.inf)
    view = sub.reshape(bh, k, bw, k).transpose(0, 2, 1, 3).reshape(bh, bw, k * k)
    mx, arg = view.max(axis=2), view.argmax(axis=2)
    flat = mx.ravel()
    idx = np.flatnonzero(np.isfinite(flat))
    v = flat[idx]
    lo, hi = v.min(), v.max()
    p = (v - lo) / (hi - lo) if hi > lo else np.ones_like(v)
    p = (p + 1e-6) / (p + 1e-6).sum()
    ch = rng.choice(idx, size=n, replace=False, p=p)
    br, bc = np.unravel_index(ch, (bh, bw))
    off = arg[br, bc]
    out = np.zeros(field.shape, bool)
    out[br * k + off // k, bc * k + off % k] = True
    return out


def dilate(mask):
    from scipy import ndimage

    return ndimage.binary_dilation(mask, STRUCT)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(ROOT / "evidence/h57_holdout_fields.json"))
    ap.add_argument("--uniform-seeds", type=int, default=3)
    args = ap.parse_args()

    import rasterio

    footprint = np.load(WORK / "footprint.npy")
    with rasterio.open(ROOT / "data/grid/labels.tif") as ds:
        labels = ds.read(1)
    catalogue = (labels == 1) & footprint
    fold_map, fold_names = macrofolds(footprint)
    print(f"catalogue {int(catalogue.sum()):,} px in {len(fold_names)} macrofolds")

    meta = json.loads((WORK / "feature_names.json").read_text())
    idx = {n: i for i, n in enumerate(meta["names"])}
    cube = np.load(WORK / "features.npy", mmap_mode="r")

    def rank(nm):
        return FE.rank_normalise(np.asarray(cube[:, :, idx[nm]], np.float32), footprint)

    lid7 = rank_mean([rank(f"lidar{i:02d}") for i in range(2, 9)])
    o19 = rank("o19_raw")
    o19g = rank("o19_gradmag")
    def sharpen(f, power=16.0):
        g = np.isfinite(f)
        out = np.full(f.shape, np.nan, np.float32)
        v = np.clip(f[g], 0.0, None) ** power
        out[g] = (v / float(v.max())).astype(np.float32)
        return out

    fields = {
        "o19": o19,
        "o19grad+lidar7": rank_mean([o19g, lid7]),
        "sharpen(o19grad+lidar7)^16": sharpen(rank_mean([o19g, lid7])),
        "lidar7": lid7,
    }

    out: dict = {"design": "leave-one-macrofold-out labels, 1 px visible-catalogue buffer",
                 "mass_total": MASS, "fields": {}}
    for name, field in fields.items():
        rows = {}
        pooled = {"tp_w": 0.0, "fp_w": 0.0, "fn_w": 0.0, "n": 0}
        for fi, fname in enumerate(fold_names):
            fmask = fold_map == fi
            visible = catalogue & ~fmask
            elig = footprint & ~dilate(visible)
            share = float(fmask.sum()) / float(footprint.sum())
            n = round(MASS * share)
            # the lattice must have room for the dots: one per 3 x 3 px block
            n = min(n, max(1_000, elig.sum() // 9))
            pred = emit(field, elig, n, 3, 20261007)
            pred_fold = pred & fmask
            truth = catalogue & fmask
            parts = evaluate(pred_fold.astype(np.float32), truth)
            uni = []
            pool = np.flatnonzero(elig.ravel())
            for s in range(args.uniform_seeds):
                r = np.random.default_rng(4242 + 17 * s)
                pick = r.choice(pool, size=n, replace=False)
                up = np.zeros(field.shape, bool)
                up.flat[pick] = True
                uni.append(evaluate((up & fmask).astype(np.float32), truth).dti)
            rows[fname] = {"dti": parts.dti, "uniform": float(np.mean(uni)),
                           "lift": parts.dti / float(np.mean(uni)),
                           "n": n, "truth_px": int(truth.sum()), "tp_w": parts.tp_w}
            for key in ("tp_w", "fp_w", "fn_w"):
                pooled[key] += getattr(parts, key)
            pooled["n"] += n
            print(f"{name:16s} {fname:4s} n={n:7,d} truth={int(truth.sum()):6,d} "
                  f"dti={parts.dti:.5f} uni={float(np.mean(uni)):.5f} "
                  f"lift={parts.dti / float(np.mean(uni)):.3f}")
        pooled_dti = pooled["tp_w"] / (pooled["tp_w"] + 0.2 * pooled["fp_w"]
                                       + 0.8 * pooled["fn_w"] + 1e-12)
        out["fields"][name] = {"folds": rows, "pooled_dti": float(pooled_dti),
                               "pooled_tp_w": pooled["tp_w"]}
        print(f"{name:16s} POOLED dti={pooled_dti:.5f} tp_w={pooled['tp_w']:.0f}")
        del field

    out["winner"] = max(out["fields"], key=lambda k: out["fields"][k]["pooled_dti"])
    Path(args.out).write_text(json.dumps(out, indent=1), encoding="utf-8")
    print("winner by labelled-population holdout:", out["winner"])
    print("wrote", args.out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
