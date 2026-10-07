"""H59 experiment 5 - mass calibration with component-preserving sparse truth.

Experiment 4 subsampled the frame-S truth *pixel by pixel*.  That destroys the
connectivity that makes a fault map a fault map: a random 20 % of the pixels of a
1 px wide trace is a string of isolated specks, which is far harder to cover than
the trace itself.  The optimum mass it produced is therefore biased high.

This experiment instead selects whole connected components of the frame-S truth
until the target pixel count is reached, so the sparse frame keeps real linear
geometry.  Both instruments are reported; the component-preserving one is the
instrument the shipped mass is frozen on.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from gems59 import features as FE  # noqa: E402
from gems59 import frames as FR  # noqa: E402
from gems59.metric import evaluate  # noqa: E402

MASSES = [30_000, 50_000, 80_000, 120_000, 180_000, 250_000]
SEEDS = (11, 22, 33)
LATTICE = 3


def scatter(field, elig, n, k, rng, floor_frac=1e-6):
    h, w = field.shape
    bh, bw = h // k, w // k
    sub = np.where(
        elig[: bh * k, : bw * k], np.nan_to_num(field[: bh * k, : bw * k], nan=-np.inf), -np.inf
    )
    view = sub.reshape(bh, k, bw, k).transpose(0, 2, 1, 3).reshape(bh, bw, k * k)
    mx, arg = view.max(axis=2), view.argmax(axis=2)
    flat = mx.ravel()
    idx = np.flatnonzero(np.isfinite(flat))
    out = np.zeros_like(elig)
    if len(idx) == 0:
        return out
    v = flat[idx]
    lo, hi = v.min(), v.max()
    p = (v - lo) / (hi - lo) if hi > lo else np.ones_like(v)
    p = (p + floor_frac) / (p + floor_frac).sum()
    chosen = rng.choice(idx, size=min(n, len(idx)), replace=False, p=p)
    br, bc = np.unravel_index(chosen, (bh, bw))
    off = arg[br, bc]
    out[br * k + off // k, bc * k + off % k] = True
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--work", default=".arena/h59")
    ap.add_argument("--out", default="evidence/h59_mass_calibration_components.json")
    args = ap.parse_args()
    work = Path(args.work)

    labels, footprint = FR.load_labels()
    positives = labels == 1
    truth_S = FR.load_sgmc_offcatalogue()
    from scipy import ndimage

    catbuf = ndimage.distance_transform_edt(~positives) <= 3
    elig = footprint & ~catbuf

    meta = json.loads((work / "feature_names.json").read_text())
    idx = {n: i for i, n in enumerate(meta["names"])}
    cube = np.load(work / "features.npy", mmap_mode="r")

    def rank_mean(names_):
        acc = np.zeros(footprint.shape, np.float32)
        cnt = np.zeros(footprint.shape, np.float32)
        for n_ in names_:
            r = FE.rank_normalise(np.asarray(cube[:, :, idx[n_]], dtype=np.float32), footprint)
            g = np.isfinite(r)
            acc[g] += r[g]
            cnt[g] += 1
        return np.where(cnt > 0, acc / np.maximum(cnt, 1), np.nan).astype(np.float32)

    lidar_top7 = rank_mean([f"lidar{i:02d}" for i in [2, 3, 4, 5, 6, 7, 8]])
    o19 = FE.rank_normalise(np.asarray(cube[:, :, idx["o19_raw"]], dtype=np.float32), footprint)
    field = np.where(
        np.isfinite(lidar_top7) & np.isfinite(o19),
        0.5 * np.nan_to_num(lidar_top7) + 0.5 * np.nan_to_num(o19),
        np.nan,
    ).astype(np.float32)
    del lidar_top7

    # component-preserving sparse truth
    lab, ncomp = ndimage.label(truth_S, structure=np.ones((3, 3), int))
    sizes = np.bincount(lab.ravel())
    order = np.argsort(sizes)[::-1]
    comps = [c for c in order if c != 0]
    rng = np.random.default_rng(2024)
    rng.shuffle(comps)
    cum, chosen = 0, []
    for c in comps:
        if cum >= 12_226:
            break
        chosen.append(c)
        cum += int(sizes[c])
    truth = np.isin(lab, chosen)
    print(f"component-preserving truth: {ncomp} components total, "
          f"{len(chosen)} used, {int(truth.sum())} px, mean comp size {cum/len(chosen):.1f}")

    pool = np.flatnonzero(elig.ravel())
    out = {
        "field": "lidar_top7 + o19 rank mean",
        "lattice": LATTICE,
        "truth_px": int(truth.sum()),
        "n_components_used": len(chosen),
        "curves": {},
    }
    for m in MASSES:
        vals, uvals = [], []
        for s in SEEDS:
            rng2 = np.random.default_rng(5000 + s + m)
            pred = scatter(field, elig, m, LATTICE, rng2)
            vals.append(evaluate(pred.astype(np.float32), truth).dti)
            u = np.zeros(elig.size, bool)
            u[rng2.choice(pool, m, replace=False)] = True
            uvals.append(evaluate(u.reshape(elig.shape).astype(np.float32), truth).dti)
        out["curves"][str(m)] = {
            "field_mean": float(np.mean(vals)),
            "uniform_mean": float(np.mean(uvals)),
            "lift": float(np.mean(vals) / max(np.mean(uvals), 1e-9)),
        }
        print(f"  N={m:>7d} field={np.mean(vals):.5f} unif={np.mean(uvals):.5f} lift={np.mean(vals)/max(np.mean(uvals),1e-9):.3f}")

    best = max(out["curves"], key=lambda k: out["curves"][k]["field_mean"])
    out["best_mass"] = int(best)
    out["flat_top_within_0.005"] = [
        int(k)
        for k in out["curves"]
        if out["curves"][k]["field_mean"] >= out["curves"][best]["field_mean"] - 0.005
    ]
    print("best mass:", best, "flat top:", out["flat_top_within_0.005"])

    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out).write_text(json.dumps(out, indent=1))
    print("wrote", args.out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
