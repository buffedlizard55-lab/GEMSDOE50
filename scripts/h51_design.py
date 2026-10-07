#!/usr/bin/env python3
"""H51 design search: choose the emission that maximizes the validated instrument score
subject to a novelty constraint against every prior artifact.

Reported for each variant:
  n            emitted dots (unmasked footprint)
  pred         instrument-predicted leaderboard score (score-weighted consensus posterior)
  novel2px     fraction of candidate dots with no prior dot within 2 px (25 full corpora)
  max_iou25    worst exact IoU against the 25 full prior rasters
  max_iou_blk  worst block-8 IoU against all 50 registered prior signatures
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
import rasterio
from scipy.ndimage import binary_dilation, distance_transform_edt

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "src"))
from gemsdoe50 import h51  # noqa: E402

G_OBS = 12226.0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--consensus", default=str(REPO / "evidence/h51_consensus.json"))
    ap.add_argument("--scratch", default=str(REPO / ".arena/work/h51"))
    ap.add_argument("--layers", default=str(REPO / ".arena/work/layers"))
    ap.add_argument("--out", default=str(REPO / "evidence/h51_design.json"))
    args = ap.parse_args()

    rep = json.load(open(args.consensus))
    q = np.load(rep["posterior_file"]).astype(np.float32)
    q = q / q.sum()
    scratch = Path(args.scratch)

    with rasterio.open(REPO / "data/grid/sample_submission.tif") as ds:
        valid = np.isfinite(ds.read(1))
    with rasterio.open(REPO / "data/grid/labels.tif") as ds:
        cat = valid & (ds.read(1) == 1)
    unmasked = valid & ~cat
    allowed = unmasked & (h51.distance_to_mask(cat) > 1.0)

    # --- prior artifacts for novelty measurement --------------------------------------
    prior = []
    for f in sorted(scratch.glob("*.tif")):
        with rasterio.open(f) as ds:
            a = ds.read(1)
        prior.append((np.isfinite(a) & (a > 0)))
    inc = REPO / "downloads/gems50-seislin-44709-20261006T2041Z-79e260ae.tif"
    if inc.exists():
        with rasterio.open(inc) as ds:
            a = ds.read(1)
        prior.append(np.isfinite(a) & (a > 0))
    sig = np.load(REPO / "registry/prior_artifact_signatures.npz", allow_pickle=True)
    blk_names = sig["names"]
    _s8 = sig["masks_block8"]
    _shape8 = tuple(int(x) for x in sig["coarse_shapes"][0])          # (466, 411)
    blk8 = np.stack([np.unpackbits(row)[: _shape8[0] * _shape8[1]].reshape(_shape8)
                     for row in _s8]).astype(bool)

    # geological layers (new evidence, not used by the consensus posterior) ------------
    geo = json.load(open(REPO / "evidence/h51_build_primary.json"))
    from scipy.ndimage import gaussian_filter
    tmi = rasterio.open(Path(args.layers) / "geodawn_extensions_u8.tif").read(4).astype(float)
    ok = tmi != 0
    L_mag = h51.normalize01(h51.gradient_lineament_response(tmi, ok), unmasked)
    rows, cols = [], []
    import csv
    for r in csv.DictReader(open(Path(args.layers) / "gdr_wellspring_in_footprint.csv")):
        if (r.get("thermalclass") or "") == "Hot":
            try:
                rows.append(float(r["row"])); cols.append(float(r["col"]))
            except Exception:
                pass
    L_spring = h51.normalize01(h51.point_alignment(np.array(rows), np.array(cols), valid.shape, 10.0), unmasked)
    corridors = np.load("/tmp/proto/seis_corridors.npy")
    L_seis = h51.normalize01(corridors, unmasked)

    def dots_for(belief: np.ndarray, spacing: float, qthr: float) -> np.ndarray:
        b = belief.copy()
        if qthr > 0:
            b[b < qthr * float(b.max())] = 0.0
        return h51.place_dots(b, allowed, h51.EmissionParams(spacing_px=spacing, budget=120000,
                                                             belief_floor=1e-12))

    def metrics(dots: np.ndarray) -> dict:
        n = int(dots.sum())
        C = h51.credit_field(dots); S = h51.support_field(dots)
        T = G_OBS * float((q * C).sum()); M = G_OBS * float((q * S).sum())
        pred = T / (0.2 * (n - M + T) + 0.8 * G_OBS)
        novel, ious = [], []
        for p in prior:
            d = binary_dilation(p, np.ones((5, 5), bool))
            novel.append(float((dots & ~d).sum()) / max(1, n))
            inter = float((dots & p).sum()); union = float((dots | p).sum())
            ious.append(inter / union if union else 0.0)
        # block-8 IoU against the 50 registered signatures
        b8 = dots[:3730 // 8 * 8, :3292 // 8 * 8].reshape(3730 // 8, 8, 3292 // 8, 8).any(axis=(1, 3))
        biou = []
        for m in blk8:
            inter = float((b8 & m).sum()); union = float((b8 | m).sum())
            biou.append(inter / union if union else 0.0)
        return dict(n=n, pred=float(pred), E_T=float(T), novel2px=float(np.mean(novel)),
                    min_novel2px=float(np.min(novel)), max_iou25=float(np.max(ious)),
                    max_iou_blk8=float(np.max(biou)), worst_prior_block=blk_names[int(np.argmax(biou))])

    variants = {}
    qmax = float(q.max())
    qn = q / qmax
    for spacing in (2.0, 2.8):
        for qt in (0.0, 0.25):
            variants[f"consensus_s{spacing}_q{qt}"] = dots_for(qn, spacing, qt)
    for w in (0.10, 0.25, 0.50):
        mix = qn + w * (0.5 * L_seis + 0.3 * L_mag + 0.2 * L_spring)
        variants[f"mix_q+w{w}_s2.8_q0.25"] = dots_for(mix / mix.max(), 2.8, 0.25)
    geo_belief = 0.5 * L_seis + 0.3 * L_mag + 0.2 * L_spring
    variants["geo_only_s2.8"] = dots_for(geo_belief / geo_belief.max(), 2.8, 0.0)
    variants["seis_only_s2.8"] = dots_for(L_seis, 2.8, 0.0)

    rows = {}
    print(f"{'variant':26s} {'n':>7s} {'pred':>7s} {'E[T]':>8s} {'novel2px':>9s} {'maxIoU25':>9s} {'maxIoUblk8':>11s}")
    for k, d in variants.items():
        m = metrics(d)
        rows[k] = m
        print(f"{k:26s} {m['n']:7d} {m['pred']:7.4f} {m['E_T']:8.1f} {m['novel2px']:9.3f} "
              f"{m['max_iou25']:9.3f} {m['max_iou_blk8']:11.3f}")
    Path(args.out).write_text(json.dumps(dict(G_obs=G_OBS, rows=rows), indent=1))
    print(f"wrote {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
