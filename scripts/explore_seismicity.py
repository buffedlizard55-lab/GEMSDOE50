#!/usr/bin/env python3
"""Exploratory + structural analysis of the official USGS ComCat catalogue.

Prints the statistics that determine the seismicity-lineament prior:
magnitude completeness, location uncertainty, the clustered-vs-background
crossover distance, cluster geometry (inertia tensors) and corridor coverage
relative to the published fault catalogue.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from gems50 import grid, seis  # noqa: E402

CAT = Path("data/external/usgs_comcat_earthquakes.csv")
WORK = Path("/tmp/gems50")


def main() -> int:
    WORK.mkdir(parents=True, exist_ok=True)
    raw = seis.read_comcat(CAT, depth_max_km=1e9, mag_min=None, drop_anthropogenic=False)
    print(f"ComCat rows inside/around the footprint: {len(raw)}")

    # --- magnitude completeness (maximum-curvature estimate) --------------------
    m = raw.mag
    hist, edges = np.histogram(m, bins=np.arange(0.0, 7.0, 0.1))
    # the modal bin of a completeness-limited catalogue approximates Mc
    mc_mode = edges[int(np.argmax(hist))]
    print(f"modal magnitude bin (approx Mc): {mc_mode:.1f}")
    for floor in (1.0, 1.5, 2.0, 2.5, 3.0):
        print(f"  events M>={floor}: {(m >= floor).sum():>7d}")

    # --- depth and location uncertainty ----------------------------------------
    d = raw.depth_km
    he = raw.hor_err_km
    print(f"depth km: p10 {np.nanpercentile(d,10):.1f} median {np.nanmedian(d):.1f} "
          f"p90 {np.nanpercentile(d,90):.1f}")
    print(f"horizontalError km: n={np.isfinite(he).sum()} "
          f"p10 {np.nanpercentile(he,10):.2f} median {np.nanmedian(he):.2f} "
          f"p90 {np.nanpercentile(he,90):.2f}")
    inerr = np.isfinite(he) & (he < 1.0)
    print(f"  events with 1-sigma < 1 km: {inerr.sum()} ({inerr.mean()*100:.1f} %)")

    # --- the working catalogue --------------------------------------------------
    cat = seis.read_comcat(CAT, depth_max_km=30.0, mag_min=2.0)
    inside = seis.inside_footprint(cat)
    cat = cat.subset(inside)
    print(f"\nworking catalogue: M>=2.0, depth<=30 km, inside footprint -> {len(cat)} events")

    cs = seis.correlation_scale(cat, k=1, n_rand=10)
    print(f"clustered/background crossover r_c = {cs['r_c_km']:.2f} km "
          f"(median NN {cs['nn_median_km']:.2f} km vs Poisson {cs['nn_median_random_km']:.2f} km); "
          f"clustered fraction {cs['clustered_fraction']*100:.1f} %")
    tri = seis.triangle_areas(cat)
    print(f"triangle-area statistic (2-D analogue of the tetrahedron test): "
          f"median {np.nanmedian(tri):.3f} km^2, p90 {np.nanpercentile(tri,90):.3f} km^2")

    # --- clustering sweep -------------------------------------------------------
    rows = []
    for eps in (2.0, 3.0, 5.0, 8.0):
        lab = seis.dbscan_labels(cat, eps_km=eps, min_samples=6)
        ncl = len(set(lab)) - (1 if -1 in lab else 0)
        cl = seis.cluster_inertia(cat, lab, min_events=8)
        lin = [c for c in cl if np.isfinite(c.elongation) and c.elongation >= 4.0
               and c.length_km >= 1.0]
        cor = seis.corridor_raster(cl, half_width_px=1.5)
        rows.append(dict(eps_km=eps, clusters=ncl, clusters_ge8=len(cl), linear=len(lin),
                         corridor_px=int((cor > 0).sum())))
        print(f"eps {eps:>4.1f} km: clusters {ncl:>5d} (>=8 events: {len(cl)}) "
              f"linear(elong>=4,len>=1km): {len(lin):>4d}  corridor px {int((cor>0).sum()):>8d}")
    (WORK / "seis_sweep.json").write_text(json.dumps(rows, indent=1))

    # --- the official-fault distance structure of one corridor set --------------
    lab = seis.dbscan_labels(cat, eps_km=5.0, min_samples=6)
    cl = seis.cluster_inertia(cat, lab, min_events=8)
    lin = [c for c in cl if np.isfinite(c.elongation) and c.elongation >= 4.0
           and c.length_km >= 1.0]
    axis = seis.corridor_raster(lin, half_width_px=1.5)
    band = seis.corridor_raster(lin, half_width_px=6.0)
    for name, arr in (("axis(1.5px)", axis), ("band(6px)", band)):
        n = int((arr > 0).sum())
        print(f"{name}: {n} px = {100*n/grid.FOOTPRINT_PX:.3f} % of the footprint "
              f"({n/ (len(lin) if lin else 1):.0f} px per linear cluster)")
    np.save(WORK / "corridor_axis_m2.npy", axis.astype(np.float32))
    np.save(WORK / "corridor_band_m2.npy", band.astype(np.float32))
    meta = [dict(label=c.label, n=c.n, length_km=c.length_km, width_km=c.width_km,
                 elongation=float(c.elongation) if np.isfinite(c.elongation) else None,
                 ani=c.anisotropy, row=c.centroid_row, col=c.centroid_col,
                 lon=c.centroid_lonlat[0], lat=c.centroid_lonlat[1])
            for c in lin]
    (WORK / "linear_clusters_m2.json").write_text(json.dumps(meta, indent=1))
    print(f"wrote {len(meta)} linear clusters to {WORK/'linear_clusters_m2.json'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
