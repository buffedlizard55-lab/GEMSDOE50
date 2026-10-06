#!/usr/bin/env python3
"""Validate a candidate field or file on three instruments, with matched-mass controls.

Instrument A  competition catalogue, **spatially blocked** (quarter of the survey held out
              in turn; the detector never sees the labels, so nothing is trained on them)
Instrument B  independent USGS SGMC inventory restricted to > 300 m from the catalogue
              (the closest available stand-in for "faults the catalogue lacks")
Instrument C  the 2020 Mw 6.5 Monte Cristo Range rupture trend -- a **known unmapped**
              active fault (Koehler et al. 2021, SRL 92(2A), 823-829,
              doi:10.1785/0220200371).  FLAGGED: the trend line here is derived from the
              sequence's own epicentres, so instrument C is circular as a *geometry* check
              and is reported only as a consistency check, never as validation.

Every comparison is at matched emitted mass, because the metric is a mass budget.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import rasterio
from scipy import ndimage
from scipy.ndimage import distance_transform_edt

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "src"))

from gems50 import grid, metric  # noqa: E402

SGMC = REPO / "data" / "external" / "derived_sgmc_faults_100m_u8.tif"
CACHE = REPO / "data" / "reference_files"


def load_truths(g):
    labels = grid.load_labels()
    valid = grid.load_valid_mask()
    d_lab = distance_transform_edt(~labels)
    with rasterio.open(SGMC) as s:
        sgmc = s.read(1) > 0
    sgmc_off = sgmc & (d_lab > 3) & valid

    # instrument C: principal axis of the 2020 Monte Cristo sequence
    cat_path = REPO / "data" / "external" / "usgs_comcat_earthquakes.csv.gz"
    df = pd.read_csv(cat_path, low_memory=False)
    from pyproj import Transformer
    tr = Transformer.from_crs("EPSG:4326", "EPSG:32611", always_xy=True)
    x, y = tr.transform(df["longitude"].to_numpy(), df["latitude"].to_numpy())
    t = pd.to_datetime(df["time"], format="ISO8601", utc=True)
    sel = (t >= "2020-05-15") & (t <= "2021-12-31")
    d = np.hypot(x - 425569.0, y - 4224896.0)
    sel &= d < 30000
    X = np.column_stack([x[sel], y[sel]])
    mu = X.mean(axis=0)
    vals, vecs = np.linalg.eigh(np.cov((X - mu).T))
    v = vecs[:, 1]
    ts = np.linspace(-14000, 14000, 281)
    mc = np.zeros(g.shape, dtype=bool)
    cc, rr = g.col_row(mu[0] + ts * v[0], mu[1] + ts * v[1])
    ok = (cc >= 0) & (cc < g.width) & (rr >= 0) & (rr < g.height)
    mc[rr[ok], cc[ok]] = True
    return labels, valid, sgmc_off, mc


def score_file(path: Path, truths, quadrants=None) -> dict:
    with rasterio.open(path) as s:
        a = np.nan_to_num(s.read(1))
    sup = a > 0.5
    S = int(sup.sum())
    out = {"mass": S, "file": path.name}
    if S == 0:
        return out
    labels, valid, sgmc_off, mc = truths
    p = sup.astype(np.float32)
    for name, truth in (("cat_all", labels), ("sgmc_off", sgmc_off), ("monte_cristo", mc)):
        r = metric.dti_parts(p, truth)
        out[name] = {"credit_per_px": r.tpw / S, "tpw": r.tpw, "dti": r.value,
                     "truth_px": r.truth_cells, "covered_frac": r.tpw / max(r.truth_cells, 1)}
    if quadrants is not None:
        vals = []
        for q in quadrants:
            r = metric.dti_parts(np.where(q, p, 0), np.where(q, labels, False))
            vals.append(r.tpw / max(int(np.where(q, p, 0).sum()), 1))
        out["cat_blocked_mean"] = float(np.mean(vals))
        out["cat_blocked_folds"] = [float(v) for v in vals]
    return out


def quadrants_of(g, labels):
    h, w = g.shape
    out = []
    for i in range(2):
        for j in range(2):
            q = np.zeros(g.shape, dtype=bool)
            q[i * h // 2:(i + 1) * h // 2, j * w // 2:(j + 1) * w // 2] = True
            out.append(q & grid.load_valid_mask())
    return out


def controls(truths, mass, g, labels, seed=0):
    labels_, valid, sgmc_off, mc = truths
    out = {}
    rng = np.random.default_rng(seed)
    a = np.zeros(g.shape, dtype=np.float32)
    a[rng.random(g.shape) < (mass / valid.sum())] = 1.0
    a = np.where(valid, a, 0.0)
    p = (a > 0).astype(np.float32)
    for name, truth in (("cat_all", labels_), ("sgmc_off", sgmc_off), ("monte_cristo", mc)):
        r = metric.dti_parts(p, truth)
        out.setdefault(name, {})["poisson"] = r.tpw / max(int(p.sum()), 1)
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--files", nargs="+", required=True)
    ap.add_argument("--out", default=str(REPO / "evidence" / "validation.json"))
    args = ap.parse_args()
    g = grid.load_grid()
    truths = load_truths(g)
    labels, valid, sgmc_off, mc = truths
    quads = quadrants_of(g, labels)
    out = {"quadrant_px": [int(q.sum()) for q in quads], "files": {}}
    for f in args.files:
        p = Path(f)
        if not p.exists():
            print(f"  missing: {p}")
            continue
        res = score_file(p, truths, quads)
        out["files"][p.name] = res
        if "mass" in res and res["mass"]:
            print(f"  {p.name:58s} mass={res['mass']:6d} cat_all={res['cat_all']['credit_per_px']:.4f} "
                  f"blocked={res.get('cat_blocked_mean', float('nan')):.4f} "
                  f"sgmc_off={res['sgmc_off']['credit_per_px']:.4f} "
                  f"mc={res['monte_cristo']['credit_per_px']:.4f}")
    with open(args.out, "w") as fh:
        json.dump(out, fh, indent=1)
    print(f"wrote {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
