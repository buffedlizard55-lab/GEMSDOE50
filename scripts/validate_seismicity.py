#!/usr/bin/env python3
"""Falsification test required by the brief.

"The hypothesis is that blind faults produce seismic lineations in places the mapped
 catalogue lacks traces ... Falsify it by showing that corridors predict withheld
 fault segments better than smoothed earthquake density."

Frame: the published USGS/INGENIOUS catalogue, split into spatial blocks.  For each
held-out block the catalogue inside the block is the truth and all catalogue pixels
outside the block are masked out of the scored domain.  Predictors are built from the
*seismicity catalogue alone* (no fault data of any kind), emitted as dots on the
metric's own spacing, and scored with the official metric (alpha=0.2, beta=0.8,
R=300 m).

Predictors compared
  A  seismicity-lineament corridors (this project's adaptation)
  B  smoothed seismicity density, quantile-thresholded (the natural baseline)
  C  uniform random dots inside the footprint (null)
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import rasterio

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from gems50 import grid, metric, seis, validate  # noqa: E402

WORK = Path("/tmp/gems50")
CAT = Path("data/external/usgs_comcat_earthquakes.csv")
LABELS = Path("/tmp/gems_work/labels.tif")


def gaussian_density(cat, shape, sigma_px=8.0):
    """Smoothed epicentre density (the baseline every seismicity method is compared to)."""
    from scipy.ndimage import gaussian_filter

    d = np.zeros(shape, dtype=np.float32)
    r = np.round(cat.row).astype(int)
    c = np.round(cat.col).astype(int)
    ok = (r >= 0) & (r < shape[0]) & (c >= 0) & (c < shape[1])
    np.add.at(d, (r[ok], c[ok]), 1.0)
    return gaussian_filter(d, sigma_px)


def corridors(cat, shape, eps_km=5.0, min_samples=6, min_events=8,
              min_elongation=4.0, min_length_px=6.0, half_width_px=1.5):
    lab = seis.dbscan_labels(cat, eps_km=eps_km, min_samples=min_samples)
    cl = seis.cluster_inertia(cat, lab, min_events=min_events)
    lin = [c for c in cl if np.isfinite(c.elongation) and c.elongation >= min_elongation
           and c.length_km * 10.0 >= min_length_px]
    return seis.corridor_raster(lin, shape=shape, half_width_px=half_width_px), lin


def main() -> int:
    with rasterio.open(LABELS) as s:
        cat_raster = (s.read(1) == 1)
    footprint = np.load(WORK / "footprint.npy") if (WORK / "footprint.npy").exists() else None
    if footprint is None:
        with rasterio.open("/tmp/gems_work/sample_submission.tif") as s:
            footprint = np.isfinite(s.read(1))
        np.save(WORK / "footprint.npy", footprint)

    events = seis.read_comcat(CAT, depth_max_km=30.0, mag_min=2.0)
    events = events.subset(seis.inside_footprint(events))
    print(f"events: {len(events)}")

    fold_labels = validate.folds(grid.SHAPE, 2, 2, footprint)
    n_folds = int(fold_labels.max()) + 1
    spacing = 2.83

    # --- A: corridors -----------------------------------------------------------
    corr, lin = corridors(events, grid.SHAPE)
    corr = corr * footprint
    print(f"A corridors: {int((corr>0).sum())} px, {len(lin)} linear clusters")

    # --- B: density, quantile-thresholded so that the emitted AREA matches A ----
    dens = gaussian_density(events, grid.SHAPE) * footprint
    area_A = int((corr > 0).sum())
    thr = np.quantile(dens[footprint & (dens > 0)], 1.0 - min(1.0, area_A / max(1, (dens > 0).sum()))) \
        if (dens > 0).any() else 0.0
    dens_mask = (dens >= thr) & footprint

    rng = np.random.default_rng(11)
    rand_mask = (rng.random(grid.SHAPE) < area_A / grid.FOOTPRINT_PX) & footprint
    print(f"B density: {int(dens_mask.sum())} px (area-matched to A); "
          f"C random: {int(rand_mask.sum())} px")

    # --- dots -------------------------------------------------------------------
    dots_A = validate.emit_dots_along(corr > 0, spacing)
    dots_B = validate.emit_dots_along(dens_mask, spacing, weight=dens)
    dots_C = validate.emit_dots_along(rand_mask, spacing)
    print(f"dots A={dots_A.sum()} B={dots_B.sum()} C={dots_C.sum()}")

    results = {}
    for name, dots in (("A_corridors", dots_A), ("B_density", dots_B), ("C_random", dots_C)):
        per_fold = []
        for f in range(n_folds):
            truth, domain = validate.scored_truth_frame(cat_raster, fold_labels, f)
            if truth.sum() == 0:
                continue
            r = validate.evaluate(dots, truth, domain)
            per_fold.append(r["dti"] * 1.0)
            per_fold[-1] = dict(dti=r["dti"], n_truth=int(truth.sum()),
                                n_pred=r["n_pred"], tp_w=r["tp_w"], fp_w=r["fp_w"])
        results[name] = per_fold
        dtis = [p["dti"] for p in per_fold]
        print(f"{name}: folds {['%.4f' % d for d in dtis]}  mean {np.mean(dtis):.4f}")

    # --- off-catalogue structure of the corridors -------------------------------
    from scipy.ndimage import distance_transform_edt

    d_cat = distance_transform_edt(~cat_raster)
    corr_px = np.argwhere((corr > 0) & footprint)
    dd = d_cat[corr_px[:, 0], corr_px[:, 1]]
    out = dict(
        corridor_px=int(corr_px.shape[0]),
        frac_within_200m_of_catalogue=float((dd <= 2).mean()),
        frac_within_500m_of_catalogue=float((dd <= 5).mean()),
        median_distance_to_catalogue_px=float(np.median(dd)),
        dots_A=int(dots_A.sum()), dots_B=int(dots_B.sum()), dots_C=int(dots_C.sum()),
        per_fold=results,
    )
    print(json.dumps({k: v for k, v in out.items() if k != "per_fold"}, indent=1))
    (WORK / "falsification.json").write_text(json.dumps(out, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
