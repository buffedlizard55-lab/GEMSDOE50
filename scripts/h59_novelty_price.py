"""H59 - the measured price of the novelty constraint.

The brief requires a genuinely new raster: no dot may reuse a pixel of any registered
prior artifact. That constraint is enforced by removing the 61-artifact positive union
(1,405,451 cells, 23.4 % of the study footprint) from the emission pool. The

    "prior artifacts were themselves concentrated on the strongest evidence"

intuition says this should hurt, because the excluded cells are not a random sample —
they are exactly where earlier candidates put their dots, which is where the evidence
peaks. This script measures the price instead of estimating it: the same field, the
same mass, the same seed, the same lattice, differing only in whether the union is
excluded, scored on frame S_matched with its own matched-mass uniform control.
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
from gems59.metric import evaluate

WORK = ROOT / ".arena/h59"
LATTICE = 3
MASS = 90_000
SEED = 20261007
SHARPEN = 16.0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(ROOT / "evidence/h59_novelty_price.json"))
    ap.add_argument("--uniform-seeds", type=int, default=5)
    args = ap.parse_args()

    import rasterio
    from scipy import ndimage

    footprint = np.load(WORK / "footprint.npy")
    truth = np.load(WORK / "truth_Smat.npy") & footprint
    with rasterio.open(ROOT / "data/grid/labels.tif") as ds:
        labels = ds.read(1)
    elig_all = footprint & ~ndimage.binary_dilation(labels == 1, np.ones((3, 3), bool))
    z = np.load(ROOT / "registry/prior_positive_union.npz")
    shp = tuple(int(x) for x in z["shape"])
    prior = np.unpackbits(z["packed"])[: shp[0] * shp[1]].reshape(shp).astype(bool)

    meta = json.loads((WORK / "feature_names.json").read_text())
    idx = {n: i for i, n in enumerate(meta["names"])}
    cube = np.load(WORK / "features.npy", mmap_mode="r")
    acc = np.zeros(footprint.shape, np.float32)
    cnt = np.zeros(footprint.shape, np.float32)
    for nm in [f"lidar{i:02d}" for i in range(2, 9)] + ["o19_gradmag"]:
        r = FE.rank_normalise(np.asarray(cube[:, :, idx[nm]], np.float32), footprint)
        good = np.isfinite(r)
        acc[good] += r[good]
        cnt[good] += 1
    base = np.where(cnt > 0, acc / np.maximum(cnt, 1), np.nan).astype(np.float32)
    del acc, cnt
    good = np.isfinite(base)
    f = np.full(base.shape, np.nan, np.float32)
    v = np.clip(base[good], 0.0, None) ** SHARPEN
    f[good] = (v / float(v.max())).astype(np.float32)
    del base, v, good

    out: dict = {"frame": "S_matched", "truth_px": int(truth.sum()), "mass": MASS,
                 "lattice_px": LATTICE, "rng_seed": SEED, "runs": {}}
    for name, pool in (("without_exclusion", elig_all),
                       ("with_exclusion", elig_all & ~prior)):
        rng = np.random.default_rng(SEED)
        h, w = f.shape
        bh, bw = h // LATTICE, w // LATTICE
        sub = np.where(pool[: bh * LATTICE, : bw * LATTICE],
                       np.nan_to_num(f[: bh * LATTICE, : bw * LATTICE], nan=-np.inf), -np.inf)
        view = sub.reshape(bh, LATTICE, bw, LATTICE).transpose(0, 2, 1, 3)
        view = view.reshape(bh, bw, LATTICE * LATTICE)
        mx, arg = view.max(axis=2), view.argmax(axis=2)
        flat = mx.ravel()
        bi = np.flatnonzero(np.isfinite(flat))
        vv = flat[bi]
        p = (vv - vv.min()) / (vv.max() - vv.min())
        p = (p + 1e-6) / (p + 1e-6).sum()
        ch = rng.choice(bi, size=MASS, replace=False, p=p)
        br, bc = np.unravel_index(ch, (bh, bw))
        off = arg[br, bc]
        pred = np.zeros(f.shape, bool)
        pred[br * LATTICE + off // LATTICE, bc * LATTICE + off % LATTICE] = True
        parts = evaluate(pred.astype(np.float32), truth)
        ucel = np.flatnonzero(elig_all.ravel())
        uni = []
        for s in range(args.uniform_seeds):
            pick = np.random.default_rng(6100 + 29 * s).choice(ucel, size=MASS, replace=False)
            up = np.zeros(f.shape, bool)
            up.flat[pick] = True
            uni.append(evaluate(up.astype(np.float32), truth).dti)
        um = float(np.mean(uni))
        out["runs"][name] = {
            "eligible_cells": int(pool.sum()),
            "dti": parts.dti, "uniform": um, "lift": parts.dti / um,
            "tp_w": parts.tp_w, "fp_w": parts.fp_w,
            "dots_on_prior_union": int((pred & prior).sum()),
        }
        print(f"{name:18s} elig={int(pool.sum()):,} dti={parts.dti:.5f} lift={parts.dti / um:.3f} "
              f"T={parts.tp_w:.0f} prior_hits={int((pred & prior).sum()):,}")
        del pred

    a = out["runs"]["without_exclusion"]; b = out["runs"]["with_exclusion"]
    out["price"] = {
        "dti_cost": a["dti"] - b["dti"],
        "relative_cost": (a["dti"] - b["dti"]) / a["dti"],
        "dots_moved_off_prior_cells": a["dots_on_prior_union"],
        "truth_credit_lost": a["tp_w"] - b["tp_w"],
        "reading": "the uniqueness guarantee is what moves those dots; the cost above is what "
                   "it buys, measured on the frame that cannot see the hidden labels",
    }
    Path(args.out).write_text(json.dumps(out, indent=1), encoding="utf-8")
    print(f"price of novelty: {out['price']['dti_cost']:.5f} DTI "
          f"({out['price']['relative_cost'] * 100:.2f} %)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
