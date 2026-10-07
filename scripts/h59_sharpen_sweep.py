"""H58 - the sharpening sweep that decides the shipped H59-revision field.

``scripts/h59_field_power_screen.py`` (evidence/h59_field_power_screen.json) found
something large and monotone: raising the frozen evidence blend to the fourth power
before sampling improves the off-catalogue DTI by 21-34 % at *every* mass, and
improves credit per dot by 34 % at 40,000.  The mechanism is not extra smoothing or
extra concentration for its own sake: the frozen field is a NaN-aware **mean** of two
rank transforms, and averaging compresses the top of the distribution exactly where
the decision is made.  Sharpening undoes that compression.

This screen finishes the question the way the repository's H56 session finished it for
its own field - by sweeping the exponent - and adds the two variants that could beat
the incumbent on physical grounds (adding the official slope band, and adding the 3 m
scarp stack).  Everything else is frozen: same frame, same emitter, same seed, same
3 px lattice, same 1 px catalogue buffer, same eligible pool.
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
MASSES = [60_000, 90_000, 120_000]
SEED = 20261007
TRANSFER = 0.887
G_GRID = [8_000, 12_226, 20_000]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(ROOT / "evidence/h59_sharpen_sweep.json"))
    ap.add_argument("--uniform-seeds", type=int, default=3)
    args = ap.parse_args()

    import rasterio
    from scipy import ndimage

    footprint = np.load(WORK / "footprint.npy")
    truth = np.load(WORK / "truth_Smat.npy") & footprint
    with rasterio.open(ROOT / "data/grid/labels.tif") as ds:
        labels = ds.read(1)
    catalogue = labels == 1
    elig = footprint & ~ndimage.binary_dilation(catalogue, np.ones((3, 3), bool))
    pool = np.flatnonzero(elig.ravel())
    print(f"eligible {int(elig.sum()):,} cells; S_matched {int(truth.sum()):,} px")

    meta = json.loads((WORK / "feature_names.json").read_text())
    idx = {n: i for i, n in enumerate(meta["names"])}
    cube = np.load(WORK / "features.npy", mmap_mode="r")

    def rank(nm):
        return FE.rank_normalise(np.asarray(cube[:, :, idx[nm]], np.float32), footprint)

    def rmean(mats):
        acc = np.zeros(footprint.shape, np.float32)
        cnt = np.zeros(footprint.shape, np.float32)
        for q in mats:
            good = np.isfinite(q)
            acc[good] += q[good]
            cnt[good] += 1
        return np.where(cnt > 0, acc / np.maximum(cnt, 1), np.nan).astype(np.float32)

    def sharpen(f, power):
        g = np.isfinite(f)
        out = np.full(f.shape, np.nan, np.float32)
        v = np.clip(f[g], 0.0, None) ** power
        m = float(v.max())
        out[g] = (v / m if m > 0 else v).astype(np.float32)
        return out

    LID = [f"lidar{i:02d}" for i in range(2, 9)]
    S3 = [f"scarp3m{i:02d}" for i in range(1, 8)]
    lid = rmean([rank(n) for n in LID])
    o19g = rank("o19_gradmag")
    o19 = rank("o19_raw")
    base = rmean([lid, o19g])
    scarp = rmean([rank(n) for n in S3])

    cands = {
        "rm(lidar7,o19grad)^2": sharpen(base, 2.0),
        "rm(lidar7,o19grad)^4": sharpen(base, 4.0),
        "rm(lidar7,o19grad)^6": sharpen(base, 6.0),
        "rm(lidar7,o19grad)^8": sharpen(base, 8.0),
        "rm(lidar7,o19,o19grad)^4": sharpen(rmean([lid, o19, o19g]), 4.0),
        "rm(lidar7,scarp3m7,o19grad)^4": sharpen(rmean([lid, scarp, o19g]), 4.0),
    }

    out = {"frame": "S_matched", "truth_px": int(truth.sum()), "eligible_cells": int(elig.sum()),
           "emitter": "3 px block-max lattice, probability proportional to sharpened block maximum",
           "rng_seed": SEED, "transfer": TRANSFER, "G_grid": G_GRID, "fields": {}}
    for name, field in cands.items():
        rng = np.random.default_rng(SEED)
        k = 3
        h, w = field.shape
        bh, bw = h // k, w // k
        sub = np.where(elig[: bh * k, : bw * k],
                       np.nan_to_num(field[: bh * k, : bw * k], nan=-np.inf), -np.inf)
        view = sub.reshape(bh, k, bw, k).transpose(0, 2, 1, 3).reshape(bh, bw, k * k)
        mx, arg = view.max(axis=2), view.argmax(axis=2)
        flat = mx.ravel()
        bi = np.flatnonzero(np.isfinite(flat))
        v = flat[bi]
        p = (v - v.min()) / (v.max() - v.min())
        p = (p + 1e-6) / (p + 1e-6).sum()
        order = rng.choice(bi, size=max(MASSES), replace=False, p=p)
        br, bc = np.unravel_index(order, (bh, bw))
        off = arg[br, bc]
        rr, cc = br * k + off // k, bc * k + off % k

        row = {}
        for n in MASSES:
            pred = np.zeros(field.shape, bool)
            pred[rr[:n], cc[:n]] = True
            parts = evaluate(pred.astype(np.float32), truth)
            uni = []
            for s in range(args.uniform_seeds):
                ur = np.random.default_rng(900 + 13 * s + n)
                pick = ur.choice(pool, size=n, replace=False)
                up = np.zeros(field.shape, bool)
                up.flat[pick] = True
                uni.append(evaluate(up.astype(np.float32), truth).dti)
            um = float(np.mean(uni))
            model = {}
            for G in G_GRID:
                model[str(G)] = min(TRANSFER * parts.tp_w, G) / (0.2 * n + 0.8 * G)
            row[str(n)] = {"dti": parts.dti, "uniform": um, "lift": parts.dti / um,
                           "tp_w": parts.tp_w, "credit_per_dot": parts.tp_w / n,
                           "modelled": model, "modelled_min_over_G": min(model.values())}
            print(f"{name:30s} N={n:7,d} dti={parts.dti:.5f} lift={parts.dti / um:.3f} "
                  f"T/N={parts.tp_w / n:.4f} model_min={min(model.values()):.4f}")
        out["fields"][name] = row
        del field

    best = max(((f, int(n), r[str(n)]["modelled_min_over_G"])
                for f, r in out["fields"].items() for n in MASSES), key=lambda x: x[2])
    out["best"] = {"field": best[0], "mass": best[1], "modelled_min_over_G": best[2]}
    Path(args.out).write_text(json.dumps(out, indent=1), encoding="utf-8")
    print(f"\nbest: {best[0]} @ {best[1]:,} -> {best[2]:.4f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
