#!/usr/bin/env python3
"""Spatially blocked validation of every candidate field, at equal dot budget.

Two frames (both proxies; the only official numbers are on the leaderboard):

F1  catalogue folds   — the published USGS/INGENIOUS catalogue split into four
    spatial blocks.  Truth = catalogue pixels inside the held-out block, after
    removing pixels within 1 km of catalogue pixels outside the block (seam
    control).  Domain = the block.  This is the frame the project's earlier work
    used, and it is known to reward placing mass on the catalogue; it is a screen.

F2  SGMC off-catalogue — truth = USGS State Geologic Map Compilation fault pixels
    that lie MORE THAN 1 km from every competition-catalogue pixel, i.e. structures
    the Quaternary catalogue does not contain.  Domain = the footprint outside a
    200 m buffer of the catalogue.  This is the frame that most resembles the
    competition's hidden inventory ("new faults not in the public catalogue").

Both frames score with the official metric at equal dot budget, so a field can only
win by placing its dots better, not by emitting more of them.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import rasterio

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from gems50 import emitter, grid, metric, validate  # noqa: E402

WORK = Path("/tmp/gems50")
CACHE = WORK / "cache"
LABELS = Path("/tmp/gems_work/labels.tif")
SGMC = Path("/tmp/gems_work/external/derived_sgmc_faults_100m_u8.tif")

BUDGETS = (5_000, 20_000, 44_090)


def load(name: str) -> np.ndarray:
    return np.load(CACHE / f"comp_{name}.npy")


def catalogue() -> np.ndarray:
    with rasterio.open(LABELS) as s:
        return s.read(1) == 1


def sgmc_off_catalogue() -> tuple:
    from scipy.ndimage import distance_transform_edt

    with rasterio.open(SGMC) as s:
        sg = s.read(1) == 1
    cat = catalogue()
    d = distance_transform_edt(~cat)
    truth = sg & (d > 10.0)          # > 1 km from any catalogue pixel
    return truth, cat


def emit_budget(belief: np.ndarray, n: int, domain: np.ndarray, spacing: float = 2.83):
    d = emitter.emit(belief * domain, target_score=0.0, domain=domain,
                     max_dots=n, min_spacing_px=spacing)
    return d


def main() -> int:
    fp = np.load(WORK / "footprint.npy")
    cat = catalogue()
    fields = {k: load(k) for k in ("struct", "scarp", "seis", "cont")}
    rng = np.random.default_rng(23)
    fields["random"] = (rng.random(grid.SHAPE) < 0.06).astype(np.float32) * fp

    # smoothed epicentre density baseline (the comparison the brief demands)
    from scipy.ndimage import gaussian_filter

    import csv as _csv
    dens = np.zeros(grid.SHAPE, dtype=np.float32)
    rows, cols = [], []
    with open("data/external/usgs_comcat_earthquakes.csv", newline="") as fh:
        for r in _csv.DictReader(fh):
            try:
                m = float(r["mag"]); d = float(r["depth"])
            except (TypeError, ValueError):
                continue
            if m < 2.0 or not np.isfinite(d) or d > 30.0:
                continue
            rows.append(float(r["latitude"])); cols.append(float(r["longitude"]))
    from pyproj import Transformer
    tr = Transformer.from_crs("EPSG:4326", grid.CRS, always_xy=True)
    x, y = tr.transform(np.array(cols), np.array(rows))
    cc = np.round((x - grid.TRANSFORM[2]) / 100.0).astype(int)
    rr = np.round((y - grid.TRANSFORM[5]) / -100.0).astype(int)
    ok = (rr >= 0) & (rr < grid.SHAPE[0]) & (cc >= 0) & (cc < grid.SHAPE[1])
    np.add.at(dens, (rr[ok], cc[ok]), 1.0)
    dens = gaussian_filter(dens, 3.0)          # 300 m smoothing = the metric's own scale
    dens = dens / max(dens.max(), 1e-9) * fp
    fields["density_300m"] = dens.astype(np.float32)

    results: dict = {"frames": {}}

    # ---------------- F1: catalogue folds --------------------------------------
    fold_labels = validate.folds(grid.SHAPE, 2, 2, fp)
    truth_cat, domain_fn = {}, {}
    for f in range(4):
        t, dom = validate.scored_truth_frame(cat, fold_labels, f, min_distance_px=10.0)
        truth_cat[f] = t
        domain_fn[f] = dom & (fold_labels == f)          # score inside the block only
    results["frames"]["F1_catalogue_folds"] = dict(
        truth_px={f: int(truth_cat[f].sum()) for f in range(4)},
        note="truth = held-out block's catalogue, minus a 1 km seam buffer; domain = block only")

    # the required falsification test: corridors vs smoothed density
    results["F1_truth_px_total"] = int(sum(truth_cat[f].sum() for f in range(4)))

    # ---------------- F2: SGMC off-catalogue -----------------------------------
    truth_sgmc, cat2 = sgmc_off_catalogue()
    from scipy.ndimage import distance_transform_edt
    d_cat = distance_transform_edt(~cat2)
    domain_sgmc = fp & (d_cat > 2.0)                     # off-catalogue only
    truth_sgmc_in = truth_sgmc & domain_sgmc
    results["frames"]["F2_sgmc_off_catalogue"] = dict(
        truth_px=int(truth_sgmc_in.sum()),
        truth_px_including_buffer=int(truth_sgmc.sum()),
        note="truth = SGMC fault pixels > 1 km from the competition catalogue")

    out = {}
    for name, field in fields.items():
        out[name] = {}
        for n in BUDGETS:
            dots = emit_budget(field, n, fp)
            # F1
            f1 = []
            for f in range(4):
                r = validate.evaluate(dots, truth_cat[f], domain_fn[f])
                f1.append(r["dti"])
            # F2
            r2 = validate.evaluate(dots, truth_sgmc_in, domain_sgmc)
            out[name][n] = dict(dots=int(dots.sum()), F1_mean=float(np.mean(f1)),
                                F1_folds=[float(x) for x in f1], F2_dti=float(r2["dti"]),
                                F2_tp=float(r2["tp_w"]), F2_fp=float(r2["fp_w"]))
            print(f"{name:12s} n={n:>6d} dots={int(dots.sum()):>6d} "
                  f"F1 {np.mean(f1):.5f}  F2 {r2['dti']:.5f}")
        del field
    (WORK / "field_validation.json").write_text(json.dumps({**results, "scores": out}, indent=1))
    print("wrote", WORK / "field_validation.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
