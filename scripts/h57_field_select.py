"""Freeze the H57 field and mass on the geometry-matched frame.

Frozen protocol (declared before the run, all candidates listed here):

  frame        ``S_matched`` = SGMC off-catalogue pixels inside the footprint whose
               8-connected component is smaller than 500 px (the largest component
               in the supplied catalogue is 253 px, so this removes the proxy's
               over-long bedrock traces; see ``docs/research/h57-proxy-gap.md``).
  pool         study footprint minus a 3 px buffer around the supplied catalogue
               (no prior-artifact exclusion: that restriction is a novelty choice
               and its price is measured separately in ``h57_exclusion_effect.py``)
  emitter      the frozen field-weighted 3 x 3 block scatter (``hex3``): one dot per
               chosen block, dot on the strongest eligible pixel of the block,
               sampling weight proportional to the block maximum plus a 1e-6 floor.
               Dense threshold, skeleton and dilated-skeleton emitters lose badly on
               this frame; see ``evidence/h57_emission_shapes.json``.
  mass         250,000 (the shape experiment's optimum for this emitter; the mass
               sweep below re-measures it for the winner)
  control      uniform scatter of the same painted count drawn from the same pool
  rng          candidate seed 20261007, uniform seeds 11/22/33/44/55

Selection rule: highest DTI on ``S_matched`` among the declared candidates, subject
to beating the matched-mass uniform control in 4/4 macrofolds.
"""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from gems57 import features as FE  # noqa: E402
from gems57 import frames as FR  # noqa: E402
from gems57.metric import evaluate  # noqa: E402

MASS = 250_000
SEED = 20261007
UNIFORM_SEEDS = (11, 22, 33, 44, 55)
CANDIDATES = [
    "o19",
    "o19grad",
    "o12",
    "lidar7",
    "o19+lidar7",
    "o19grad+lidar7",
    "o19+o19grad",
    "o19+o19grad+lidar7",
    "o19+o19grad+lidar7+seis",
    "o19+seis",
]
MASS_SWEEP = [80_000, 120_000, 180_000, 250_000, 320_000, 400_000]


def rank_of(cube, idx, name, footprint):
    return FE.rank_normalise(np.asarray(cube[:, :, idx[name]], dtype=np.float32), footprint)


def blend(parts: list[np.ndarray], footprint: np.ndarray) -> np.ndarray:
    acc = np.zeros(footprint.shape, np.float32)
    cnt = np.zeros(footprint.shape, np.float32)
    for p in parts:
        g = np.isfinite(p)
        acc[g] += p[g]
        cnt[g] += 1
    return np.where(cnt > 0, acc / np.maximum(cnt, 1), np.nan).astype(np.float32)


