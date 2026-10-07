"""H57 experiment 3 - select the field, emission mass and lattice on frame S.

Emitter under test: **field-weighted blue-noise scatter**.  The footprint is
tiled with k x k pixel blocks; each block is offered with probability
proportional to the field's maximum inside it; the dot sits on the strongest
eligible pixel of the chosen block.  One dot per block guarantees that no two
dots are closer than k px, and k = 3 is the metric's own support R.

Round 2 fixes the p = 0 sampling defect of round 1 (blocks with zero belief are
given a small floor so that ``numpy.random.Generator.choice`` can always draw the
requested number of blocks) and reports fold-wise consistency.
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

MASSES = [80_000, 160_000, 250_000, 400_000]
UNIFORM_SEEDS = (11, 12, 13, 14, 15)


def dti(mask, truth, footprint):
    return evaluate((mask & footprint).astype(np.float32), truth & footprint).dti


def scatter(field, elig, n, k, rng, floor_frac=1e-6):
    h, w = field.shape
    bh, bw = h // k, w // k
    sub = np.where(elig[: bh * k, : bw * k], np.nan_to_num(field[: bh * k, : bw * k], nan=-np.inf), -np.inf)
    blocks = sub.reshape(bh, k, bw, k)
    view = blocks.transpose(0, 2, 1, 3).reshape(bh, bw, k * k)
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
    p = p + floor_frac
    p = p / p.sum()
    chosen = rng.choice(idx, size=take, replace=False, p=p)
    br, bc = np.unravel_index(chosen, (bh, bw))
    off = arg[br, bc]
    rr = br * k + off // k
    cc = bc * k + off % k
    out[rr, cc] = True
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--work", default=".arena/h57")
    ap.add_argument("--out", default="evidence/h57_select.json")
    args = ap.parse_args()
    work = Path(args.work)

    labels, footprint = FR.load_labels()
    positives = labels == 1
    truth_S = FR.load_sgmc_offcatalogue()
    fold, fold_names = FR.macrofolds(footprint)
    from scipy import ndimage

    catbuf = ndimage.distance_transform_edt(~positives) <= 3
    elig = footprint & ~catbuf

    meta = json.loads((work / "feature_names.json").read_text())
    idx = {n: i for i, n in enumerate(meta["names"])}
    cube = np.load(work / "features.npy", mmap_mode="r")
    col = lambda name: np.asarray(cube[:, :, idx[name]], dtype=np.float32)  # noqa: E731

    def rank_mean(names_):
        acc = np.zeros(footprint.shape, np.float32)
        cnt = np.zeros(footprint.shape, np.float32)
        for n_ in names_:
            r = FE.rank_normalise(col(n_), footprint)
            g = np.isfinite(r)
            acc[g] += r[g]
            cnt[g] += 1
        return np.where(cnt > 0, acc / np.maximum(cnt, 1), np.nan).astype(np.float32)

    LIDAR_TOP = [f"lidar{i:02d}" for i in [2, 3, 4, 5, 6, 7, 8]]
    fields = {
        "lidar02": FE.rank_normalise(col("lidar02"), footprint),
        "lidar07": FE.rank_normalise(col("lidar07"), footprint),
        "lidar_top7": rank_mean(LIDAR_TOP),
        "lidar_all9": rank_mean([f"lidar{i:02d}" for i in range(1, 10)]),
        "o19_rank": FE.rank_normalise(col("o19_raw"), footprint),
    }
    fields["lidar_o19"] = np.nanmean(
        np.stack([fields["lidar_top7"], fields["o19_rank"]]), axis=0
    ).astype(np.float32)
    fields["lidar_o19_scarp3m"] = np.nanmean(
        np.stack([fields["lidar_top7"], fields["o19_rank"], rank_mean(["scarp3m03", "scarp3m04"])]),
        axis=0,
    ).astype(np.float32)
    fields["lidar_o19_seis"] = np.nanmean(
        np.stack(
            [
                fields["lidar_top7"],
                fields["o19_rank"],
                0.5 * FE.rank_normalise(col("seis_corridor3"), footprint),
            ]
        ),
        axis=0,
    ).astype(np.float32)

    pool = np.flatnonzero(elig.ravel())
    uniform = {}
    for m in MASSES:
        vals = []
        for s in UNIFORM_SEEDS:
            rng = np.random.default_rng(9000 + s)
            u = np.zeros(elig.size, bool)
            u[rng.choice(pool, m, replace=False)] = True
            vals.append(dti(u.reshape(elig.shape), truth_S, footprint))
        uniform[m] = {"mean": float(np.mean(vals)), "values": [round(v, 5) for v in vals]}

    out: dict[str, object] = {"uniform": uniform, "fields": {}}
    print("uniform:", json.dumps({str(k): round(v["mean"], 5) for k, v in uniform.items()}))

    for fname, field in fields.items():
        rec = {}
        for k in (3,):
            for m in MASSES:
                rng = np.random.default_rng(555 + m)
                pred = scatter(field, elig, m, k, rng)
                d = dti(pred, truth_S, footprint)
                folds = [dti(pred & (fold == i), truth_S, footprint) for i in range(len(fold_names))]
                rec[f"k{k}@{m}"] = {
                    "mass": int(pred.sum()),
                    "S": round(d, 5),
                    "uniform_mean": uniform[m]["mean"],
                    "lift": round(d / max(uniform[m]["mean"], 1e-9), 4),
                    "S_folds": [round(x, 5) for x in folds],
                }
                print(f"{fname:22s} k{k}@{m:<7d} mass={pred.sum():>7d} S={d:.5f} unif={uniform[m]['mean']:.5f} lift={d/max(uniform[m]['mean'],1e-9):.3f} folds={[round(x,4) for x in folds]}")
        out["fields"][fname] = rec
        del field

    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out).write_text(json.dumps(out, indent=1))
    print("wrote", args.out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
