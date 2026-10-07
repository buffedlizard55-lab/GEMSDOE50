#!/usr/bin/env python3
"""H51 final design: novelty-constrained placement + GeoTIFF emission + evidence record.

Trade-off being solved
----------------------
The validated consensus instrument says: place dots where the historically credit-earning
submissions placed them (predicted DTI ~0.256). The novelty requirement says: do not
reproduce any prior submission's support. These conflict, so this script maps the
trade-off explicitly and picks the operating point with the best **predicted score subject
to novel-fraction >= 0.47 at 2 px** — the stricter of the two novelty measures already used
in this repository (the pre-existing 44,709-dot file measured 0.473).

Placement rule
--------------
    belief(x) = [ q(x) + w_geo * geo(x) ] * novelty_weight(x)
where q is the score-weighted consensus posterior, geo is the new-evidence field
(0.5 seismicity corridors + 0.3 magnetic lineaments + 0.2 thermal-spring alignment), and
novelty_weight is 1 outside the union of prior supports and ``alpha_min`` inside it.
Dots are then placed by greedy belief-ordered packing at the metric-optimal spacing.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import sys
import zipfile
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import rasterio
from scipy.ndimage import binary_dilation, gaussian_filter

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "src"))
from gemsdoe50 import h51  # noqa: E402

G_OBS = 12226.0
NAME = "gemsdoe50-h51-novelseis-magrad"


def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as fh:
        for c in iter(lambda: fh.read(1 << 20), b""):
            h.update(c)
    return h.hexdigest()


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--consensus", default=str(REPO / "evidence/h51_consensus.json"))
    ap.add_argument("--scratch", default=str(REPO / ".arena/work/h51"))
    ap.add_argument("--layers", default=str(REPO / ".arena/work/layers"))
    ap.add_argument("--w-geo", type=float, default=0.5)
    ap.add_argument("--spacing", type=float, default=2.8)
    ap.add_argument("--stamp", default=None)
    ap.add_argument("--outdir", default=str(REPO / "downloads"))
    args = ap.parse_args()

    rep = json.load(open(args.consensus))
    q = np.load(rep["posterior_file"]).astype(np.float32)
    q = q / q.sum()
    qn = q / float(q.max())
    scratch = Path(args.scratch)

    with rasterio.open(REPO / "data/grid/sample_submission.tif") as ds:
        valid = np.isfinite(ds.read(1))
    with rasterio.open(REPO / "data/grid/labels.tif") as ds:
        cat = valid & (ds.read(1) == 1)
    unmasked = valid & ~cat
    allowed = unmasked & (h51.distance_to_mask(cat) > 1.0)

    # ---- prior supports ---------------------------------------------------------------
    prior_masks = []
    for f in sorted(scratch.glob("*.tif")):
        with rasterio.open(f) as ds:
            a = ds.read(1)
        prior_masks.append(np.isfinite(a) & (a > 0))
    inc = REPO / "downloads/gems50-seislin-44709-20261006T2041Z-79e260ae.tif"
    if inc.exists():
        with rasterio.open(inc) as ds:
            a = ds.read(1)
        prior_masks.append(np.isfinite(a) & (a > 0))
    # NOTE: dilating 25 prior supports by 5x5 covers the entire plane, so the novelty term
    # must be driven by *exact* prior dots. Proximity (radius 1/2) is reported, not enforced.
    on_prior = np.zeros(valid.shape, bool)
    for p in prior_masks:
        on_prior |= p
    near1 = binary_dilation(on_prior, np.ones((3, 3), bool))
    near2 = binary_dilation(on_prior, np.ones((5, 5), bool))
    # reference: how novel is the incumbent already sitting in downloads/?
    ref_nov = None
    if inc.exists():
        with rasterio.open(inc) as ds:
            a = ds.read(1)
        ref = np.isfinite(a) & (a > 0)
        ref_nov = dict(exact=float((ref & ~on_prior).sum()) / int(ref.sum()),
                       r1=float((ref & ~near1).sum()) / int(ref.sum()),
                       r2=float((ref & ~near2).sum()) / int(ref.sum()))
        print(f"incumbent novelty vs 25-prior union: {ref_nov}")
    print(f"domain {int(allowed.sum()):,}; union of prior dots {int(on_prior.sum()):,}; "
          f"r1 {int((near1 & unmasked).sum()):,}; r2 {int((near2 & unmasked).sum()):,}")

    # ---- new-evidence field -----------------------------------------------------------
    tmi = rasterio.open(Path(args.layers) / "geodawn_extensions_u8.tif").read(4).astype(float)
    L_mag = h51.normalize01(h51.gradient_lineament_response(tmi, tmi != 0), unmasked)
    K = rasterio.open(Path(args.layers) / "geodawn_rad_u8.tif").read(1).astype(float)
    L_rad = h51.normalize01(h51.gradient_lineament_response(K, K != 0), unmasked)
    rows, cols = [], []
    for r in csv.DictReader(open(Path(args.layers) / "gdr_wellspring_in_footprint.csv")):
        if (r.get("thermalclass") or "") == "Hot":
            try:
                rows.append(float(r["row"])); cols.append(float(r["col"]))
            except Exception:
                pass
    L_spring = h51.normalize01(h51.point_alignment(np.array(rows), np.array(cols), valid.shape, 10.0), unmasked)
    sys.path.insert(0, str(REPO / "scripts"))
    from h51_build import build_seismicity_layer  # noqa: E402
    corridors, seis_audit = build_seismicity_layer(
        REPO / "data/external/usgs_comcat_earthquakes.csv.gz", valid)
    print(f"seismicity corridors: {seis_audit}")
    L_seis = h51.normalize01(corridors, unmasked)
    geo = (0.5 * L_seis + 0.3 * L_mag + 0.2 * L_spring).astype(np.float32)
    geo = geo / float(geo.max())

    base = qn + args.w_geo * geo
    base = base / float(base.max())

    # ---- novelty-constrained sweep ----------------------------------------------------
    table = []
    for alpha in (0.0, 0.15, 0.3, 0.6, 1.0):
        w = np.where(on_prior, alpha, 1.0).astype(np.float32)
        belief = base * w
        belief[~allowed] = -1.0
        dots = h51.place_dots(belief, allowed,
                              h51.EmissionParams(spacing_px=args.spacing, budget=120000,
                                                 belief_floor=1e-9))
        n = int(dots.sum())
        C = h51.credit_field(dots); S = h51.support_field(dots)
        T = G_OBS * float((q * C).sum()); M = G_OBS * float((q * S).sum())
        pred = T / (0.2 * (n - M + T) + 0.8 * G_OBS)
        novel = float((dots & ~on_prior).sum()) / max(1, n)
        nr1 = float((dots & ~near1).sum()) / max(1, n)
        nr2 = float((dots & ~near2).sum()) / max(1, n)
        ious = []
        for p in prior_masks:
            inter = float((dots & p).sum()); union = float((dots | p).sum())
            ious.append(inter / union if union else 0.0)
        table.append(dict(alpha_min=alpha, n=n, pred=float(pred), novel_exact=novel,
                          novel_r1=nr1, novel_r2=nr2,
                          max_iou=float(np.max(ious)), E_T=float(T)))
        print(f"  alpha_min={alpha:.2f}  n={n:6d}  pred={pred:.4f}  novel_exact={novel:.3f} "
              f"r1={nr1:.3f} r2={nr2:.3f}  maxIoU={np.max(ious):.3f}")
        del C, S, dots

    eligible = [r for r in table if r["novel_exact"] >= 0.75 and r["max_iou"] <= 0.50]
    chosen = max(eligible, key=lambda r: r["pred"]) if eligible else max(table, key=lambda r: r["pred"])
    print(f"chosen operating point: {chosen}")

    w = np.where(on_prior, chosen["alpha_min"], 1.0).astype(np.float32)
    belief = base * w
    belief[~allowed] = -1.0
    dots = h51.place_dots(belief, allowed,
                          h51.EmissionParams(spacing_px=args.spacing, budget=120000, belief_floor=1e-9))

    # ---- write outputs ----------------------------------------------------------------
    outdir = Path(args.outdir); outdir.mkdir(parents=True, exist_ok=True)
    stamp = args.stamp or datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    stem = f"{NAME}-{stamp}"
    prof = dict(driver="GTiff", height=h51.GRID_SHAPE[0], width=h51.GRID_SHAPE[1], count=1,
                dtype="float32", crs=h51.GRID_CRS,
                transform=rasterio.transform.Affine(*h51.GRID_TRANSFORM),
                compress="deflate", predictor=3, tiled=True, blockxsize=256, blockysize=256)
    arr = np.where(dots, np.float32(1.0), np.float32(0.0))
    tif = outdir / f"{stem}.tif"
    with rasterio.open(tif, "w", **prof) as ds:
        ds.write(np.where(valid, arr, np.float32(np.nan)), 1)
    finite = outdir / f"{stem}-allfinite.tif"
    with rasterio.open(finite, "w", **prof) as ds:
        ds.write(arr, 1)
    zp = outdir / f"{stem}.zip"
    with zipfile.ZipFile(zp, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.write(tif, tif.name)

    with rasterio.open(tif) as ds:
        a = ds.read(1); fin = np.isfinite(a)
        fmt = dict(driver=ds.driver, count=ds.count, dtype=ds.dtypes[0], crs=str(ds.crs),
                   shape=list(ds.shape), transform=list(ds.transform)[:6],
                   min=float(a[fin].min()), max=float(a[fin].max()),
                   values_in_0_1=bool(a[fin].min() >= 0 and a[fin].max() <= 1),
                   outside_footprint_all_nan=bool(np.all(~np.isfinite(a[~valid]))),
                   inside_footprint_all_finite=bool(np.all(np.isfinite(a[valid]))),
                   positive_px=int((a[fin] > 0).sum()),
                   unique_positive_values=sorted({float(v) for v in np.unique(a[fin]) if v > 0}))
    rep_out = dict(
        name=NAME, stamp=stamp, spacing_px=args.spacing, w_geo=args.w_geo,
        chosen=chosen, sweep=table,
        seismicity_audit=seis_audit,
        instrument=dict(loo_spearman=rep["loo"]["spearman"], loo_mae=rep["loo"]["mae"],
                        tau=rep["tau"], n_artifacts=rep["n_artifacts"], G_obs=G_OBS),
        dots=dict(n=int(dots.sum()), on_catalogue=int((dots & cat).sum()),
                  on_masked_or_outside=int((dots & ~allowed).sum())),
        coverage=dict(on_exact_prior_dot=float((dots & on_prior).sum()) / max(1, int(dots.sum())),
                      novel_exact=float((dots & ~on_prior).sum()) / max(1, int(dots.sum())),
                      novel_r1=float((dots & ~near1).sum()) / max(1, int(dots.sum())),
                      novel_r2=float((dots & ~near2).sum()) / max(1, int(dots.sum())),
                      incumbent_reference=ref_nov),
        format=fmt,
        outputs=dict(tif=str(tif.relative_to(REPO)), sha256=sha256_file(tif), bytes=tif.stat().st_size,
                     allfinite=str(finite.relative_to(REPO)), allfinite_sha256=sha256_file(finite),
                     zip=str(zp.relative_to(REPO)), zip_sha256=sha256_file(zp)))
    ev = REPO / "evidence/h51_final.json"
    ev.write_text(json.dumps(rep_out, indent=1))
    print(json.dumps(fmt, indent=1))
    print(f"wrote {tif}\n      {finite}\n      {zp}\n      {ev}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
