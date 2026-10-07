#!/usr/bin/env python3
"""H60 arms — which belief field, at which mass, is the best *measured* emitter?

The repository has already established two things by measurement:

1. the metric collapses to ``DTI = T / (0.2 N + 0.8 G)`` for dots >= 3 px apart, so a further
   dot pays only while its expected credit exceeds ``alpha s / (1 - alpha s)`` (0.0588 at
   ``s = 0.2778``); and
2. every shipped artifact family re-ranks the *same* terrain (LiDAR scarp / 10 m topographic
   step) evidence, which is why the corpus's dotted artifacts all capture T ~ 5.2 k and
   plateau at 0.26-0.28.

This script compares four arms on identical machinery and identical truth frames:

``A_morph``      the H57 recipe (LiDAR scarp family + 10 m topographic family) - the
                 repository's best-measured field, reproduced from its own source code;
``B_official``   the H60 field: official-stack channels only, four physical families
                 (detrended topography, magnetics via the `tc` derivative, isostatic gravity,
                 geodetic dilatation-rate ridge), every channel measured at >= 1.85 stratified
                 lift with 5/5 elevation strata won;
``C_union``      ``A_morph`` emitted first, then ``B_official`` on the cells at least 3 px away
                 from every accepted dot - an *independent-family* union, which is the only
                 way to buy credit the morphology family cannot reach;
``D_official_topo_union``  as C but the official topography family first.

Selection rule for the shipped artifact: highest **model-mean** hidden DTI, with the F1 frame
reported beside it so the reader can see the disagreement between the two proxies.

Usage
-----
    python scripts/h60_arms.py --inputs .arena/inputs --out evidence/h60_arms.json
"""

from __future__ import annotations

import argparse
import json
import math
import os
import sys
import time

import numpy as np
import rasterio
from scipy import ndimage as ndi

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from build_h57 import belief_field as morph_field
from build_h57 import metric_emit
from h57_frames import build_frames, load_grid
from h60_sweep import G_HAT, MODEL_BOTH, MODEL_MASS, hidden_dti
from h60_sweep import belief_field as official_field

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_MASSES = (25000, 37654, 50000, 65000, 80000)


def emit_excluding(belief, eligible, mass, excluded, block=3, spacing=3):
    """``metric_emit`` with an extra mask: never accept a cell within ``spacing`` of
    an already-accepted dot *or* of any cell in ``excluded``."""
    elig = eligible & ~excluded
    return metric_emit(belief, elig, mass, block=block, spacing=spacing)


