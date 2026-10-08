"""H59 experiment 8 - which field, at which mass, under the transfer model.

The H56 diagnosis (``docs/research/h56-diagnosis.md``) established two things this
script takes seriously:

* the repository's best-supported forward model of the hidden leaderboard is
  ``DTI_hidden(N) = min(a * T_proxy(N), G) / (0.2 N + 0.8 G)`` with a per-dot credit
  transfer ``a = 0.887`` (measured, eight artifacts, band 0.79-0.92) and
  ``G = 12,226`` px (the blind-lattice inversion);
* a *sharpened* detector beat a smoothed one monotonically on H56's own field.

H59 froze a field (NaN-aware rank mean of the LiDAR scarp stack and the official
band-19 slope edge) and a mass (180,000, by minimax regret against the matched
frame's own optimum).  Neither was chosen against the transfer model.  This screen
finishes the job: seven fields, five masses, one emitter, one frame, and the
transfer model as the decision rule, with the proxy DTI reported alongside so the
two readings can be compared instead of conflated.

Masses are nested prefixes of a single draw, so the curves are paired rather than
independently sampled and the comparison between masses is not confounded by draw
noise.
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
LATTICE = 3
RNG_SEED = 20261007
MASSES = [40_000, 60_000, 90_000, 120_000, 180_000]
G_HIDDEN = 12_226          # px, blind-lattice inversion (docs/research/h51-analysis.md)
TRANSFER = 0.887           # hidden credit per dot / matched-frame credit per dot
TRANSFER_LO, TRANSFER_HI = 0.79, 0.92
G_GRID = [8_000, 12_226, 20_000]
FLOOR_FRAC = 1e-6


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(ROOT / "evidence/h59_field_power_screen.json"))
    ap.add_argument("--seeds", type=int, default=2)
    args = ap.parse_args()

    import rasterio

    footprint = np.load(WORK / "footprint.npy")
    truth = np.load(WORK / "truth_Smat.npy") & footprint
    with rasterio.open(ROOT / "data/grid/labels.tif") as ds:
        labels = ds.read(1)
    catalogue = labels == 1

    # 1 px catalogue buffer, exactly as the frozen build (staff ruling R5)
    from scipy import ndimage

    near_cat = ndimage.binary_dilation(catalogue, np.ones((3, 3), bool))
    elig = footprint & ~near_cat
    print(f"eligible blocks pool {int(elig.sum()):,} cells; frame S_matched {int(truth.sum()):,} px")

    meta = json.loads((WORK / "feature_names.json").read_text())
    idx = {n: i for i, n in enumerate(meta["names"])}
    cube = np.load(WORK / "features.npy", mmap_mode="r")

    def rank(nm: str) -> np.ndarray:
        return FE.rank_normalise(np.asarray(cube[:, :, idx[nm]], np.float32), footprint)

    def rank_mean(names: list[str]) -> np.ndarray:
        acc = np.zeros(footprint.shape, np.float32)
        cnt = np.zeros(footprint.shape, np.float32)
        for nm in names:
            r = rank(nm)
            good = np.isfinite(r)
            acc[good] += r[good]
            cnt[good] += 1
        return np.where(cnt > 0, acc / np.maximum(cnt, 1), np.nan).astype(np.float32)

    def sharpen(f: np.ndarray, power: float) -> np.ndarray:
        g = np.isfinite(f)
        out = np.full(f.shape, np.nan, np.float32)
        v = np.clip(f[g], 0.0, None) ** power
        m = float(v.max())
        out[g] = (v / m if m > 0 else v).astype(np.float32)
        return out

    LID = [f"lidar{i:02d}" for i in range(2, 9)]
    print("building fields ...")
    lid7 = rank_mean(LID)
    o19g = rank("o19_gradmag")

    def rank_mean_of(parts):
        acc = np.zeros(footprint.shape, np.float32)
        cnt = np.zeros(footprint.shape, np.float32)
        for q in parts:
            good = np.isfinite(q)
            acc[good] += q[good]
            cnt[good] += 1
        return np.where(cnt > 0, acc / np.maximum(cnt, 1), np.nan).astype(np.float32)

    base = rank_mean_of([lid7, o19g])          # the frozen H59 field
    fields = {
        "frozen_rm(l7,o19g)": base,
        "o19_raw": rank("o19_raw"),
        "o19_sal_s4": rank("o19_sal_s4"),
        "o12_sal_s2": rank("o12_sal_s2"),
        "lidar_rankmean": rank("lidar_rankmean"),
        "rm(l7,o19g)_4": sharpen(base, 4.0),
        "rm(l7,o19raw,o12raw)": rank_mean_of([lid7, rank("o19_raw"), rank("o12_raw")]),
    }

    pool = np.flatnonzero(elig.ravel())
    results: dict[str, dict] = {}
    for name, field in fields.items():
        rng = np.random.default_rng(RNG_SEED)
        k = LATTICE
        h, w = field.shape
        bh, bw = h // k, w // k
        sub = np.where(
            elig[: bh * k, : bw * k],
            np.nan_to_num(field[: bh * k, : bw * k], nan=-np.inf),
            -np.inf,
        )
        view = sub.reshape(bh, k, bw, k).transpose(0, 2, 1, 3).reshape(bh, bw, k * k)
        mx, arg = view.max(axis=2), view.argmax(axis=2)
        flat = mx.ravel()
        block_idx = np.flatnonzero(np.isfinite(flat))
        if len(block_idx) < max(MASSES):
            raise SystemExit(f"{name}: only {len(block_idx)} eligible blocks")
        v = flat[block_idx]
        lo, hi = v.min(), v.max()
        p = (v - lo) / (hi - lo) if hi > lo else np.ones_like(v)
        p = (p + FLOOR_FRAC) / (p + FLOOR_FRAC).sum()
        order = rng.choice(block_idx, size=max(MASSES), replace=False, p=p)
        br_all, bc_all = np.unravel_index(order, (bh, bw))
        off_all = arg[br_all, bc_all]
        rr_all, cc_all = br_all * k + off_all // k, bc_all * k + off_all % k

        row: dict = {"masses": {}}
        for n in MASSES:
            pred = np.zeros(field.shape, bool)
            pred[rr_all[:n], cc_all[:n]] = True
            parts = evaluate(pred.astype(np.float32), truth)
            uni = []
            for s in range(args.seeds):
                ur = np.random.default_rng(1000 + 7 * s + n)
                pick = ur.choice(pool, size=n, replace=False)
                up = np.zeros(field.shape, bool)
                up.flat[pick] = True
                uni.append(evaluate(up.astype(np.float32), truth).dti)
            u_mean = float(np.mean(uni))
            t = parts.tp_w
            cred_per_dot = t / n
            model = {}
            for G in G_GRID:
                th = min(TRANSFER * t, G)
                model[str(G)] = th / (0.2 * n + 0.8 * G)
            row["masses"][str(n)] = {
                "dti_matched_frame": parts.dti,
                "uniform_matched_pool_mean": u_mean,
                "lift": parts.dti / u_mean if u_mean else None,
                "tp_w": t,
                "fp_w": parts.fp_w,
                "credit_per_dot": cred_per_dot,
                "modelled_hidden_dti": model,
                "modelled_hidden_dti_min_over_G": min(model.values()),
            }
            print(
                f"{name:26s} N={n:7,d} dti={parts.dti:.5f} uni={u_mean:.5f} "
                f"lift={parts.dti / u_mean:.3f} T/N={cred_per_dot:.4f} "
                f"model={min(model.values()):.4f}"
            )
        results[name] = row
        del field

    best = max(
        ((f, int(n), r["masses"][n]["modelled_hidden_dti_min_over_G"])
         for f, r in results.items() for n in r["masses"]),
        key=lambda x: x[2],
    )
    best_proxy = max(
        ((f, int(n), r["masses"][n]["dti_matched_frame"])
         for f, r in results.items() for n in r["masses"]),
        key=lambda x: x[2],
    )
    payload = {
        "frame": "S_matched (SGMC off-catalogue, components < 500 px)",
        "truth_px": int(truth.sum()),
        "eligible_cells": int(elig.sum()),
        "emitter": "3 px block-max lattice, probability proportional to block maximum",
        "rng_seed": RNG_SEED,
        "masses": MASSES,
        "transfer_model": {
            "credit_per_dot_transfer": TRANSFER,
            "band": [TRANSFER_LO, TRANSFER_HI],
            "G_hidden_px": G_HIDDEN,
            "G_grid": G_GRID,
            "source": "docs/research/h56-diagnosis.md sections 5 and 6",
            "caveat": "an assumption calibrated on the repository's own detector family, "
                      "not on H59's field; a 20 % error moves the modelled value by ~0.05",
        },
        "fields": results,
        "best_by_transfer_model": {"field": best[0], "mass": best[1], "modelled_dti": best[2]},
        "best_by_proxy_dti": {"field": best_proxy[0], "mass": best_proxy[1], "dti": best_proxy[2]},
    }
    out = Path(args.out)
    out.write_text(json.dumps(payload, indent=1), encoding="utf-8")
    print(f"\nbest by transfer model : {best[0]} @ {best[1]:,} -> {best[2]:.4f}")
    print(f"best by proxy DTI      : {best_proxy[0]} @ {best_proxy[1]:,} -> {best_proxy[2]:.5f}")
    print(f"wrote {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