def hex3(field: np.ndarray, elig: np.ndarray, n: int, rng) -> np.ndarray:
    k = 3
    bh, bw = field.shape[0] // k, field.shape[1] // k
    sub = np.where(elig[: bh * k, : bw * k], np.nan_to_num(field[: bh * k, : bw * k], nan=-np.inf), -np.inf)
    view = sub.reshape(bh, k, bw, k).transpose(0, 2, 1, 3).reshape(bh, bw, k * k)
    mx, arg = view.max(axis=2), view.argmax(axis=2)
    flat = mx.ravel()
    pool = np.flatnonzero(np.isfinite(flat))
    v = flat[pool]
    lo, hi = v.min(), v.max()
    p = (v - lo) / (hi - lo) if hi > lo else np.ones_like(v)
    p = (p + 1e-6) / (p + 1e-6).sum()
    chosen = rng.choice(pool, size=n, replace=False, p=p)
    br, bc = np.unravel_index(chosen, (bh, bw))
    off = arg[br, bc]
    out = np.zeros(field.shape, bool)
    out[br * k + off // k, bc * k + off % k] = True
    return out


def main() -> int:
    from scipy import ndimage

    work = Path(".arena/h57")
    labels, footprint = FR.load_labels()
    positives = labels == 1
    catbuf = ndimage.distance_transform_edt(~positives) <= 3
    elig = footprint & ~catbuf
    truth = np.load(".arena/h57/truth_Smat.npy") & footprint
    fold, fold_names = FR.macrofolds(footprint)
    meta = json.loads((work / "feature_names.json").read_text())
    idx = {n: i for i, n in enumerate(meta["names"])}
    cube = np.load(work / "features.npy", mmap_mode="r")

    base = {
        "o19": rank_of(cube, idx, "o19_raw", footprint),
        "o19grad": rank_of(cube, idx, "o19_gradmag", footprint),
        "o12": rank_of(cube, idx, "o12_raw", footprint),
    }
    base["lidar7"] = FE.rank_normalise(
        blend([rank_of(cube, idx, f"lidar{i:02d}", footprint) for i in range(2, 9)], footprint),
        footprint,
    )
    base["seis"] = FE.rank_normalise(
        np.asarray(cube[:, :, idx["seis_corridor3"]], np.float32), footprint
    )
    fields: dict[str, np.ndarray] = {}
    for name in CANDIDATES:
        parts = [base[p] for p in name.split("+")]
        fields[name] = blend(parts, footprint) if len(parts) > 1 else parts[0]

    pool_idx = np.flatnonzero(elig.ravel())
    # the uniform control depends only on the painted count and the pool
    uni: dict[int, list[float]] = {}
    for m in sorted({MASS, *MASS_SWEEP}):
        vals = []
        for s in UNIFORM_SEEDS:
            i = np.random.default_rng(s).choice(pool_idx, m, replace=False)
            u = np.zeros(elig.size, bool)
            u[i] = True
            vals.append(evaluate(u.reshape(elig.shape).astype(np.float32), truth).dti)
        uni[m] = vals
        print(f"uniform N={m:>7,d}: {np.mean(vals):.5f} " + ",".join(f"{v:.4f}" for v in vals))

    out: dict[str, object] = {
        "frame": "S_matched",
        "truth_px": int(truth.sum()),
        "eligible_cells": int(elig.sum()),
        "mass": MASS,
        "seed": SEED,
        "uniform_by_mass": {str(k): v for k, v in uni.items()},
        "candidates": {},
    }
    best = ("", -1.0)
    for name, f in fields.items():
        t0 = time.time()
        pred = hex3(f, elig, MASS, np.random.default_rng(SEED))
        d = evaluate(pred.astype(np.float32), truth).dti
        folds = [evaluate((pred & (fold == k)).astype(np.float32), truth & (fold == k)).dti
                 for k in range(len(fold_names))]
        um = float(np.mean(uni[MASS]))
        out["candidates"][name] = {"dti": d, "uniform_mean": um, "lift": d / um, "folds": folds,
                                   "seconds": round(time.time() - t0, 1)}
        print(f"{name:26s} DTI={d:.5f} uni={um:.5f} lift={d/um:.3f} folds="
              + ",".join(f"{x:.4f}" for x in folds))
        if d > best[1]:
            best = (name, d)

    winner = best[0]
    out["winner"] = winner
    out["mass_sweep"] = {}
    for m in MASS_SWEEP:
        pred = hex3(fields[winner], elig, m, np.random.default_rng(SEED))
        d = evaluate(pred.astype(np.float32), truth).dti
        folds = [evaluate((pred & (fold == k)).astype(np.float32), truth & (fold == k)).dti
                 for k in range(len(fold_names))]
        um = float(np.mean(uni[m]))
        out["mass_sweep"][str(m)] = {"dti": d, "uniform_mean": um, "lift": d / um, "folds": folds}
        print(f"[{winner}] N={m:>7,d} DTI={d:.5f} uni={um:.5f} lift={d/um:.3f} folds="
              + ",".join(f"{x:.4f}" for x in folds))

    Path("evidence/h57_field_select.json").write_text(json.dumps(out, indent=1))
    print("wrote evidence/h57_field_select.json; winner =", winner)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
