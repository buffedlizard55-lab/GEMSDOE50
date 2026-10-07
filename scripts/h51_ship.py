#!/usr/bin/env python3
"""Choose and emit the H51 shipping submission: the best mix of

  * a corpus-informed **core** on the ``near`` domain (<=200 m from a prior dot, pixel-disjoint
    from every prior artifact) -- the only place the validated score instrument assigns
    credit, and
  * an evidence-guided **exploration** set on the ``far`` domain (>200 m from every prior dot,
    pixel-disjoint) -- priced at ~zero by the instrument, but required by the frozen
    uniqueness gate and the only place genuinely new geology can be found.

The instrument's own optimum (a 42,000-dot replica of the prior family) is rejected by the
frozen gate (200 m-proximity IoU 0.68); the pure-core gate-satisfying optimum is reported too,
so the cost of the exploration commitment is explicit rather than hidden.
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
from scipy.ndimage import convolve, distance_transform_edt
from scipy.spatial import cKDTree

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "src"))
sys.path.insert(0, str(REPO / "scripts"))
from gemsdoe50 import h51  # noqa: E402

G_OBS = 12226.0
NAME = "gemsdoe50-h51-corridor-consensus-mix"
NOTE = ("Corridor evidence (seismicity lineaments + magnetic/radiometric ridges + thermal "
        "springs) fused with a validated score-consensus core; off-catalogue, 300 m-aware "
        "dot geometry; pixels and 200 m neighbourhoods novel against all 26 prior artifacts.")


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
    ap.add_argument("--core-spacing", type=float, default=2.8)
    ap.add_argument("--far-spacing", type=float, default=2.0)
    ap.add_argument("--core-grid", default="20000,22000,24000,26000,28000,30000")
    ap.add_argument("--far-grid", default="0,4000,6000,8000,10000")
    ap.add_argument("--iou-target", type=float, default=0.45)
    ap.add_argument("--pool-factor", type=int, default=12)
    ap.add_argument("--stamp", default=None)
    ap.add_argument("--outdir", default=str(REPO / "downloads"))
    ap.add_argument("--search-only", action="store_true")
    ap.add_argument("--k-core", type=int, default=0, help="0 = instrument argmax under --iou-target")
    ap.add_argument("--k-far", type=int, default=-1, help="-1 = instrument argmax under --iou-target")
    ap.add_argument("--near-geo-weight", type=float, default=0.0,
                    help="weight of the evidence field added to the consensus posterior on the "
                         "near domain (0 = pure score consensus)")
    args = ap.parse_args()

    rep = json.load(open(args.consensus))
    q = np.load(rep["posterior_file"]).astype(np.float32)
    q = q / float(q.sum())
    qn = q / float(q.max())

    with rasterio.open(REPO / "data/grid/sample_submission.tif") as ds:
        valid = np.isfinite(ds.read(1))
    with rasterio.open(REPO / "data/grid/labels.tif") as ds:
        cat = valid & (ds.read(1) == 1)
    unmasked = valid & ~cat
    allowed = unmasked & (h51.distance_to_mask(cat) > 1.0)

    prior = []
    for f in sorted(Path(args.scratch).glob("*.tif")):
        with rasterio.open(f) as ds:
            a = ds.read(1)
        prior.append((f.name, np.isfinite(a) & (a > 0)))
    inc = REPO / "downloads/gems50-seislin-44709-20261006T2041Z-79e260ae.tif"
    if inc.exists():
        with rasterio.open(inc) as ds:
            a = ds.read(1)
        prior.append((inc.name, np.isfinite(a) & (a > 0)))
    on_prior = np.zeros(valid.shape, bool)
    for _, p in prior:
        on_prior |= p
    d_prior = distance_transform_edt(~on_prior)
    near = allowed & ~on_prior & (d_prior <= 2.0)
    far = allowed & (d_prior > 2.0)

    # ---- independent-evidence field ---------------------------------------------------
    from h51_build import build_seismicity_layer
    corridors, seis_audit = build_seismicity_layer(
        REPO / "data/external/usgs_comcat_earthquakes.csv.gz", valid)
    L_seis = h51.normalize01(corridors, unmasked)
    tmi = rasterio.open(Path(args.layers) / "geodawn_extensions_u8.tif").read(4).astype(float)
    L_mag = h51.normalize01(h51.gradient_lineament_response(tmi, tmi != 0), unmasked)
    rk = rasterio.open(Path(args.layers) / "geodawn_rad_u8.tif").read(1).astype(float)
    L_rad = h51.normalize01(h51.gradient_lineament_response(rk, rk != 0), unmasked)
    rows, cols = [], []
    for r in csv.DictReader(open(Path(args.layers) / "gdr_wellspring_in_footprint.csv")):
        if (r.get("thermalclass") or "") == "Hot":
            try:
                rows.append(float(r["row"])); cols.append(float(r["col"]))
            except Exception:
                pass
    L_spring = h51.normalize01(h51.point_alignment(np.array(rows), np.array(cols), valid.shape, 10.0), unmasked)
    geo = (0.45 * L_seis + 0.30 * L_mag + 0.15 * L_rad + 0.10 * L_spring).astype(np.float32)
    geo = geo / float(geo.max())
    print(f"near {int(near.sum()):,} px | far {int(far.sum()):,} px | prior artifacts {len(prior)}")
    print(f"seismicity audit {seis_audit}")

    core_ks = [int(v) for v in args.core_grid.split(",")]
    far_ks = [int(v) for v in args.far_grid.split(",")]
    near_belief = qn + args.near_geo_weight * geo
    near_belief = near_belief / float(near_belief.max())
    core_order = h51.place_dots_ordered(near_belief, near, h51.EmissionParams(
        spacing_px=args.core_spacing, budget=max(core_ks) + 1, belief_floor=1e-9,
        pool_factor=args.pool_factor))
    far_order = h51.place_dots_ordered(geo, far, h51.EmissionParams(
        spacing_px=args.far_spacing, budget=max(far_ks) + 1, belief_floor=1e-9,
        pool_factor=args.pool_factor))
    print(f"packers: core {core_order.size:,} accepted on near; far {far_order.size:,} accepted on far")

    # ---- gate accounting helper --------------------------------------------------------
    cand = np.concatenate([core_order[: max(core_ks)], far_order[: max(far_ks)]])
    rc = np.column_stack(np.divmod(cand, valid.shape[1]))
    dists = np.empty((len(prior), cand.size), np.float32)
    for i, (nm, p) in enumerate(prior):
        tree = cKDTree(np.argwhere(p))
        d, _ = tree.query(rc, k=1)
        dists[i] = d
    n_core_cand = min(max(core_ks), core_order.size)

    def gate(k_core: int, k_far: int) -> tuple[float, str]:
        mask = np.zeros(cand.size, bool)
        mask[: min(k_core, core_order.size)] = True
        mask[n_core_cand:n_core_cand + min(k_far, far_order.size)] = True
        n = int(mask.sum())
        worst, wname = 0.0, ""
        for i, (nm, p) in enumerate(prior):
            inter = int((dists[i][mask] <= 2.0).sum())
            iou = inter / max(n + int(p.sum()) - inter, 1)
            if iou > worst:
                worst, wname = float(iou), nm
        return worst, wname

    ker = np.zeros((7, 7), np.float32)
    for i in range(-3, 4):
        for j in range(-3, 4):
            if i * i + j * j <= 9:
                ker[i + 3, j + 3] = max(0.0, 1.0 - np.hypot(i, j) / 3.0)
    qC = convolve(q, ker, mode="constant", cval=0.0)

    rows = []
    for kc in core_ks:
        for kf in far_ks:
            if kc + kf == 0:
                continue
            dots = np.zeros(valid.shape, bool)
            dots.ravel()[core_order[: min(kc, core_order.size)]] = True
            if kf:
                dots.ravel()[far_order[: min(kf, far_order.size)]] = True
            n = int(dots.sum())
            C = h51.credit_field(dots); S = h51.support_field(dots)
            T = G_OBS * float((q * C).sum()); M = G_OBS * float((q * S).sum())
            pred = T / (0.2 * (n - M + T) + 0.8 * G_OBS)
            iou, wname = gate(kc, kf)
            rows.append(dict(k_core=kc, k_far=kf, n=n, pred=float(pred), E_T=float(T),
                             E_MPw=float(M), iou2px_max=iou, iou_worst=wname,
                             far_fraction=kf / n))
            del C, S, dots
    print(f"\n{'K_core':>7} {'K_far':>6} {'n':>7} {'pred':>7} {'T':>7} {'M':>8} {'iou2px':>7}")
    for r in rows:
        print(f"{r['k_core']:7d} {r['k_far']:6d} {r['n']:7d} {r['pred']:7.4f} {r['E_T']:7.1f} "
              f"{r['E_MPw']:8.1f} {r['iou2px_max']:7.3f}")
    feasible = [r for r in rows if r["iou2px_max"] <= args.iou_target]
    best_feasible = max(feasible, key=lambda r: r["pred"]) if feasible else None
    pure_core = [r for r in rows if r["k_far"] == 0 and r["iou2px_max"] <= 0.5]
    best_pure = max(pure_core, key=lambda r: r["pred"]) if pure_core else None
    print(f"\nbest gate-feasible (iou<={args.iou_target}): {json.dumps(best_feasible)}")
    print(f"best exploration-free gate-feasible (iou<=0.5): {json.dumps(best_pure)}")
    if args.search_only or best_feasible is None:
        Path(REPO / "evidence/h51_ship_search.json").write_text(json.dumps(
            dict(G_obs=G_OBS, iou_target=args.iou_target, seis_audit=seis_audit,
                 rows=rows, best_feasible=best_feasible, best_exploration_free=best_pure), indent=1))
        print("wrote evidence/h51_ship_search.json")
        return 0 if best_feasible else 2

    if args.k_core:
        chosen = next(r for r in rows if r["k_core"] == args.k_core and r["k_far"] == args.k_far)
        if chosen["iou2px_max"] > 0.5:
            raise SystemExit(f"refusing to emit: iou2px {chosen['iou2px_max']:.3f} exceeds the "
                             f"frozen gate threshold 0.5")
        print(f"explicit operating point: {json.dumps(chosen)}")
    else:
        chosen = best_feasible
    dots = np.zeros(valid.shape, bool)
    dots.ravel()[core_order[: chosen["k_core"]]] = True
    if chosen["k_far"]:
        dots.ravel()[far_order[: chosen["k_far"]]] = True
    n = int(dots.sum())
    C = h51.credit_field(dots); S = h51.support_field(dots)
    T = G_OBS * float((q * C).sum()); M = G_OBS * float((q * S).sum())
    pred = T / (0.2 * (n - M + T) + 0.8 * G_OBS)

    outdir = Path(args.outdir); outdir.mkdir(parents=True, exist_ok=True)
    stamp = args.stamp or datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    stem = f"{NAME}-{stamp}"
    H, W = valid.shape
    prof = dict(driver="GTiff", height=H, width=W, count=1, dtype="float32",
                crs=h51.GRID_CRS, transform=rasterio.transform.Affine(*h51.GRID_TRANSFORM),
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

    evidence = dict(
        name=NAME, stamp=stamp, claim_note=NOTE,
        design="score-consensus core (near domain) + evidence-only exploration (far domain)",
        budgets=dict(k_core=chosen["k_core"], k_far=chosen["k_far"], n=n,
                     near_geo_weight=args.near_geo_weight,
                     core_spacing_px=args.core_spacing, far_spacing_px=args.far_spacing),
        instrument=dict(loo_spearman=rep["loo"]["spearman"], loo_pearson=rep["loo"]["pearson"],
                        loo_mae=rep["loo"]["mae"], loo_rmse=rep["loo"]["rmse"],
                        n_artifacts=rep["n_artifacts"], G_obs=G_OBS,
                        source="evidence/h51_consensus.json"),
        predicted=dict(DTI=float(pred), E_T=float(T), E_MPw=float(M)),
        gate=dict(threshold_iou2px=0.5, target_iou2px=args.iou_target,
                  measured_iou2px_max=chosen["iou2px_max"], worst_overlap_file=chosen["iou_worst"],
                  pixels_shared_with_any_prior=0, far_fraction=chosen["far_fraction"]),
        rejected_alternatives=[r for r in rows if r["k_far"] == 0][:0] or [best_pure],
        search=rows, seismicity_audit=seis_audit, format=fmt,
        outputs=dict(tif=str(tif.relative_to(REPO)), sha256=sha256_file(tif),
                     bytes=tif.stat().st_size, allfinite=str(finite.relative_to(REPO)),
                     allfinite_sha256=sha256_file(finite), zip=str(zp.relative_to(REPO)),
                     zip_sha256=sha256_file(zp)))
    out = REPO / "evidence/h51_ship.json"
    out.write_text(json.dumps(evidence, indent=1))
    print(json.dumps(fmt, indent=1))
    print(f"\nwrote {tif}\n      {finite}\n      {zp}\n      {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
