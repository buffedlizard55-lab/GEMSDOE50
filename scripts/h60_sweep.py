#!/usr/bin/env python3
"""H60 deliberation — mass sweep on the official-stack belief field.

The repository's closed-form and fitted models say the competitive lever is **not** the size of
an emitter but the *credit per dot*: with binary dots at >= 3 px separation the official metric
collapses to ``DTI = T / (0.2 N + 0.8 G)``, and a further dot pays only if its expected credit
exceeds ``alpha * s / (1 - alpha * s)`` (0.0588 at s = 0.2778).

This script measures, for the H60 official-stack belief field:

* ``F1`` frame credit per dot and exact DTI at each requested mass (measured);
* the *modelled* hidden DTI at each mass under the two models fitted in
  ``evidence/h57_hidden_model.json`` on the 21 owner-reported score anchors (modelled, not
  measured - the hidden labels are not available to anyone outside the organizer).

Nothing here is a score claim.  The sweep exists so the shipped mass is chosen by a stated rule
instead of by taste.

Usage
-----
    python scripts/h60_sweep.py --inputs .arena/inputs --out evidence/h60_sweep.json
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

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from h57_frames import build_frames, load_grid
from h60_screen import CHANNELS  # noqa: F401  (documentation of the screened set)

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

#: Belief-field specification.  Membership is decided by `evidence/h60_screen.json`: each
#: entry is an official-stack channel and an operator, and every entry below measured
#: (a) a stratified lift >= 1.85 against the F1 proxy and (b) 5/5 elevation strata won.
#: The measured lifts are recorded beside each entry.
#:
#: Deliberately absent: every raw magnetic amplitude channel (0.50-0.98), every raw geodetic
#: channel (0.28-0.38), the shipped gradient products `iso_grav_anom_hg`/`_vg`/`_slope`
#: (0.31-0.73 under the same test) and `depth_to_base_surf` in every operator (0.33-1.18).
FAMILIES = {
    "official_topography": [("raw", "det_elev"), ("raw", "det_elev_slope"),
                            ("grad", "det_elev_slope"), ("ridge2", "det_elev_slope")],
    "official_magnetics": [("grad", "tc"), ("ridge2", "tc")],
    "official_gravity": [("raw", "iso_grav_anom")],
    "official_geodesy": [("ridge2", "geod_dilaterate")],
}
MEASURED_LIFTS = {
    "raw::det_elev": 2.193, "raw::det_elev_slope": 2.198, "grad::det_elev_slope": 2.064,
    "ridge2::det_elev_slope": 1.877, "grad::tc": 1.969, "ridge2::tc": 1.491,
    "raw::iso_grav_anom": 1.909, "ridge2::geod_dilaterate": 1.887,
}
#: fitted in evidence/h57_hidden_model.json on 21 owner-reported anchors
MODEL_MASS = {"form": "h = exp(a) * N**p", "a": 4.7618681848226645, "p": -0.6709233268544545,
              "r2": 0.5148654742410103}
MODEL_BOTH = {"form": "h = a + b*F1_c_per_dot + c*ln N", "a": 0.5305166674464777,
              "b": -0.16688318131690957, "c": -0.03898323221976038, "r2": 0.6510543342410142}
G_HAT = 14088.75

DEFAULT_MASSES = (15000, 25000, 37654, 50000, 65000, 80000, 100000, 130000)


def hidden_dti(n_dots: int, h: float, g: float = G_HAT) -> float:
    """Modelled hidden DTI for ``n_dots`` dots at hidden credit per dot ``h``."""
    t = n_dots * h
    return t / (0.2 * n_dots + 0.8 * g)


def read_channel(inputs: str, key: str, name: str, operator: str) -> np.ndarray:
    """One official-stack channel with one operator applied (NaN-safe)."""
    from h57_screen import TRANSFORMS
    path = {
        "tf": "training_features.tif", "lidar": "lidar_scarp_features_u8.tif",
        "topo": "topo_u8.tif", "rad": "radiometric_u8.tif",
        "grad": "geodawn_rad_u8.tif", "gext": "geodawn_extensions_u8.tif",
    }[key]
    with rasterio.open(os.path.join(inputs, path)) as ds:
        descs = [(d.split(" - ")[0].strip() if d else f"band{i}")
                 for i, d in enumerate(ds.descriptions, 1)]
        raw = ds.read(descs.index(name) + 1).astype(np.float32)
    raw[raw < -1e30] = np.nan  # -3.4028235e38 nodata sentinel in the feature cube
    return raw if operator == "raw" else TRANSFORMS[operator](raw)


def rank01(a: np.ndarray, mask: np.ndarray) -> np.ndarray:
    out = np.full(a.shape, np.nan, dtype=np.float32)
    v = np.where(np.isfinite(a), a, np.nan)[mask]
    order = np.argsort(v)
    r = np.empty(v.size, dtype=np.float32)
    r[order] = np.arange(v.size, dtype=np.float32)
    out[mask] = r / max(v.size - 1, 1)
    return out


def belief_field(inputs: str, footprint: np.ndarray):
    """Equal-weight mean of the per-family rank-means (families weighted equally)."""
    fam_means, prov = [], {}
    for fam, entries in FAMILIES.items():
        ranks = []
        for operator, name in entries:
            arr = read_channel(inputs, "tf", name, operator)
            ranks.append(rank01(arr, footprint))
            del arr
        fam_means.append(np.nanmean(np.stack(ranks), axis=0).astype(np.float32))
        prov[fam] = [f"{operator}::tf.{name}" for operator, name in entries]
        del ranks
    belief = np.nanmean(np.stack(fam_means), axis=0).astype(np.float32)
    return belief, prov


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--inputs", default=".arena/inputs")
    ap.add_argument("--labels", default="data/grid/labels.tif")
    ap.add_argument("--sgmc", default="data/external/derived_sgmc_faults_100m_u8.tif")
    ap.add_argument("--out", default="evidence/h60_sweep.json")
    ap.add_argument("--belief-cache", default=".arena/h60_belief.npy")
    ap.add_argument("--masses", default=",".join(str(m) for m in DEFAULT_MASSES))
    args = ap.parse_args(argv)
    masses = [int(x) for x in args.masses.split(",")]

    t0 = time.time()
    footprint, catalogue, _, _ = load_grid(args.labels)
    from scipy import ndimage as ndi
    d_cat = ndi.distance_transform_edt(~catalogue)
    eligible = footprint & (d_cat > 3.0)

    if os.path.exists(args.belief_cache):
        belief = np.load(args.belief_cache)
        prov = {"cached": args.belief_cache}
        print(f"loaded belief field from {args.belief_cache}")
    else:
        belief, prov = belief_field(args.inputs, footprint)
        os.makedirs(os.path.dirname(args.belief_cache) or ".", exist_ok=True)
        np.save(args.belief_cache, belief)
        print(f"built belief field in {time.time() - t0:.0f} s")

    with rasterio.open(args.sgmc) as ds:
        sgmc = ds.read(1) == 1
    with rasterio.open(os.path.join(args.inputs, "lidar_scarp_features_u8.tif")) as ds:
        lidar_valid = ds.read(12) > 0
    f1 = build_frames(footprint, catalogue, sgmc, lidar_valid)["F1_sgmc_off"]
    base = f1.base_c_per_dot

    from build_h57 import metric_emit  # the metric-exact greedy emitter (3 px Chebyshev)

    rows = []
    for n in masses:
        sel = metric_emit(belief, eligible, n)
        got = int(sel.sum())
        credit = float(np.nansum(f1.K[sel]))
        h_f1 = credit / got if got else 0.0
        t = min(credit, float(f1.n_truth))
        dti_f1 = t / (0.2 * t + 0.2 * (got - credit) + 0.8 * f1.n_truth) if got else 0.0
        h_mass = math.exp(MODEL_MASS["a"]) * got ** MODEL_MASS["p"]
        h_both = MODEL_BOTH["a"] + MODEL_BOTH["b"] * h_f1 + MODEL_BOTH["c"] * math.log(got)
        rows.append({
            "requested_mass": n, "dots": got, "F1_c_per_dot": h_f1, "F1_lift": h_f1 / base,
            "F1_dti": dti_f1,
            "hidden_c_per_dot_mass_model": h_mass, "hidden_dti_mass_model": hidden_dti(got, h_mass),
            "hidden_c_per_dot_both_model": h_both, "hidden_dti_both_model": hidden_dti(got, h_both),
            "hidden_dti_model_mean": 0.5 * (hidden_dti(got, h_mass) + hidden_dti(got, h_both)),
        })
        print(f"  N={got:7d}  F1 c/dot={h_f1:.4f} (lift {h_f1 / base:.2f})  F1 DTI={dti_f1:.4f}  "
              f"modelled hidden DTI: mass {rows[-1]['hidden_dti_mass_model']:.3f}  "
              f"both {rows[-1]['hidden_dti_both_model']:.3f}  "
              f"mean {rows[-1]['hidden_dti_model_mean']:.3f}")
        del sel

    best = max(rows, key=lambda r: r["hidden_dti_model_mean"])
    rep = {
        "generated_utc": time.strftime("%Y%m%dT%H%M%SZ", time.gmtime()),
        "field": prov,
        "measured_lifts": MEASURED_LIFTS,
        "frame": "F1_sgmc_off",
        "frame_uniform_c_per_dot": base,
        "models": {"mass": MODEL_MASS, "both": MODEL_BOTH, "G_hat": G_HAT,
                   "source": "evidence/h57_hidden_model.json, fitted on 21 owner-reported "
                             "score anchors; transfer model r2 is negative - treat as weak"},
        "rows": rows,
        "argmax_by_model_mean": {"dots": best["dots"],
                                 "hidden_dti_model_mean": best["hidden_dti_model_mean"]},
        "caveat": "Modelled hidden DTI is arithmetic under a fitted transfer model, not a "
                  "measurement and not an organizer score.",
        "seconds": round(time.time() - t0, 1),
    }
    os.makedirs(os.path.dirname(args.out) or ".", exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as fh:
        json.dump(rep, fh, indent=1)
    print(f"\nwrote {args.out}; model-mean argmax N = {best['dots']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
