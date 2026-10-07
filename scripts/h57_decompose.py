"""Decompose the gap between the frozen-build score and the selection screen.

The selection screen (scripts/h57_final_select.py) reported S_matched DTI 0.21994
at N=180,000 while the built artifact reads 0.17990 under the same truth.  Two
candidate causes: (a) the eligibility pool (catalogue buffer 0 vs 1, prior-artifact
union excluded or not) and (b) a difference in how the field is assembled -- the
screen re-ranks the LiDAR rank-mean before the 50/50 mix, the builder does not.

This script emits the four combinations and prints the truth-side credit so the
gap is attributed rather than guessed.
"""
from __future__ import annotations
import json, sys
from pathlib import Path
import numpy as np
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from gems57 import features as FE
from gems57 import frames as FR
from gems57.metric import evaluate

SEED = 20261007
N = 180_000

def rank_of(cube, i, name, fp):
    return FE.rank_normalise(np.asarray(cube[:, :, i[name]], np.float32), fp)

def rmean(parts, fp):
    acc = np.zeros(fp.shape, np.float32); cnt = np.zeros(fp.shape, np.float32)
    for p in parts:
        g = np.isfinite(p); acc[g] += p[g]; cnt[g] += 1
    return np.where(cnt > 0, acc / np.maximum(cnt, 1), np.nan).astype(np.float32)

def hex3(field, elig, n, rng, k=3):
    bh, bw = field.shape[0] // k, field.shape[1] // k
    sub = np.where(elig[: bh*k, : bw*k], np.nan_to_num(field[: bh*k, : bw*k], nan=-np.inf), -np.inf)
    view = sub.reshape(bh, k, bw, k).transpose(0, 2, 1, 3).reshape(bh, bw, k*k)
    mx, arg = view.max(axis=2), view.argmax(axis=2)
    flat = mx.ravel(); pool = np.flatnonzero(np.isfinite(flat))
    v = flat[pool]; lo, hi = v.min(), v.max()
    p = (v - lo) / (hi - lo) if hi > lo else np.ones_like(v)
    p = (p + 1e-6) / (p + 1e-6).sum()
    ch = rng.choice(pool, size=n, replace=False, p=p)
    br, bc = np.unravel_index(ch, (bh, bw)); off = arg[br, bc]
    out = np.zeros(field.shape, bool); out[br*k + off//k, bc*k + off%k] = True
    return out

def main():
    from scipy import ndimage
    work = Path(".arena/h57")
    labels, fp = FR.load_labels(); pos = labels == 1
    d = ndimage.distance_transform_edt(~pos)
    z = np.load("registry/prior_positive_union.npz"); shp = tuple(int(x) for x in z["shape"])
    prior = np.unpackbits(z["packed"])[: shp[0]*shp[1]].reshape(shp).astype(bool)
    truth = np.load(".arena/h57/truth_Smat.npy") & fp
    meta = json.loads((work / "feature_names.json").read_text()); idx = {n: i for i, n in enumerate(meta["names"])}
    cube = np.load(work, mmap_mode="r") if False else np.load(work / "features.npy", mmap_mode="r")
    o19g = rank_of(cube, idx, "o19_gradmag", fp)
    lidar_raw = rmean([rank_of(cube, idx, f"lidar{i:02d}", fp) for i in range(2, 9)], fp)
    lidar_rerank = FE.rank_normalise(lidar_raw, fp)
    fields = {"A_builder_no_rerank": rmean([o19g, lidar_raw], fp),
              "B_screen_rerank": rmean([o19g, lidar_rerank], fp)}
    pools = {"p0_buf0_noprior": fp & (d > 0),
             "p1_buf1_noprior": fp & (d > 1),
             "p2_buf1_prior":  fp & (d > 1) & ~prior}
    res = {}
    for fn, f in fields.items():
        for pn, pool in pools.items():
            pred = hex3(f, pool, N, np.random.default_rng(SEED))
            parts = evaluate(pred.astype(np.float32), truth)
            res[f"{fn}|{pn}"] = {"dti": parts.dti, "tp_w": parts.tp_w, "fp_w": parts.fp_w,
                                 "fn_w": parts.fn_w, "eligible": int(pool.sum()),
                                 "prior_hits": int((pred & prior).sum())}
            print(f"{fn:22s} {pn:18s} elig={int(pool.sum()):>9,d} DTI={parts.dti:.5f} "
                  f"TPw={parts.tp_w:7.0f} FPw={parts.fp_w:7.0f}")
    Path("evidence/h57_decompose.json").write_text(json.dumps(res, indent=1))
    print("wrote evidence/h57_decompose.json")

if __name__ == "__main__":
    raise SystemExit(main())
