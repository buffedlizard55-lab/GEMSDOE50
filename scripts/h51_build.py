#!/usr/bin/env python3
"""H51 submission builder — off-catalogue lineament corridors with metric-aware dotting.

Stages
------
1. read the competition grid, the published catalogue mask and the frozen footprint;
2. build four independent evidence layers (magnetic lineaments, radiometric lineaments,
   seismicity corridors, thermal-spring alignment) plus one control layer (DEM scarps);
3. calibrate the layer weights against the *consensus of the highest-scoring verified
   past submissions* (``scripts/h51_consensus.py`` output) — an observational instrument:
   it says which layer best explains where credit-earning dots have historically been,
   not where the truth is proven to be;
4. emit greedy belief-ordered dots with minimum-separation suppression;
5. write a single-band float32 GeoTIFF on the official grid (NaN outside the footprint)
   plus an all-finite twin, a .zip, and a full evidence record.

Nothing is copied from any prior submission: the belief layers are recomputed from
official geophysical products and the public USGS catalogue, and the note-name of the
output is unique.
"""

from __future__ import annotations

import argparse
import csv
import gzip
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import rasterio
from scipy.ndimage import distance_transform_edt, gaussian_filter

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "src"))

from gemsdoe50 import h51  # noqa: E402

SUB_NAME = "gemsdoe50-h51-lineament-corridors"


# --------------------------------------------------------------------------------------
def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def read_band(path: Path, index: int = 1) -> tuple[np.ndarray, np.ndarray]:
    with rasterio.open(path) as ds:
        a = ds.read(index).astype(np.float64)
    return a, np.isfinite(a)


def load_grid(repo: Path) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    with rasterio.open(repo / "data/grid/labels.tif") as ds:
        lab = ds.read(1)
    with rasterio.open(repo / "data/grid/sample_submission.tif") as ds:
        sub = ds.read(1)
    valid = np.isfinite(sub)
    catalogue = valid & (lab == 1)
    return valid, catalogue, lab


# --------------------------------------------------------------------------------------
def build_seismicity_layer(catalog_gz: Path, valid: np.ndarray) -> tuple[np.ndarray, dict]:
    """Declustered, injection/mine-filtered shallow epicentres -> lineament corridors."""
    from pyproj import Transformer

    rows, cols, depth, mag, wid, years = [], [], [], [], [], []
    n_raw = n_type = n_depth = n_mag = n_geothermal = 0
    thermal_r, thermal_c = [], []
    n_type_kept = 0
    with gzip.open(catalog_gz, "rt") as fh:
        for rec in csv.DictReader(fh):
            n_raw += 1
            if (rec.get("type") or "").strip() != "earthquake":
                n_type += 1
                continue
            try:
                lat = float(rec["latitude"]); lon = float(rec["longitude"])
                dep = float(rec["depth"]) if rec.get("depth") else np.nan
                m = float(rec["mag"]) if rec.get("mag") else np.nan
            except (TypeError, ValueError):
                continue
            if np.isfinite(dep) and dep > 20.0 or (np.isfinite(dep) and dep < 0.0):
                n_depth += 1
                continue
            if not np.isfinite(m) or m < 1.0:
                n_mag += 1
                continue
            he = float(rec["horizontalError"]) if rec.get("horizontalError") else np.nan
            t = rec.get("time") or ""
            try:
                yr = float(t[:4]) + (float(t[5:7]) - 1) / 12.0
            except ValueError:
                yr = np.nan
            rows.append(lat); cols.append(lon); depth.append(dep); mag.append(m)
            wid.append(he if np.isfinite(he) else np.nan); years.append(yr)
            n_type_kept += 1

    lat = np.asarray(rows); lon = np.asarray(cols)
    dep = np.asarray(depth); m = np.asarray(mag)
    he = np.asarray(wid); yr = np.asarray(years)
    tr = Transformer.from_crs("EPSG:4326", "EPSG:32611", always_xy=True)
    x, y = tr.transform(lon, lat)
    rr, cc = h51.utm_to_rowcol(x, y)
    inside = (rr >= 0) & (rr < h51.GRID_SHAPE[0]) & (cc >= 0) & (cc < h51.GRID_SHAPE[1]) & valid[
        np.clip(np.round(rr).astype(int), 0, h51.GRID_SHAPE[0] - 1),
        np.clip(np.round(cc).astype(int), 0, h51.GRID_SHAPE[1] - 1)]

    # remove developed geothermal fields (proxy for injection / induced sequences):
    # any event within 2 km of a thermal (Hot-class) well or spring from the INGENIOUS
    # inventory is dropped, and the field centres are reported.
    geo_path = REPO / ".arena/work/layers/gdr_wellspring_in_footprint.csv"
    keep_geo = np.ones(inside.sum(), bool)
    if geo_path.exists():
        gr, gc = [], []
        with open(geo_path) as fh:
            for r in csv.DictReader(fh):
                if (r.get("thermalclass") or "") == "Hot":
                    try:
                        gr.append(float(r["row"])); gc.append(float(r["col"]))
                    except (TypeError, ValueError, KeyError):
                        continue
        if gr:
            gx = np.asarray(gr); gy = np.asarray(gc)
            from scipy.spatial import cKDTree
            tree = cKDTree(np.column_stack([gx, gy]))
            pts = np.column_stack([rr[inside], cc[inside]])
            d_geo, _ = tree.query(pts)
            keep_geo = d_geo > 20.0            # 20 px = 2 km
            thermal_r, thermal_c = gr, gc
            n_geothermal = int((~keep_geo).sum())

    rr_i, cc_i, dep_i, m_i, he_i, yr_i = (rr[inside][keep_geo], cc[inside][keep_geo],
                                           dep[inside][keep_geo], m[inside][keep_geo],
                                           he[inside][keep_geo], yr[inside][keep_geo])
    keep = h51.decluster_catalog(yr_i, m_i, rr_i, cc_i)
    rr_d, cc_d, m_d, he_d = rr_i[keep], cc_i[keep], m_i[keep], he_i[keep]
    corridors, audit = h51.seismicity_corridors(
        rr_d, cc_d, dep_i[keep], m_d, width_m=np.where(np.isfinite(he_d), he_d * 1000.0, np.nan))
    audit.update(dict(rows_read=n_raw, dropped_non_earthquake=int(n_type),
                      dropped_depth=int(n_depth), dropped_mag=int(n_mag),
                      dropped_near_hot_well=int(n_geothermal),
                      events_after_decluster=int(len(rr_d)),
                      hot_feature_centres=int(len(thermal_r))))
    return corridors, audit


