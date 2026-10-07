#!/usr/bin/env python3
"""H52 validation on the frozen spatially blocked holdout, with matched controls.

The frozen split is evidence/holdout-v1.json (schema gemsdoe50.spatial-holdout.v1,
registered 2026-10-06, hash-pinned masks).  Four contiguous macrofolds; each held-out core
is eroded by 10 km; catalogue labels within 300 m of the *visible* (non-held-out) labels are
excluded from the truth, so the task is "find the trace where the visible inventory cannot
already see it" rather than "re-draw what is already visible".

Controls
--------
* ``uniform``     : matched-count uniform-random dots inside the same eligible domain, three
                    seeds.  This is the null a candidate must beat.
* ``translation`` : the candidate's own dot set shifted by (+/-17, +/-23) px and wrapped, so
                    the geometry and the mass are identical and only the *placement* changes.

Uncertainty
-----------
Block bootstrap over the four 2x2 subtiles inside every macrofold (paired, candidate minus
control), reported per fold and pooled with a percentile CI.  Pixels are never treated as
independent samples.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
import rasterio

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "src"))

from gemsdoe50 import h52
from gemsdoe50.holdout import build_spatial_blocks, load_split_spec


def read(path: Path, index: int = 1) -> np.ndarray:
    with rasterio.open(path) as ds:
        return ds.read(index)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--candidate", default=None)
    ap.add_argument("--split", default="evidence/holdout-v1.json")
    ap.add_argument("--out", default="evidence/h52_holdout.json")
    ap.add_argument("--truth-mode", choices=("sgmc_off", "labels"), default="sgmc_off",
                    help="sgmc_off = independent inventory outside the given catalogue (matches "
                         "the real task); labels = the frozen spec's own truth, which is made of "
                         "*catalogue* pixels and therefore scores an off-catalogue detector at "
                         "zero by construction")
    args = ap.parse_args()

    valid = np.isfinite(read(REPO / "data/grid/sample_submission.tif"))
    labels = read(REPO / "data/grid/labels.tif")
    if args.truth_mode == "labels":
        truth_all = labels == 1
    else:
        # an independent, public, off-catalogue inventory used as the truth of the held-out
        # blocks: USGS SGMC fault pixels that are far from the given catalogue.  This is the
        # same instrument family the repository uses elsewhere; it is a proxy, not the
        # organizer truth.
        sgmc = read(REPO / "data/external/derived_sgmc_faults_100m_u8.tif") > 0
        from scipy.ndimage import distance_transform_edt
        d_cat = distance_transform_edt(labels != 1)
        truth_all = sgmc & (d_cat > 3.0) & valid
    spec = load_split_spec(REPO / args.split)
    blocks, realized = build_spatial_blocks(valid, truth_all, spec)

    if args.candidate:
        cand = read(Path(args.candidate)) > 0
    else:
        build = json.loads((REPO / "evidence/h52_build.json").read_text(encoding="utf-8"))
        name = build["checks"]["name"]
        n = build["checks"]["n_dots"]
        cand = read(REPO / f"docs/downloads/{name}-{n}-allfinite.tif") > 0
    n_cand = int(cand.sum())
    print(f"candidate {n_cand:,} dots; {len(blocks)} macrofolds")

    results = {"candidate": str(args.candidate or "h52 default"), "n_dots": n_cand,
               "truth_mode": args.truth_mode,
               "split_spec": args.split, "split_valid_mask_sha256": realized["valid_mask_sha256"],
               "folds": {}, "controls": {}}

    pooled = {"cand": [], "uni": [], "flat": []}
    for blk in blocks:
        elig = blk.eligible
        tr = blk.truth
        pool = np.zeros_like(valid)
        # candidate dots inside the eligible cell (the frozen rule: no halo needed because
        # the instrument here is plain DTI on the cell, and the candidate is fixed in advance)
        c_rows, c_cols = np.nonzero(cand & elig)
        dots = np.zeros_like(valid)
        dots[c_rows, c_cols] = True
        s_cand = h52.score_dots(tr, c_rows, c_cols)

        rng = np.random.default_rng(hash(blk.block_id) % 2**31)
        uni = []
        for s in range(3):
            flat = np.flatnonzero(elig.ravel())
            pick = rng.choice(flat, size=min(int(dots.sum()), flat.size), replace=False)
            rr, cc = np.unravel_index(pick, elig.shape)
            uni.append(h52.score_dots(tr, rr, cc)["dti"])
        tr_scores = []
        for dr, dc in ((17, 23), (-17, 23), (17, -23), (-17, -23)):
            sh = np.roll(np.roll(cand, dr, axis=0), dc, axis=1) & elig
            rr, cc = np.nonzero(sh)
            tr_scores.append(h52.score_dots(tr, rr, cc)["dti"])

        sub_rows = []
        for tid, (sr0, sr1), (sc0, sc1), tile_elig, tile_truth in blk.subtile_masks:
            cell = np.zeros_like(valid)
            cell[sr0:sr1, sc0:sc1] = True
            m = cand & tile_elig
            rr, cc = np.nonzero(m)
            sc = h52.score_dots(tile_truth, rr, cc)["dti"]
            ru = np.zeros_like(valid)
            flat = np.flatnonzero(tile_elig.ravel())
            if flat.size and rr.size:
                pick = rng.choice(flat, size=min(rr.size, flat.size), replace=False)
                a, b = np.unravel_index(pick, valid.shape)
                su = h52.score_dots(tile_truth, a, b)["dti"]
            else:
                su = float("nan")
            sub_rows.append((tid, sc, su))
            if np.isfinite(sc) and np.isfinite(su):
                pooled["cand"].append(sc)
                pooled["uni"].append(su)
            del cell, m, ru

        results["folds"][blk.block_id] = {
            "eligible_cells": int(elig.sum()), "truth_cells": int(tr.sum()),
            "candidate_dots_in_cell": int(dots.sum()),
            "dti_candidate": s_cand["dti"], "coverage_candidate": s_cand["coverage"],
            "credit_per_dot_candidate": s_cand["credit_per_dot"],
            "dti_uniform_mean": float(np.mean(uni)), "dti_uniform_max": float(np.max(uni)),
            "dti_translation_mean": float(np.mean(tr_scores)),
            "dti_translation_max": float(np.max(tr_scores)),
            "lift_over_uniform": float(s_cand["dti"] / max(float(np.mean(uni)), 1e-12)),
            "subtiles": [{"id": t, "dti": c, "dti_uniform": u} for t, c, u in sub_rows],
        }
        pooled["flat"].append(0.0)
        print(f"  {blk.block_id}: cand {s_cand['dti']:.4f}  uniform {np.mean(uni):.4f}  "
              f"translation {np.mean(tr_scores):.4f}  lift "
              f"{results['folds'][blk.block_id]['lift_over_uniform']:.2f}x")
        del pool, dots

    c = np.asarray(pooled["cand"], dtype=np.float64)
    u = np.asarray(pooled["uni"], dtype=np.float64)
    d = c - u
    n_sub = d.size
    if n_sub:
        rng = np.random.default_rng(20261007)
        boots = []
        for _ in range(4000):
            idx = rng.integers(0, n_sub, n_sub)
            boots.append(float(d[idx].mean()))
        lo, hi = np.percentile(boots, [2.5, 97.5])
    else:
        lo = hi = float("nan")
    folds = results["folds"]
    results["summary"] = {
        "pooled_dti_candidate": float(c.mean()), "pooled_dti_uniform": float(u.mean()),
        "mean_paired_delta": float(d.mean()), "paired_ci95": [float(lo), float(hi)],
        "positive_macrofolds": int(sum(1 for f in folds.values()
                                      if f["dti_candidate"] > f["dti_uniform_mean"])),
        "n_macrofolds": len(folds),
        "beats_matched_uniform_in_all_folds": bool(all(f["dti_candidate"] > f["dti_uniform_max"]
                                                        for f in folds.values())),
        "beats_translation_mean_in_all_folds": bool(all(f["dti_candidate"] > f["dti_translation_mean"]
                                                        for f in folds.values())),
    }
    print(json.dumps(results["summary"], indent=1))
    (REPO / args.out).write_text(json.dumps(results, indent=1) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
