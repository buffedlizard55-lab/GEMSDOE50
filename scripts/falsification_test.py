#!/usr/bin/env python3
"""The brief's falsification gate, run so that it cannot be circular.

The task is to predict faults that are *not* in the given catalogue.  The 2020 Mw 6.5
Monte Cristo Range earthquake ruptured a fault that no ground-truth raster in this
competition contains, so it is the one unmapped rupture in the survey area with an
independently recorded ground truth.  Testing against it with corridors built from the
2020-2021 sequence itself would be circular, so the detector here is given **only events
older than 2020-05-15** -- it has to predict the rupture from the historical record.

The comparison is at matched emitted mass against the two controls the brief names:
smoothed earthquake density (the density band the task forbids as an input) and a uniform
random field.  Instruments:
  A  the 2020-2021 sequence trend (the unmapped rupture)   -- the test
  B  USGS SGMC faults > 300 m from the given catalogue       -- broad off-catalogue inventory
  C  the given catalogue raster                              -- anti-instrument, printed last
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

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "src"))

from gems50 import catalog as gcat, emission, lineation  # noqa: E402
from gems50 import dti as metric  # noqa: E402
from gems50 import grid_io as grid  # noqa: E402

CUTOFF = pd.Timestamp("2020-05-15", tz="UTC")
MC_POINT = (425569.0, 4224896.0)  # USGS epicentre of the 2020-05-15 Mw 6.5 event


def mc_truth(g):
    """Trend of the 2020-2021 Monte Cristo sequence = the unmapped rupture (1 px wide)."""
    from pyproj import Transformer
    df = pd.read_csv(REPO / "data/external/usgs_comcat_earthquakes.csv.gz", low_memory=False)
    tr = Transformer.from_crs("EPSG:4326", "EPSG:32611", always_xy=True)
    x, y = tr.transform(df["longitude"].to_numpy(), df["latitude"].to_numpy())
    t = pd.to_datetime(df["time"], format="ISO8601", utc=True)
    sel = ((t >= "2020-05-15") & (t <= "2022-01-01")
           & (np.hypot(x - MC_POINT[0], y - MC_POINT[1]) < 30000))
    X = np.column_stack([x[sel], y[sel]])
    mu = X.mean(axis=0)
    mu = np.append(mu, 0.0)[:3]
    _, vecs = np.linalg.eigh(np.cov((X - X.mean(axis=0)).T))
    v = vecs[:, 1]
    ts = np.linspace(-14000, 14000, 281)
    out = np.zeros(g.shape, bool)
    cc, rr = g.col_row(mu[0] + ts * v[0], mu[1] + ts * v[1])
    ok = (cc >= 0) & (cc < g.width) & (rr >= 0) & (rr < g.height)
    out[rr[ok], cc[ok]] = True
    return out, X


def main() -> int:
    t0 = time.time()
    g = grid.load_grid()
    valid = grid.load_valid_mask()
    labels = grid.load_labels()
    d_lab = distance_transform_edt(~labels)
    with rasterio.open(REPO / "data/external/derived_sgmc_faults_100m_u8.tif") as s:
        sgmc = s.read(1) > 0
    sgmc_off = sgmc & (d_lab > 3) & valid
    mc, X2020 = mc_truth(g)
    print(f"2020 sequence events {len(X2020)}; truth cells {int(mc.sum())}; "
          f"sgmc_off {int(sgmc_off.sum())}", flush=True)

    cat = gcat.build_catalog(REPO / "data/external/usgs_comcat_earthquakes.csv.gz",
                             min_magnitude=1.5, max_depth_km=20.0, start_year=1970)
    df = cat.frame
    before = pd.to_datetime(df["time"], utc=True) < CUTOFF
    xy = cat.xy[before.to_numpy()]
    t = df["t_years"].to_numpy()[before.to_numpy()]
    h = df["h_err_km"].to_numpy()[before.to_numpy()] * 1000.0
    print(f"pre-2020 events {len(xy)}", flush=True)

    near = np.hypot(xy[:, 0] - MC_POINT[0], xy[:, 1] - MC_POINT[1]) < 40000
    print(f"  of which within 40 km of Monte Cristo: {int(near.sum())}", flush=True)

    # --- detector: OADC-style split clusters + spines, exactly as shipped -------------
    clusters = lineation.cluster_lineations(xy, t, h, eps_m=3000.0, min_samples=15,
                                            delta_m=600.0, min_events=12)
    labels_ = lineation.dbscan_labels(xy, t, h, eps_m=3000.0, min_samples=15)
    spines = lineation.cluster_spines(xy, labels_, min_events=15, n_bins=24)
    corridors = np.zeros(g.shape, bool)
    for i in range(len(clusters)):
        n = max(int(2 * clusters.half_length_m[i] / 100.0) + 1, 2)
        off = np.linspace(-clusters.half_length_m[i], clusters.half_length_m[i], n)
        cc, rr = g.col_row(clusters.x[i] + off * clusters.ux[i], clusters.y[i] + off * clusters.uy[i])
        ok = (rr >= 0) & (rr < g.height) & (cc >= 0) & (cc < g.width)
        corridors[rr[ok], cc[ok]] = True
    for pts in spines:
        for k in range(len(pts) - 1):
            n = max(int(np.hypot(*(pts[k + 1] - pts[k])) / 300.0) + 1, 2)
            cc, rr = g.col_row(np.linspace(pts[k, 0], pts[k + 1, 0], n),
                               np.linspace(pts[k, 1], pts[k + 1, 1], n))
            ok = (rr >= 0) & (rr < g.height) & (cc >= 0) & (cc < g.width)
            corridors[rr[ok], cc[ok]] = True
    mass = int(corridors.sum())
    print(f"pre-2020 corridors: {len(clusters)} clusters, {len(spines)} spines, {mass} px "
          f"({time.time()-t0:.0f}s)", flush=True)

    # --- controls at matched mass -----------------------------------------------------
    dens = np.zeros(g.shape, dtype=np.float32)
    cc, rr = g.col_row(xy[:, 0], xy[:, 1])
    ok = (rr >= 0) & (rr < g.height) & (cc >= 0) & (cc < g.width)
    np.add.at(dens, (rr[ok], cc[ok]), 1.0)
    dens_blur = ndimage.gaussian_filter(dens, 10.0)

    verdicts = {}
    ways = {"corridors (this work)": corridors}
    for thr in (0.0,):
        pass
    # density: take the top `mass` cells of the smoothed density *inside the survey*
    # (ranking the whole rectangle would place the control outside the AOI, where it can
    #  credit nothing -- the bug this line exists to prevent)
    cand = np.flatnonzero(valid.ravel())
    rank = cand[np.argsort(-dens_blur.ravel()[cand])]
    for sig, label in ((10.0, "sigma=10 px"), (20.0, "sigma=20 px")):
        b = ndimage.gaussian_filter(dens, sig)
        r2 = cand[np.argsort(-b.ravel()[cand])][:mass]
        sup = np.zeros(dens.size, bool)
        sup[r2] = True
        ways[f"smoothed earthquake density ({label}), top {mass} px in survey"] = sup.reshape(g.shape)
    rng = np.random.default_rng(20261006)
    rnd = np.zeros(dens.size, bool)
    rnd[rng.choice(np.flatnonzero(valid.ravel()), size=mass, replace=False)] = True
    ways["uniform random, matched mass"] = rnd.reshape(g.shape)

    for name, sup in ways.items():
        row = {"mass": int(sup.sum())}
        for inst_name, truth in (("mc_rupture_2020", mc), ("sgmc_off_catalogue", sgmc_off),
                                 ("given_catalogue", labels)):
            r = metric.dti_parts(sup.astype(np.float32), truth)
            row[inst_name] = {"credit_per_px": r.tpw / max(int(sup.sum()), 1), "tpw": r.tpw,
                              "truth_px": r.truth_cells,
                              "covered_frac": r.tpw / max(r.truth_cells, 1)}
        verdicts[name] = row
        print(f"  {name:44s} mass={row['mass']:6d} "
              f"c_mc={row['mc_rupture_2020']['credit_per_px']:.5f} "
              f"mc_cov={row['mc_rupture_2020']['covered_frac']:.3f} "
              f"c_sgmc={row['sgmc_off_catalogue']['credit_per_px']:.5f} "
              f"c_cat={row['given_catalogue']['credit_per_px']:.5f}", flush=True)

    out = {"cutoff": str(CUTOFF), "events_before_cutoff": int(len(xy)),
           "events_before_cutoff_within_40km": int(near.sum()),
           "n_clusters": int(len(clusters)), "n_spines": len(spines),
           "monte_cristo_truth_px": int(mc.sum()), "results": verdicts,
           "note": "the detector sees only events before 2020-05-15; the 2020-2021 sequence "
                   "supplies the truth trend, so this test cannot reward memorising the rupture"}
    path = REPO / "evidence" / "falsification_test.json"
    path.write_text(json.dumps(out, indent=1))
    print(f"wrote {path}  ({time.time()-t0:.0f}s)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
