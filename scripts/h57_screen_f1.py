"""H57 F1 screen — the official 19-band feature stack on the structurally
correct frame.

`scripts/h57_transfer.py` shows that the catalogue-holdout frame (F2) is
*anti-predictive* for the real leaderboard score (Spearman rho = -0.477,
p = 0.029 on 21 byte-verified score-recorded artifacts), because its truth is
the compiled catalogue while the competition's scored truth is a set of faults
the compilers did **not** have. F1 (faults in an independent compilation that
are > 300 m from the given catalogue) is the only frame whose truth is *outside*
the catalogue, so it is the only frame on which a channel may be selected.

Usage
-----
    python scripts/h57_screen_f1.py --inputs .arena/inputs --out evidence/h57_screen_f1.json
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from h57_frames import build_frames, load_grid
from h57_screen import TRANSFORMS, Rasters, _top_within

MASSES = (15000, 30000, 60000)


def eval_on(frame, arr, masses):
    row = {"enrichment": None}
    v = np.where(np.isfinite(arr), arr, np.nan)
    with np.errstate(invalid="ignore", divide="ignore"):
        t = np.nanmean(v[frame.truth]) if frame.truth.any() else np.nan
        d = np.nanmean(v[frame.domain])
    row["enrichment"] = float(t / d) if np.isfinite(d) and d else float("nan")
    for m in masses:
        sel = _top_within(arr, frame.domain, m)
        n = int(sel.sum())
        if n == 0:
            row[f"m{m}"] = None
            continue
        credit = float(np.nansum(frame.K[sel]))
        tt = min(credit, float(frame.n_truth))
        dd = 0.2 * tt + 0.2 * (n - credit) + 0.8 * frame.n_truth
        row[f"m{m}"] = {"n_dots": n, "credit": credit, "c_per_dot": credit / n,
                        "coverage": tt / frame.n_truth, "dti": tt / dd}
    return row


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--inputs", default=".arena/inputs")
    ap.add_argument("--labels", default="data/grid/labels.tif")
    ap.add_argument("--sgmc", default="data/external/derived_sgmc_faults_100m_u8.tif")
    ap.add_argument("--out", default="evidence/h57_screen_f1.json")
    ap.add_argument("--keys", default="tf,lidar,topo,rad,grad,gext")
    ap.add_argument("--transforms", default="raw,res9")
    args = ap.parse_args(argv)
    import rasterio

    footprint, catalogue, _, _ = load_grid(args.labels)
    with rasterio.open(args.sgmc) as ds:
        sgmc = ds.read(1) == 1
    with rasterio.open(os.path.join(args.inputs, "lidar_scarp_features_u8.tif")) as ds:
        valid = ds.read(12) > 0
    frames = build_frames(footprint, catalogue, sgmc, valid)
    f1 = frames["F1_sgmc_off"]
    print(f"F1: truth {f1.n_truth} px, domain {f1.domain_px} px, "
          f"uniform base {f1.base_c_per_dot:.5f}")

    rast = Rasters(args.inputs)
    transforms = [t for t in args.transforms.split(",") if t]
    rows, t0 = [], time.time()
    for key in [k for k in args.keys.split(",") if k]:
        for i, d in enumerate(rast.descriptions(key), start=1):
            raw = rast.band(key, i)
            for tn in transforms:
                arr = raw if tn == "raw" else TRANSFORMS[tn](raw)
                name = f"{tn}::{key}.{d}"
                rows.append({"channel": name, **eval_on(f1, arr, MASSES)})
            del raw
        print(f"  {key} done ({time.time()-t0:.0f}s)", flush=True)

    # incumbents
    lid = {d: i for i, d in enumerate(rast.descriptions("lidar"), 1)}

    def rank(a, mask):
        out = np.full(a.shape, np.nan, dtype=np.float32)
        v = np.where(np.isfinite(a), a, np.nan)[mask]
        o = np.argsort(v)
        r = np.empty(v.size, dtype=np.float32)
        r[o] = np.arange(v.size, dtype=np.float32)
        out[mask] = r / max(v.size - 1, 1)
        return out

    parts = [rank(rast.band("lidar", lid[b]), footprint)
             for b in ("ex_max", "step_max", "lapneg_max", "downface_max", "relief")]
    inc = np.nanmean(np.stack(parts), axis=0).astype(np.float32)
    rows.append({"channel": "INCUMBENT_lidar_scarp_rankmean", **eval_on(f1, inc, MASSES)})
    rows.append({"channel": "EXTRA_lidar_valid_mask",
                 **eval_on(f1, rast.band("lidar", 12).astype(np.float32), MASSES)})

    rep = {"generated_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
           "frame": f1.detail, "masses": list(MASSES),
           "transforms": transforms, "n_channels": len(rows), "rows": rows}
    os.makedirs(os.path.dirname(args.out) or ".", exist_ok=True)
    with open(args.out, "w") as fh:
        json.dump(rep, fh, indent=1)
    print(f"wrote {args.out} ({time.time()-t0:.0f}s)")

    tab = []
    for r in rows:
        s = r.get("m30000")
        if s:
            tab.append((s["c_per_dot"] / f1.base_c_per_dot, r["channel"], r["enrichment"], s))
    tab.sort(reverse=True)
    print(f"\n{'channel':40s} {'lift':>6s} {'enrich':>7s} {'c/dot':>7s} {'cov':>6s} {'DTI':>7s}")
    for lift, ch, enr, s in tab[:30]:
        print(f"{ch[:40]:40s} {lift:6.3f} {enr:7.3f} {s['c_per_dot']:7.4f} "
              f"{s['coverage']:6.3f} {s['dti']:7.4f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
