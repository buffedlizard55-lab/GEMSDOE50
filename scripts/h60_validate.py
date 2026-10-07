#!/usr/bin/env python3
"""H60 validation — pooled whole-map proxy frame, matched controls, and comparators.

The competition metric is pooled over the whole scored domain: one T, one FP mass and one |G|.
`scripts/validate_h56.py` reports the *mean of per-macrofold DTIs*, which is a different
estimator and rewards a candidate for concentrating its dots in truth-dense folds.  This script
reports the pooled estimator as well, on the same F1 truth (USGS SGMC fault pixels more than
300 m from the given catalogue) that the repository's channel screens use, with:

* ``uniform``      - matched-mass uniform scatter inside the same eligible domain, 5 seeds;
* ``translation``  - the candidate's own dots displaced by fixed offsets (geometry control);
* comparators      - any prior artifact on disk, scored with identical code on the identical
                     frame, so the number is comparable.

Usage
-----
    python scripts/h60_validate.py --candidate docs/downloads/<file>.tif \
        --compare docs/downloads/gemsdoe50-h57-scarpstep-80000-20261007T1830Z-allfinite.tif \
        --out evidence/h60_validation.json
"""

from __future__ import annotations

import argparse
import json
import os
import sys

import numpy as np
import rasterio

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from h57_frames import build_frames, load_grid

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
R_PX = 3.0


def pooled(fr, rows, cols) -> dict:
    """Exact pooled metric components for a sparse dot set on a Frame."""
    n = int(rows.size)
    if n == 0:
        return {"dots": 0, "credit": 0.0, "c_per_dot": 0.0, "dti": 0.0, "coverage": 0.0}
    credit = float(np.nansum(fr.K[rows, cols]))
    g = float(fr.n_truth)
    t = min(credit, g)
    dti = t / (0.2 * t + 0.2 * (n - credit) + 0.8 * g)
    return {"dots": n, "credit": credit, "c_per_dot": credit / n, "dti": dti,
            "coverage": t / g}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--candidate", required=True)
    ap.add_argument("--compare", action="append", default=[])
    ap.add_argument("--labels", default="data/grid/labels.tif")
    ap.add_argument("--sgmc", default="data/external/derived_sgmc_faults_100m_u8.tif")
    ap.add_argument("--inputs", default=".arena/inputs")
    ap.add_argument("--out", default="evidence/h60_validation.json")
    ap.add_argument("--seeds", type=int, default=5)
    args = ap.parse_args(argv)

    footprint, catalogue, _, _ = load_grid(args.labels)
    with rasterio.open(args.sgmc) as ds:
        sgmc = ds.read(1) == 1
    lidar_valid = None
    lv = os.path.join(args.inputs, "lidar_scarp_features_u8.tif")
    if os.path.exists(lv):
        with rasterio.open(lv) as ds:
            lidar_valid = ds.read(12) > 0
    frames = build_frames(footprint, catalogue, sgmc, lidar_valid)
    f1 = frames["F1_sgmc_off"]
    base = f1.base_c_per_dot

    def read(path):
        with rasterio.open(path) as ds:
            return ds.read(1) > 0

    cand = read(args.candidate)
    r, c = np.nonzero(cand & f1.domain)
    import hashlib
    with open(args.candidate, "rb") as fh:
        digest = hashlib.sha256(fh.read()).hexdigest()
    res = {"artifact": os.path.basename(args.candidate), "artifact_sha256": digest,
           "frame": "F1_sgmc_off", "frame_truth_px": f1.n_truth,
           "frame_domain_px": f1.domain_px, "uniform_c_per_dot": base,
           "candidate": pooled(f1, r, c), "comparators": {}, "controls": {}}

    res["candidate"]["dots_outside_domain"] = int(cand.sum()) - r.size
    res["candidate"]["lift_over_uniform"] = res["candidate"]["c_per_dot"] / base

    rng = np.random.default_rng(20261007)
    flat = np.flatnonzero(f1.domain.ravel())
    uni = []
    for _ in range(args.seeds):
        pick = rng.choice(flat, size=r.size, replace=False)
        rr, cc = np.unravel_index(pick, f1.domain.shape)
        uni.append(pooled(f1, rr, cc))
    res["controls"]["uniform"] = {
        "dots": r.size,
        "dti_mean": float(np.mean([u["dti"] for u in uni])),
        "dti_max": float(np.max([u["dti"] for u in uni])),
        "c_per_dot_mean": float(np.mean([u["c_per_dot"] for u in uni])),
        "seeds": args.seeds,
    }
    trans = []
    for dr, dc in ((4, 6), (-4, 6), (4, -6), (-4, -6), (9, 0), (0, -9)):
        sh = np.roll(np.roll(cand, dr, axis=0), dc, axis=1)
        rr, cc = np.nonzero(sh & f1.domain)
        trans.append(pooled(f1, rr, cc))
    res["controls"]["translation"] = {
        "dti_mean": float(np.mean([t["dti"] for t in trans])),
        "dti_max": float(np.max([t["dti"] for t in trans])),
        "offsets": [[4, 6], [-4, 6], [4, -6], [-4, -6], [9, 0], [0, -9]],
    }
    for path in args.compare:
        if not os.path.exists(path):
            continue
        arr = read(path)
        rr, cc = np.nonzero(arr & f1.domain)
        p = pooled(f1, rr, cc)
        p["dots_total_in_file"] = int(arr.sum())
        p["lift_over_uniform"] = p["c_per_dot"] / base
        res["comparators"][os.path.basename(path)] = p

    res["summary"] = {
        "candidate_dti": res["candidate"]["dti"],
        "candidate_beats_uniform_mean": res["candidate"]["dti"]
        > res["controls"]["uniform"]["dti_mean"],
        "candidate_beats_uniform_max": res["candidate"]["dti"]
        > res["controls"]["uniform"]["dti_max"],
        "candidate_beats_translation_mean": res["candidate"]["dti"]
        > res["controls"]["translation"]["dti_mean"],
        "note": "Pooled whole-map estimator (the competition's own pooling), F1 proxy truth. "
                "This is not the organizer truth and not a score.",
    }
    os.makedirs(os.path.dirname(args.out) or ".", exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as fh:
        json.dump(res, fh, indent=1)
    print(json.dumps({k: v for k, v in res.items() if k != "comparators"}, indent=1))
    for name, p in res["comparators"].items():
        print(f"  comparator {name}: N={p['dots']} DTI={p['dti']:.4f} "
              f"lift={p['lift_over_uniform']:.2f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
