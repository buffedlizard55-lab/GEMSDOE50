#!/usr/bin/env python3
"""Frozen spatially blocked holdout for the H52 submission.

Reconstructs the frozen four-macrofold split (``evidence/holdout-v1.json``,
schema ``gemsdoe50.spatial-holdout.v1``) and scores the shipped artifact inside each held-out
fold against two controls computed at matched mass inside the same fold:

* **uniform** -- a blue-noise emission at the same separation and the same count, drawn on the
  fold's eligible mask, three seeds;
* **translation** -- the candidate's own dots displaced by a fixed pixel offset that keeps them
  inside the fold, which controls for the possibility that any dense dot field helps.

The uncertainty is a **block bootstrap over the fold's 2x2 subtiles** (the units the split was
designed around), never over pixels.

Truth here is the held-out catalogue itself, so a candidate that deliberately never places a dot
inside any visible-catalogue pixel scores exactly 0.0000 by construction -- that is a property of
this instrument, not a result, and the off-catalogue instrument
(``scripts/validate_h52.py --truth-mode sgmc_off``) is the one that can move.  Both are recorded.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

import numpy as np
import rasterio

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "src"))
from gemsdoe50 import h52
from gemsdoe50.holdout import build_spatial_blocks, load_split_spec

R_PX = 3.0


def read(path: Path) -> np.ndarray:
    with rasterio.open(path) as ds:
        return ds.read(1)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--split", default="evidence/holdout-v1.json")
    ap.add_argument("--submission", default=None,
                    help="defaults to the artifact recorded in evidence/h52_build.json")
    ap.add_argument("--seeds", default="11,12,13")
    ap.add_argument("--translations", type=int, default=4)
    ap.add_argument("--n-boot", type=int, default=2000)
    ap.add_argument("--out", default="evidence/h52_holdout.json")
    args = ap.parse_args()

    build = json.loads((REPO / "evidence/h52_build.json").read_text(encoding="utf-8"))
    name = build["checks"]["name"]
    n = build["checks"]["n_dots"]
    sub = Path(args.submission) if args.submission else \
        REPO / f"docs/downloads/{name}-{n}-allfinite.tif"
    with rasterio.open(sub) as ds:
        cand = ds.read(1) > 0
    lab = read(REPO / "data/grid/labels.tif")
    spec = load_split_spec(REPO / args.split)
    blocks, meta = build_spatial_blocks(lab >= 0, lab == 1, spec)
    print(f"{sub.name}: {int(cand.sum()):,} dots; "
          f"{len(blocks)} macrofolds; split sha {meta.get('split_spec_sha256', '?')[:16]}")

    rng = np.random.default_rng(5207)
    rows = []
    for blk in blocks:
        elig = blk.eligible
        t = blk.truth
        cr = np.argwhere(cand & elig)
        n_fold = int(cr.shape[0])
        if n_fold == 0 or not t.any():
            continue
        # score inside the fold's own bounding box: score_dots builds a full-grid distance
        # transform, so running it on 3730 x 3292 per bootstrap draw costs minutes per fold for
        # no change in the estimand.
        rr0, rr1 = (max(blk.rows[0] - 4, 0), min(blk.rows[1] + 4, t.shape[0]))
        cc0, cc1 = (max(blk.cols[0] - 4, 0), min(blk.cols[1] + 4, t.shape[1]))
        sub_t = t[rr0:rr1, cc0:cc1]
        s_c = h52.score_dots(sub_t, cr[:, 0] - rr0, cr[:, 1] - cc0)
        sub_elig = elig[rr0:rr1, cc0:cc1]
        uni = []
        for sd in (int(x) for x in args.seeds.split(",")):
            u = h52.emit_blue_noise(np.ones(sub_elig.shape), sub_elig, n_target=n_fold,
                                    min_sep_px=R_PX, seed=sd)
            uni.append(h52.score_dots(sub_t, u.rows, u.cols))
        tr_ = []
        for k in range(int(args.translations)):
            d = 17 * (k + 1)
            rr = (cr[:, 0] + d) % t.shape[0]
            cc = (cr[:, 1] + (2 * d)) % t.shape[1]
            keep = elig[rr, cc]
            if keep.sum() == 0:
                continue
            tr_.append(h52.score_dots(sub_t, rr[keep] - rr0, cc[keep] - cc0))

        # Paired block bootstrap over the fold's 2x2 subtiles.  The uniform reference is
        # resampled with the same subtile draw, so the difference is paired by construction --
        # re-emitting a uniform field inside the loop would make this O(n_boot) full-grid
        # emissions and would not change the estimand.
        u = h52.emit_blue_noise(np.ones(sub_elig.shape), sub_elig, n_target=n_fold,
                                min_sep_px=R_PX, seed=99991)
        sub_idx = []
        for _, _, _, sub_m, _tr_m in blk.subtile_masks:
            small = np.asarray(sub_m)[rr0:rr1, cc0:cc1]
            idx = np.flatnonzero(small.reshape(-1))
            if idx.size:
                sub_idx.append(idx)
        deltas = []
        for _ in range(int(args.n_boot)):
            if not sub_idx:
                break
            pick = rng.integers(0, len(sub_idx), size=len(sub_idx))
            boot = np.zeros(sub_t.size, bool)
            for j in pick:
                boot[sub_idx[j]] = True
            boot = boot.reshape(sub_t.shape)
            ck = boot[cr[:, 0] - rr0, cr[:, 1] - cc0]
            uk = boot[u.rows, u.cols]
            if ck.sum() == 0 or uk.sum() == 0:
                continue
            sc = h52.score_dots(sub_t, cr[ck, 0] - rr0, cr[ck, 1] - cc0)["dti"]
            su = h52.score_dots(sub_t, u.rows[uk], u.cols[uk])["dti"]
            deltas.append(sc - su)
        deltas = np.asarray(deltas, dtype=float)
        rows.append({
            "fold": blk.block_id, "n_dots_in_fold": n_fold,
            "candidate_dti": s_c["dti"],
            "uniform_mean": float(np.mean([x["dti"] for x in uni])),
            "uniform_draws": [float(x["dti"]) for x in uni],
            "uniform_max": float(np.max([x["dti"] for x in uni])),
            "translation_mean": float(np.mean([x["dti"] for x in tr_])) if tr_ else None,
            "paired_delta_mean": float(deltas.mean()) if deltas.size else None,
            "paired_ci95": [float(np.percentile(deltas, 2.5)),
                            float(np.percentile(deltas, 97.5))] if deltas.size > 20 else None,
            "beats_uniform_mean": bool(s_c["dti"] > np.mean([x["dti"] for x in uni])),
            "beats_uniform_max": bool(s_c["dti"] > np.max([x["dti"] for x in uni])),
            "beats_translation_mean": bool(tr_ and s_c["dti"] > np.mean([x["dti"] for x in tr_])),
            "truth_px": int(t.sum()), "eligible_px": int(elig.sum()),
        })
        print(f"  {blk.block_id:4s} cand {s_c['dti']:.4f}  uniform "
              f"{rows[-1]['uniform_mean']:.4f}  translation "
              f"{rows[-1]['translation_mean'] if rows[-1]['translation_mean'] is None else round(rows[-1]['translation_mean'], 4)}"
              f"  n={n_fold}")

    pos = sum(1 for r in rows if r["beats_uniform_mean"])
    pooled_d = float(np.mean([r["paired_delta_mean"] for r in rows])) if rows else None
    payload = {
        "artifact": sub.name, "sha256": hashlib.sha256(sub.read_bytes()).hexdigest(),
        "split_spec": args.split, "split_spec_sha256": hashlib.sha256(
            (REPO / args.split).read_bytes()).hexdigest(),
        "instrument": "frozen four-macrofold spatial holdout; truth = held-out catalogue labels",
        "note": "A detector that never places a dot inside a visible-catalogue pixel scores 0.0000 "
                "on this instrument by construction; that is a property of the split, not a result. "
                "The off-catalogue instrument is scripts/validate_h52.py --truth-mode sgmc_off.",
        "folds": rows,
        "summary": {
            "n_macrofolds": len(rows),
            "positive_macrofolds": pos,
            "pooled_candidate": float(np.mean([r["candidate_dti"] for r in rows])) if rows else None,
            "pooled_uniform": float(np.mean([r["uniform_mean"] for r in rows])) if rows else None,
            "mean_paired_delta": pooled_d,
            "beats_uniform_in_all_folds": bool(rows and all(r["beats_uniform_mean"] for r in rows)),
            "beats_translation_in_all_folds": bool(rows and all(
                r["beats_translation_mean"] for r in rows)),
        },
    }
    (REPO / args.out).write_text(json.dumps(payload, indent=1) + "\n", encoding="utf-8")
    print(json.dumps(payload["summary"], indent=1))
    print("wrote", args.out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
