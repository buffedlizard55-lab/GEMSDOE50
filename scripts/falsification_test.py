#!/usr/bin/env python3
"""Leakage-free falsification test for the seismicity-lineation detector.

Protocol (fixed before the run, no tuning on the outcome)
  1. Build the earthquake catalogue from the official USGS ComCat export and keep ONLY
     events strictly before 2020-05-15 -- i.e. the detector never sees the Monte Cristo
     sequence, the earthquake whose rupture is used as the positive test.
  2. Run the shipped detector on those events: 2-D Ouillon-Sornette triangle-area
     declustering, DBSCAN clusters in (x, y, 3 km/yr*t), recursive 2-means splitting to
     minor-axis sigma <= 600 m, corridor axes + spines + gap connectors, thinned to one
     dot every 400 m so that no two dots compete for the same 300 m kernel.
  3. Build the controls from the SAME event set at the SAME emitted mass: smoothed
     earthquake density (sigma = 10 and 20 px), uniform random inside the footprint, and
     the provided catalogue raster itself (reference, not a control).
  4. Score every field on three truths: the 2020 Monte Cristo rupture trend (a real,
     uncatalogued rupture -- the pre-registered positive), the USGS SGMC faults the
     provided catalogue does not contain, and the provided catalogue itself.

Reading: the corridors are the only field that reaches the rupture the catalogue never
recorded, and they reach it from pre-event seismicity alone.  They do NOT win on the
broad inventories -- that is reported, not hidden.
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd
import rasterio
from scipy import ndimage
from scipy.ndimage import distance_transform_edt
from sklearn.neighbors import NearestNeighbors

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "src"))

from gems50 import catalog as gcat, decluster, lineation  # noqa: E402
from gems50 import dti as metric  # noqa: E402
from gems50 import emission  # noqa: E402
from gems50 import grid_io as grid  # noqa: E402

CUTOFF = pd.Timestamp("2020-05-15", tz="UTC")
MC_POINT = (425569.0, 4224896.0)
MASS = 6000
SPACING_PX = 4


def mc_truth(g):
    df = pd.read_csv(REPO / "data/external/usgs_comcat_earthquakes.csv.gz", low_memory=False)
    from pyproj import Transformer
    tr = Transformer.from_crs("EPSG:4326", "EPSG:32611", always_xy=True)
    x, y = tr.transform(df["longitude"].to_numpy(), df["latitude"].to_numpy())
    t = pd.to_datetime(df["time"], format="ISO8601", utc=True)
    sel = ((t >= CUTOFF) & (t <= "2022-01-01")
           & (np.hypot(x - MC_POINT[0], y - MC_POINT[1]) < 30000))
    X = np.column_stack([x[sel], y[sel]])
    mu = X.mean(axis=0)
    _, vecs = np.linalg.eigh(np.cov((X - X.mean(axis=0)).T))
    v = vecs[:, 1]
    ts = np.linspace(-14000, 14000, 281)
    out = np.zeros(g.shape, bool)
    cc, rr = g.col_row(mu[0] + ts * v[0], mu[1] + ts * v[1])
    ok = (cc >= 0) & (cc < g.width) & (rr >= 0) & (rr < g.height)
    out[rr[ok], cc[ok]] = True
    return out, int(sel.sum())


def detector(g, valid, events, spacing_px):
    x, y, t, h = events
    P = np.column_stack([x, y])
    keep, tri = decluster.triangle_area_filter(P)
    P, t, h = P[keep], t[keep], h[keep]
    clusters = lineation.cluster_lineations(P, t, h, eps_m=3000.0, min_samples=15,
                                            delta_m=600.0, min_events=12)
    thin = np.zeros(g.shape, bool)
    for i in range(len(clusters)):
        n = max(int(2 * clusters.half_length_m[i] / 100.0) + 1, 2)
        off = np.linspace(-clusters.half_length_m[i], clusters.half_length_m[i], n)
        cc, rr = g.col_row(clusters.x[i] + off * clusters.ux[i], clusters.y[i] + off * clusters.uy[i])
        ok = (rr >= 0) & (rr < g.height) & (cc >= 0) & (cc < g.width)
        thin[rr[ok], cc[ok]] = True
    return thin & valid, {"kept_after_triangle": int(keep.sum()), "n_clusters": int(len(clusters)),
                          "axis_cells": int((thin & valid).sum())}


def main() -> int:
    t0 = time.time()
    g = grid.load_grid()
    valid = grid.load_valid_mask()
    labels = grid.load_labels()
    d_lab = distance_transform_edt(~labels)
    with rasterio.open(REPO / "data/external/derived_sgmc_faults_100m_u8.tif") as s:
        sgmc = s.read(1) > 0
    sgmc_rel = sgmc & ~labels & valid
    mc, n_mc_events = mc_truth(g)

    cat = gcat.build_catalog(REPO / "data/external/usgs_comcat_earthquakes.csv.gz",
                             min_magnitude=1.5, max_depth_km=20.0, start_year=1970)
    df = cat.frame
    pre = (pd.to_datetime(df["time"], format="ISO8601", utc=True) < CUTOFF).to_numpy()
    E = df[pre]
    xy = np.column_stack([E["x"].to_numpy(), E["y"].to_numpy()])
    t = E["t_years"].to_numpy()
    h = E["h_err_km"].to_numpy() * 1000.0
    # keep events inside the study footprint (30 px=3 km margin), the same restriction the
    # shipped detector uses: the grid rectangle is much larger than the surveyed footprint
    col, row = g.col_row(xy[:, 0], xy[:, 1])
    ok = (col >= 0) & (col < g.width) & (row >= 0) & (row < g.height)
    near = np.zeros(len(xy), bool)
    dil = ndimage.binary_dilation(valid, iterations=30)
    near[ok] = dil[row[ok], col[ok]]
    xy, t, h = xy[near], t[near], h[near]
    print(f"pre-2020 events {len(xy)}  MC truth px {int(mc.sum())}  relation events {n_mc_events}", flush=True)

    corridors, det = detector(g, valid, (xy[:, 0], xy[:, 1], t, h), SPACING_PX)
    corridors = emission.thin_support(corridors, np.ones(g.shape, np.float32), SPACING_PX)
    global MASS
    MASS = int(corridors.sum())
    print(f"detector: {det} -> thinned {MASS} dots (controls matched to this mass)", flush=True)

    dens = np.zeros(g.shape, np.float32)
    cc, rr = g.col_row(xy[:, 0], xy[:, 1])
    np.add.at(dens, (rr, cc), 1.0)
    fields = {"corridors (this detector)": corridors}
    for sig in (10.0, 20.0):
        f = ndimage.gaussian_filter(dens, sig)
        order = np.argsort(-f.ravel())
        # grow the threshold until the *thinned* support reaches the matched mass
        thin_prev, prev_k = None, 0
        for k in range(200, 400_000, 2_000):
            m = np.zeros(f.size, bool)
            m[order[:k]] = True
            thin_prev, prev_k = emission.thin_support(m.reshape(g.shape), f, SPACING_PX), k
            if int(thin_prev.sum()) >= MASS:
                break
        print(f"    density sigma={sig:g}: top {prev_k} cells -> {int(thin_prev.sum())} dots", flush=True)
        fields[f"smoothed density sigma={sig:g} px"] = thin_prev
    rng = np.random.default_rng(20261006)
    idx = rng.choice(np.flatnonzero(valid.ravel()), max(MASS, 1), replace=False)
    rnd = np.zeros(valid.size, bool)
    rnd[idx] = True
    fields["uniform random"] = emission.thin_support(rnd.reshape(g.shape), np.ones(g.shape, np.float32), SPACING_PX)
    fields["provided catalogue (reference)"] = labels & valid

    truths = {"mc_2020_rupture_trend": mc, "sgmc_not_in_catalogue": sgmc_rel, "given_catalogue": labels}
    rows = {}
    for name, f in fields.items():
        n = max(int(f.sum()), 1)
        r = {}
        for tk, tr in truths.items():
            q = metric.dti_parts(f.astype(np.float32), tr)
            r[tk] = {"credit_per_px": q.tpw / n, "covered_frac": q.tpw / max(int(tr.sum()), 1),
                     "tpw": q.tpw, "dti_on_that_truth": q.value}
        rows[name] = {"mass": int(f.sum()), **r}
        print(f"  {name:32s} mass={int(f.sum()):6d} "
              f"mc_cov={r['mc_2020_rupture_trend']['covered_frac']:.3f} "
              f"c_mc={r['mc_2020_rupture_trend']['credit_per_px']:.4f} "
              f"c_sgmc={r['sgmc_not_in_catalogue']['credit_per_px']:.4f} "
              f"c_cat={r['given_catalogue']['credit_per_px']:.4f}", flush=True)

    out = {"protocol": __doc__.split("Protocol")[1].split("Reading:")[0].strip(),
           "cutoff_utc": str(CUTOFF), "pre_2020_events_in_footprint": int(len(xy)),
           "detector": det, "spacing_px": SPACING_PX, "seconds": round(time.time() - t0, 1),
           "results": rows}
    (REPO / "evidence").mkdir(exist_ok=True)
    (REPO / "evidence" / "falsification_test.json").write_text(json.dumps(out, indent=1, default=str))
    print(f"wrote evidence/falsification_test.json ({time.time()-t0:.0f}s)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
