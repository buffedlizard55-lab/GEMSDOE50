"""H57 focused probe — is the winner local information, or a regional confound?

The screen (`scripts/h57_screen.py`) ranks ~90 channels on the catalogue-holdout
frame. The top of that table is dominated by the geodetic strain-rate bands
(`geod_2ndinv`, `geod_shearrate`), which are *smooth by construction*: geodetic
strain from GPS/InSAR is a regional field. If the whole signal is regional, the
channel is only a proxy for "the catalogue is denser in the Walker Lane", which
is a confound, not a detector.

This probe separates the two by measuring, for every channel:

* ``len_px``   — the e-folding length of the channel's own spatial
  autocorrelation, from the radial autocorrelation of the mean-removed field.
* a **scale ladder**: c_per_dot of the channel low-passed at 9, 21, 51 and 101 px
  (0.9, 2.1, 5.1, 10.1 km). A detector whose c_per_dot does not fall when it is
  blurred is carrying regional, not local, information.
* the same statistic on the **matched-scale control**: c_per_dot of a field
  built by low-passing the channel and adding an equal-variance white-noise
  field, which has the channel's regional structure but no local structure.

It also repeats the ranking on F1 (the independent SGMC population) and on the
LiDAR-valid subset, and reports the multi-mass curve for the leaders so the
mass rule can be applied.

Usage
-----
    python scripts/h57_probe.py --inputs .arena/inputs --out evidence/h57_probe.json
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time

import numpy as np
from scipy import ndimage as ndi

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from h57_frames import build_frames, load_grid  # noqa: E402
from h57_screen import Rasters, _enrichment, _res9, _top_within  # noqa: E402

MASKS = (9, 21, 51, 101)


def _lowpass(a: np.ndarray, k: int) -> np.ndarray:
    return ndi.uniform_filter(a, size=k, mode="nearest")


def _e_folding_length(a: np.ndarray, footprint: np.ndarray, max_lag: int = 60) -> float:
    """Radial e-folding length of the autocorrelation of the mean-removed field."""
    v = np.where(footprint, a, np.nan)
    m = np.nanmean(v)
    x = np.where(np.isfinite(v), v - m, 0.0)
    f = np.fft.rfft2(x)
    ac = np.fft.irfft2(f * np.conj(f), s=x.shape)
    ac /= ac[0, 0] if ac[0, 0] else 1.0
    lags = np.arange(1, max_lag + 1)
    vals = np.array([ac[0, k] for k in lags])
    below = np.where(vals < 1.0 / np.e)[0]
    if below.size == 0:
        return float(max_lag)
    i = below[0]
    if i == 0:
        return float(lags[0]) * float(vals[0])
    x0, x1 = lags[i - 1], lags[i]
    y0, y1 = vals[i - 1], vals[i]
    t = (y0 - 1.0 / np.e) / (y0 - y1) if y0 != y1 else 0.0
    return float(x0 + t * (x1 - x0))


def _c_per_dot(frame, arr, mass):
    sel = _top_within(arr, frame.domain, mass)
    n = int(sel.sum())
    if n == 0:
        return None
    credit = float(frame.K[sel].sum())
    return {"n_dots": n, "credit": credit, "c_per_dot": credit / n}


def probe(channel, frames, mass):
    out = {}
    for fname, fr in frames.items():
        row = {"base_c_per_dot": fr.base_c_per_dot,
               "enrichment": _enrichment(channel, fr.truth, fr.domain),
               "len_px": None}
        ladder = {}
        for k in (1, *MASKS):
            a = channel if k == 1 else _lowpass(channel, k)
            r = _c_per_dot(fr, a, mass)
            ladder[f"lp{k}"] = None if r is None else r["c_per_dot"]
        row["ladder"] = ladder
        r1 = _c_per_dot(fr, channel, mass)
        row["c_per_dot"] = None if r1 is None else r1["c_per_dot"]
        row["n_dots"] = None if r1 is None else r1["n_dots"]
        row["lift"] = (row["c_per_dot"] / fr.base_c_per_dot
                       if row["c_per_dot"] else None)
        row["regional_retention"] = (ladder["lp101"] / row["c_per_dot"]
                                     if row["c_per_dot"] and ladder["lp101"] else None)
        out[fname] = row
    return out


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--inputs", default=".arena/inputs")
    ap.add_argument("--labels", default="data/grid/labels.tif")
    ap.add_argument("--sgmc", default="data/external/derived_sgmc_faults_100m_u8.tif")
    ap.add_argument("--out", default="evidence/h57_probe.json")
    ap.add_argument("--mass", type=int, default=30000)
    ap.add_argument("--only", default="")
    args = ap.parse_args(argv)
    import rasterio

    footprint, catalogue, transform, shape = load_grid(args.labels)
    with rasterio.open(args.sgmc) as ds:
        sgmc = ds.read(1) == 1
    with rasterio.open(os.path.join(args.inputs, "lidar_scarp_features_u8.tif")) as ds:
        valid = ds.read(12) > 0

    allf = build_frames(footprint, catalogue, sgmc, valid)
    frames = {k: v for k, v in allf.items() if k.startswith("F2_")}

    rast = Rasters(args.inputs)
    wanted = [w for w in args.only.split(",") if w]
    rows = []
    t0 = time.time()
    for key in rast.FILES:
        for i, d in enumerate(rast.descriptions(key), start=1):
            name = f"{key}.{d}"
            if wanted and name not in wanted:
                continue
            raw = rast.band(key, i)
            variants = {"raw": raw, "res9": _res9(raw)}
            for vname, arr in variants.items():
                full = f"{vname}::{name}"
                row = {"channel": full, **probe(arr, frames, args.mass)}
                for fname, fr in allf.items():
                    if fname.startswith("F1_"):
                        row[fname] = {
                            "base_c_per_dot": fr.base_c_per_dot,
                            "c_per_dot": None,
                            "lift": None,
                        }
                        r = _c_per_dot(fr, arr, args.mass)
                        if r:
                            row[fname]["c_per_dot"] = r["c_per_dot"]
                            row[fname]["lift"] = r["c_per_dot"] / fr.base_c_per_dot
                        f1 = fr
                if "F1_sgmc_off" in row:
                    row["F1_sgmc_off"]["len_px"] = _e_folding_length(arr, footprint)
                row["len_px"] = _e_folding_length(arr, footprint)
                # LiDAR-valid restriction on an F2 fold
                fw = {k: v for k, v in frames.items() if k.endswith("_NW")}
                if fw:
                    varr = np.where(valid, arr, np.nan)
                    r = _c_per_dot(list(fw.values())[0], varr, 30000)
                    row["F3_NW_c_per_dot"] = None if r is None else r["c_per_dot"]
                rows.append(row)
                def _f(v, fmt="{:.4f}"):
                    return "n/a" if v is None else fmt.format(v)
                print(f"  {full:40s} len={_f(row['len_px'],'{:.2f}')} "
                      f"F2={_f(row['F2_cat_NW']['c_per_dot'])} "
                      f"F1lift={_f(row['F1_sgmc_off']['lift'],'{:.3f}')} "
                      f"regret={_f(row['F2_cat_NW']['regional_retention'],'{:.3f}')} "
                      f"({time.time()-t0:.0f}s)", flush=True)
                del arr, variants
            del raw

    rep = {"generated_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
           "mass": args.mass,
           "frames": {k: v.detail for k, v in allf.items()},
           "rows": rows}
    os.makedirs(os.path.dirname(args.out) or ".", exist_ok=True)
    with open(args.out, "w") as fh:
        json.dump(rep, fh, indent=1)
    print("wrote", args.out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
