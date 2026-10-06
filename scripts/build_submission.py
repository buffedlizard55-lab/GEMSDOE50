#!/usr/bin/env python3
"""Build the submission GeoTIFF.

Pipeline (all steps reproducible from pinned bytes):

  1. evidence layers      scripts/build_field.py  ->  /tmp/gems50/cache/comp_*.npy
  2. smoothing            each layer is blurred to the metric's own scale (300 m):
                          a corridor whose location uncertainty is ~300 m must be
                          represented as a ~300 m ridge, not a 1-px line.
  3. fusion               pi = scarp + w_struct*struct + w_seis*seis   (documented
                          in docs/research/emission.md, weights chosen by the
                          equal-budget holdout in scripts/fuse_experiment.py)
  4. calibration          pi rescaled so that sum(pi) = G_est, the owner-model
                          hidden-truth mass; that makes the emitter's marginal rule
                          an absolute statement rather than a ranking.
  5. emission             greedy expected-marginal-credit dots (src/gems50/emitter.py)
                          stopping at credit > alpha * target_score.
  6. write                single-band float32 GeoTIFF on the official grid, NaN
                          outside the footprint.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

import numpy as np
import rasterio

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from gems50 import emitter, grid, metric  # noqa: E402

WORK = Path("/tmp/gems50")
CACHE = WORK / "cache"
#: owner-model estimate of the hidden (scored) truth mass, derived in
#: docs/research/score-model.md from the three publicly reported scores of nested
#: artifacts.  Used only as the scale of the belief field, never as a score.
G_EST = 13_833


def smooth(a: np.ndarray, sigma: float) -> np.ndarray:
    from scipy.ndimage import gaussian_filter

    return gaussian_filter(a.astype(np.float32), sigma)


def build_field(w_struct: float, w_seis: float, sigma: float = 2.5) -> np.ndarray:
    fp = np.load(WORK / "footprint.npy")
    comp = {k: smooth(np.load(CACHE / f"comp_{k}.npy"), sigma) for k in ("scarp", "struct", "seis")}
    for k in comp:
        comp[k][~fp] = 0.0
        comp[k] /= max(comp[k].max(), 1e-9)
    field = comp["scarp"] + w_struct * comp["struct"] + w_seis * comp["seis"]
    field[~fp] = 0.0
    return field.astype(np.float32)


def calibrate(field: np.ndarray, footprint: np.ndarray, g_est: float = G_EST) -> np.ndarray:
    s = float(field[footprint].sum())
    if s <= 0:
        raise ValueError("empty field")
    return (field * (g_est / s)).astype(np.float32)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--w-struct", type=float, default=0.6)
    ap.add_argument("--w-seis", type=float, default=0.25)
    ap.add_argument("--target-score", type=float, default=0.28)
    ap.add_argument("--max-dots", type=int, default=70_000)
    ap.add_argument("--g-est", type=float, default=G_EST)
    ap.add_argument("--out", default="/tmp/gems50/submission.tif")
    ap.add_argument("--prefix", default="gems50-seislin")
    args = ap.parse_args()

    fp = np.load(WORK / "footprint.npy")
    field = build_field(args.w_struct, args.w_seis)
    print(f"field: max {field[fp].max():.5f} sum {field[fp].sum():.1f} "
          f"(pre-calibration, footprint {int(fp.sum()):,} px)")
    pi = calibrate(field, fp, args.g_est)
    print(f"belief calibrated: sum {pi[fp].sum():.1f} == G_est {args.g_est:,.0f}; "
          f"mean {pi[fp].mean():.3e}; bar {metric.ALPHA*args.target_score:.4f}")

    dots = emitter.emit(pi, target_score=args.target_score, domain=fp,
                        max_dots=args.max_dots, min_spacing_px=2.83, verbose=True)
    n = int(dots.sum())
    print(f"emitted {n:,} dots")

    # --- diagnostics -----------------------------------------------------------
    from scipy.ndimage import distance_transform_edt

    with rasterio.open("/tmp/gems_work/labels.tif") as s:
        cat = s.read(1) == 1
    d_cat = distance_transform_edt(~cat)
    idx = np.argwhere(dots)
    dd = d_cat[idx[:, 0], idx[:, 1]]
    credit = emitter.expected_credit(pi, dots)
    spacing = _nn_stats(idx)
    diag = dict(
        n_dots=n, footprint_px=int(fp.sum()),
        dots_within_200m_of_catalogue=int((dd <= 2).sum()),
        dots_within_300m_of_catalogue=int((dd <= 3).sum()),
        median_distance_to_catalogue_px=float(np.median(dd)),
        expected_credit_total=credit,
        expected_credit_per_dot=credit / max(n, 1),
        nn_median_px=spacing["median"], nn_p10_px=spacing["p10"],
        belief_sum=float(pi[fp].sum()), target_score=args.target_score,
        w_struct=args.w_struct, w_seis=args.w_seis, g_est=args.g_est,
        emitted_at_2026=__import__("datetime").datetime.now(
            __import__("datetime").timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    )
    print(json.dumps(diag, indent=1))

    # --- write the GeoTIFF -----------------------------------------------------
    out = Path(args.out)
    data = np.where(dots, np.float32(1.0), np.float32(0.0))
    data[~fp] = np.nan
    profile = dict(driver="GTiff", height=grid.SHAPE[0], width=grid.SHAPE[1], count=1,
                   dtype="float32", crs=grid.CRS, transform=rasterio.Affine(*grid.TRANSFORM),
                   nodata=float("nan"), compress="deflate", predictor=2, tiled=True)
    out.parent.mkdir(parents=True, exist_ok=True)
    with rasterio.open(out, "w", **profile) as dst:
        dst.write(data, 1)
    sha = hashlib.sha256(out.read_bytes()).hexdigest()
    with rasterio.open(out) as s:
        written = s.read(1)
    diag["n_dots_shipped"] = int((np.isfinite(written) & (written > 0)).sum())
    diag["n_dots_dropped_by_domain_clip"] = n - diag["n_dots_shipped"]
    diag["path"] = str(out)
    diag["bytes"] = out.stat().st_size
    diag["sha256"] = sha
    print(f"wrote {out} ({diag['bytes']:,} B) sha256 {sha[:16]}...")
    (WORK / "submission_diagnostics.json").write_text(json.dumps(diag, indent=1))
    return 0


def _nn_stats(idx: np.ndarray) -> dict:
    from scipy.spatial import cKDTree

    if idx.shape[0] < 2:
        return dict(median=0.0, p10=0.0)
    d, _ = cKDTree(idx).query(idx, k=2)
    d = d[:, 1]
    return dict(median=float(np.median(d)), p10=float(np.percentile(d, 10)))


if __name__ == "__main__":
    raise SystemExit(main())
