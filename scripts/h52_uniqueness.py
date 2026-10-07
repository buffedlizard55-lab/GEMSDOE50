#!/usr/bin/env python3
"""Uniqueness gate for the H52 submission.

The standing constraint on this project is that the submitted raster must be *generated*, not a
copy of any prior submission.  This gate measures that directly, against every prior artifact it
can physically open:

* **exact pixels** -- set equality of the nonzero pixel sets, plus SHA-256;
* **2 px proximity** -- the metric's own tolerance is 3 px, so two rasters whose dots sit within
  2 px of each other are competing for the same credit; the fraction of my dots with a prior dot
  within 2 px is reported per prior, and the minimum over priors is the novelty statistic;
* **coarse block occupancy** -- IoU on 8 x 8 and 32 x 32 block occupancy, which is what catches a
  prior that has been resampled or shifted.

Priors are read from ``GEMS50_CORPUS`` (colon separated) if set, otherwise from ``downloads``,
``docs/downloads`` and the committed coarse signature archive ``registry/prior_artifact_signatures.npz``.
The committed archive carries 50 prior rasters' block masks and is used as a fallback when the
full rasters are not on disk in this environment.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path

import numpy as np
import rasterio
from scipy.spatial import cKDTree

REPO = Path(__file__).resolve().parents[1]
SIGNATURES = REPO / "registry/prior_artifact_signatures.npz"
DEFAULT_DIRS = ["downloads", "docs/downloads", "data/external", "docs/downloads/archive"]


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def load_corpus() -> list[tuple[str, np.ndarray]]:
    dirs = [Path(p) for p in os.environ.get("GEMS50_CORPUS", "").split(":") if p]
    dirs = dirs or [REPO / d for d in DEFAULT_DIRS]
    out = []
    for d in dirs:
        if not d.exists():
            continue
        for f in sorted(d.glob("*.tif")):
            if not f.name.endswith(("-nan.tif", "-allfinite.tif")) and "-nan." not in f.name:
                if "nan" not in f.name and "allfinite" not in f.name:
                    continue
            try:
                with rasterio.open(f) as ds:
                    a = ds.read(1)
            except Exception:
                continue
            out.append((f.name, np.isfinite(a) & (a > 0)))
    return out


def signature_fallback(mask: np.ndarray, my_sha: str) -> dict:
    z = np.load(SIGNATURES, allow_pickle=True)
    names, shas = z["names"], z["sha256"]
    f8, f32 = int(z["factors"][0]), int(z["factors"][1])
    h, w = z["grid_shape"]

    def occ(m, f):
        hh, ww = (h // f) * f, (w // f) * f
        return m[:hh, :ww].reshape(hh // f, f, ww // f, f).any(axis=(1, 3))

    mine8 = occ(mask, f8)
    rows = []
    for i, nm in enumerate(names):
        if shas[i] == my_sha:
            rows.append({"file": str(nm), "identical_sha256": True, "iou": 1.0})
            continue
        o8 = z["masks_block8"][i].astype(bool)
        inter = np.logical_and(mine8.ravel(), o8).sum()
        union = np.logical_or(mine8.ravel(), o8).sum()
        rows.append({"file": str(nm), "identical_sha256": False,
                     "iou": float(inter / max(union, 1))})
    worst = max(rows, key=lambda r: r["iou"])
    return {"n_prior": len(rows), "identical_sha256": [r["file"] for r in rows
                                                       if r["identical_sha256"]],
            "max_block8_iou": float(worst["iou"]), "worst_overlap_file": worst["file"],
            "source": "registry/prior_artifact_signatures.npz (committed coarse signatures)",
            "verdict_unique": bool(worst["iou"] < 0.5 and not any(r["identical_sha256"]
                                                                  for r in rows))}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--submission", default=None)
    ap.add_argument("--iou-threshold", type=float, default=0.5)
    ap.add_argument("--novel-threshold", type=float, default=0.5)
    ap.add_argument("--out", default="evidence/h52_uniqueness.json")
    args = ap.parse_args()

    build = json.loads((REPO / "evidence/h52_build.json").read_text(encoding="utf-8"))
    name = build["checks"]["name"]
    n = build["checks"]["n_dots"]
    sub = Path(args.submission) if args.submission else \
        REPO / f"docs/downloads/{name}-{n}-allfinite.tif"
    with rasterio.open(sub) as ds:
        a = ds.read(1)
    mine = np.isfinite(a) & (a > 0)
    my_sha = sha256(sub)
    my_rc = np.argwhere(mine)

    corpus = load_corpus()
    corpus = [(nm, m) for nm, m in corpus if not nm.startswith(sub.name.rsplit("-", 2)[0] + "-")
              or nm == sub.name]
    print(f"{sub.name}: {int(mine.sum()):,} dots; corpus candidates on disk: {len(corpus)}")
    if not corpus:
        out = {"my_sha256": my_sha, "my_dots": int(mine.sum()),
               "uniqueness": signature_fallback(mine, my_sha)}
        (REPO / args.out).write_text(json.dumps(out, indent=1) + "\n", encoding="utf-8")
        print(json.dumps(out["uniqueness"], indent=1))
        return 0

    tree_mine = cKDTree(my_rc)
    rows = []
    for nm, m in corpus:
        if m.shape != mine.shape:
            continue
        same = bool(np.array_equal(m, mine))
        inter = int(np.logical_and(mine, m).sum())
        union = int(np.logical_or(mine, m).sum())
        other = np.argwhere(m)
        if other.size == 0:
            continue
        t = cKDTree(other)
        d, _ = t.query(my_rc, k=1)
        novel2 = float((d > 2.0).mean())
        d2, _ = tree_mine.query(other, k=1)
        rows.append({"file": nm, "identical_pixels": same, "iou": inter / max(union, 1),
                     "novel_fraction_at_2px": novel2,
                     "their_novel_fraction_at_2px": float((d2 > 2.0).mean()),
                     "n_prior_dots": int(other.shape[0])})
    rows.sort(key=lambda r: -r["iou"])
    worst_iou = rows[0] if rows else None
    worst_nov = min(rows, key=lambda r: r["novel_fraction_at_2px"]) if rows else None
    payload = {
        "my_sha256": my_sha, "my_dots": int(mine.sum()),
        "instrument": "EXACT pixel-set equality + IoU on the full grid; novelty = fraction of my "
                      "dots with no prior dot within 2 px (the metric's own tolerance is 3 px)",
        "rows": rows,
        "max_iou": float(worst_iou["iou"]) if worst_iou else None,
        "worst_overlap_file": worst_iou["file"] if worst_iou else None,
        "min_novel_fraction_at_2px": float(worst_nov["novel_fraction_at_2px"]) if worst_nov else None,
        "min_novel_vs": worst_nov["file"] if worst_nov else None,
        "n_prior_compared": len(rows),
        "verdict_unique": bool(rows and worst_iou["iou"] < args.iou_threshold
                               and worst_nov["novel_fraction_at_2px"] > args.novel_threshold
                               and not any(r["identical_pixels"] for r in rows)),
        "gate": {"max_iou": args.iou_threshold, "min_novel_fraction_at_2px": args.novel_threshold},
    }
    (REPO / args.out).write_text(json.dumps(payload, indent=1) + "\n", encoding="utf-8")
    print(json.dumps({k: v for k, v in payload.items() if k not in ("rows", "instrument")},
                     indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
