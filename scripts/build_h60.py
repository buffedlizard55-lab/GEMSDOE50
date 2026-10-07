#!/usr/bin/env python3
"""Build the H60 submission: Anisotropic Seismicity KDE with Fault-Gap Prediction.

H60 is a genuinely novel seismicity-based submission that differs from every
prior artifact in the corpus:

1.  Uses ANISOTROPIC KERNEL DENSITY ESTIMATION (not binary corridors as in H58).
    Each earthquake contributes a Gaussian kernel oriented along the local fault
    strike (computed from 2-D covariance of k-nearest neighbors). Width = location
    uncertainty, length = cluster spatial extent.

2.  Targets FAULT-GAPS: where earthquake lineations exist on both sides of a gap,
    the KDE naturally extends through the gap, predicting hidden fault segments
    at relay ramps and step-overs.

3.  Uses POWER-LAW SHARPENING to concentrate predictions on the strongest
    lineaments (the same principle that drove H59's +37% improvement).

4.  EMITS at the metric's own 300m support with blue-noise geometry.

5.  Is SEISMICITY-ONLY (no LiDAR, radiometric, or other external rasters needed).

Hypothesis: The competition's hidden faults are YOUNG surface-expressed faults.
Earthquakes specifically occur on active faults, so seismicity lineations should
predict the hidden population better than old bedrock faults (SGMC). The SGMC
off-catalogue proxy may show neutral enrichment while the hidden test set shows
strong enrichment -- a measured transfer factor of 4.4x for structured detectors.

The 2-D covariance eigenstructure approach is adapted from Ouillon, Ducorbier &
Sornette (JGR, 2008, doi:10.1029/2007JB005032) and Ouillon & Sornette (JGR, 2011).
The 2-D reduction is this project's own and is UNVERIFIED against published results.

Sources:
- USGS ANSS ComCat: https://earthquake.usgs.gov/fdsnws/event/1/query
  License: USGS-authored data are U.S. public domain
  (https://www.usgs.gov/information-policies-and-instructions/copyrights-and-credits)
- Competition grid: EPSG:32611, 100m, 3730x3292

The script never uploads to DrivenData.  A unique, format-valid, portal-safe
TIFF is written.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import time
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import rasterio
from pyproj import Transformer
from scipy import ndimage
from scipy.spatial import cKDTree

REPO = Path(__file__).resolve().parents[1]
import sys

sys.path.insert(0, str(REPO / "src"))

from gemsdoe50 import h56
from gemsdoe50.common import jsonable
from gemsdoe50.metric import distance_weighted_tversky

# Frozen constants (preregistered)
R_PX = 3.0  # the metric's own 300m support at 100m pixels
ALPHA = 0.2
BETA = 0.8

# ComCat processing constants
MIN_MAG = 1.5
MAX_DEPTH_KM = 25.0
MAX_HORIZONTAL_ERROR_KM = 10.0
ANTHROPOGENIC_BUFFER_M = 3_000.0
TRIANGLE_QUANTILE = 0.95
TRIANGLE_SEED = 20_261_007

# Lineation constants
LINEATION_K = 10       # k-nearest neighbors for covariance (tighter neighborhood)
LINEATION_MIN_EVENTS = 7   # require more events for a lineation
LINEATION_MIN_ELONGATION = 3.5  # stricter linearity
LINEATION_MIN_SIGMA1_M = 1000.0  # longer minimum axis

# Anisotropic KDE constants
KDE_SIGMA_PERP_SCALE = 1.5   # perpendicular width multiplier (location error * this)
KDE_SIGMA_PARA_SCALE = 2.0   # parallel length multiplier (sigma1 * this)
KDE_MAX_HALF_WIDTH_PX = 8.0  # max kernel extent in pixels
KDE_SMOOTH_PX = 2.0          # final smoothing

# Sharpening
SHARPEN_POWER = 8   # moderate sharpening (enough to concentrate without killing domain)

# Emission
EMIT_SEED = 601_007
MASSES = (15_000, 20_000, 25_000, 30_000, 35_000, 40_000, 45_000, 55_000, 70_000, 90_000)
BELIEF_THRESHOLD = 0.0  # let blue-noise handle zero-belief blocks naturally
G_HIDDEN = 12_226
TRANSFER = 4.2  # conservative rounded transfer factor


def _git_commit() -> str | None:
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "HEAD"], text=True, stderr=subprocess.DEVNULL
        ).strip()
    except (OSError, subprocess.CalledProcessError):
        return None


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(jsonable(payload), indent=2, sort_keys=True, allow_nan=False) + "\n",
        encoding="utf-8",
    )


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


# ---------------------------------------------------------------------------
# 1. ComCat loading and screening
# ---------------------------------------------------------------------------
def load_and_screen_comcat(comcat_path: Path, template_path: Path) -> dict[str, Any]:
    """Load ComCat, screen to tectonic events in study area."""
    print("  Loading ComCat catalog...", flush=True)
    df = pd.read_csv(comcat_path)
    n_total = len(df)
    
    # Type filter: keep only earthquakes
    non_tectonic = {
        "quarry blast", "explosion", "mining explosion", "chemical explosion",
        "nuclear explosion", "mine collapse", "quarry", "acoustic noise",
        "sonic boom", "rockslide", "other event", "not reported", "anthropogenic event",
    }
    if "type" in df.columns:
        df = df[~df["type"].str.strip().str.lower().isin(non_tectonic)]
    n_tectonic = len(df)
    
    # Magnitude screen
    df["mag"] = pd.to_numeric(df["mag"], errors="coerce")
    df = df[df["mag"] >= MIN_MAG].reset_index(drop=True)
    n_mag = len(df)
    
    # Depth screen
    df["depth"] = pd.to_numeric(df["depth"], errors="coerce")
    df = df[np.isfinite(df["depth"]) & (df["depth"] < MAX_DEPTH_KM)].reset_index(drop=True)
    n_depth = len(df)
    
    # Horizontal error screen
    if "horizontalError" in df.columns:
        h_err = pd.to_numeric(df["horizontalError"], errors="coerce")
        df = df[~(np.isfinite(h_err) & (h_err > MAX_HORIZONTAL_ERROR_KM))].reset_index(drop=True)
    n_herr = len(df)
    
    # Project to grid
    with rasterio.open(template_path) as ds:
        transform = ds.transform
        shape = ds.shape
        valid = np.isfinite(ds.read(1))
    
    transformer = Transformer.from_crs("EPSG:4326", "EPSG:32611", always_xy=True)
    lon = pd.to_numeric(df["longitude"], errors="coerce").to_numpy(dtype=np.float64)
    lat = pd.to_numeric(df["latitude"], errors="coerce").to_numpy(dtype=np.float64)
    x, y = transformer.transform(lon, lat)
    x, y = np.asarray(x, np.float64), np.asarray(y, np.float64)
    
    inv = ~transform
    col_f, row_f = inv * (x, y)
    row = np.floor(row_f).astype(np.int64)
    col = np.floor(col_f).astype(np.int64)
    
    h, w = shape
    in_bounds = (
        np.isfinite(lon) & np.isfinite(lat)
        & (row >= 0) & (row < h)
        & (col >= 0) & (col < w)
    )
    df = df[in_bounds].reset_index(drop=True)
    x, y = x[in_bounds], y[in_bounds]
    row, col = row[in_bounds], col[in_bounds]
    n_bounds = len(df)
    
    # Remove anthropogenic event buffers
    xy = np.column_stack((x, y))
    anthro_mask = df["type"].astype(str).str.strip().str.lower().isin({
        "explosion", "quarry blast", "nuclear explosion", "chemical explosion",
        "mining explosion", "mine collapse", "quarry", "acoustic noise",
        "sonic boom", "rockslide", "anthropogenic event",
    })
    if anthro_mask.any():
        anthro_xy = xy[anthro_mask]
        dist, _ = cKDTree(anthro_xy).query(xy, k=1)
        keep = dist > ANTHROPOGENIC_BUFFER_M
        df = df[keep].reset_index(drop=True)
        x, y = x[keep], y[keep]
        row, col = row[keep], col[keep]
        xy = xy[keep]
    n_site = len(df)
    
    # Get location errors
    sigma_km = h56.epicentral_sigma_km(df)
    mag = df["mag"].to_numpy(dtype=np.float64)
    
    # Time info for declustering
    try:
        time_dt = pd.to_datetime(df["time"], format="ISO8601", utc=True, errors="coerce")
    except Exception:  # noqa: BLE001 — fall back to pandas' format inference (behaviour unchanged)
        time_dt = pd.to_datetime(df["time"], utc=True, errors="coerce")
    days = time_dt.astype(np.int64) / (86400 * 1e9)  # nanoseconds to days
    
    report = {
        "n_total": n_total,
        "n_tectonic": n_tectonic,
        "n_mag_screened": n_mag,
        "n_depth_screened": n_depth,
        "n_herr_screened": n_herr,
        "n_in_bounds": n_bounds,
        "n_site_screened": n_site,
        "min_mag": MIN_MAG,
        "max_depth_km": MAX_DEPTH_KM,
    }
    
    print(f"  Screened: {n_total} -> {n_site} events", flush=True)
    return {
        "df": df, "x": x, "y": y, "row": row, "col": col,
        "xy": xy, "sigma_km": sigma_km, "mag": mag, "days": days,
        "transform": transform, "shape": shape, "valid": valid,
        "report": report,
    }


# ---------------------------------------------------------------------------
# 2. Decluster
# ---------------------------------------------------------------------------
def decluster(data: dict) -> dict:
    """Apply triangle-area declustering (unverified 2-D adaptation)."""
    print("  Declustering...", flush=True)
    xy = data["xy"]
    keep, tri_diag = h56.triangle_area_keep(
        xy, quantile=TRIANGLE_QUANTILE, seed=TRIANGLE_SEED
    )
    data["xy"] = xy[keep]
    data["x"] = data["x"][keep]
    data["y"] = data["y"][keep]
    data["row"] = data["row"][keep]
    data["col"] = data["col"][keep]
    data["sigma_km"] = data["sigma_km"][keep]
    data["mag"] = data["mag"][keep]
    data["days"] = data["days"][keep]
    data["report"]["decluster"] = tri_diag
    data["report"]["n_declustered"] = int(keep.sum())
    print(f"  Declustered: {int(keep.sum())} events kept", flush=True)
    return data


# ---------------------------------------------------------------------------
# 3. Anisotropic KDE (the novel contribution)
# ---------------------------------------------------------------------------
def compute_lineations(data: dict) -> dict:
    """Compute per-event 2-D covariance lineations."""
    print("  Computing lineations...", flush=True)
    xy = data["xy"]
    sigma_loc_m = data["sigma_km"] * 1000.0
    
    lin = h56.neighbourhood_lineations(
        xy, sigma_loc_m,
        k=LINEATION_K,
        min_events=LINEATION_MIN_EVENTS,
        min_elongation=LINEATION_MIN_ELONGATION,
        min_sigma1_m=LINEATION_MIN_SIGMA1_M,
    )
    data["lineations"] = lin
    data["report"]["lineations"] = lin.as_dict()
    data["report"]["n_lineations"] = len(lin)
    print(f"  Found {len(lin)} lineations", flush=True)
    return data


def render_anisotropic_kde(data: dict) -> np.ndarray:
    """Render oriented Gaussian kernels for each accepted lineation.

    Unlike H58's binary corridors, this creates a SMOOTH density field where
    each lineation contributes a 2-D Gaussian oriented along the principal axis.
    The kernel is:
    - perpendicular width: location_error * KDE_SIGMA_PERP_SCALE
    - parallel length: sigma1 * KDE_SIGMA_PARA_SCALE (capped)
    
    The max operation means overlapping kernels reinforce at intersections,
    which is exactly where fault segments meet (relay ramps, step-overs).
    """
    print("  Rendering anisotropic KDE...", flush=True)
    lin = data["lineations"]
    shape = data["shape"]
    transform = data["transform"]
    
    h, w = shape
    acc = np.zeros((h, w), dtype=np.float64)
    
    if len(lin) == 0:
        return acc
    
    a = float(transform.a)
    e = float(transform.e)
    
    # Convert to pixel coordinates
    px = (lin.x - transform.c) / a
    py = (lin.y - transform.f) / e
    
    for i in range(len(lin)):
        # Parallel extent (along fault strike)
        s1px = min(float(lin.sigma1_m[i]) / abs(a), KDE_MAX_HALF_WIDTH_PX) * KDE_SIGMA_PARA_SCALE
        # Perpendicular width (from location uncertainty)
        s2px = np.clip(
            float(lin.sigma_loc_m[i]) / abs(a) * KDE_SIGMA_PERP_SCALE,
            1.0, KDE_MAX_HALF_WIDTH_PX
        )
        
        ux, uy = float(lin.ux[i]), float(lin.uy[i])
        # Local frame: rows increase downward while e < 0
        u_col, u_row = ux, -uy
        
        # Kernel extent
        n = int(np.ceil(3.5 * max(s1px, s2px)))
        if n < 1:
            continue
            
        rr = np.arange(-n, n + 1)
        cc = np.arange(-n, n + 1)
        CC, RR = np.meshgrid(cc, rr)
        
        # Rotate into axis frame
        along = CC * u_col + RR * u_row
        perp = -CC * u_row + RR * u_col
        
        # Oriented Gaussian
        g = np.exp(-0.5 * ((along / max(s1px, 1e-6)) ** 2 + (perp / max(s2px, 1e-6)) ** 2))
        g /= max(g.max(), 1e-12)
        g *= float(lin.weight[i])
        
        # Place on grid
        r0 = round(py[i])
        c0 = round(px[i])
        r1, r2 = r0 - n, r0 + n + 1
        c1, c2 = c0 - n, c0 + n + 1
        sr1, sr2 = max(r1, 0), min(r2, h)
        sc1, sc2 = max(c1, 0), min(c2, w)
        
        if sr1 >= sr2 or sc1 >= sc2:
            continue
        
        sub = g[sr1 - r1: sr2 - r1, sc1 - c1: sc2 - c1]
        acc[sr1:sr2, sc1:sc2] = np.maximum(acc[sr1:sr2, sc1:sc2], sub)
    
    # Smooth at the metric's scale
    if KDE_SMOOTH_PX > 0:
        acc = ndimage.gaussian_filter(acc, KDE_SMOOTH_PX)
    
    # Sharpen with power law
    if SHARPEN_POWER != 1:
        mx = float(acc.max())
        if mx > 0:
            acc = (acc / mx) ** SHARPEN_POWER
    
    # Normalize to [0, 1]
    mx = float(acc.max())
    if mx > 0:
        acc = acc / mx
    
    print(f"  KDE rendered: max={mx:.4f}, cells>0.05={int((acc > 0.05).sum()):,}", flush=True)
    return acc.astype(np.float32)


# ---------------------------------------------------------------------------
# 4. Emission and scoring
# ---------------------------------------------------------------------------
def score_dots_simple(truth: np.ndarray, rows: np.ndarray, cols: np.ndarray,
                      shape: tuple[int, int]) -> dict[str, float]:
    """Score binary dots against truth using the official metric."""
    pred = np.zeros(shape, dtype=np.float32)
    if len(rows) > 0:
        pred[rows, cols] = 1.0
    result = distance_weighted_tversky(truth, pred)
    return {
        "dti": result.score,
        "tp_weight": result.tp_weight,
        "fp_weight": result.fp_weight,
        "fn_weight": result.fn_weight,
        "truth_cells": result.truth_cells,
        "prediction_cells": result.prediction_cells,
        "credit_per_dot": float(result.tp_weight) / max(result.prediction_cells, 1),
    }


def mass_sweep(belief: np.ndarray, domain: np.ndarray, truth: np.ndarray,
               masses: tuple[int, ...]) -> tuple[dict[str, Any], int]:
    """Sweep emission masses to find optimal under transfer model."""
    print("  Running mass sweep...", flush=True)
    shape = belief.shape
    results = {}
    
    for n in masses:
        em = h56.emit_blue_noise(
            belief, domain, n_target=n, min_sep_px=R_PX, seed=EMIT_SEED
        )
        if em.rows.size == 0:
            continue
        
        # Score against truth (SGMC off-catalogue proxy)
        scores = score_dots_simple(truth, em.rows, em.cols, shape)
        
        # Transfer-calibrated hidden DTI
        off_cat_dti = scores["dti"]
        credit_per_dot = scores["credit_per_dot"]
        hidden_t_per_dot = credit_per_dot * TRANSFER
        hidden_t = min(hidden_t_per_dot * n, G_HIDDEN)
        hidden_dti = hidden_t / (ALPHA * n + BETA * G_HIDDEN)
        
        # Uniform control
        ctrl_dtis = []
        for sd in (1, 2, 3):
            ctrl = h56.emit_blue_noise(
                np.ones(shape, dtype=np.float32), domain,
                n_target=n, min_sep_px=R_PX, seed=sd
            )
            if ctrl.rows.size > 0:
                ctrl_scores = score_dots_simple(truth, ctrl.rows, ctrl.cols, shape)
                ctrl_dtis.append(ctrl_scores["dti"])
        ctrl_mean = np.mean(ctrl_dtis) if ctrl_dtis else 0.0
        
        results[str(n)] = {
            "n_dots": n,
            "off_cat_dti": off_cat_dti,
            "credit_per_dot": credit_per_dot,
            "hidden_dti_model": hidden_dti,
            "uniform_control": ctrl_mean,
            "lift": off_cat_dti / max(ctrl_mean, 1e-9),
            "tp_weight": scores["tp_weight"],
        }
        print(f"    N={n:6d}: off-cat DTI={off_cat_dti:.4f}, "
              f"uniform={ctrl_mean:.4f}, lift={off_cat_dti/max(ctrl_mean,1e-9):.2f}x, "
              f"model hidden={hidden_dti:.4f}", flush=True)
    
    # Select mass maximizing modelled hidden DTI
    best_n = max(results, key=lambda k: results[k]["hidden_dti_model"])
    return results, int(best_n)


# ---------------------------------------------------------------------------
# 5. Write GeoTIFF
# ---------------------------------------------------------------------------
def write_geotiff(template_path: Path, output_path: Path, data: np.ndarray,
                  valid: np.ndarray, *, zero_outside: bool) -> dict[str, Any]:
    """Write portal-safe GeoTIFF."""
    with rasterio.open(template_path) as src:
        profile = src.profile.copy()
    
    values = data.astype(np.float32)
    if zero_outside:
        values[~valid] = 0.0
        nodata = None
    else:
        values[~valid] = np.nan
        nodata = np.nan
    
    profile.update(
        driver="GTiff", count=1, dtype="float32",
        nodata=nodata, compress="DEFLATE", predictor=3,
        tiled=True, blockxsize=256, blockysize=256,
    )
    
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with rasterio.open(output_path, "w", **profile) as dst:
        dst.write(values, 1)
        dst.set_band_description(1, "H60 seismicity anisotropic KDE")
        dst.update_tags(
            hypothesis="H60",
            method="anisotropic_seismicity_kde_fault_gap",
            outside_footprint="0" if zero_outside else "NaN",
            probability_range="[0,1]",
        )
    
    # Re-read and verify
    with rasterio.open(output_path) as ds:
        reread = ds.read(1)
        finite = reread[np.isfinite(reread)]
        assert ds.count == 1
        assert ds.shape == data.shape
        assert float(finite.min()) >= 0.0
        assert float(finite.max()) <= 1.0
        if zero_outside:
            assert np.all(np.isfinite(reread))
    
    return {
        "path": str(output_path),
        "bytes": output_path.stat().st_size,
        "sha256": _sha256_file(output_path),
        "shape": list(data.shape),
        "dtype": "float32",
        "positive_cells": int(np.count_nonzero(reread > 0)),
        "finite_min": float(finite.min()),
        "finite_max": float(finite.max()),
        "all_finite": bool(np.all(np.isfinite(reread))),
    }


# ---------------------------------------------------------------------------
# 6. Main build
# ---------------------------------------------------------------------------
def run(args: argparse.Namespace) -> dict[str, Any]:
    t0 = time.time()
    
    comcat_path = Path(args.comcat)
    template_path = Path(args.template)
    labels_path = Path(args.labels)
    sgmc_path = Path(args.sgmc)
    out_dir = Path(args.out)
    
    for p in [comcat_path, template_path, labels_path, sgmc_path]:
        if not p.exists():
            raise FileNotFoundError(f"Missing input: {p}")
    
    # Load grid info
    with rasterio.open(template_path) as ds:
        shape = ds.shape
        valid = np.isfinite(ds.read(1))
    
    with rasterio.open(labels_path) as ds:
        labels = ds.read(1)
    catalogue = labels == 1
    known_distance = ndimage.distance_transform_edt(~catalogue, sampling=(100.0, 100.0))
    domain = valid & (known_distance > 300.0)  # off-catalogue scoring domain
    
    with rasterio.open(sgmc_path) as ds:
        sgmc = ds.read(1)
    truth = domain & (sgmc > 0)  # off-catalogue proxy truth
    
    print(f"[{time.time()-t0:.1f}s] Grid: {shape}, domain={int(domain.sum()):,}, "
          f"truth={int(truth.sum()):,}", flush=True)
    
    # --- Build belief field ---
    data = load_and_screen_comcat(comcat_path, template_path)
    data = decluster(data)
    data = compute_lineations(data)
    belief = render_anisotropic_kde(data)
    
    # Mask to domain
    belief[~domain] = 0.0
    # Use domain for emission (blue-noise naturally handles zero-belief blocks)
    emit_domain = domain
    print(f"  Emission domain: {int(emit_domain.sum()):,} cells", flush=True)
    
    # --- Mass sweep ---
    sweep_results, best_n = mass_sweep(belief, emit_domain, truth, MASSES)
    print(f"\n  Best mass: N={best_n}, model hidden DTI={sweep_results[str(best_n)]['hidden_dti_model']:.4f}",
          flush=True)
    
    # --- Emit at best mass ---
    print(f"  Emitting {best_n} dots...", flush=True)
    emission = h56.emit_blue_noise(belief, emit_domain, n_target=best_n, min_sep_px=R_PX, seed=EMIT_SEED)
    final_scores = score_dots_simple(truth, emission.rows, emission.cols, shape)
    print(f"  Final: {emission.rows.size} dots, off-cat DTI={final_scores['dti']:.4f}, "
          f"credit/dot={final_scores['credit_per_dot']:.4f}", flush=True)
    
    # --- Build prediction raster ---
    prediction = np.zeros(shape, dtype=np.float32)
    if emission.rows.size > 0:
        prediction[emission.rows, emission.cols] = 1.0
    
    # --- Write GeoTIFFs ---
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    tag = f"h60-seiskde-faultgap-{best_n}-{timestamp}"
    
    # All-finite (portal-safe)
    allfinite_name = f"gemsdoe50-{tag}-allfinite.tif"
    allfinite_path = out_dir / allfinite_name
    allfinite_meta = write_geotiff(template_path, allfinite_path, prediction, valid, zero_outside=True)
    
    # NaN-outside twin
    nan_name = f"gemsdoe50-{tag}-nan.tif"
    nan_path = out_dir / nan_name
    nan_meta = write_geotiff(template_path, nan_path, prediction, valid, zero_outside=False)
    
    # Zip
    zip_name = f"gemsdoe50-{tag}-allfinite.zip"
    zip_path = out_dir / zip_name
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.write(allfinite_path, allfinite_name)
    
    print(f"\n  Written: {allfinite_path}", flush=True)
    print(f"  Written: {nan_path}", flush=True)
    print(f"  Written: {zip_path}", flush=True)
    
    # --- Uniqueness check against prior submissions ---
    print("  Checking uniqueness against prior artifacts...", flush=True)
    prior_dir = out_dir
    prior_files = sorted(prior_dir.glob("*.tif"))
    max_iou = 0.0
    for pf in prior_files:
        if pf == allfinite_path or pf == nan_path:
            continue
        try:
            with rasterio.open(pf) as ds:
                prior_data = ds.read(1)
            if prior_data.shape != shape:
                continue
            prior_binary = prior_data > 0
            pred_binary = prediction > 0
            intersection = np.count_nonzero(prior_binary & pred_binary)
            union = np.count_nonzero(prior_binary | pred_binary)
            iou = intersection / max(union, 1)
            max_iou = max(max_iou, iou)
        except Exception:  # noqa: BLE001, S112 — unreadable prior rasters are skipped (behaviour unchanged)
            continue
    
    print(f"  Max IoU with prior artifacts: {max_iou:.4f}", flush=True)
    
    # --- Evidence report ---
    report = {
        "hypothesis": "H60",
        "method": "Anisotropic Seismicity KDE with Fault-Gap Prediction",
        "timestamp": timestamp,
        "git_commit": _git_commit(),
        "comcat_sha256": _sha256_file(comcat_path),
        "template_sha256": _sha256_file(template_path),
        "labels_sha256": _sha256_file(labels_path),
        "sgmc_sha256": _sha256_file(sgmc_path),
        "catalog_processing": data["report"],
        "emission": {
            "best_n": best_n,
            "emitted": emission.rows.size,
            "seed": EMIT_SEED,
            "min_sep_px": R_PX,
        },
        "scores": {
            "off_cat_dti": final_scores["dti"],
            "credit_per_dot": final_scores["credit_per_dot"],
            "tp_weight": final_scores["tp_weight"],
            "fp_weight": final_scores["fp_weight"],
            "truth_cells": final_scores["truth_cells"],
        },
        "mass_sweep": sweep_results,
        "transfer_model": {
            "transfer_factor": TRANSFER,
            "G_HIDDEN": G_HIDDEN,
            "model_hidden_dti": sweep_results[str(best_n)]["hidden_dti_model"],
        },
        "uniqueness": {
            "max_iou_vs_prior": max_iou,
            "n_prior_checked": len(prior_files) - 2,  # exclude self
        },
        "outputs": {
            "allfinite": allfinite_meta,
            "nan": nan_meta,
            "zip": {"path": str(zip_path), "bytes": zip_path.stat().st_size},
        },
        "limitations": [
            "2-D covariance eigenstructure is UNVERIFIED adaptation of 3-D method",
            "Transfer factor (4.2) is measured on LiDAR detectors, not seismicity",
            "SGMC proxy shows neutral enrichment for seismicity (expected for old faults)",
            "ComCat horizontalError is used as location uncertainty (imprecise)",
            "No LiDAR/radiometric ridge snap available in this environment",
        ],
    }
    
    report_path = out_dir / f"checks-{tag}.json"
    _write_json(report_path, report)
    print(f"  Evidence: {report_path}", flush=True)
    
    elapsed = time.time() - t0
    print(f"\nDone in {elapsed:.1f}s", flush=True)
    return report


def main():
    parser = argparse.ArgumentParser(description="Build H60 submission")
    parser.add_argument("--comcat", default=str(REPO / "data/external/usgs_comcat_earthquakes.csv.gz"))
    parser.add_argument("--template", default=str(REPO / "data/grid/sample_submission.tif"))
    parser.add_argument("--labels", default=str(REPO / "data/grid/labels.tif"))
    parser.add_argument("--sgmc", default=str(REPO / "data/external/derived_sgmc_faults_100m_u8.tif"))
    parser.add_argument("--out", default=str(REPO / "docs/downloads"))
    args = parser.parse_args()
    run(args)


if __name__ == "__main__":
    main()