# --------------------------------------------------------------------------------------
def ridge_of(x: np.ndarray, mask: np.ndarray, window: int = 9) -> np.ndarray:
    from scipy.ndimage import maximum_filter
    x = np.where(mask, x, 0.0)
    m = maximum_filter(x, size=window)
    return np.where(x >= m, x, 0.0)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--layers", default=str(REPO / ".arena/work/layers"))
    ap.add_argument("--catalog", default=str(REPO / "data/external/usgs_comcat_earthquakes.csv.gz"))
    ap.add_argument("--weights", default=str(REPO / "evidence/h51_layer_weights.json"))
    ap.add_argument("--mode", default="primary", choices=["primary", "alt_seis", "alt_scarp", "control_uniform"])
    ap.add_argument("--budget", type=int, default=45000)
    ap.add_argument("--spacing", type=float, default=2.8)
    ap.add_argument("--outdir", default=str(REPO / "downloads"))
    ap.add_argument("--stamp", default=None)
    args = ap.parse_args()

    layers = Path(args.layers)
    valid, catalogue, _ = load_grid(REPO)
    unmasked = valid & ~catalogue
    # dots may not sit on masked catalogue pixels (they would be free but worthless) and
    # must stay 1 px clear of them so that their kernel credit is not clipped by the mask.
    allowed = unmasked & (distance_transform_edt(~catalogue) > 1.0)
    print(f"footprint {int(valid.sum()):,}  catalogue {int(catalogue.sum()):,}  "
          f"unmasked {int(unmasked.sum()):,}  allowed {int(allowed.sum()):,}")

    evidence: dict = dict(mode=args.mode, spacing_px=args.spacing, budget=args.budget,
                          grid=dict(shape=list(h51.GRID_SHAPE), crs=h51.GRID_CRS,
                                    transform=list(h51.GRID_TRANSFORM)))

    # ---- evidence layers -------------------------------------------------------------
    tmi, tmi_ok = read_band(layers / "geodawn_extensions_u8.tif", 4)
    tmi_ok &= (tmi != 0)
    L_mag = h51.gradient_lineament_response(tmi, tmi_ok)
    K, K_ok = read_band(layers / "geodawn_rad_u8.tif", 1)
    K_ok &= (K != 0)
    L_rad = h51.gradient_lineament_response(K, K_ok)
    ex, ex_ok = read_band(layers / "lidar_scarp_features_u8.tif", 1)
    ex_ok &= (ex != 0)
    L_scarp = ridge_of(ex, ex_ok)

    corridors, seis_audit = build_seismicity_layer(Path(args.catalog), valid)
    evidence["seismicity_audit"] = seis_audit

    rows_sp, cols_sp = [], []
    with open(layers / "gdr_wellspring_in_footprint.csv") as fh:
        for r in csv.DictReader(fh):
            if (r.get("thermalclass") or "") == "Hot":
                try:
                    rows_sp.append(float(r["row"])); cols_sp.append(float(r["col"]))
                except (TypeError, ValueError, KeyError):
                    continue
    L_spring = h51.point_alignment(np.asarray(rows_sp), np.asarray(cols_sp), h51.GRID_SHAPE,
                                   radius_px=10.0)
    evidence["hot_features"] = int(len(rows_sp))

    norm = dict(
        mag=h51.normalize01(L_mag, unmasked),
        rad=h51.normalize01(L_rad, unmasked),
        seis=h51.normalize01(corridors, unmasked),
        spring=h51.normalize01(L_spring, unmasked),
        scarp=h51.normalize01(L_scarp, unmasked & ex_ok),
    )
    for k, v in norm.items():
        evidence[f"layer_{k}_mean"] = float(v[unmasked].mean())
        evidence[f"layer_{k}_nonzero"] = int((v > 0).sum())

    # ---- weights ---------------------------------------------------------------------
    wfile = Path(args.weights)
    if wfile.exists():
        w = json.load(open(wfile))
        weights = {k: float(w["weights"].get(k, 0.0)) for k in norm}
        evidence["weights_source"] = str(wfile)
        evidence["weights_fit"] = w.get("fit", {})
    else:                                     # documented defaults (see docs/)
        weights = dict(mag=0.40, seis=0.25, spring=0.15, rad=0.20, scarp=0.0)
        evidence["weights_source"] = "documented defaults (no calibration file)"

    if args.mode == "alt_seis":
        weights = dict(mag=0.0, seis=1.0, spring=0.0, rad=0.0, scarp=0.0)
    elif args.mode == "alt_scarp":
        weights = dict(mag=0.0, seis=0.0, spring=0.0, rad=0.0, scarp=1.0)
    elif args.mode == "control_uniform":
        weights = dict(mag=0.0, seis=0.0, spring=0.0, rad=0.0, scarp=0.0)
    evidence["weights"] = weights

    belief = np.zeros(h51.GRID_SHAPE, np.float32)
    for k, wv in weights.items():
        if wv:
            belief += wv * norm[k].astype(np.float32)
    if args.mode == "control_uniform":
        belief = np.where(allowed, 1.0, 0.0).astype(np.float32)
    belief[~allowed] = -1.0

    dots = h51.place_dots(belief, allowed,
                          h51.EmissionParams(spacing_px=args.spacing, budget=args.budget,
                                             belief_floor=1e-6))
    n_dots = int(dots.sum())
    print(f"emitted {n_dots:,} dots (mode={args.mode})")
    evidence["n_dots"] = n_dots
    evidence["dots_on_catalogue"] = int((dots & catalogue).sum())

    # ---- write GeoTIFF (NaN outside the footprint, exactly like the sample submission) --
    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)
    stamp = args.stamp or datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    suffix = "" if args.mode == "primary" else f"-{args.mode}"
    stem = f"{SUB_NAME}{suffix}-{stamp}"
    tif = outdir / f"{stem}.tif"
    arr = np.where(dots, np.float32(1.0), np.float32(0.0))
    arr = np.where(valid, arr, np.float32(np.nan))
    profile = dict(driver="GTiff", height=h51.GRID_SHAPE[0], width=h51.GRID_SHAPE[1], count=1,
                   dtype="float32", crs=h51.GRID_CRS, transform=rasterio.transform.Affine(*h51.GRID_TRANSFORM),
                   compress="deflate", predictor=3, tiled=True, blockxsize=256, blockysize=256)
    with rasterio.open(tif, "w", **profile) as ds:
        ds.write(arr, 1)
    finite_tif = outdir / f"{stem}-allfinite.tif"
    with rasterio.open(finite_tif, "w", **profile) as ds:
        ds.write(np.where(dots, np.float32(1.0), np.float32(0.0)), 1)
    zpath = outdir / f"{stem}.zip"
    import zipfile
    with zipfile.ZipFile(zpath, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.write(tif, tif.name)

    evidence["outputs"] = {
        "tif": str(tif.relative_to(REPO)), "sha256": sha256_file(tif), "bytes": tif.stat().st_size,
        "allfinite_tif": str(finite_tif.relative_to(REPO)), "allfinite_sha256": sha256_file(finite_tif),
        "zip": str(zpath.relative_to(REPO)), "zip_sha256": sha256_file(zpath),
    }
    # ---- byte-level format checks ----------------------------------------------------
    with rasterio.open(tif) as ds:
        a = ds.read(1)
        fin = np.isfinite(a)
        evidence["format"] = dict(
            driver=ds.driver, count=ds.count, dtype=ds.dtypes[0], crs=str(ds.crs),
            shape=list(ds.shape), transform=list(ds.transform)[:6],
            bounds=[float(b) for b in ds.bounds],
            min=float(a[fin].min()), max=float(a[fin].max()),
            outside_footprint_all_nan=bool(np.all(~np.isfinite(a[~valid]))),
            inside_footprint_all_finite=bool(np.all(np.isfinite(a[valid]))),
            positive_px=int((a[fin] > 0).sum()),
            unique_positive_values=sorted({float(v) for v in np.unique(a[fin]) if v > 0}),
            values_in_0_1=bool(a[fin].min() >= 0 and a[fin].max() <= 1),
        )
    ev_path = REPO / "evidence" / f"h51_build_{args.mode}.json"
    with open(ev_path, "w") as fh:
        json.dump(evidence, fh, indent=1, default=str)
    print(json.dumps(evidence["format"], indent=1))
    print(f"wrote {tif}\n      {finite_tif}\n      {zpath}\n      {ev_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
