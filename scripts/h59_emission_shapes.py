"""Emission-shape experiment on the geometry-matched frame.

Theory.  With unit-height binary predictions the official metric reduces to

    DTI = T / (0.2 (P - A) + 0.8 G + 0.2 T)

where ``P`` is the number of painted pixels, ``A = sum_x k(d(x, G))`` is the
dot-side credit and ``T = sum_g max_x k(d(x, g))`` the truth-side credit.  A
painted pixel that sits exactly on a truth pixel adds 0.2 to the numerator and
nothing to ``P - A``: duplicates are free.  A 3 px gap between painted pixels
therefore costs roughly 0.22 of the truth-side credit (the kernel is 1, 2/3, 1/3,
0 at distance 0, 1, 2, 3) without saving any false-positive mass.  The repository's
"3 px blue noise" doctrine assumed the opposite, so this script measures it.

Emitters compared at matched *painted-pixel* count on the same field:
  * ``hex3``   -- the frozen 1-dot-per-3x3-block field-weighted scatter
  * ``dense``  -- the top-P pixels of the field, painted as they come (blobs)
  * ``skel``   -- skeleton (1 px wide) of the thresholded field
  * ``skel3``  -- that skeleton dilated by one pixel (3 px wide corridors)
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

MASSES = [60_000, 120_000, 250_000, 400_000]
SEED = 20261007
CACHE = Path(".arena/h59/field_frozen_h59.npy")


def fields(work: Path, footprint: np.ndarray) -> dict[str, np.ndarray]:
    meta = json.loads((work / "feature_names.json").read_text())
    idx = {n: i for i, n in enumerate(meta["names"])}
    cube = np.load(work / "features.npy", mmap_mode="r")
    out = {
        "o19_rank": FE.rank_normalise(np.asarray(cube[:, :, idx["o19_raw"]], np.float32), footprint),
        "o12_rank": FE.rank_normalise(np.asarray(cube[:, :, idx["o12_raw"]], np.float32), footprint),
        "o19grad_rank": FE.rank_normalise(
            np.asarray(cube[:, :, idx["o19_gradmag"]], np.float32), footprint
        ),
    }
    return out


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


def top_p_mask(field: np.ndarray, elig: np.ndarray, p: int) -> np.ndarray:
    """Paint the P highest-field eligible pixels."""
    vals = np.where(elig, np.nan_to_num(field, nan=-np.inf), -np.inf).ravel()
    pool = np.flatnonzero(np.isfinite(vals))
    if p > pool.size:
        raise SystemExit(f"top_p {p} > pool {pool.size}")
    v = vals[pool]
    thr = np.partition(v, v.size - p)[v.size - p]
    return elig & (field >= thr)


def main() -> int:
    from scipy import ndimage
    from skimage.morphology import skeletonize

    work = Path(".arena/h59")
    labels, footprint = FR.load_labels()
    positives = labels == 1
    catbuf = ndimage.distance_transform_edt(~positives) <= 3
    elig = footprint & ~catbuf
    truth = np.load(".arena/h59/truth_Smat.npy") & footprint
    fold, fold_names = FR.macrofolds(footprint)
    fs = fields(work, footprint)
    pool_idx = np.flatnonzero(elig.ravel())

    out: dict[str, object] = {"frame": "S_matched", "truth_px": int(truth.sum()),
                              "eligible_cells": int(elig.sum()), "runs": {}}
    for fname, field in fs.items():
        for variant in ("hex3", "dense", "skel", "skel3", "skel_cat1"):
            for p in MASSES:
                t0 = time.time()
                el = elig
                if variant == "skel_cat1":
                    el = footprint & ~(ndimage.distance_transform_edt(~positives) <= 1)
                if variant == "hex3":
                    pred = hex3(field, el, p, np.random.default_rng(SEED))
                else:
                    m = top_p_mask(field, el, p)
                    if variant in ("skel", "skel_cat1"):
                        pred = skeletonize(m)
                    elif variant == "skel3":
                        pred = ndimage.binary_dilation(skeletonize(m), np.ones((3, 3), bool))
                    else:
                        pred = m
                n = int(pred.sum())
                d = evaluate(pred.astype(np.float32), truth).dti
                uv = []
                for s in (11, 22, 33):
                    idx = np.random.default_rng(s).choice(pool_idx, n, replace=False)
                    u = np.zeros(elig.size, bool)
                    u[idx] = True
                    uv.append(evaluate(u.reshape(elig.shape).astype(np.float32), truth).dti)
                um = float(np.mean(uv))
                folds = [evaluate((pred & (fold == k)).astype(np.float32), truth & (fold == k)).dti
                         for k in range(len(fold_names))]
                key = f"{fname}|{variant}|{p}"
                out["runs"][key] = {"painted": n, "dti": d, "uniform_mean": um,
                                    "lift": d / um, "folds": folds,
                                    "seconds": round(time.time() - t0, 1)}
                print(f"{fname:13s} {variant:10s} req={p:>7,d} painted={n:>7,d} "
                      f"DTI={d:.5f} uni={um:.5f} lift={d/um:.3f} ({time.time()-t0:.0f}s)")
    Path("evidence/h59_emission_shapes.json").write_text(json.dumps(out, indent=1))
    print("wrote evidence/h59_emission_shapes.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
