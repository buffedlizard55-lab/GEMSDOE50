#!/usr/bin/env python3
"""H60 screen — do the OFFICIAL competition-stack structure channels carry off-catalogue
information about faults the given catalogue does not contain?

Why this screen exists
----------------------
`evidence/h57_stratified.json` already screened the raw official bands (`tf.det_elev`,
`tf.geod_*`, `tf.iso_grav_*`, `tf.tmi*`, `tf.cond_surf`, `tf.depth_to_base_surf`) and found
every one of them below the in-stratum uniform control when used **raw** (lift 0.28-0.98 for
the potential-field, geodetic and subsurface families).  H57 therefore built its belief field
from the owner-mirrored LiDAR scarp and 10 m topographic stacks, which do win (2.1-2.7).

Raw band value is the wrong operator for a *structural* channel: a fault is a localized
gradient/step of `depth_to_base_surf`, `cond_surf` or the isostatic gravity field, not a high
absolute value of it.  This screen asks the question the raw screen could not: **does a
directional-derivative or ridge operator applied to the official stack's gravity, magnetic,
subsurface and topographic channels beat the in-stratum uniform control?**

Instrument (identical to `scripts/h57_stratified.py`, so the numbers are comparable):

* frame F1 — truth = USGS SGMC fault pixels > 3 px from any given-catalogue pixel;
  domain = footprint pixels > 3 px from the given catalogue;
* the metric's own credit field `K(x) = max_g clip(1 - d(x,g)/3, 0)`;
* **elevation stratification**: truth and domain are intersected with each quintile of the
  mean-elevation distribution, which removes the "pick the mountains" terrain confound that
  makes `raw::topo.dem_mean` look like a detector on the unstratified frame;
* for each channel the top `mass / n_strata` cells inside each stratum are selected, their
  metric credit is summed, and

      lift = (credit per dot) / (uniform credit per dot in the same stratum)

  is reported per stratum plus pooled.  A channel with pooled lift < 1.0 is *worse* than
  scattering the same number of dots uniformly inside the stratum.

Usage
-----
    python scripts/h60_screen.py --inputs .arena/inputs --out evidence/h60_screen.json
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
from h57_screen import TRANSFORMS, Rasters, _top_within

#: Official-stack channels whose *structural* operator is under test.  Grouped by the physical
#: question each group asks; the group is what a belief-field family would be built from.
CHANNELS = [
    ("tf", "depth_to_base_surf"),   # thickness of sedimentary cover
    ("tf", "cond_surf"),            # electrical conductivity surface
    ("tf", "iso_grav_anom"),        # isostatic gravity anomaly
    ("tf", "iso_grav_anom_hg"),     # ... horizontal gradient (shipped as a product)
    ("tf", "iso_grav_anom_vg"),     # ... vertical gradient (shipped as a product)
    ("tf", "iso_grav_anom_slope"),  # ... slope (shipped as a product)
    ("tf", "tmi"),                  # total magnetic intensity
    ("tf", "tmi_hg"),               # ... horizontal gradient
    ("tf", "tmi_vg"),               # ... vertical gradient
    ("tf", "rtp"),                  # reduced-to-pole magnetic anomaly
    ("tf", "mag_anom"),             # magnetic anomaly
    ("tf", "tc"),                   # band labelled tilt angle / total curvature
    ("tf", "det_elev"),             # detrended elevation
    ("tf", "det_elev_slope"),       # detrended elevation slope
    ("tf", "geod_2ndinv"),          # geodetic strain second invariant
    ("tf", "geod_shearrate"),
    ("tf", "geod_dilaterate"),
]
OPERATORS = ("raw", "grad", "ridge2")


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--inputs", default=".arena/inputs")
    ap.add_argument("--labels", default="data/grid/labels.tif")
    ap.add_argument("--sgmc", default="data/external/derived_sgmc_faults_100m_u8.tif")
    ap.add_argument("--out", default="evidence/h60_screen.json")
    ap.add_argument("--mass", type=int, default=30000)
    ap.add_argument("--n-strata", type=int, default=5)
    ap.add_argument("--operators", default=",".join(OPERATORS))
    args = ap.parse_args(argv)

    operators = tuple(x for x in args.operators.split(",") if x)

    footprint, catalogue, _, _ = load_grid(args.labels)
    with rasterio.open(args.sgmc) as ds:
        sgmc = ds.read(1) == 1
    with rasterio.open(os.path.join(args.inputs, "lidar_scarp_features_u8.tif")) as ds:
        lidar_valid = ds.read(12) > 0
    f1 = build_frames(footprint, catalogue, sgmc, lidar_valid)["F1_sgmc_off"]

    with rasterio.open(os.path.join(args.inputs, "topo_u8.tif")) as ds:
        descs = [d.split(" - ")[0].strip() for d in ds.descriptions]
        dem = ds.read(descs.index("dem_mean") + 1).astype(np.float32)
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
        strata.append(Frame(f"dem_q{i}", truth, domain))
    print(f"frame F1: truth {f1.n_truth:,} px, domain {f1.domain_px:,} px, "
          f"uniform credit/dot {f1.base_c_per_dot:.5f}")
    print(f"strata: {[(s.name, s.n_truth, s.domain_px) for s in strata]}")

    rasters = Rasters(args.inputs)

    def measure(arr: np.ndarray) -> dict:
        rows = []
        for fr in strata:
            sel = _top_within(arr, fr.domain, args.mass // len(strata))
            n = int(sel.sum())
            if n == 0:
                continue
            credit = float(np.nansum(fr.K[sel]))
            rows.append({"stratum": fr.name, "n_dots": n, "credit": credit,
                         "c_per_dot": credit / n, "base": fr.base_c_per_dot,
                         "lift": (credit / n) / fr.base_c_per_dot})
        if not rows:
            return {"error": "no stratum produced a selection"}
        dots = sum(r["n_dots"] for r in rows)
        cred = sum(r["credit"] for r in rows)
        base = sum(r["base"] for r in rows) / len(rows)
        return {"pooled_c_per_dot": cred / dots, "pooled_base": base,
                "pooled_lift": (cred / dots) / base,
                "strata_won": sum(1 for r in rows if r["lift"] > 1.0),
                "strata": len(rows),
                "per_stratum_lift": [round(r["lift"], 4) for r in rows]}

    rows = []
    t0 = time.time()
    for key, name in CHANNELS:
        try:
            idx = rasters.descriptions(key).index(name) + 1
            raw = rasters.band(key, idx).astype(np.float32)
        except (KeyError, ValueError, OSError) as exc:  # pragma: no cover - input availability
            rows.append({"channel": f"{key}.{name}", "error": repr(exc)})
            continue
        for op in operators:
            arr = raw if op == "raw" else TRANSFORMS[op](raw)
            m = measure(arr)
            rows.append({"channel": f"{op}::{key}.{name}", **m})
            print(f"  {op:6s} {key}.{name:22s} pooled lift {m.get('pooled_lift', float('nan')):.3f} "
                  f"strata {m.get('strata_won', 0)}/{m.get('strata', 0)}")
            del arr
        del raw

    rows.sort(key=lambda r: -(r.get("pooled_lift") or -1))
    rep = {
        "generated_utc": time.strftime("%Y%m%dT%H%M%SZ", time.gmtime()),
        "frame": "F1_sgmc_off (USGS SGMC faults > 300 m from the given catalogue)",
        "instrument": "scripts/h57_stratified.py methodology: elevation-stratified, "
                      "metric-exact credit per dot, uniform control inside each stratum",
        "mass": args.mass, "n_strata": len(strata), "operators": list(operators),
        "frame_stats": {"n_truth": f1.n_truth, "domain_px": f1.domain_px,
                        "uniform_c_per_dot": f1.base_c_per_dot},
        "channels": rows,
        "seconds": round(time.time() - t0, 1),
        "scope_note": "This is a proxy frame, not the organizer truth. A lift above 1.0 means "
                      "the operator selects cells closer to *state-geologic-map* structures "
                      "beyond the given catalogue than a uniform emitter does; it does not "
                      "prove the same ordering against the hidden label set.",
    }
    os.makedirs(os.path.dirname(args.out) or ".", exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as fh:
        json.dump(rep, fh, indent=1)
    print(f"\nwrote {args.out}  ({rep['seconds']} s)")
    print("top 8:")
    for r in rows[:8]:
        print(f"  {r['channel']:36s} {r.get('pooled_lift', float('nan')):.3f} "
              f"({r.get('strata_won', 0)}/{r.get('strata', 0)})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
