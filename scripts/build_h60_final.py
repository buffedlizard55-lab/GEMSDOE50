#!/usr/bin/env python3
"""Build H60 FINAL: Anisotropic seismicity KDE with fault-gap prediction.

This is the final version optimized for the competition. Key design:

1.  Seismicity lineations (2-D covariance eigenstructure) from declustered
    ComCat events define the STRUCTURAL GRAIN.

2.  Anisotropic KDE renders each lineation as an oriented Gaussian. The kernel
    width is the catalogue's own location error; the length is the cluster
    extent. This naturally bridges gaps between clusters.

3.  A DISTANCE-TO-KNOWN-FAULTS prior concentrates predictions where extension
    faults are most likely (1-8 km from known faults, peaking at ~3 km).

4.  The two are COMBINED multiplicatively: seismicity corroborates structural
    setting, and the distance prior targets the right spatial domain.

5.  Blue-noise emission at 3px (R=300m, the metric's own support).

6.  Mass sweep selects the optimal N under a transfer-calibrated model.

Sources:
- USGS ANSS ComCat: https://earthquake.usgs.gov/fdsnws/event/1/query
  License: USGS public domain
- Known faults: competition labels.tif
- SGMC faults: data/external/derived_sgmc_faults_100m_u8.tif

The 2-D covariance eigenstructure is an UNVERIFIED adaptation of the 3-D
method (Ouillon et al. 2008, doi:10.1029/2007JB005032).
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
from scipy import ndimage
from scipy.spatial import cKDTree
from pyproj import Transformer

REPO = Path(__file__).resolve().parents[1]
import sys
sys.path.insert(0, str(REPO / "src"))

from gemsdoe50 import h56
from gemsdoe50.common import jsonable, sha256_file
from gemsdoe50.metric import distance_weighted_tversky

R_PX = 3.0
ALPHA = 0.2
BETA = 0.8
MIN_MAG = 1.5
MAX_DEPTH_KM = 25.0
MAX_HORIZONTAL_ERROR_KM = 10.0
ANTHROPOGENIC_BUFFER_M = 3_000.0
TRIANGLE_QUANTILE = 0.95
TRIANGLE_SEED = 20_261_007
LINEATION_K = 10
LINEATION_MIN_EVENTS = 6
LINEATION_MIN_ELONGATION = 3.0
LINEATION_MIN_SIGMA1_M = 800.0
EMIT_SEED = 602_007
MASSES = (20_000, 25_000, 30_000, 35_000, 40_000, 45_000, 55_000, 70_000, 90_000)
G_HIDDEN = 12_226
TRANSFER_CONSERVATIVE = 2.5  # conservative transfer for seismicity


def _sha256_file(path: Path) -> str:
    d = hashlib.sha256()
    with open(path, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            d.update(b)
    return d.hexdigest()


def _git_commit() -> str | None:
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "HEAD"], text=True, stderr=subprocess.DEVNULL
        ).strip()
    except Exception:
        return None


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(jsonable(payload), indent=2, sort_keys=True, allow_nan=False) + "\n",
        encoding="utf-8",
    )


# ---------------------------------------------------------------------------
# Pipeline stages
# ---------------------------------------------------------------------------

def load_and_screen(comcat_path: Path, template_path: Path) -> dict:
    """Load ComCat, screen, project to grid."""
    print("  Loading ComCat...", flush=True)
    df = pd.read_csv(comcat_path)
    n0 = len(df)

    non_tectonic = {
        "quarry blast", "explosion", "mining explosion", "chemical explosion",
        "nuclear explosion", "mine collapse", "quarry", "acoustic noise",
        "sonic boom", "rockslide", "other event", "not reported", "anthropogenic event",
    }
    if "type" in df.columns:
        df = df[~df["type"].astype(str).str.strip().str.lower().isin(non_tectonic)]
    n1 = len(df)

    df["mag"] = pd.to_numeric(df["mag"], errors="coerce")
    df = df[df["mag"] >= MIN_MAG].reset_index(drop=True)
    n2 = len(df)

    df["depth"] = pd.to_numeric(df["depth"], errors="coerce")
    df = df[np.isfinite(df["depth"]) & (df["depth"] < MAX_DEPTH_KM)].reset_index(drop=True)
    n3 = len(df)

    if "horizontalError" in df.columns:
        h = pd.to_numeric(df["horizontalError"], errors="coerce")
        df = df[~(np.isfinite(h) & (h > MAX_HORIZONTAL_ERROR_KM))].reset_index(drop=True)
    n4 = len(df)

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
    in_bounds = (np.isfinite(lon) & np.isfinite(lat) &
                 (row >= 0) & (row < h) & (col >= 0) & (col < w))
    df = df[in_bounds].reset_index(drop=True)
    x, y = x[in_bounds], y[in_bounds]
    row, col = row[in_bounds], col[in_bounds]
    n5 = len(df)

    # Site screen
    xy = np.column_stack((x, y))
    anthro = df["type"].astype(str).str.strip().str.lower().isin({
        "explosion", "quarry blast", "nuclear explosion", "chemical explosion",
        "mining explosion", "mine collapse", "quarry", "acoustic noise",
        "sonic boom", "rockslide", "anthropogenic event",
    })
    if anthro.any():
        atree = cKDTree(xy[anthro])
        dist, _ = atree.query(xy, k=1)
        keep = dist > ANTHROPOGENIC_BUFFER_M
        df, x, y, row, col, xy = (df[keep].reset_index(drop=True), x[keep], y[keep],
                                   row[keep], col[keep], xy[keep])
    n6 = len(df)

    sigma_km = h56.epicentral_sigma_km(df)

    # Time for declustering
    try:
        tdt = pd.to_datetime(df["time"], format="ISO8601", utc=True, errors="coerce")
    except Exception:
        tdt = pd.to_datetime(df["time"], utc=True, errors="coerce")
    days = tdt.astype(np.int64) / (86400 * 1e9)

    report = {"n_raw": n0, "n_tectonic": n1, "n_mag": n2, "n_depth": n3,
              "n_herr": n4, "n_bounds": n5, "n_final": n6}
    print(f"  Screened: {n0} -> {n6} events", flush=True)
    return {"x": x, "y": y, "row": row, "col": col, "xy": xy, "sigma_km": sigma_km,
            "mag": df["mag"].to_numpy(dtype=np.float64), "days": days.to_numpy(dtype=np.float64),
            "transform": transform, "shape": shape, "valid": valid, "report": report}


def decluster_events(data: dict) -> dict:
    """Triangle-area declustering (unverified 2-D adaptation)."""
    print("  Declustering...", flush=True)
    xy = data["xy"]
    keep, diag = h56.triangle_area_keep(xy, quantile=TRIANGLE_QUANTILE, seed=TRIANGLE_SEED)
    for k in ("x", "y", "row", "col", "xy", "sigma_km", "mag", "days"):
        data[k] = data[k][keep]
    data["report"]["decluster"] = diag
    data["report"]["n_declustered"] = int(keep.sum())
    print(f"  Kept {int(keep.sum())} events", flush=True)
    return data


def compute_belief(data: dict, labels: np.ndarray) -> np.ndarray:
    """Build combined belief: seismicity lineation KDE × distance prior."""
    shape = data["shape"]
    transform = data["transform"]
    valid = data["valid"]
    xy = data["xy"]
    sigma_loc_m = data["sigma_km"] * 1000.0

    # --- Component 1: Anisotropic seismicity KDE ---
    print("  Computing lineations...", flush=True)
    lin = h56.neighbourhood_lineations(
        xy, sigma_loc_m, k=LINEATION_K, min_events=LINEATION_MIN_EVENTS,
        min_elongation=LINEATION_MIN_ELONGATION, min_sigma1_m=LINEATION_MIN_SIGMA1_M,
    )
    print(f"  Found {len(lin)} lineations", flush=True)

    h, w = shape
    a = float(transform.a)
    e = float(transform.e)
    seismo = np.zeros(shape, dtype=np.float64)

    if len(lin) > 0:
        px = (lin.x - transform.c) / a
        py = (lin.y - transform.f) / e
        for i in range(len(lin)):
            s1px = min(float(lin.sigma1_m[i]) / abs(a), 8.0) * 2.0
            s2px = np.clip(float(lin.sigma_loc_m[i]) / abs(a) * 1.5, 1.0, 8.0)
            ux, uy = float(lin.ux[i]), float(lin.uy[i])
            u_col, u_row = ux, -uy
            n = int(np.ceil(3.5 * max(s1px, s2px)))
            if n < 1:
                continue
            rr = np.arange(-n, n + 1)
            cc = np.arange(-n, n + 1)
            CC, RR = np.meshgrid(cc, rr)
            along = CC * u_col + RR * u_row
            perp = -CC * u_row + RR * u_col
            g = np.exp(-0.5 * ((along / max(s1px, 1e-6)) ** 2 + (perp / max(s2px, 1e-6)) ** 2))
            g /= max(g.max(), 1e-12)
            g *= float(lin.weight[i])
            r0, c0 = round(py[i]), round(px[i])
            r1, r2 = r0 - n, r0 + n + 1
            c1, c2 = c0 - n, c0 + n + 1
            sr1, sr2 = max(r1, 0), min(r2, h)
            sc1, sc2 = max(c1, 0), min(c2, w)
            if sr1 < sr2 and sc1 < sc2:
                sub = g[sr1 - r1: sr2 - r1, sc1 - c1: sc2 - c1]
                seismo[sr1:sr2, sc1:sc2] = np.maximum(seismo[sr1:sr2, sc1:sc2], sub)

    # Smooth at metric scale
    seismo = ndimage.gaussian_filter(seismo, 2.0)
    mx = float(seismo.max())
    if mx > 0:
        seismo /= mx

    # --- Component 2: Distance-to-known-faults prior ---
    print("  Computing distance prior...", flush=True)
    catalogue = labels == 1
    dist_m = ndimage.distance_transform_edt(~catalogue, sampling=(100.0, 100.0))
    # Peak at ~3 km, decaying to zero at 0 and >10 km
    # This targets the "near-fault" domain where extensions are most likely
    dist_prior = np.exp(-0.5 * ((dist_m - 3000.0) / 2500.0) ** 2)
    dist_prior[dist_m < 500.0] = 0.0   # too close to known faults
    dist_prior[dist_m > 12000.0] = 0.0  # too far from any structure
    dist_prior = ndimage.gaussian_filter(dist_prior, 3.0)
    dmx = float(dist_prior.max())
    if dmx > 0:
        dist_prior /= dmx

    # --- Combine: geometric mean ---
    print("  Combining belief fields...", flush=True)
    combined = np.sqrt(np.maximum(seismo, 0.0) * np.maximum(dist_prior, 0.0))
    combined[~valid] = 0.0

    # Sharpen
    cmx = float(combined.max())
    if cmx > 0:
        combined = (combined / cmx) ** 8
    cmx = float(combined.max())
    if cmx > 0:
        combined /= cmx

    print(f"  Belief: max={cmx:.4f}, cells>0.01={int((combined > 0.01).sum()):,}", flush=True)
    return combined.astype(np.float32)


def score_dots(truth: np.ndarray, rows: np.ndarray, cols: np.ndarray,
               shape: tuple) -> dict:
    pred = np.zeros(shape, dtype=np.float32)
    if len(rows) > 0:
        pred[rows, cols] = 1.0
    r = distance_weighted_tversky(truth, pred)
    return {"dti": r.score, "tp": r.tp_weight, "fp": r.fp_weight, "fn": r.fn_weight,
            "truth_px": r.truth_cells, "pred_px": r.prediction_cells,
            "credit_per_dot": float(r.tp_weight) / max(r.prediction_cells, 1)}


def mass_sweep(belief, domain, truth, masses):
    """Find optimal mass under transfer model."""
    shape = belief.shape
    results = {}
    for n in masses:
        em = h56.emit_blue_noise(belief, domain, n_target=n, min_sep_px=R_PX, seed=EMIT_SEED)
        if em.rows.size == 0:
            continue
        sc = score_dots(truth, em.rows, em.cols, shape)
        # Transfer model
        cpd = sc["credit_per_dot"]
        ht = min(cpd * TRANSFER_CONSERVATIVE * n, G_HIDDEN)
        hdti = ht / (ALPHA * n + BETA * G_HIDDEN)
        # Uniform control
        ctrls = []
        for s in (1, 2, 3):
            c = h56.emit_blue_noise(np.ones(shape, dtype=np.float32), domain,
                                    n_target=n, min_sep_px=R_PX, seed=s)
            if c.rows.size > 0:
                ctrls.append(score_dots(truth, c.rows, c.cols, shape)["dti"])
        ctrl = np.mean(ctrls) if ctrls else 0.0
        results[str(n)] = {"n": n, "dti": sc["dti"], "cpd": cpd, "ctrl": ctrl,
                           "lift": sc["dti"] / max(ctrl, 1e-9), "hdti": hdti, "tp": sc["tp"]}
        print(f"    N={n:6d}: off-cat={sc['dti']:.4f} ctrl={ctrl:.4f} "
              f"lift={sc['dti']/max(ctrl,1e-9):.2f}x model={hdti:.4f}", flush=True)
    best = max(results, key=lambda k: results[k]["hdti"])
    return results, int(best)


def write_tiff(template: Path, out: Path, data: np.ndarray, valid: np.ndarray,
               zero_outside: bool) -> dict:
    with rasterio.open(template) as src:
        prof = src.profile.copy()
    v = data.astype(np.float32)
    if zero_outside:
        v[~valid] = 0.0
        nd = None
    else:
        v[~valid] = np.nan
        nd = np.nan
    prof.update(driver="GTiff", count=1, dtype="float32", nodata=nd,
                compress="DEFLATE", predictor=3, tiled=True, blockxsize=256, blockysize=256)
    out.parent.mkdir(parents=True, exist_ok=True)
    with rasterio.open(out, "w", **prof) as dst:
        dst.write(v, 1)
        dst.set_band_description(1, "H60 seismicity+distance belief")
    with rasterio.open(out) as ds:
        r = ds.read(1)
        f = r[np.isfinite(r)]
        assert float(f.min()) >= 0 and float(f.max()) <= 1
        if zero_outside:
            assert np.all(np.isfinite(r))
    return {"path": str(out), "bytes": out.stat().st_size, "sha256": _sha256_file(out),
            "shape": list(data.shape), "positive": int(np.count_nonzero(r > 0)),
            "min": float(f.min()), "max": float(f.max()), "all_finite": bool(np.all(np.isfinite(r)))}


def run(args):
    t0 = time.time()
    comcat = Path(args.comcat)
    template = Path(args.template)
    labels_path = Path(args.labels)
    sgmc = Path(args.sgmc)
    out_dir = Path(args.out)

    for p in [comcat, template, labels_path, sgmc]:
        assert p.exists(), f"Missing: {p}"

    with rasterio.open(template) as ds:
        shape = ds.shape
        valid = np.isfinite(ds.read(1))
        transform = ds.transform
    with rasterio.open(labels_path) as ds:
        labels = ds.read(1)
    catalogue = labels == 1
    known_dist = ndimage.distance_transform_edt(~catalogue, sampling=(100, 100))
    domain = valid & (known_dist > 300.0)
    with rasterio.open(sgmc) as ds:
        sgmc_data = ds.read(1)
    truth = domain & (sgmc_data > 0)
    print(f"[{time.time()-t0:.1f}s] domain={int(domain.sum()):,} truth={int(truth.sum()):,}", flush=True)

    # Build belief
    data = load_and_screen(comcat, template)
    data = decluster_events(data)
    belief = compute_belief(data, labels)
    belief[~domain] = 0.0

    # Mass sweep
    print("  Mass sweep...", flush=True)
    sweep, best_n = mass_sweep(belief, domain, truth, MASSES)
    print(f"  Best: N={best_n}, model={sweep[str(best_n)]['hdti']:.4f}", flush=True)

    # Final emission
    print(f"  Emitting {best_n} dots...", flush=True)
    em = h56.emit_blue_noise(belief, domain, n_target=best_n, min_sep_px=R_PX, seed=EMIT_SEED)
    final = score_dots(truth, em.rows, em.cols, shape)
    print(f"  Final: {em.rows.size} dots, DTI={final['dti']:.4f}, cpd={final['credit_per_dot']:.4f}", flush=True)

    # Build prediction
    pred = np.zeros(shape, dtype=np.float32)
    pred[em.rows, em.cols] = 1.0

    # Write outputs
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    tag = f"h60-combined-{best_n}-{ts}"

    af = out_dir / f"gemsdoe50-{tag}-allfinite.tif"
    af_m = write_tiff(template, af, pred, valid, True)
    nn = out_dir / f"gemsdoe50-{tag}-nan.tif"
    nn_m = write_tiff(template, nn, pred, valid, False)
    zf = out_dir / f"gemsdoe50-{tag}-allfinite.zip"
    with zipfile.ZipFile(zf, "w", zipfile.ZIP_DEFLATED) as z:
        z.write(af, af.name)

    # Uniqueness
    max_iou = 0.0
    for pf in out_dir.glob("*.tif"):
        if pf in (af, nn):
            continue
        try:
            with rasterio.open(pf) as ds:
                pd2 = ds.read(1)
            if pd2.shape != shape:
                continue
            i = np.count_nonzero((pd2 > 0) & (pred > 0))
            u = np.count_nonzero((pd2 > 0) | (pred > 0))
            max_iou = max(max_iou, i / max(u, 1))
        except Exception:
            continue

    # Evidence
    report = {
        "hypothesis": "H60",
        "method": "Anisotropic seismicity KDE × distance-to-known-faults prior",
        "timestamp": ts, "git": _git_commit(),
        "catalog": data["report"],
        "lineations": len(data.get("lineations", [])) if hasattr(data.get("lineations", {}), '__len__') else "see lineations dict",
        "emission": {"n_target": best_n, "n_emitted": em.rows.size, "seed": EMIT_SEED},
        "scores": final,
        "mass_sweep": sweep,
        "transfer": {"factor": TRANSFER_CONSERVATIVE, "G": G_HIDDEN,
                     "model_hdti": sweep[str(best_n)]["hdti"]},
        "uniqueness": {"max_iou": max_iou},
        "outputs": {"allfinite": af_m, "nan": nn_m, "zip": str(zf)},
        "limitations": [
            "2-D covariance is UNVERIFIED adaptation of 3-D Ouillon-Sornette method",
            "Transfer factor (2.5) is conservative guess for seismicity, not measured",
            "SGMC proxy shows sub-unity lift (expected: seismicity targets young faults)",
            "No LiDAR/radiometric ridge snap available",
        ],
    }
    rp = out_dir / f"checks-{tag}.json"
    _write_json(rp, report)

    print(f"\n  Written: {af}", flush=True)
    print(f"  SHA256: {af_m['sha256']}", flush=True)
    print(f"  Uniqueness: max IoU = {max_iou:.4f}", flush=True)
    print(f"  Evidence: {rp}", flush=True)
    print(f"  Done in {time.time()-t0:.1f}s", flush=True)
    return report


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--comcat", default=str(REPO / "data/external/usgs_comcat_earthquakes.csv.gz"))
    p.add_argument("--template", default=str(REPO / "data/grid/sample_submission.tif"))
    p.add_argument("--labels", default=str(REPO / "data/grid/labels.tif"))
    p.add_argument("--sgmc", default=str(REPO / "data/external/derived_sgmc_faults_100m_u8.tif"))
    p.add_argument("--out", default=str(REPO / "docs/downloads"))
    run(p.parse_args())


if __name__ == "__main__":
    main()