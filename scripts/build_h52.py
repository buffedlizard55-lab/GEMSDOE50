"""Build the GEMSDOE50 H52 submission raster.

Inputs (all public / competition-provided; nothing is read from a previous
submission):
  * the competition's own ``training_features.tif`` (19 bands, EPSG:32611),
  * ``topo_u8.tif`` and ``radiometric_u8.tif`` — quantised derivatives of
    official USGS products carried in the sibling transport repo,
  * ``lidar_scarp_features_u8.tif`` — derivatives of USGS 3DEP 1 m DEM tiles,
  * the competition's ``example_submission.tif`` (grid + footprint template)
    and ``existing_faults.tif`` (the provided catalogue, used only as a
    measured exclusion mask).

Output: one single-band float32 GeoTIFF on the template grid, values in {0, 1}
inside the footprint and NaN outside, plus an all-finite twin.

    python scripts/build_h52.py --inputs DIR --out-dir DIR --budget 40000
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import rasterio
from scipy.ndimage import distance_transform_edt, gaussian_filter

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from gemsdoe50.coincidence import coincidence_score, greedy_isolated_emission

TAU = 0.90
BLOCK_RADIUS_PX = 2
CATALOGUE_BUFFER_M = 200.0
FAMILIES = {
    # family -> (source key, band indices)
    "T": ("features", [12, 19]),                       # detrended elevation + slope
    "S": ("topo", [1, 2, 3, 4, 5, 6, 7, 8, 9]),        # 10 m topographic descriptors
    "L": ("scarp", list(range(1, 13))),                # 1 m-DEM-derived scarp descriptors
    "R": ("radiometric", [1, 2, 3, 4, 5, 6, 7]),      # airborne radiometrics + ratios
    "D": ("geodawn_rad", [1, 2, 3, 4]),                # independent radiometric mosaic
    "P": ("features", [1, 2, 3, 9, 11, 13, 14, 15, 18, 6, 5]),   # potential field
    "G": ("features", [4, 7, 8, 17]),                  # geodetic strain + conductivity
    "Q": ("features", [10, 16]),                       # seismicity bands (ComCat-derived)
}


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def saliency(a: np.ndarray, valid: np.ndarray, sigmas=(1.5, 3.0, 6.0)) -> np.ndarray:
    """Multi-scale structure-tensor lineament saliency: gradient energy x coherence."""
    out = np.zeros(a.shape, np.float32)
    fill = float(np.nanmedian(a[valid])) if valid.any() else 0.0
    x = np.where(valid, a, fill).astype(np.float32)
    for sg in sigmas:
        gx = gaussian_filter(x, sg, order=(0, 1), mode="nearest")
        gy = gaussian_filter(x, sg, order=(1, 0), mode="nearest")
        rho = 2.0 * sg
        jxx = gaussian_filter(gx * gx, rho, mode="nearest")
        jyy = gaussian_filter(gy * gy, rho, mode="nearest")
        jxy = gaussian_filter(gx * gy, rho, mode="nearest")
        tr = jxx + jyy
        coh = np.sqrt((jxx - jyy) ** 2 + 4.0 * jxy**2) / np.maximum(tr, 1e-20)
        out = np.maximum(out, np.sqrt(np.maximum(tr, 0.0)) * coh)
    out[~valid] = 0.0
    return out


def percentile_rank(field: np.ndarray, valid: np.ndarray) -> np.ndarray:
    """Within-source percentile rank of ``field`` over ``valid`` cells."""
    out = np.zeros(field.shape, np.float32)
    v = field[valid]
    if v.size == 0:
        return out
    order = np.argsort(v, kind="stable")
    r = np.empty(v.size, np.float32)
    r[order] = np.arange(v.size, dtype=np.float32) / max(v.size - 1, 1)
    out[valid] = r
    return out


def family_field(sources: dict, path: Path, bands: list[int]) -> np.ndarray:
    acc = None
    for b in bands:
        with rasterio.open(path) as ds:
            a = ds.read(b).astype(np.float32)
            nod = ds.nodata
        valid = np.isfinite(a)
        if nod is not None:
            valid &= a != np.float32(nod)
        if int(valid.sum()) < 1000:
            continue
        sal = saliency(a, valid)
        q = float(np.percentile(sal[valid], 99.0))
        sal = np.clip(sal / max(q, 1e-30), 0.0, 1.0)
        pct = percentile_rank(sal, valid)
        acc = pct if acc is None else np.maximum(acc, pct)
    if acc is None:
        raise RuntimeError(f"no usable bands in {path}")
    return acc


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--inputs", required=True, type=Path)
    ap.add_argument("--out-dir", required=True, type=Path)
    ap.add_argument("--budget", type=int, default=40000)
    ap.add_argument("--tag", default="r1")
    ap.add_argument(
        "--score-out", type=Path, default=None,
        help="optional path for the coincidence score field (float32, .npy); "
             "the minimum sufficient statistic for re-emitting at another budget",
    )
    ap.add_argument(
        "--agreement-out", type=Path, default=None,
        help="optional path for the count of agreeing families per cell (uint8, .npy)",
    )
    args = ap.parse_args()

    args.out_dir.mkdir(parents=True, exist_ok=True)
    inp = args.inputs
    features = inp / "training_features.tif"
    topo = inp / "topo_u8.tif"
    radiometric = inp / "radiometric_u8.tif"
    scarp = inp / "lidar_scarp_features_u8.tif"
    geodawn_rad = inp / "geodawn_rad_u8.tif"
    template_p = inp / "example_submission.tif"
    labels_p = inp / "existing_faults.tif"
    for p in (features, topo, radiometric, scarp, geodawn_rad, template_p, labels_p):
        if not p.exists():
            print(f"missing input: {p}", file=sys.stderr)
            return 2
    sources = {
        "features": features, "topo": topo, "radiometric": radiometric,
        "scarp": scarp, "geodawn_rad": geodawn_rad,
    }

    with rasterio.open(template_p) as ds:
        template = ds.read(1)
        profile = ds.profile.copy()
        raster_transform = ds.transform
    footprint = np.isfinite(template)          # the organizer's own valid mask
    with rasterio.open(labels_p) as ds:
        labels = ds.read(1)
    catalogue = labels == 1

    family_percentiles = []
    family_names = sorted(FAMILIES)
    for name in family_names:
        key, bands = FAMILIES[name]
        family_percentiles.append(family_field(sources, sources[key], bands))
    P = np.stack(family_percentiles)
    del family_percentiles

    score = coincidence_score(P, tau=TAU)
    agreement = (P >= TAU).sum(axis=0)

    distance_to_catalogue_m = distance_transform_edt(~catalogue) * 100.0
    allowed = footprint & (distance_to_catalogue_m >= CATALOGUE_BUFFER_M)
    score = np.where(allowed, score, -1.0)

    if args.score_out is not None:
        args.score_out.parent.mkdir(parents=True, exist_ok=True)
        np.save(args.score_out, score.astype(np.float32))
    if args.agreement_out is not None:
        args.agreement_out.parent.mkdir(parents=True, exist_ok=True)
        np.save(args.agreement_out, (P >= TAU).sum(axis=0).astype(np.uint8))

    accepted = greedy_isolated_emission(score, allowed, args.budget, BLOCK_RADIUS_PX)
    if int(accepted.sum()) < args.budget:
        print(f"note: only {int(accepted.sum())} of {args.budget} cells could be placed", file=sys.stderr)

    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")

    # --- primary: all-finite (no nodata tag), 0 outside the organizer footprint
    allfin = np.zeros(template.shape, dtype=np.float32)
    allfin[accepted] = 1.0
    primary = args.out_dir / f"gems50-h52-coincidence8-{int(accepted.sum())}-{stamp}.tif"
    profile.update(
        driver="GTiff", count=1, dtype="float32", compress="deflate",
        predictor=2, tiled=False, nodata=None,
    )
    with rasterio.open(primary, "w", **profile) as ds:
        ds.write(allfin, 1)

    # --- twin: literal published encoding (NaN outside the footprint, no nodata tag)
    nanout = np.where(footprint, allfin, np.float32("nan")).astype(np.float32)
    profile.update(nodata=float("nan"))
    twin = args.out_dir / f"{primary.stem}-nanoutside.tif"
    with rasterio.open(twin, "w", **profile) as ds:
        ds.write(nanout, 1)

    def digest(path: Path) -> dict:
        with rasterio.open(path) as ds:
            a = ds.read(1)
        finite = np.isfinite(a)
        rec = {
            "bytes": path.stat().st_size,
            "sha256": sha256_file(path),
            "driver": "GTiff", "count": 1, "dtype": str(a.dtype),
            "shape": [int(a.shape[0]), int(a.shape[1])],
            "crs": "EPSG:32611",
            "transform": [float(v) for v in raster_transform][:6],
            "nodata": None if ds.nodata is None or np.isnan(ds.nodata) else float(ds.nodata),
            "finite_cells": int(finite.sum()),
            "nan_cells": int((~finite).sum()),
            "min": float(a[finite].min()),
            "max": float(a[finite].max()),
            "values_outside_0_1": int(((a[finite] < 0.0) | (a[finite] > 1.0)).sum()),
            "positive_cells": int((a[finite] > 0).sum()),
            "outside_footprint_nonzero": int((a[finite & ~footprint] > 0).sum()),
        }
        return rec

    evidence = {
        "schema": "gemsdoe50.h52.build.v1",
        "built_utc": datetime.now(timezone.utc).isoformat(),
        "budget": args.budget,
        "emitted": int(accepted.sum()),
        "block_radius_px": BLOCK_RADIUS_PX,
        "tau": TAU,
        "catalogue_buffer_m": CATALOGUE_BUFFER_M,
        "families": {k: FAMILIES[k][1] for k in family_names},
        "family_order": family_names,
        "agreement_composition": {
            str(k): int((agreement[accepted] == k).sum()) for k in range(len(family_names) + 1)
            if int((agreement[accepted] == k).sum()) > 0
        },
        "dots_on_catalogue": int((accepted & catalogue).sum()),
        "dots_within_200m_of_catalogue": int((accepted & (distance_to_catalogue_m < CATALOGUE_BUFFER_M)).sum()),
        "min_distance_to_catalogue_m": float(distance_to_catalogue_m[accepted].min()),
        "inputs": {
            "training_features.tif": sha256_file(features),
            "topo_u8.tif": sha256_file(topo),
            "radiometric_u8.tif": sha256_file(radiometric),
            "lidar_scarp_features_u8.tif": sha256_file(scarp),
            "geodawn_rad_u8.tif": sha256_file(geodawn_rad),
            "example_submission.tif": sha256_file(template_p),
            "existing_faults.tif": sha256_file(labels_p),
        },
        "score_field_sha256": (sha256_file(args.score_out) if args.score_out is not None else None),
        "primary": digest(primary),
        "twin": digest(twin),
    }
    evidence["primary"]["path"] = str(primary)
    evidence["twin"]["path"] = str(twin)
    (args.out_dir / f"{primary.stem}.build.json").write_text(json.dumps(evidence, indent=1))
    print(json.dumps({k: evidence[k] for k in
                      ("emitted", "agreement_composition", "dots_on_catalogue",
                       "min_distance_to_catalogue_m")}, indent=1))
    print(json.dumps(evidence["primary"], indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
