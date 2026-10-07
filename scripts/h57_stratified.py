"""H57 stratified control — is a channel a fault detector, or a terrain proxy?

`scripts/h57_screen_f1.py` ranks `raw::topo.steep_frac` and `raw::topo.dem_mean`
at the top of the F1 frame. `dem_mean` is literally mean elevation, so the F1
frame rewards "pick the high, steep mountains" — which is where the *bedrock*
faults of the State Geologic Map Compilation live, and is not where the young
basin-filling faults of the given catalogue live. The F1 head is therefore a
terrain confound, not a detector ranking.

This script removes the confound by stratifying: the F1 truth is intersected
with a band of the mean-elevation distribution and the domain is restricted to
the same band (and to the same 3 px catalogue buffer). Inside one stratum the
low-frequency terrain term is approximately constant, so any residual
credit-per-dot lift is *local* information.

Reported for each channel: the pooled lift inside the strata (percentile bands
of `topo_u8.dem_mean`) and the number of strata in which the channel beats the
in-stratum uniform control.

Usage
-----
    python scripts/h57_stratified.py --inputs .arena/inputs --out evidence/h57_stratified.json
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time

import numpy as np
import rasterio

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from h57_frames import Frame, build_frames, load_grid
from h57_screen import TRANSFORMS, _top_within

CHANNELS = [
    ("lidar", "step_max"), ("lidar", "ex_max"), ("lidar", "ex_mean"),
    ("lidar", "downface_max"), ("lidar", "lapneg_max"), ("lidar", "relief"),
    ("lidar", "coh100"), ("lidar", "strike"), ("lidar", "valid"),
    ("topo", "slope_max"), ("topo", "steep_frac"), ("topo", "hs_lineament"),
    ("topo", "curv_prof_absmax"), ("topo", "relief_local"), ("topo", "slope_std"),
    ("topo", "dem_mean"),
]
TF_CHANNELS = [
    ("tf", "det_elev"), ("tf", "det_elev_slope"), ("tf", "geod_2ndinv"),
    ("tf", "geod_shearrate"), ("tf", "geod_dilaterate"), ("tf", "iso_grav_anom"),
    ("tf", "iso_grav_anom_slope"), ("tf", "iso_grav_anom_hg"), ("tf", "iso_grav_anom_vg"),
    ("tf", "tc"), ("tf", "tmi"), ("tf", "tmi_hg"), ("tf", "tmi_vg"), ("tf", "rtp"),
    ("tf", "mag_anom"), ("tf", "deq_n100a15"), ("tf", "ieq_n100a15"),
    ("tf", "cond_surf"), ("tf", "depth_to_base_surf"),
]
FILES = {"lidar": "lidar_scarp_features_u8.tif", "topo": "topo_u8.tif",
         "tf": "training_features.tif"}


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--inputs", default=".arena/inputs")
    ap.add_argument("--labels", default="data/grid/labels.tif")
    ap.add_argument("--sgmc", default="data/external/derived_sgmc_faults_100m_u8.tif")
    ap.add_argument("--out", default="evidence/h57_stratified.json")
    ap.add_argument("--mass", type=int, default=30000)
    ap.add_argument("--n-strata", type=int, default=5)
    args = ap.parse_args(argv)

    footprint, catalogue, _, _ = load_grid(args.labels)
    with rasterio.open(args.sgmc) as ds:
        sgmc = ds.read(1) == 1
    with rasterio.open(os.path.join(args.inputs, "lidar_scarp_features_u8.tif")) as ds:
        valid = ds.read(12) > 0
    f1 = build_frames(footprint, catalogue, sgmc, valid)["F1_sgmc_off"]

    handles = {k: rasterio.open(os.path.join(args.inputs, v)) for k, v in FILES.items()}
    descs = {k: [d.split(" - ")[0].strip() for d in h.descriptions]
             for k, h in handles.items()}
    idx = {k: {d: i for i, d in enumerate(v, 1)} for k, v in descs.items()}

    dem = handles["topo"].read(idx["topo"]["dem_mean"]).astype(np.float32)
    dem[~footprint] = np.nan
    qs = np.nanpercentile(dem[footprint], np.linspace(0, 100, args.n_strata + 1))
    strata = []
    for i in range(args.n_strata):
        lo, hi = qs[i], qs[i + 1]
        m = footprint & (dem >= lo) & (dem <= hi if i == args.n_strata - 1 else dem < hi)
        truth = f1.truth & m
        domain = f1.domain & m
        if truth.sum() < 300 or domain.sum() < 5000:
            continue
        strata.append((f"dem_q{i}", Frame(f"dem_q{i}", truth, domain)))
    print(f"strata: {[(s[0], s[1].n_truth, s[1].domain_px) for s in strata]}")

    def measure(arr):
        out = []
        for name, fr in strata:
            sel = _top_within(arr, fr.domain, args.mass // len(strata))
            n = int(sel.sum())
            if n == 0:
                continue
            credit = float(np.nansum(fr.K[sel]))
            out.append({"stratum": name, "n_dots": n, "credit": credit,
                        "c_per_dot": credit / n, "base": fr.base_c_per_dot,
                        "lift": (credit / n) / fr.base_c_per_dot})
        if not out:
            return None
        dots = sum(o["n_dots"] for o in out)
        cred = sum(o["credit"] for o in out)
        base = sum(o["base"] for o in out) / len(out)
        return {"pooled_c_per_dot": cred / dots, "pooled_base": base,
                "pooled_lift": (cred / dots) / base,
                "strata_won": sum(1 for o in out if o["lift"] > 1.0),
                "strata": out}

    rows = []
    t0 = time.time()
    for key, name in CHANNELS + TF_CHANNELS:
        if name not in idx[key]:
            continue
        raw = handles[key].read(idx[key][name]).astype(np.float32)
        raw[raw < -1e30] = np.nan
        for tn in ("raw", "res9"):
            arr = raw if tn == "raw" else TRANSFORMS["res9"](raw)
            r = measure(arr)
            if r:
                r["channel"] = f"{tn}::{key}.{name}"
                rows.append(r)
                print(f"  {r['channel']:32s} lift={r['pooled_lift']:.3f} "
                      f"won={r['strata_won']}/{len(r['strata'])}  "
                      f"({time.time()-t0:.0f}s)", flush=True)

    rep = {"generated_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
           "frame": "F1 truth x mean-elevation stratum",
           "n_strata": args.n_strata, "mass_per_stratum": args.mass // len(strata),
           "strata_meta": [{"name": n, "truth_px": fr.n_truth,
                            "domain_px": fr.domain_px,
                            "base_c_per_dot": fr.base_c_per_dot}
                           for n, fr in strata],
           "rows": rows}
    os.makedirs(os.path.dirname(args.out) or ".", exist_ok=True)
    with open(args.out, "w") as fh:
        json.dump(rep, fh, indent=1)
    print("wrote", args.out)
    tab = sorted(rows, key=lambda r: -r["pooled_lift"])
    print(f"\n{'channel':32s} {'lift':>6s} {'won':>6s}")
    for r in tab:
        print(f"{r['channel']:32s} {r['pooled_lift']:6.3f} "
              f"{r['strata_won']}/{len(r['strata'])}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
