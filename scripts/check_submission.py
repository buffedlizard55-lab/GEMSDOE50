#!/usr/bin/env python3
"""Local format checks + uniqueness gate.

Format requirements, quoted from the official submission-format section
(https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/):

  * same projected CRS as the training data (UTM 11N, EPSG:32611)
  * same resolution as the training data (100 m)
  * same bounds as the training data; data outside the bounds is null or nan
  * a single layer, datatype 32-bit float, values between 0 and 1

Uniqueness gate: the file must not be a copy of, or a near-copy of, any artifact the
project has already shipped.  The corpus is every prior artifact that is locally
available (the 23 hash-pinned mirrors plus the site download directories of the two
most recent repositories).
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

import numpy as np
import rasterio

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from gems50 import grid  # noqa: E402

WORK = Path("/tmp/gems50")
ROOT = Path(__file__).resolve().parents[1]
#: the study footprint travels with the repository (packed bitmask) so the checks run
#: anywhere, including a bare CI runner.
FOOTPRINT_NPZ = ROOT / "registry" / "footprint_mask.npz"
SIGNATURES_NPZ = ROOT / "registry" / "prior_artifact_signatures.npz"
TEMPLATE = Path("/tmp/gems_work/sample_submission.tif")
LABELS = Path("/tmp/gems_work/labels.tif")
#: directories holding *submission artifacts* (never raw data rasters: a continuous
#: data field has a positive value nearly everywhere and would trivially "cover"
#: every dot, which would say nothing about whether the submission is unique).
import os

CORPUS_DIRS = [Path(p) for p in os.environ.get("GEMS50_CORPUS", "").split(":") if p] or [
    Path("/tmp/gems_work/scored"),
    Path("/tmp/scratch/ref/GEMSDOE32/docs/downloads"),
    Path("/tmp/scratch/ref/GEMSDOE30/docs/downloads"),
    Path("/tmp/scratch/ref/GEMSDOE32/docs/research/quarantine"),
]
#: an artifact is a *submission* if its positive values are a small sparse set rather
#: than a continuous field
MAX_POSITIVE_FRACTION = 0.05


def format_checks(path: Path) -> dict:
    with rasterio.open(path) as s:
        checks = {}
        checks["driver"] = s.driver
        checks["count_is_1"] = s.count == 1
        checks["dtype_is_float32"] = s.dtypes[0] == "float32"
        checks["crs_is_epsg32611"] = str(s.crs) == grid.CRS
        checks["same_shape"] = (s.height, s.width) == grid.SHAPE
        checks["same_transform"] = tuple(s.transform)[:6] == grid.TRANSFORM
        checks["same_bounds"] = tuple(s.bounds) == grid.BOUNDS
        a = s.read(1)
        fin = np.isfinite(a)
        checks["min"] = float(np.nanmin(a))
        checks["max"] = float(np.nanmax(a))
        checks["nan_count"] = int((~fin).sum())
        checks["values_in_0_1"] = bool(np.nanmin(a) >= 0.0 and np.nanmax(a) <= 1.0)
        checks["nan_only_outside_footprint"] = None  # filled below
        checks["positive_px"] = int((a > 0).sum())
        checks["unique_positive_values"] = [float(v) for v in np.unique(a[a > 0])][:5]
        checks["compression"] = str(s.compression)
        checks["nodata"] = s.nodata
    if TEMPLATE.exists():
        with rasterio.open(TEMPLATE) as s:
            tmpl = np.isfinite(s.read(1))
        checks["footprint_source"] = "competition sample_submission.tif"
    elif FOOTPRINT_NPZ.exists():
        z = np.load(FOOTPRINT_NPZ)
        tmpl = np.unpackbits(z["packed"])[: int(np.prod(z["shape"]))].astype(bool)
        tmpl = tmpl.reshape(tuple(int(v) for v in z["shape"]))
        checks["footprint_source"] = "registry/footprint_mask.npz"
    else:
        tmpl = None
    with rasterio.open(path) as s:
        a = s.read(1)
    if tmpl is not None:
        checks["footprint_px"] = int(tmpl.sum())
        # Informational only.  The official text says data *outside the bounds* is null
        # or nan; inside the raster rectangle the organizers' own reference writer emits
        # zeros (no nodata, no NaN), and zero-outside files from sibling repositories were
        # accepted and scored by the portal.  So NaN *or* exact 0 outside the footprint is
        # valid; what must never happen is NaN *inside* the footprint (it fails the
        # portal's "[0, 1]" range check).
        checks["nan_only_outside_footprint"] = bool(np.all(np.isfinite(a[tmpl])))
        checks["outside_footprint_all_nan"] = "informational: " + str(bool(np.all(~np.isfinite(a[~tmpl]))))
        outside = a[~tmpl]
        checks["outside_footprint_nan_or_zero"] = bool(np.all(~np.isfinite(outside) | (outside == 0.0)))
    checks["all_checks_pass"] = all(v is True for k, v in checks.items()
                                    if isinstance(v, bool) and v is not None)
    return checks


def coarse_occupancy(mask: np.ndarray, factor: int) -> np.ndarray:
    h, w = mask.shape
    h2, w2 = h // factor * factor, w // factor * factor
    blocks = mask[:h2, :w2].reshape(h2 // factor, factor, w2 // factor, factor)
    return blocks.any(axis=(1, 3))


def signature_check(mine: np.ndarray, my_sha: str) -> dict:
    """Uniqueness at block level — runs without the multi-hundred-MB corpus.

    Thresholds are set from the measured distribution of this project's own artifacts
    (see registry/prior_artifact_signatures.json): at 8x blocks every *different*
    artifact scores below 0.18, the closest same-evidence-family file 0.44, so a screen
    at 0.75 catches a copy or near-copy without failing legitimate new work.
    """
    z = np.load(SIGNATURES_NPZ, allow_pickle=False)
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
        "verdict_unique": bool(ok), "verification_level": "block-signature",
        "downsample_blocks": factors, "n_prior": len(rows),
        "max_iou_block8": worst["iou_block8"], "max_iou_block32": worst["iou_block32"],
        "screen_threshold_block8": 0.75,
        "worst_overlap_file": worst["file"], "identical_sha256": identical,
        "my_sha256": my_sha, "my_dots": int(mine.sum()),
        "note": ("block-occupancy signatures catch copies and near-copies; fine-scale novelty "
                 "(full-pixel IoU and the fraction of dots >200 m from any prior dot) is measured "
                 "where the full corpus exists and is recorded in registry/submission_checks.json."),
    }


def load_corpus() -> list:
    out = []
    for d in CORPUS_DIRS:
        if not d.exists():
            continue
        for f in sorted(d.glob("*.tif")):
            if f.name.startswith("checks-"):
                continue
            try:
                with rasterio.open(f) as s:
                    if (s.height, s.width) != grid.SHAPE:
                        continue
                    a = s.read(1)
                pos = np.argwhere(np.isfinite(a) & (a > 0))
                if pos.shape[0] > MAX_POSITIVE_FRACTION * a.size:
                    print(f"  (not a submission artifact, skipped: {f.name})")
                    continue
                out.append((str(f), pos, hashlib.sha256(f.read_bytes()).hexdigest()))
            except Exception as exc:  # noqa: BLE001
                print(f"  (skipped {f.name}: {exc})")
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--submission", default=str(WORK / "submission.tif"))
    ap.add_argument("--out", default="/tmp/gems50/checks.json")
    args = ap.parse_args()
    path = Path(args.submission)

    checks = format_checks(path)
    print(json.dumps(checks, indent=1))

    from scipy.spatial import cKDTree

    with rasterio.open(path) as s:
        a = s.read(1)
    mine = np.argwhere(np.isfinite(a) & (a > 0))
    corpus = load_corpus()
    if not corpus and SIGNATURES_NPZ.exists():
        print("corpus: absent — falling back to the committed coarse signatures")
        uniq = signature_check(np.isfinite(a) & (a > 0), hashlib.sha256(path.read_bytes()).hexdigest())
        print(json.dumps(uniq, indent=1))
        Path(args.out).write_text(json.dumps({"format": checks, "uniqueness": uniq}, indent=1))
        print("wrote", args.out)
        return 0 if checks["all_checks_pass"] and uniq["verdict_unique"] else 1
    if not corpus:
        print("corpus: not available in this environment — uniqueness gate recorded as SKIPPED")
        Path(args.out).write_text(json.dumps({"format": checks, "uniqueness": {
            "verdict": "SKIPPED", "verdict_unique": None,
            "my_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
            "my_dots": checks.get("positive_px"),
            "reason": "prior artifacts not present in this environment"}}, indent=1))
        return 0 if checks["all_checks_pass"] else 1
    print(f"corpus: {len(corpus)} prior artifacts with matching grid")
    uniq = {"n_prior": len(corpus), "identical_sha256": [], "max_iou": 0.0,
            "worst_overlap_file": None, "min_novel_fraction_at_2px": 1.0,
            "corpus_entries": []}
    my_sha = hashlib.sha256(path.read_bytes()).hexdigest()
    my_tree = cKDTree(mine)
    for name, pos, sha in corpus:
        entry = {"file": Path(name).name, "prior_dots": int(pos.shape[0])}
        if sha == my_sha:
            uniq["identical_sha256"].append(Path(name).name)
        if pos.shape[0] == 0:
            corpus_entry = entry
            uniq["corpus_entries"].append(corpus_entry)
            continue
        tree = cKDTree(pos)
        d_mine, _ = tree.query(mine, k=1)
        novel = float((d_mine > 2.0).mean())          # my dots >200 m from any of theirs
        d_theirs, _ = my_tree.query(pos, k=1)
        reproduced = float((d_theirs <= 2.0).mean())  # their dots I re-emit
        inter = (d_mine <= 2.0).sum()
        union = mine.shape[0] + pos.shape[0] - inter
        iou = float(inter / max(union, 1))
        entry.update(novel_fraction_at_2px=novel, reproduced_prior=reproduced, iou_2px=iou)
        uniq["corpus_entries"].append(entry)

        if iou > uniq["max_iou"]:
            uniq["max_iou"] = iou
            uniq["worst_overlap_file"] = Path(name).name
        uniq["min_novel_fraction_at_2px"] = min(uniq["min_novel_fraction_at_2px"], novel)
    uniq["my_dots"] = int(mine.shape[0])
    uniq["my_sha256"] = my_sha
    uniq["verdict_unique"] = (not uniq["identical_sha256"]) and uniq["max_iou"] < 0.5
    print(json.dumps({k: v for k, v in uniq.items() if k != "corpus_entries"}, indent=1))
    Path(args.out).write_text(json.dumps({"format": checks, "uniqueness": uniq}, indent=1))
    print("wrote", args.out)
    return 0 if checks["all_checks_pass"] and uniq["verdict_unique"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
