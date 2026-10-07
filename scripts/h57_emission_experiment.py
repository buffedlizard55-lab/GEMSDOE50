"""H57 experiment 1 - emission geometry and detector-field comparison.

Question under test (from the official metric, transcribed in ``gems57.metric``):

    For unit-height binary predictions the official index reduces exactly to
        DTI = T / ( alpha(|S| - A) + beta|G| + (1 - beta) T )
    where every predicted pixel that lies *on* a truth pixel costs nothing
    (k(0) = 1, so its false-positive weight is 1 - 1 = 0) while every predicted
    pixel more than 300 m from truth costs alpha = 0.2 by itself.

    Consequence: once a trace is believed, painting it *densely* (one pixel of
    line per pixel of trace) captures full credit and pays only the 0.2 N term,
    whereas leaving one-pixel gaps pays the same 0.2 N term for the painted pixels
    and additionally loses 0.33-0.67 of the credit on each gap pixel.  The project's
    earlier H52/H56 doctrine ("emit on a 3-pixel blue-noise lattice") is the
    opposite of this, so it is tested here directly.

Every field and every emitter below is frozen before the numbers are read.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from gems57 import features as FE  # noqa: E402
from gems57 import frames as FR  # noqa: E402
from gems57.metric import evaluate  # noqa: E402

LIDAR_TOP = [1, 2, 3, 4, 5, 6, 7, 8, 9]
SCARP3M_TOP = [3, 4]
MASKS = (20_000, 35_000, 60_000)


def build_fields(cube: np.memmap, names: list[str], footprint: np.ndarray) -> dict[str, np.ndarray]:
    idx = {n: i for i, n in enumerate(names)}

    lidar = np.stack([np.asarray(cube[:, :, idx[f"lidar{i:02d}"]]) for i in LIDAR_TOP])
    with np.errstate(invalid="ignore"):
        lidar_rank = np.nanmean(
            np.stack([FE.rank_normalise(b, footprint) for b in lidar]), axis=0
        ).astype(np.float32)
    del lidar

    scarp = np.stack([np.asarray(cube[:, :, idx[f"scarp3m{i:02d}"]]) for i in SCARP3M_TOP])
    with np.errstate(invalid="ignore"):
        scarp_rank = np.nanmean(
            np.stack([FE.rank_normalise(b, footprint) for b in scarp]), axis=0
        ).astype(np.float32)
    del scarp

    o19 = np.asarray(cube[:, :, idx["o19_raw"]])
    o19_grad = np.asarray(cube[:, :, idx["o19_gradmag"]])
    o19r = FE.rank_normalise(o19, footprint)
    o19g = FE.rank_normalise(o19_grad, footprint)

    seis = np.asarray(cube[:, :, idx["seis_corridor3"]])

    combo = np.nanmean(np.stack([lidar_rank, scarp_rank, o19g]), axis=0).astype(np.float32)

    fields = {
        "lidar_rank": lidar_rank,
        "lidar_sal": FE.structure_tensor_saliency(np.nan_to_num(lidar_rank), 2.0),
        "scarp3m_rank": scarp_rank,
        "o19_rank": o19r,
        "o19grad_rank": o19g,
        "combo_rank": combo,
        "combo_sal": FE.structure_tensor_saliency(np.nan_to_num(combo), 2.0),
        "seis_corridor": seis,
    }
    return fields


def topn(field: np.ndarray, elig: np.ndarray, n: int) -> np.ndarray:
    a = np.where(elig, np.nan_to_num(field, nan=-np.inf), -np.inf)
    flat = a.ravel()
    n = min(n, int(np.isfinite(flat).sum()))
    idx = np.argpartition(flat, -n)[-n:]
    pos = np.zeros(flat.size, bool)
    pos[idx] = True
    pos &= elig.ravel()
    return pos.reshape(field.shape)


def skeleton_emit(field: np.ndarray, elig: np.ndarray, n_seeds: int, width: int) -> np.ndarray:
    """Threshold, skeletonise, optionally widen; mass is reported, not fixed."""
    from skimage.morphology import binary_dilation, disk, skeletonize

    mask = topn(field, elig, n_seeds)
    sk = skeletonize(mask)
    if width > 1:
        sk = binary_dilation(sk, disk(width // 2))
    return sk & elig


def dotted_emit(field: np.ndarray, elig: np.ndarray, n_seeds: int, spacing: int) -> np.ndarray:
    """The H52/H56 doctrine: skeleton then keep one pixel per ``spacing`` block."""
    sk = skeleton_emit(field, elig, n_seeds, 1)
    out = np.zeros_like(sk)
    rr, cc = np.nonzero(sk)
    sel = (rr % spacing == 0) & (cc % spacing == 0)
    out[rr[sel], cc[sel]] = True
    return out


def score(pred: np.ndarray, truth: np.ndarray, footprint: np.ndarray) -> tuple[float, int]:
    p = np.where(footprint & pred, 1.0, 0.0).astype(np.float32)
    return evaluate(p, truth & footprint).dti, int(pred.sum())


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--work", default=".arena/h57")
    ap.add_argument("--out", default="evidence/h57_emission.json")
    ap.add_argument("--folds", action="store_true")
    args = ap.parse_args()
    work = Path(args.work)

    labels, footprint = FR.load_labels()
    positives = labels == 1
    truth_S = FR.load_sgmc_offcatalogue()
    fold, fold_names = FR.macrofolds(footprint)

    from scipy import ndimage

    catbuf = ndimage.distance_transform_edt(~positives) <= 3
    elig = footprint & ~catbuf
    print(f"eligible cells: {int(elig.sum())}")

    meta = json.loads((work / "feature_names.json").read_text())
    cube = np.load(work / "features.npy", mmap_mode="r")
    fields = build_fields(cube, meta["names"], footprint)

    results: dict[str, object] = {"eligible_cells": int(elig.sum()), "fields": {}, "uniform": {}}

    rng = np.random.default_rng(7)
    pool = np.flatnonzero(elig.ravel())
    for n in MASKS:
        u = np.zeros(elig.size, bool)
        u[rng.choice(pool, n, replace=False)] = True
        u = u.reshape(elig.shape)
        results["uniform"][str(n)] = {
            "S": score(u, truth_S, footprint)[0],
            "L": score(u, positives, footprint)[0],
        }
    print("uniform:", json.dumps(results["uniform"], indent=1))

    for fname, field in fields.items():
        entry: dict[str, object] = {"emissions": {}}
        for n in MASKS:
            em = {
                "topn": topn(field, elig, n),
                "skel1": skeleton_emit(field, elig, n, 1),
                "skel3": skeleton_emit(field, elig, n, 3),
                "dotted3": dotted_emit(field, elig, n, 3),
            }
            for ename, pred in em.items():
                d_s, m_s = score(pred, truth_S, footprint)
                d_l, m_l = score(pred, positives, footprint)
                entry["emissions"][f"{ename}@{n}"] = {
                    "mass": m_s,
                    "S": round(d_s, 5),
                    "L": round(d_l, 5),
                }
                if args.folds:
                    entry["emissions"][f"{ename}@{n}"]["S_folds"] = [
                        round(score(pred & (fold == k), truth_S, footprint)[0], 5)
                        for k in range(len(fold_names))
                    ]
        results["fields"][fname] = entry
        print(f"--- {fname} ---")
        for key, val in entry["emissions"].items():
            print(f"   {key:16s} mass={val['mass']:>8d} S={val['S']:.5f} L={val['L']:.5f}")

    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out).write_text(json.dumps(results, indent=1))
    print("wrote", args.out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
