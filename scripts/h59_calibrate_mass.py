"""H59 experiment 4 - mass calibration against the assumed hidden truth size.

The official index is

    DTI = T / ( alpha (N - A) + beta |G| + (1 - beta) T ),   alpha=0.2, beta=0.8

which is *not* scale free in ``N`` and ``|G|``: halving the number of truth pixels
while halving the number of predictions leaves the ratio unchanged only if the
spatial arrangement is otherwise identical.  The instrument available on this
machine has ``|G_S| = 61,664`` truth pixels, while the repository's published
blind-lattice inversion of the owner-reported scores puts the hidden label mass at
``|G_h| ~ 12,226`` pixels.  This experiment measures the optimum emission mass as a
function of ``|G|`` by drawing random subsets of the frame-S truth, which makes the
scaling law measurable rather than assumed.

The output fixes the emission mass used by ``scripts/build_h59.py``.
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

G_TARGETS = [6_000, 12_226, 25_000, 61_664]
MASSES = [15_000, 30_000, 50_000, 80_000, 120_000, 180_000, 250_000, 350_000]
LATTICE = 3
SEEDS = (101, 202, 303)


def scatter(field, elig, n, k, rng, floor_frac=1e-6):
    h, w = field.shape
    bh, bw = h // k, w // k
    sub = np.where(
        elig[: bh * k, : bw * k], np.nan_to_num(field[: bh * k, : bw * k], nan=-np.inf), -np.inf
    )
    view = sub.reshape(bh, k, bw, k).transpose(0, 2, 1, 3).reshape(bh, bw, k * k)
    mx = view.max(axis=2)
    arg = view.argmax(axis=2)
    flat = mx.ravel()
    idx = np.flatnonzero(np.isfinite(flat))
    out = np.zeros_like(elig)
    if len(idx) == 0 or n <= 0:
        return out
    take = min(n, len(idx))
    v = flat[idx]
    lo, hi = v.min(), v.max()
    p = (v - lo) / (hi - lo) if hi > lo else np.ones_like(v)
    p = (p + floor_frac) / (p + floor_frac).sum()
    chosen = rng.choice(idx, size=take, replace=False, p=p)
    br, bc = np.unravel_index(chosen, (bh, bw))
    off = arg[br, bc]
    out[br * k + off // k, bc * k + off % k] = True
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--work", default=".arena/h59")
    ap.add_argument("--out", default="evidence/h59_mass_calibration.json")
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
    field = np.nanmean(np.stack([lidar_top7, o19]), axis=0).astype(np.float32)
    del lidar_top7

    pool = np.flatnonzero(elig.ravel())
    out: dict[str, object] = {"field": "lidar_top7 + o19 rank mean", "lattice": LATTICE, "frames": {}}

    for g_target in G_TARGETS:
        rng_truth = np.random.default_rng(31337)
        sel = rng_truth.choice(np.flatnonzero(truth_S.ravel()), g_target, replace=False)
        truth = np.zeros(truth_S.size, bool)
        truth[sel] = True
        truth = truth.reshape(truth_S.shape)
        rec = {"n_truth": int(truth.sum()), "curves": {}}
        for m in MASSES:
            vals, uvals = [], []
            for s in SEEDS:
                rng = np.random.default_rng(7000 + s + m)
                pred = scatter(field, elig, m, LATTICE, rng)
                vals.append(evaluate(pred.astype(np.float32), truth).dti)
                u = np.zeros(elig.size, bool)
                u[rng.choice(pool, m, replace=False)] = True
                uvals.append(evaluate(u.reshape(elig.shape).astype(np.float32), truth).dti)
            rec["curves"][str(m)] = {
                "field_mean": float(np.mean(vals)),
                "uniform_mean": float(np.mean(uvals)),
                "lift": float(np.mean(vals) / max(np.mean(uvals), 1e-9)),
                "field_values": [round(v, 5) for v in vals],
                "uniform_values": [round(v, 5) for v in uvals],
            }
        best = max(rec["curves"], key=lambda k: rec["curves"][k]["field_mean"])
        rec["best_mass"] = int(best)
        rec["best_dti"] = rec["curves"][best]["field_mean"]
        rec["optimum_flat_top"] = [
            int(k)
            for k in rec["curves"]
            if rec["curves"][k]["field_mean"]
            >= rec["curves"][best]["field_mean"] - 0.005
        ]
        out["frames"][str(g_target)] = rec
        print(
            f"|G|={g_target:>6d}  best mass={best:>7s}  dti={rec['curves'][best]['field_mean']:.5f} "
            f"flat top={rec['optimum_flat_top']}"
        )
        for k in sorted(rec["curves"], key=int):
            c = rec["curves"][k]
            print(f"     N={k:>7s} field={c['field_mean']:.5f} unif={c['uniform_mean']:.5f} lift={c['lift']:.3f}")

    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out).write_text(json.dumps(out, indent=1))
    print("wrote", args.out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
