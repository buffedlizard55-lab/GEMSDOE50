#!/usr/bin/env python3
"""Independently re-read the H51 deliverable and check the portal contract.

This is deliberately a *separate* code path from ``scripts/build_h51.py``: it opens the
written file with rasterio, compares it against the official template and label rasters in
``data/grid/``, re-hashes it, unpacks the zip, and writes
``evidence/checks_h51_raster.json``.  Run it after every rebuild.

Contract (quoted from the competition submission-format section):

* same projected CRS as the training data (EPSG:32611),
* same resolution and bounds (100 m, transform [100, 0, 243350, 0, -100, 4508550]),
* a single layer, 32-bit float, values between 0 and 1,
* data outside the bounds null or NaN.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import zipfile
from pathlib import Path

import numpy as np
import rasterio

REPO = Path(__file__).resolve().parents[1]
TEMPLATE = REPO / "data" / "grid" / "sample_submission.tif"
LABELS = REPO / "data" / "grid" / "labels.tif"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def check(tif: Path, evidence: Path) -> dict:
    report: dict = {"file": str(tif.relative_to(REPO)) if REPO in tif.parents else str(tif),
                    "sha256": sha256(tif), "checks": {}, "errors": []}
    with rasterio.open(TEMPLATE) as template:
        template_data = template.read(1)
        template_profile = {
            "crs": str(template.crs), "transform": [float(v) for v in template.transform][:6],
            "height": template.height, "width": template.width, "dtype": template.dtypes[0],
            "count": template.count,
        }
    with rasterio.open(tif) as ds:
        data = ds.read(1)
        profile = {
            "crs": str(ds.crs), "transform": [float(v) for v in ds.transform][:6],
            "height": ds.height, "width": ds.width, "dtype": ds.dtypes[0], "count": ds.count,
            "nodata": None if ds.nodata is None else float(ds.nodata),
        }
    finite = np.isfinite(data)
    checks = report["checks"]
    checks["single_band"] = profile["count"] == 1
    checks["float32"] = profile["dtype"] == "float32"
    checks["crs_matches_template"] = profile["crs"] == template_profile["crs"]
    checks["shape_matches_template"] = (
        (profile["height"], profile["width"]) == (template_profile["height"], template_profile["width"]))
    checks["transform_matches_template"] = np.allclose(
        profile["transform"], template_profile["transform"], atol=0.0)
    checks["values_finite_in_range"] = bool(
        np.all((data[finite] >= 0.0) & (data[finite] <= 1.0)))
    checks["nan_only_where_template_is_nan"] = bool(
        np.array_equal(np.isnan(data), np.isnan(template_data)))
    checks["nonzero_only_inside_template"] = int(np.count_nonzero(data[~np.isfinite(template_data)] > 0)) == 0
    checks["has_predictions"] = int(np.count_nonzero(data > 0)) > 0
    report["predicted_cells"] = int(np.count_nonzero(data > 0))
    report["finite_cells"] = int(finite.sum())
    report["nan_cells"] = int((~finite).sum())
    report["profile"] = profile
    report["template"] = template_profile
    for key, value in checks.items():
        if not value:
            report["errors"].append(key)
    # the checksum the submission note carries must be this file's own
    if evidence.exists():
        build = json.loads(evidence.read_text(encoding="utf-8"))
        recorded = build.get("outputs", {}).get("primary", {}).get("sha256")
        checks["sha256_matches_build_evidence"] = recorded == report["sha256"]
        report["mass_matches_evidence"] = build.get("outputs", {}).get("primary", {}).get(
            "footprint_nonzero") == report["predicted_cells"]
        if not checks["sha256_matches_build_evidence"]:
            report["errors"].append("sha256_matches_build_evidence")
    return report


def check_zip(zpath: Path, tif: Path) -> dict:
    with zipfile.ZipFile(zpath) as zf:
        names = zf.namelist()
        payload = zf.read(names[0]) if names else b""
    return {"entries": names, "single_geotiff": len(names) == 1 and names[0].endswith(".tif"),
            "bytes_match_tif": hashlib.sha256(payload).hexdigest() == sha256(tif),
            "sha256": sha256(zpath)}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--tif", default=None)
    ap.add_argument("--evidence", default=str(REPO / "evidence" / "build_h51.json"))
    ap.add_argument("--out", default=str(REPO / "evidence" / "checks_h51_raster.json"))
    args = ap.parse_args()
    evidence = Path(args.evidence)
    if args.tif:
        tif = Path(args.tif)
    else:
        build = json.loads(evidence.read_text(encoding="utf-8"))
        tif = REPO / build["outputs"]["primary"]["path"]
    report = check(tif, evidence)
    allfinite = tif.with_name(tif.name.replace("-nan.tif", "-allfinite.tif"))
    if allfinite.exists():
        with rasterio.open(allfinite) as ds:
            data = ds.read(1)
        with rasterio.open(TEMPLATE) as template:
            footprint = np.isfinite(template.read(1))
        report["allfinite_twin"] = {
            "file": str(allfinite.name),
            "all_finite": bool(np.all(np.isfinite(data))),
            "outside_footprint_nonzero": int(np.count_nonzero(data[~footprint] > 0)),
        }
    zpath = tif.with_suffix(".zip")
    if zpath.exists():
        report["zip"] = check_zip(zpath, tif)
        if not report["zip"]["single_geotiff"] or not report["zip"]["bytes_match_tif"]:
            report["errors"].append("zip")
    Path(args.out).write_text(json.dumps(report, indent=1), encoding="utf-8")
    print(json.dumps({"file": report["file"], "sha256": report["sha256"],
                      "predicted_cells": report["predicted_cells"],
                      "checks": report["checks"], "errors": report["errors"]}, indent=1))
    return 1 if report["errors"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
