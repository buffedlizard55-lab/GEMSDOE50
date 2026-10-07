"""Measure what the prior-artifact exclusion costs, on the matched frame.

The frame-geometry screen (``scripts/h59_frame_geometry.py``) drew both the
candidate and the matched-mass uniform control from the same pool
``footprint & ~catalogue_buffer``.  The frozen build added a second restriction --
never on a pixel of the registered prior-artifact positive union, 1,405,451 cells
or 23.4 % of the study footprint.  That is a *novelty* choice, not a rule of the
competition, and this script measures its price.

Both pools are emitted with the identical frozen field, lattice, mass list and
seed, and each candidate is compared with a matched-mass uniform control drawn
from its own pool, so the lift is an apples-to-apples number in both cases.
"""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from gems59 import features as FE  # noqa: E402
from gems59 import frames as FR  # noqa: E402
from gems59.metric import evaluate  # noqa: E402

MASSES = [80_000, 120_000, 180_000, 250_000]
LATTICE = 3
SEED = 20261007
FLOOR_FRAC = 1e-6
UNIFORM_SEEDS = (11, 22, 33)
CACHE = Path(".arena/h59/field_frozen_h59.npy")


def frozen_field(work: Path, footprint: np.ndarray) -> np.ndarray:
    if CACHE.exists():
        return np.load(CACHE)
    meta = json.loads((work / "feature_names.json").read_text())
    idx = {n: i for i, n in enumerate(meta["names"])}
    cube = np.load(work / "features.npy", mmap_mode="r")

    def rank_mean(names_: list[str]) -> np.ndarray:
        acc = np.zeros(footprint.shape, np.float32)
        cnt = np.zeros(footprint.shape, np.float32)
        for n_ in names_:
            r = FE.rank_normalise(np.asarray(cube[:, :, idx[n_]], dtype=np.float32), footprint)
            g = np.isfinite(r)
            acc[g] += r[g]
            cnt[g] += 1
        return np.where(cnt > 0, acc / np.maximum(cnt, 1), np.nan).astype(np.float32)

    lidar7 = rank_mean([f"lidar{i:02d}" for i in range(2, 9)])
    o19g = FE.rank_normalise(np.asarray(cube[:, :, idx["o19_gradmag"]], np.float32), footprint)
    field = np.where(
        np.isfinite(lidar7) & np.isfinite(o19g),
        0.5 * np.nan_to_num(lidar7) + 0.5 * np.nan_to_num(o19g),
        np.nan,
    ).astype(np.float32)
    CACHE.parent.mkdir(parents=True, exist_ok=True)
    np.save(CACHE, field)
    return field


def scatter(field: np.ndarray, elig: np.ndarray, n: int, k: int, rng) -> np.ndarray:
    bh, bw = field.shape[0] // k, field.shape[1] // k
    sub = np.where(
        elig[: bh * k, : bw * k], np.nan_to_num(field[: bh * k, : bw * k], nan=-np.inf), -np.inf
    )
    view = sub.reshape(bh, k, bw, k).transpose(0, 2, 1, 3).reshape(bh, bw, k * k)
    mx, arg = view.max(axis=2), view.argmax(axis=2)
    flat = mx.ravel()
    pool = np.flatnonzero(np.isfinite(flat))
    if len(pool) < n:
        raise SystemExit(f"pool {len(pool)} < mass {n}")
    v = flat[pool]
    lo, hi = v.min(), v.max()
    p = (v - lo) / (hi - lo) if hi > lo else np.ones_like(v)
    p = (p + FLOOR_FRAC) / (p + FLOOR_FRAC).sum()
    chosen = rng.choice(pool, size=n, replace=False, p=p)
    br, bc = np.unravel_index(chosen, (bh, bw))
    off = arg[br, bc]
    out = np.zeros(field.shape, bool)
    out[br * k + off // k, bc * k + off % k] = True
    return out


def main() -> int:
    work = Path(".arena/h59")
    from scipy import ndimage

    labels, footprint = FR.load_labels()
    positives = labels == 1
    catbuf = ndimage.distance_transform_edt(~positives) <= 3
    z = np.load("registry/prior_positive_union.npz")
    shape = tuple(int(x) for x in z["shape"])
    prior = np.unpackbits(z["packed"])[: shape[0] * shape[1]].reshape(shape).astype(bool)

    base = footprint & ~catbuf
    pools = {
        "no_prior_exclusion": base,
        "prior_union_excluded": base & ~prior,
    }
    field = frozen_field(work, footprint)
    truth = np.load(".arena/h59/truth_Smat.npy") if Path(".arena/h59/truth_Smat.npy").exists() else None
    if truth is None:
        t = FR.load_sgmc_offcatalogue()
        lab, _ = ndimage.label(t, structure=np.ones((3, 3), int))
        sizes = np.bincount(lab.ravel())
        sizes[0] = 0
        truth = np.isin(lab, np.flatnonzero((sizes > 0) & (sizes < 500)))
        np.save(".arena/h59/truth_Smat.npy", truth)
    truth_m = truth & footprint

    fold, fold_names = FR.macrofolds(footprint)
    out: dict[str, object] = {
        "frame": "S_matched",
        "truth_px": int(truth_m.sum()),
        "lattice": LATTICE,
        "seed": SEED,
        "pools": {},
    }
    for pname, pool in pools.items():
        rec: dict[str, object] = {"eligible_cells": int(pool.sum()), "masses": {}}
        print(f"--- {pname}: {int(pool.sum())} eligible cells")
        for m in MASSES:
            t0 = time.time()
            pred = scatter(field, pool, m, LATTICE, np.random.default_rng(SEED))
            d = evaluate(pred.astype(np.float32), truth_m).dti
            folds = [evaluate((pred & (fold == k)).astype(np.float32), truth_m & (fold == k)).dti
                     for k in range(len(fold_names))]
            pool_idx = np.flatnonzero(pool.ravel())
            uv = []
            for s in UNIFORM_SEEDS:
                idx = np.random.default_rng(s).choice(pool_idx, m, replace=False)
                u = np.zeros(pool.size, bool)
                u[idx] = True
                uv.append(evaluate(u.reshape(pool.shape).astype(np.float32), truth_m).dti)
            um = float(np.mean(uv))
            rec["masses"][str(m)] = {
                "dti": d,
                "lift": d / um,
                "folds": folds,
                "uniform_mean": um,
                "uniform_values": uv,
                "seconds": round(time.time() - t0, 1),
            }
            print(f"    N={m:>7,d}  DTI={d:.5f}  uniform={um:.5f}  lift={d/um:.3f}  "
                  f"({time.time()-t0:.0f}s)  folds=" + ",".join(f"{x:.4f}" for x in folds))
        out["pools"][pname] = rec

    Path("evidence").mkdir(exist_ok=True)
    Path("evidence/h59_exclusion_effect.json").write_text(json.dumps(out, indent=1))
    print("wrote evidence/h59_exclusion_effect.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
