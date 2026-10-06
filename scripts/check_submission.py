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
TEMPLATE = Path("/tmp/gems_work/sample_submission.tif")
LABELS = Path("/tmp/gems_work/labels.tif")
#: directories holding *submission artifacts* (never raw data rasters: a continuous
#: data field has a positive value nearly everywhere and would trivially "cover"
#: every dot, which would say nothing about whether the submission is unique).
CORPUS_DIRS = [
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
        checks["nan_only_outside_footprint"] = bool(np.all(~np.isfinite(a[~tmpl])))
        checks["footprint_px"] = int(tmpl.sum())
        checks["outside_footprint_all_nan"] = bool(np.all(~np.isfinite(a[~tmpl])))
    checks["all_checks_pass"] = all(v is True for k, v in checks.items()
                                    if isinstance(v, bool) and v is not None)
    return checks


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
    if not corpus:
        print("corpus: not available in this environment — uniqueness gate recorded as SKIPPED")
        Path(args.out).write_text(json.dumps({"format": checks, "uniqueness": {
            "verdict": "SKIPPED", "reason": "prior artifacts not present in this environment"}}, indent=1))
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
