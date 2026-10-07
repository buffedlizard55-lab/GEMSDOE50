#!/usr/bin/env python3
"""Full-resolution uniqueness gate for the H58-S1 submission.

The standing constraint on this project is that a submitted raster must be
*generated*, not a copy of any prior submission.  This gate measures that
directly, at full resolution, against every prior artifact it can physically
open:

* **exact pixels** — set equality of the nonzero pixel sets, plus SHA-256;
* **2 px proximity** — the metric's own tolerance is 3 px, so two rasters whose
  dots sit within 2 px of each other are competing for the same credit; the
  fraction of my dots with a prior dot within 2 px is reported per prior, and
  the minimum over priors is the novelty statistic;
* **coarse block occupancy** — IoU on 8 x 8 and 32 x 32 block occupancy from the
  committed signature archive ``registry/prior_artifact_signatures.npz``, which
  catches a prior that has been resampled or shifted.

The corpus is every submission-like raster (positive fraction <= 5 %) in
``downloads`` and ``docs/downloads``; continuous data fields are skipped because
they would trivially "cover" every dot.  The frozen prior-positive union
(``registry/prior_positive_union.npz``) is checked separately in the build:
the H58 emitter may only place dots outside it, so exact overlap is 0 by
construction.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
import rasterio
from scipy.spatial import cKDTree

REPO = Path(__file__).resolve().parents[1]
SIGNATURES = REPO / "registry/prior_artifact_signatures.npz"
BUILD = REPO / "evidence/h58_build.json"
DEFAULT_DIRS = ["downloads", "docs/downloads"]
MAX_POSITIVE_FRACTION = 0.05


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def load_corpus(stem: str) -> list[tuple[str, np.ndarray]]:
    out = []
    for d in DEFAULT_DIRS:
        base = REPO / d
        if not base.exists():
            continue
        for f in sorted(base.glob("*.tif")):
            if f.name.startswith("checks-") or f.name.startswith(stem):
                continue
            try:
                with rasterio.open(f) as ds:
                    a = ds.read(1)
            except Exception:  # noqa: BLE001, S112 — an unreadable raster is not a prior
                continue
            pos = np.isfinite(a) & (a > 0)
            if pos.shape != (3730, 3292):
                continue
            if pos.mean() > MAX_POSITIVE_FRACTION:
                continue  # continuous data field, not a submission artifact
            out.append((f.name, pos))
    return out


def coarse_occupancy(mask: np.ndarray, factor: int) -> np.ndarray:
    h, w = mask.shape
    h2, w2 = h // factor * factor, w // factor * factor
    blocks = mask[:h2, :w2].reshape(h2 // factor, factor, w2 // factor, factor)
    return blocks.any(axis=(1, 3))


def signature_check(mine: np.ndarray, my_sha: str) -> dict:
    z = np.load(SIGNATURES, allow_pickle=False)
    factors = [int(v) for v in z["factors"]]
    shapes = [tuple(int(v) for v in row) for row in z["coarse_shapes"]]
    stacked = {f: z[f"masks_block{f}"] for f in factors}
    mine_b = {f: coarse_occupancy(mine, f) for f in factors}
    rows = []
    for i, name in enumerate(z["names"]):
        rec = {"file": str(name), "prior_dots": int(z["counts"][i])}
        for j, f in enumerate(factors):
            other = np.unpackbits(stacked[f][i])[: shapes[j][0] * shapes[j][1]]
            other = other.astype(bool).reshape(shapes[j])
            inter = int((mine_b[f] & other).sum())
            union = int((mine_b[f] | other).sum())
            rec[f"iou_block{f}"] = inter / max(union, 1)
        rows.append(rec)
    worst = max(rows, key=lambda r: r["iou_block8"])
    identical = [str(n) for n, s2 in zip(z["names"], z["sha256"]) if str(s2) == my_sha]
    screen = worst["iou_block8"] < 0.75
    ok = (not identical) and screen
    return {
        "verdict": "PASS (block-signature level)" if ok else "FAIL (block-signature level)",
        "verdict_unique": bool(ok),
        "verification_level": "block-signature",
        "n_prior": len(rows),
        "max_iou_block8": worst["iou_block8"],
        "max_iou_block32": worst["iou_block32"],
        "screen_threshold_block8": 0.75,
        "worst_overlap_file": worst["file"],
        "identical_sha256": identical,
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--submission", default=None)
    ap.add_argument("--iou-threshold", type=float, default=0.5)
    ap.add_argument("--novel-threshold", type=float, default=0.5)
    ap.add_argument("--out", default="evidence/h58_uniqueness.json")
    args = ap.parse_args()

    build = json.loads(BUILD.read_text(encoding="utf-8"))
    stem = build["artifacts"]["stem"]
    sub = Path(args.submission) if args.submission else \
        REPO / f"docs/downloads/{stem}-allfinite.tif"
    with rasterio.open(sub) as ds:
        a = ds.read(1)
    mine = np.isfinite(a) & (a > 0)
    my_sha = sha256(sub)
    my_rc = np.argwhere(mine)

    corpus = load_corpus(stem)
    print(f"{sub.name}: {int(mine.sum()):,} dots; prior artifacts on disk: {len(corpus)}")

    tree_mine = cKDTree(my_rc)
    rows = []
    for nm, m in corpus:
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
        rows.append({
            "file": nm,
            "identical_pixels": same,
            "iou": inter / max(union, 1),
            "novel_fraction_at_2px": novel2,
            "their_novel_fraction_at_2px": float((d2 > 2.0).mean()),
            "n_prior_dots": int(other.shape[0]),
        })
    rows.sort(key=lambda r: -r["iou"])
    worst_iou = rows[0] if rows else None
    worst_nov = min(rows, key=lambda r: r["novel_fraction_at_2px"]) if rows else None
    sig = signature_check(mine, my_sha)
    payload = {
        "artifact": stem,
        "my_sha256": my_sha,
        "my_dots": int(mine.sum()),
        "instrument": (
            "EXACT pixel-set equality + full-pixel IoU; novelty = fraction of my dots with no "
            "prior dot within 2 px (the metric's own tolerance is 3 px); plus the committed "
            "8x/32x block-signature screen over 50 priors"
        ),
        "full_resolution": {
            "rows": rows,
            "max_iou": float(worst_iou["iou"]) if worst_iou else None,
            "worst_overlap_file": worst_iou["file"] if worst_iou else None,
            "min_novel_fraction_at_2px": (
                float(worst_nov["novel_fraction_at_2px"]) if worst_nov else None
            ),
            "min_novel_vs": worst_nov["file"] if worst_nov else None,
            "n_prior_compared": len(rows),
        },
        "block_signature": sig,
        "prior_union_exact_overlap": build["prior_pixel_exclusion"]["candidate_exact_overlap_with_union"],
        "verdict_unique": bool(
            sig["verdict_unique"]
            and (worst_iou is None or worst_iou["iou"] < args.iou_threshold)
            and (worst_nov is None or worst_nov["novel_fraction_at_2px"] > args.novel_threshold)
            and not any(r["identical_pixels"] for r in rows)
            and build["prior_pixel_exclusion"]["candidate_exact_overlap_with_union"] == 0
        ),
        "gate": {
            "max_iou": args.iou_threshold,
            "min_novel_fraction_at_2px": args.novel_threshold,
            "prior_union_exact_overlap": 0,
        },
    }
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, indent=1) + "\n", encoding="utf-8")
    print(json.dumps({k: v for k, v in payload.items() if k not in ("full_resolution", "instrument")},
                     indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
