"""H57 experiment 6 - geometry-matched off-catalogue frame.

Why this exists
---------------
The supplied catalogue is the only public object that is drawn with the same
cartographic conventions as the hidden target (``labels.tif`` = the USGS/INGENIOUS
fault compilation that the competition hands out).  Its connected-component
statistics are therefore the best available model of the *geometry* of the expert
labels that will be scored.  This script measures those statistics, compares them
with the off-catalogue proxy frame, and rebuilds the proxy frame so that its
component sizes are drawn from the same regime.  Field selection and mass
calibration are then re-run on that matched frame.
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

ST = np.ones((3, 3), int)
MASSES = [40_000, 80_000, 120_000, 180_000, 250_000]
SEEDS = (7, 8, 9)
LATTICE = 3
MAX_COMPONENT_PX = 500  # largest component in the supplied catalogue is < 500 px


def size_classes(lab: np.ndarray) -> dict[str, np.ndarray]:
    sizes = np.bincount(lab.ravel())
    out = {}
    for name, lo, hi in [
        ("small_lt50", 1, 50),
        ("med_50_199", 50, 200),
        ("huge_ge200", 200, 10**9),
    ]:
        labels_in_class = np.flatnonzero((sizes >= lo) & (sizes < hi))
        out[name] = np.isin(lab, labels_in_class)
    return out


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
    ap.add_argument("--work", default=".arena/h57")
    ap.add_argument("--out", default="evidence/h57_frame_geometry.json")
    args = ap.parse_args()
    work = Path(args.work)

    labels, footprint = FR.load_labels()
    positives = labels == 1
    truth_S = FR.load_sgmc_offcatalogue()
    from scipy import ndimage

    catbuf = ndimage.distance_transform_edt(~positives) <= 3
    elig = footprint & ~catbuf

    lab_L, n_L = ndimage.label(positives, structure=ST)
    lab_S, n_S = ndimage.label(truth_S, structure=ST)
    szL = np.bincount(lab_L.ravel())
    szL[0] = 0
    szS = np.bincount(lab_S.ravel())
    szS[0] = 0

    def hist(sz):
        s = sz[sz > 0]
        return {
            "components": int(len(s)),
            "pixels": int(s.sum()),
            "median_px": float(np.median(s)),
            "p90_px": float(np.quantile(s, 0.9)),
            "p99_px": float(np.quantile(s, 0.99)),
            "ge500_components": int((s >= 500).sum()),
            "frac_px_ge200": float(s[s >= 200].sum() / s.sum()),
            "frac_px_lt200": float(s[s < 200].sum() / s.sum()),
        }

    geo = {
        "labels_provided": hist(szL),
        "sgmc_offcatalogue_raw": hist(szS),
        "max_component_px_used_for_matching": MAX_COMPONENT_PX,
    }
    print("geometry:", json.dumps(geo, indent=1))

    # geometry-matched proxy: drop proxy components at or above the largest
    # component ever drawn in the supplied catalogue.
    keep = np.flatnonzero((szS > 0) & (szS < MAX_COMPONENT_PX))
    truth_Smat = np.isin(lab_S, keep)
    geo["sgmc_offcatalogue_matched"] = hist(np.bincount(lab_S[truth_Smat].ravel()))

    classes_S = size_classes(lab_S)
    classes_L = size_classes(lab_L)

    meta = json.loads((work / "feature_names.json").read_text())
    idx = {n: i for i, n in enumerate(meta["names"])}
    cube = np.load(work / "features.npy", mmap_mode="r")
    col = lambda nm: np.asarray(cube[:, :, idx[nm]], dtype=np.float32)  # noqa: E731

    def rank_mean(names_):
        acc = np.zeros(footprint.shape, np.float32)
        cnt = np.zeros(footprint.shape, np.float32)
        for n_ in names_:
            r = FE.rank_normalise(col(n_), footprint)
            g = np.isfinite(r)
            acc[g] += r[g]
            cnt[g] += 1
        return np.where(cnt > 0, acc / np.maximum(cnt, 1), np.nan).astype(np.float32)

    fields = {
        "lidar_top7": rank_mean([f"lidar{i:02d}" for i in [2, 3, 4, 5, 6, 7, 8]]),
        "o19_rank": FE.rank_normalise(col("o19_raw"), footprint),
        "o19grad_rank": FE.rank_normalise(col("o19_gradmag"), footprint),
        "seis_corridor": col("seis_corridor3"),
    }
    fields["lidar_o19"] = np.where(
        np.isfinite(fields["lidar_top7"]) & np.isfinite(fields["o19_rank"]),
        0.5 * np.nan_to_num(fields["lidar_top7"]) + 0.5 * np.nan_to_num(fields["o19_rank"]),
        np.nan,
    ).astype(np.float32)

    pool = np.flatnonzero(elig.ravel())
    out: dict[str, object] = {"geometry": geo, "matched_frame_px": int(truth_Smat.sum()), "curves": {}}

    print("\n--- field curve on the geometry-matched frame ---")
    for fname, field in fields.items():
        rec = {}
        for m in MASSES:
            fv, uv = [], []
            for s in SEEDS:
                rng = np.random.default_rng(31000 + s + m)
                pred = scatter(field, elig, m, LATTICE, rng)
                fv.append(evaluate(pred.astype(np.float32), truth_Smat).dti)
                u = np.zeros(elig.size, bool)
                u[rng.choice(pool, m, replace=False)] = True
                uv.append(evaluate(u.reshape(elig.shape).astype(np.float32), truth_Smat).dti)
            rec[str(m)] = {
                "field_mean": float(np.mean(fv)),
                "uniform_mean": float(np.mean(uv)),
                "lift": float(np.mean(fv) / max(np.mean(uv), 1e-9)),
            }
        out["curves"][fname] = rec
        line = "  ".join(f"{m}:{rec[str(m)]['field_mean']:.4f}/{rec[str(m)]['lift']:.3f}" for m in MASSES)
        print(f"{fname:16s} {line}")

    # size-class detail for the frozen field at three masses, on the raw frame
    print("\n--- size-class lift, raw frame, field = lidar_o19 ---")
    det = {}
    for m in (60_000, 120_000, 250_000):
        rng = np.random.default_rng(777 + m)
        pred = scatter(fields["lidar_o19"], elig, m, LATTICE, rng)
        u = np.zeros(elig.size, bool)
        u[rng.choice(pool, m, replace=False)] = True
        u = u.reshape(elig.shape)
        det[str(m)] = {}
        for cname, cmask in classes_S.items():
            df = evaluate(pred.astype(np.float32), cmask).dti
            du = evaluate(u.astype(np.float32), cmask).dti
            det[str(m)][cname] = {
                "px": int(cmask.sum()),
                "field": round(df, 5),
                "uniform": round(du, 5),
                "lift": round(df / max(du, 1e-9), 3),
            }
        print(f"  N={m}: " + "  ".join(
            f"{k}={v['lift']:.3f}" for k, v in det[str(m)].items()))
    out["size_class_detail"] = det
    out["label_size_class_share"] = {
        name: round(float(mask.sum()) / float(positives.sum()), 4)
        for name, mask in classes_L.items()
    }

    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out).write_text(json.dumps(out, indent=1))
    print("wrote", args.out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