def score_frame(fr, sel, n_total):
    credit = float(np.nansum(fr.K[sel]))
    t = min(credit, float(fr.n_truth))
    dti = t / (0.2 * t + 0.2 * (n_total - credit) + 0.8 * fr.n_truth) if n_total else 0.0
    return credit, dti


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--inputs", default=".arena/inputs")
    ap.add_argument("--labels", default="data/grid/labels.tif")
    ap.add_argument("--sgmc", default="data/external/derived_sgmc_faults_100m_u8.tif")
    ap.add_argument("--out", default="evidence/h60_arms.json")
    ap.add_argument("--belief-a", default=".arena/h60_beliefA.npy")
    ap.add_argument("--belief-b", default=".arena/h60_belief.npy")
    ap.add_argument("--masses", default=",".join(str(m) for m in DEFAULT_MASSES))
    args = ap.parse_args(argv)
    masses = [int(x) for x in args.masses.split(",")]

    t0 = time.time()
    footprint, catalogue, _, _ = load_grid(args.labels)
    d_cat = ndi.distance_transform_edt(~catalogue)
    eligible = footprint & (d_cat > 3.0)

    def cached(path, builder):
        if os.path.exists(path):
            print(f"  cached {path}")
            return np.load(path)
        b = builder()
        np.save(path, b)
        return b

    field_a = cached(args.belief_a, lambda: morph_field(args.inputs, footprint)[0])
    field_b = cached(args.belief_b, lambda: official_field(args.inputs, footprint)[0])

    with rasterio.open(args.sgmc) as ds:
        sgmc = ds.read(1) == 1
    with rasterio.open(os.path.join(args.inputs, "lidar_scarp_features_u8.tif")) as ds:
        lidar_valid = ds.read(12) > 0
    f1 = build_frames(footprint, catalogue, sgmc, lidar_valid)["F1_sgmc_off"]
    base = f1.base_c_per_dot

    rows = []
    for n in masses:
        arms = {}
        sel_a = metric_emit(field_a, eligible, n)
        arms["A_morph"] = sel_a
        sel_b = metric_emit(field_b, eligible, n)
        arms["B_official"] = sel_b
        # C: morphology first, then the official field on cells >= 3 px from A's dots
        # Chebyshev radius 2 => the union keeps >= 3 px separation across both fields
        blocked_a = ndi.binary_dilation(sel_a, structure=np.ones((3, 3), bool), iterations=2)
        arms["C_union"] = sel_a | metric_emit(field_b, eligible & ~blocked_a, n)
        # D: official topography family first is not separated here (B already aggregates it);
        # this arm instead throttles the union to a total 1.5 n
        sel_b2 = metric_emit(field_b, eligible & ~blocked_a, int(n // 2))
        arms["D_union_half"] = sel_a | sel_b2
        for name, sel in arms.items():
            got = int(sel.sum())
            credit, dti_f1 = score_frame(f1, sel, got)
            h_f1 = credit / got if got else 0.0
            h_mass = math.exp(MODEL_MASS["a"]) * got ** MODEL_MASS["p"]
            h_both = MODEL_BOTH["a"] + MODEL_BOTH["b"] * h_f1 + MODEL_BOTH["c"] * math.log(got)
            rows.append({
                "arm": name, "requested_mass": n, "dots": got,
                "F1_credit": credit, "F1_c_per_dot": h_f1, "F1_lift": h_f1 / base,
                "F1_dti": dti_f1,
                "hidden_dti_mass_model": hidden_dti(got, h_mass),
                "hidden_dti_both_model": hidden_dti(got, h_both),
                "hidden_dti_model_mean": 0.5 * (hidden_dti(got, h_mass)
                                                + hidden_dti(got, h_both)),
            })
            del sel
        del sel_a, sel_b, sel_b2, blocked_a

    rows.sort(key=lambda r: -r["hidden_dti_model_mean"])
    rep = {
        "generated_utc": time.strftime("%Y%m%dT%H%M%SZ", time.gmtime()),
        "frame": "F1_sgmc_off", "frame_uniform_c_per_dot": base,
        "G_hat": G_HAT,
        "models": {"mass": MODEL_MASS, "both": MODEL_BOTH},
        "rows": rows,
        "best_by_model_mean": [r for r in rows[:6]],
        "caveat": "The hidden-DTI columns are arithmetic under models fitted to 21 owner-reported "
                  "anchors (transfer r2 negative); they are not scores and not measurements. "
                  "F1 is a proxy frame built from the State Geologic Map Compilation, not the "
                  "organizer truth.",
        "seconds": round(time.time() - t0, 1),
    }
    os.makedirs(os.path.dirname(args.out) or ".", exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as fh:
        json.dump(rep, fh, indent=1)
    print(f"\n{'arm':16s} {'N':>8s} {'F1 lift':>8s} {'F1 DTI':>8s} {'hid(mass)':>10s} "
          f"{'hid(both)':>10s} {'mean':>7s}")
    for r in rows[:12]:
        print(f"{r['arm']:16s} {r['dots']:8d} {r['F1_lift']:8.2f} {r['F1_dti']:8.4f} "
              f"{r['hidden_dti_mass_model']:10.3f} {r['hidden_dti_both_model']:10.3f} "
              f"{r['hidden_dti_model_mean']:7.3f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
