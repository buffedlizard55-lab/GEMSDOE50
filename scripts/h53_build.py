#!/usr/bin/env python3
"""Build the fixed H53-A research raster after the baseline-only audit is frozen.

This script builds a new score field from the GDR probe archive and GeoDAWN TMI only. It never
reads the SGMC proxy, private labels, or any previous prediction pixels. The baseline report is
read solely for the preregistered output budget and provenance check.
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import rasterio
from scipy.ndimage import distance_transform_edt

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "src"))

from gems51 import emit
from gems51 import grid as g
from gemsdoe50.common import sha256_array, sha256_file
from gemsdoe50.h53 import (
    build_probe_lineation,
    build_tmi_lineaments,
    deduplicate_area_cells,
    read_probe_points,
    warm_probe_marks,
)

BASELINE = REPO / "evidence/h53-baseline-20261007.json"
PROBE_ZIP = REPO / ".arena/public-inputs/2m_temperature_probe_INGENIOUS_regional_data.zip"
GEODAWN_TMI = REPO / ".arena/public-inputs/geodawn_extensions_u8.tif"
EXPECTED_PROBE_SHA = "1301f70d230058e616ea5d34d1c7a32fabf7d49198172f376c59c89bd652eca3"
EXPECTED_TMI_SHA = "a35a9c6d2a14786f4dab85481ee59769213072f5dab5b2535ea82ae4d9bb7d9b"
EXPECTED_BASELINE_SHA = "acd05c2a55d4d5a64a297075907bd53b5c0d52a78f655ddf3d34bc1d4d85f7bb"
OUT_DIR = REPO / "docs/downloads"


def _write_submission(path: Path, support: np.ndarray, valid: np.ndarray, template_path: Path) -> dict:
    support = np.asarray(support, dtype=bool)
    valid = np.asarray(valid, dtype=bool)
    if support.shape != valid.shape or np.any(support & ~valid):
        raise ValueError("support must lie wholly inside the official valid footprint")
    with rasterio.open(template_path) as template:
        profile = template.profile.copy()
        if (support.shape[1], support.shape[0]) != (template.width, template.height):
            raise ValueError("support shape does not match official submission grid")
    profile.update(driver="GTiff", count=1, dtype="float32", nodata=np.nan, compress="deflate",
                   predictor=3, tiled=True, blockxsize=256, blockysize=256)
    values = np.full(support.shape, np.nan, dtype=np.float32)
    values[valid] = support[valid].astype(np.float32)
    if not np.isfinite(values[valid]).all() or np.any((values[valid] < 0) | (values[valid] > 1)):
        raise ValueError("in-footprint submission values must be finite and lie in [0, 1]")
    with rasterio.open(path, "w", **profile) as dst:
        dst.write(values, 1)
        dst.set_band_description(1, "H53-A binary fault likelihood; 1=selected, 0=not selected")
        dst.update_tags(
            AREA_OR_POINT="Area",
            candidate="GEMSDOE50 H53-A research-only no-go artifact",
            method="survey-normalized 2 m probe point lineations concordant with GeoDAWN TMI_up150",
            note="Local proxy experiment only; not organizer-scored. NaN outside the valid prediction footprint per official format.",
            external_data="GDR INGENIOUS submission 1391 (CC BY 4.0); USGS GeoDAWN DOI 10.5066/P93LGLVQ (CC0 1.0)",
        )
    with rasterio.open(path) as ds:
        readback = ds.read(1)
        in_bounds = readback[valid]
        finite_outside = int(np.count_nonzero(np.isfinite(readback[~valid])))
        info = {
            "path": str(path.relative_to(REPO)),
            "sha256": sha256_file(path),
            "width": ds.width,
            "height": ds.height,
            "crs": str(ds.crs),
            "transform": [float(v) for v in tuple(ds.transform)[:6]],
            "dtype": ds.dtypes[0],
            "nodata": "NaN",
            "all_finite_in_valid_footprint": bool(np.isfinite(in_bounds).all()),
            "finite_pixels_outside_valid_footprint": finite_outside,
            "min_in_valid_footprint": float(in_bounds.min()),
            "max_in_valid_footprint": float(in_bounds.max()),
            "positive_cells": int(np.count_nonzero(in_bounds > 0)),
            "unique_values_in_valid_footprint": np.unique(in_bounds).tolist(),
        }
    return info


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--baseline", type=Path, default=BASELINE)
    parser.add_argument("--probe-zip", type=Path, default=PROBE_ZIP)
    parser.add_argument("--geodawn-tmi", type=Path, default=GEODAWN_TMI)
    parser.add_argument("--out-dir", type=Path, default=OUT_DIR)
    args = parser.parse_args()

    if not args.baseline.is_file():
        raise FileNotFoundError("run scripts/h53_baseline_audit.py first; frozen baseline report is absent")
    baseline_sha = sha256_file(args.baseline)
    if EXPECTED_BASELINE_SHA and baseline_sha != EXPECTED_BASELINE_SHA:
        raise ValueError(f"baseline report hash mismatch: {baseline_sha}")
    baseline = json.loads(args.baseline.read_text(encoding="utf-8"))
    if baseline.get("schema") != "gemsdoe50.h53-baseline-audit.v1" or baseline.get("status") != "BASELINE_FROZEN_AWAITING_H53":
        raise ValueError("baseline report is not a frozen candidate-independent audit")
    for path, expected, label in [
        (args.probe_zip, EXPECTED_PROBE_SHA, "GDR probe archive"),
        (args.geodawn_tmi, EXPECTED_TMI_SHA, "GeoDAWN extension raster"),
    ]:
        if not path.is_file():
            raise FileNotFoundError(f"{label} missing: {path}; run scripts/fetch_h53_inputs.sh")
        actual = sha256_file(path)
        if actual != expected:
            raise ValueError(f"{label} hash mismatch: {actual}")

    template_path = REPO / "data/grid/sample_submission.tif"
    with rasterio.open(template_path) as template:
        valid = np.isfinite(template.read(1))
        transform = template.transform
        shape = (template.height, template.width)
        expected_grid = ("EPSG:32611", 3292, 3730, (100.0, 0.0, 243350.0, 0.0, -100.0, 4508550.0))
        actual_grid = (str(template.crs), template.width, template.height,
                       tuple(float(v) for v in tuple(template.transform)[:6]))
        if actual_grid != expected_grid:
            raise ValueError(f"official sample grid differs from preregistered grid: {actual_grid}")

    with rasterio.open(args.geodawn_tmi) as ds:
        if (ds.width, ds.height) != (shape[1], shape[0]) or ds.crs != rasterio.crs.CRS.from_epsg(32611):
            raise ValueError("GeoDAWN TMI extension is not on the official grid")
        if not ds.transform.almost_equals(transform) or ds.count < 4:
            raise ValueError("GeoDAWN extension transform/band count does not match preregistration")
        description = ds.descriptions[3] if ds.descriptions else None
        if description != "TMI_up150":
            raise ValueError(f"expected band 4 TMI_up150, found {description!r}")
        tmi = ds.read(4)
        band_tags = dict(ds.tags(4))
    if tmi.dtype != np.uint8:
        raise ValueError(f"quantized GeoDAWN band expected uint8; found {tmi.dtype}")

    labels = g.load_labels()
    catalogue_distance = distance_transform_edt(~labels, sampling=(100.0, 100.0))
    allowed = valid & (catalogue_distance > 300.0)
    del catalogue_distance

    raw_points, source_audit = read_probe_points(
        args.probe_zip, transform=transform, valid=valid, target_crs="EPSG:32611"
    )
    points, dedup_audit = deduplicate_area_cells(raw_points)
    warm, ranks, mark_audit = warm_probe_marks(
        points, minimum_area_points=12, within_area_quantile=0.75
    )
    warm_rule_passed = bool(warm.any())
    tmi_lines = build_tmi_lineaments(
        tmi, valid, scales=(2.0, 5.0, 10.0), coherence_sigma=3.0,
        ridge_quantile=0.95, coherence_min=0.25,
    )
    lineation, lineation_audit = build_probe_lineation(
        points, ranks, warm, tmi_lines, transform=transform, valid=valid,
        pixel_size_m=100.0, cluster_radius_m=1500.0, minimum_cluster_points=5,
        minimum_axis_ratio=3.0, minimum_length_m=800.0, maximum_length_m=20_000.0,
        max_tmi_distance_px=5.0, max_angle_deg=30.0,
        minimum_tmi_alignment=0.50, corridor_sigma_px=1.5,
    )
    accepted_lineations = int(lineation_audit["clusters_accepted"])
    if accepted_lineations == 0:
        # Preserve the registered no-go outcome as a valid, all-zero research raster rather than
        # silently relaxing geometry thresholds or borrowing pixels from a prior submission.
        lineation.fill(0.0)

    incumbent_name = baseline["incumbent"]["name"]
    budget = int(baseline["incumbent"]["full_grid_positive_cells"])
    fold_budgets = {str(k): int(v) for k, v in baseline["incumbent"]["matched_mass_by_fold"].items()}
    if budget <= 0 or sum(fold_budgets.values()) <= 0:
        raise ValueError("frozen incumbent has no positive prediction budget")

    support, pack_audit = emit.pack(
        lineation, budget, valid=allowed, suppression_px=3.0, seed=5301
    )
    field_sha = sha256_array(lineation)
    candidate_name = f"gemsdoe50-h53-probe-tmi-pointlineation-20261007-{field_sha[:8]}"
    args.out_dir.mkdir(parents=True, exist_ok=True)
    output_path = args.out_dir / f"{candidate_name}.tif"
    artifact = _write_submission(output_path, support, valid, template_path)
    probe_sha = sha256_file(args.probe_zip)
    tmi_sha = sha256_file(args.geodawn_tmi)
    report = {
        "schema": "gemsdoe50.h53-build.v1",
        "built_utc": datetime.now(timezone.utc).isoformat(),
        "status": ("NO_GO_NO_ACCEPTED_LINEATIONS" if accepted_lineations == 0 else
                   "RESEARCH_ONLY_AWAITING_BLOCKED_VALIDATION"),
        "candidate": {
            "name": "GEMSDOE50-H53-PROBE-TMI-POINTLINEATION-20261007",
            "filename": output_path.name,
            "optional_note": "Survey-normalized 2 m probe point-pattern lineations concordant with GeoDAWN TMI_up150; 300 m known-catalogue exclusion; research proxy only, not organizer-scored.",
            "field_sha256": field_sha,
            "artifact": artifact,
            "build_support_count": int(support.sum()),
            "requested_native_budget": budget,
            "warm_mark_gate_passed": warm_rule_passed,
            "accepted_lineation_gate_passed": accepted_lineations > 0,
            "mass_gate_passed": int(support.sum()) == budget,
            "positive_cells_within_allowed_footprint": int((support & allowed).sum()),
            "artifact_sha_differs_from_registered_baseline_files": artifact["sha256"] not in {
                item["sha256"] for item in baseline["registered_baselines"].values()
            },
        },
        "baseline": {
            "path": str(args.baseline.relative_to(REPO)) if args.baseline.is_relative_to(REPO) else str(args.baseline),
            "sha256": baseline_sha,
            "frozen_incumbent": incumbent_name,
            "incumbent_sha256": baseline["incumbent"]["sha256"],
            "native_budget": budget,
            "matched_mass_by_fold": fold_budgets,
        },
        "inputs": {
            "gdr_probe_archive": {"path": str(args.probe_zip), "sha256": probe_sha,
                                  "official_doi": "10.15121/1881483", "licence": "CC BY 4.0",
                                  "source_mirror_commit": "07345ea0604953d7efb858d9cfbc21e20c7aca0b",
                                  "direct_official_binary_match": False},
            "geodawn_extension": {"path": str(args.geodawn_tmi), "sha256": tmi_sha,
                                  "band": 4, "description": description, "dtype": str(tmi.dtype),
                                  "tags": band_tags, "licence": "CC0 1.0",
                                  "source_mirror_commit": "07345ea0604953d7efb858d9cfbc21e20c7aca0b",
                                  "direct_official_binary_match": False},
        },
        "source_audit": source_audit,
        "deduplication_audit": dedup_audit,
        "warm_mark_rule": mark_audit,
        "lineation_rule": lineation_audit,
        "candidate_pack": pack_audit,
        "control_design": {
            "probe_density_500m": "Gaussian-smoothed warm-probe ranks, sigma 5 px, no point geometry",
            "probe_density_1km": "Gaussian-smoothed warm-probe ranks, sigma 10 px, no point geometry",
            "tmi_only": "TMI ridge strength only, no thermal probes",
            "all_controls_to_be_packed_at_frozen_per_fold_mass": True,
        },
        "grid": {"crs": "EPSG:32611", "width": shape[1], "height": shape[0],
                 "transform": list(expected_grid[3]),
                 "all_finite_in_valid_footprint": artifact["all_finite_in_valid_footprint"],
                 "nan_outside_valid_footprint": artifact["finite_pixels_outside_valid_footprint"] == 0,
                 "range_in_valid_footprint": [artifact["min_in_valid_footprint"], artifact["max_in_valid_footprint"]]},
        "honest_note": (
            "This build is generated from the H53-A source features, not copied pixels. "
            + ("The preregistered geometry produced zero accepted lineations; the linked all-zero "
               "raster is a no-go research artifact, not a useful competition prediction. "
               if accepted_lineations == 0 else "The candidate still requires blocked validation. ")
            + "The mirrored source bytes have not been matched to official downloads; no "
              "competition slot is authorized."
        ),
    }
    evidence_path = REPO / "evidence/h53-build-20261007.json"
    evidence_path.write_text(json.dumps(report, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    print(json.dumps({
        "candidate": output_path.name,
        "artifact_sha256": artifact["sha256"],
        "positive_cells": artifact["positive_cells"],
        "requested_budget": budget,
        "incumbent": incumbent_name,
        "accepted_clusters": lineation_audit["clusters_accepted"],
        "candidate_score_cells": lineation_audit["positive_score_cells"],
        "controls": "frozen controls are packed and scored by scripts/h53_validate.py",
        "evidence": str(evidence_path),
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
