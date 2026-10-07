#!/usr/bin/env python3
"""Exact score-vs-budget frontier for candidate H51 designs.

Why this exists
---------------
``place_dots`` accepts dots greedily in belief order, so the accepted set for *any* budget is
a prefix of one ordering. Walking that ordering once and maintaining

  * ``Cmax`` — the running ``max over accepted dots of k(d(x, dot))`` (the metric's credit
    field is a max, not a sum, so it cannot be accumulated additively), and
  * ``M``    — the running ``sum over accepted dots of (q * k)(dot)`` (the support field *is*
    a convolution, so it is exactly additive),

gives the true predicted score ``T/(0.2(N - M + T) + 0.8G)`` for every budget without
re-running the packer. The frontier is what decides the final emission, because the
marginal-inclusion rule (``docs/research/score-model.md`` Corollary 2) says a dot only pays
when its credit contribution beats ``0.2 x`` its own support mass.
"""
from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path

import numpy as np
import rasterio
from scipy.ndimage import binary_dilation, convolve, gaussian_filter

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "src"))
from gemsdoe50 import h51  # noqa: E402

G_OBS = 12226.0


def triangular_kernel() -> np.ndarray:
    r = int(np.ceil(h51.RADIUS_M / h51.PIXEL_M))
    yy, xx = np.mgrid[-r:r + 1, -r:r + 1]
    return np.maximum(0.0, 1.0 - (np.hypot(yy, xx) * h51.PIXEL_M) / h51.RADIUS_M).astype(np.float32)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--consensus", default=str(REPO / "evidence/h51_consensus.json"))
    ap.add_argument("--scratch", default=str(REPO / ".arena/work/h51"))
    ap.add_argument("--layers", default=str(REPO / ".arena/work/layers"))
    ap.add_argument("--budget", type=int, default=90000)
    ap.add_argument("--spacing", type=float, default=2.8)
    ap.add_argument("--grid-step", type=int, default=2500)
    ap.add_argument("--which", default="all", choices=("all", "replica", "novel"))
    ap.add_argument("--pool-factor", type=int, default=4)
    ap.add_argument("--out", default=str(REPO / "evidence/h51_frontier.json"))
    ap.add_argument("--stage", default="")
    args = ap.parse_args()

    rep = json.load(open(args.consensus))
    q = np.load(rep["posterior_file"]).astype(np.float32)
    q = q / float(q.sum())
    qn = q / float(q.max())
    scratch = Path(args.scratch)

    with rasterio.open(REPO / "data/grid/sample_submission.tif") as ds:
        valid = np.isfinite(ds.read(1))
    with rasterio.open(REPO / "data/grid/labels.tif") as ds:
        cat = valid & (ds.read(1) == 1)
    unmasked = valid & ~cat
    allowed = unmasked & (h51.distance_to_mask(cat) > 1.0)

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
    on_prior = np.zeros(valid.shape, bool)
    for p in prior_masks:
        on_prior |= p
    print(f"prior union {int(on_prior.sum()):,} px of the {int(unmasked.sum()):,} px unmasked domain")

    # ---- new-evidence field (independent of the score corpus by construction) ----------
    sys.path.insert(0, str(REPO / "scripts"))
    from h51_build import build_seismicity_layer  # noqa: E402
    corridors, seis_audit = build_seismicity_layer(
        REPO / "data/external/usgs_comcat_earthquakes.csv.gz", valid)
    L_seis = h51.normalize01(corridors, unmasked)
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
    geo = (0.5 * L_seis + 0.3 * L_mag + 0.2 * L_rad * 0.5 + 0.2 * L_spring).astype(np.float32)
    geo = geo / float(geo.max())
    print(f"geo field built; seismicity audit {seis_audit}")

    ker = triangular_kernel()
    qC = convolve(q, ker, mode="constant", cval=0.0)          # additive support increments
    half = ker.shape[0] // 2
    rr, cc = np.mgrid[-half:half + 1, -half:half + 1]
    rr = rr.ravel(); cc = cc.ravel(); kv = ker.ravel()

    novel = allowed & ~on_prior
    designs = {}
    if args.which in ("all", "replica"):
        designs["consensus"] = (qn, allowed)
        designs["consensus_geo0.25"] = (None, allowed)
    for w in (0.0, 0.25, 0.5, 1.0, 2.0):
        b = qn + w * geo
        designs[f"novelpx_q+w{w}"] = (b / float(b.max()), novel)
    designs["consensus_geo0.25"] = (None, allowed)
    gm = qn + 0.25 * geo
    designs["consensus_geo0.25"] = (gm / float(gm.max()), allowed)

    ks = list(range(args.grid_step, args.budget + 1, args.grid_step))
    results = {}
    for name, (belief, dom) in designs.items():
        order = h51.place_dots_ordered(belief, dom, h51.EmissionParams(
            spacing_px=args.spacing, budget=args.budget, belief_floor=1e-9,
            pool_factor=args.pool_factor))
        print(f"{name}: packer accepted {order.size:,} dots")
        Cmax = np.zeros(valid.shape, np.float32)   # running max-credit field
        cumM = 0.0                                 # running additive support mass / G
        curve, step = [], 0
        H, W = valid.shape
        for i, idx in enumerate(order, start=1):
            r0, c0 = divmod(int(idx), W)
            a1, a2 = max(0, r0 - half), min(H, r0 + half + 1)
            b1, b2 = max(0, c0 - half), min(W, c0 + half + 1)
            kr1, kc1 = half - (r0 - a1), half - (c0 - b1)
            np.maximum(Cmax[a1:a2, b1:b2],
                       ker[kr1:kr1 + (a2 - a1), kc1:kc1 + (b2 - b1)],
                       out=Cmax[a1:a2, b1:b2])
            cumM += float(qC[r0, c0])
            if step < len(ks) and i == ks[step]:
                T = G_OBS * float((q * Cmax).sum())
                M = G_OBS * cumM
                curve.append(dict(K=i, pred=float(T / (0.2 * (i - M + T) + 0.8 * G_OBS)),
                                  T=float(T), M=float(M)))
                step += 1
                if step >= len(ks):
                    break
        results[name] = curve
        best = max(curve, key=lambda r: r["pred"])
        print(f"  best K={best['K']:,} pred={best['pred']:.4f}  "
              + " ".join(f"{r['K'] // 1000}k:{r['pred']:.4f}" for r in curve[::max(1, len(curve) // 8)]))

    # novelty + IoU for the best operating point of each design
    summary = {}
    for name, curve in results.items():
        best = max(curve, key=lambda r: r["pred"])
        belief, dom = designs[name]
        order = h51.place_dots_ordered(belief, dom, h51.EmissionParams(
            spacing_px=args.spacing, budget=best["K"], belief_floor=1e-9,
            pool_factor=args.pool_factor))
        dots = np.zeros(valid.shape, bool)
        dots.ravel()[order] = True
        novel_exact = float((dots & ~on_prior).sum()) / max(1, int(dots.sum()))
        ious = []
        for p in prior_masks:
            inter = float((dots & p).sum()); union = float((dots | p).sum())
            ious.append(inter / union if union else 0.0)
        summary[name] = dict(best=best, n=int(dots.sum()), novel_exact=novel_exact,
                             max_iou=float(np.max(ious)), mean_iou=float(np.mean(ious)))
        print(f"{name:24s} K={best['K']:6d} pred={best['pred']:.4f} novel_exact={novel_exact:.3f} "
              f"maxIoU={np.max(ious):.3f} meanIoU={np.mean(ious):.3f}")

    Path(args.out).write_text(json.dumps(dict(
        G_obs=G_OBS, spacing=args.spacing, stage=args.stage, seismicity_audit=seis_audit,
        prior_union_px=int(on_prior.sum()), curves=results, summary=summary), indent=1))
    print(f"wrote {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
