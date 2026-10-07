import hashlib
import json
from pathlib import Path

from scripts.build_h50_site import build_pages


def _report(tiff_path: Path, *, built: bool, sha256: str) -> dict:
    split_path = Path(__file__).parents[1] / "evidence/holdout-v1.json"
    split = json.loads(split_path.read_text(encoding="utf-8"))
    grid = split["grid"]
    transform = grid["transform"]
    width, height = grid["width"], grid["height"]
    left, top = transform[2], transform[5]
    bounds = [left, top + height * transform[4], left + width * transform[0], top]
    byte_validation = {
        "sha256": sha256,
        "bytes": tiff_path.stat().st_size,
        "positive_cells": 40,
        "minimum_valid_value": 0.0,
        "maximum_valid_value": 1.0,
        "range_pass": True,
        "nodata_mask_matches_template": True,
        "band_count": 1,
        "dtype": "float32",
        "crs": grid["crs"],
        "width": width,
        "height": height,
        "transform": transform,
        "bounds": bounds,
    }
    method_names = [
        "H50-S1",
        "H50-prior",
        "H32-D",
        "H47-S3",
        "H48-DS",
        "Smoothed-density-300m",
    ]
    method_results = {
        name: {
            "pooled": {
                "score": 0.1,
                "truth_cells": 100,
                "prediction_cells": 40,
                "tp_weight": 25.0,
                "fp_weight": 20.0,
                "fn_weight": 75.0,
            },
            "folds": [
                {
                    "id": "F1",
                    "dti": 0.1,
                    "prediction_cells": 40,
                    "truth_cells": 100,
                }
            ],
        }
        for name in method_names
    }
    return {
        "registered_split": {
            "spec_sha256": hashlib.sha256(split_path.read_bytes()).hexdigest(),
        },
        "data": {
            "competition_training_rasters": {
                "template_sha256": grid["template_sha256"],
                "labels_sha256": grid["official_label_raster_sha256"],
            },
        },
        "evaluation": {
            "method_results": method_results,
            "incumbent_method": "H50-prior",
            "candidate_minus_incumbent_pooled_dti": 0.0,
            "promotion_gate": {
                "pass": True,
                "decision": "HOLDOUT_PASS_REVIEW_ONLY",
                "components": {"beats_smoothed_density_control": True},
            },
            "subtile_bootstrap": {"percentile_ci_95": [-0.01, 0.02]},
            "translation_controls": {
                "count": 1,
                "pooled_dti_q95": 0.09,
                "scores": [{"id": "translate-01", "pooled_dti": 0.08}],
            },
            "time_shuffle_controls": {
                "count": 1,
                "pooled_dti_q95": 0.08,
                "scores": [{"id": "time-shuffle-01", "pooled_dti": 0.07}],
            },
        },
        "submission_artifact": {
            "built": built,
            "unique_name": tiff_path.name,
            "optional_note": "research diagnostic only",
            "sha256": sha256,
            "bytes": tiff_path.stat().st_size if tiff_path.exists() else None,
            "positive_cells": 40,
            "validation": byte_validation,
        },
        "submission_eligibility": {
            "pass": False,
            "decision": "NO_SLOT",
            "note": "Vertical datum and event uncertainty remain unresolved.",
            "gates": {
                "statistical_holdout_promotion": True,
                "catalog_to_dem_vertical_datum_transformation_verified": False,
            },
        },
    }


def test_site_only_links_artifact_when_report_hash_matches_and_keeps_science_gate_separate(tmp_path: Path):
    output_dir = tmp_path / "site"
    report_path = tmp_path / "report.json"
    tiff_path = tmp_path / "candidate.tif"
    tiff_path.write_bytes(b"synthetic test bytes")
    expected_hash = hashlib.sha256(tiff_path.read_bytes()).hexdigest()
    report_path.write_text(
        json.dumps(_report(tiff_path, built=True, sha256=expected_hash)),
        encoding="utf-8",
    )
    build_pages(output_dir, report_path, tiff_path)

    index = (output_dir / "index.html").read_text(encoding="utf-8")
    results = (output_dir / "results.html").read_text(encoding="utf-8")
    methods = (output_dir / "methods.html").read_text(encoding="utf-8")
    submission = (output_dir / "submission.html").read_text(encoding="utf-8")

    assert "Download research-only GeoTIFF" in index
    assert expected_hash in index
    assert "Scientific and submission eligibility (separate gate)" in results
    assert "NO SLOT — ARTIFACT OR SCIENTIFIC / PROVENANCE GATES NOT VERIFIED" in results
    assert "intersect each plausible plane numerically with bilinearly sampled local terrain" in methods
    assert "intersect plausible planes with z=0" not in methods
    assert "0.2778 association remains unresolved" in methods
    assert "0.3195" in methods
    assert "Statistical gate passed only" in submission
    assert "No upload was performed" in submission


def test_site_refuses_a_hash_matching_tiff_with_off_grid_validation_metadata(tmp_path: Path):
    output_dir = tmp_path / "site"
    report_path = tmp_path / "report.json"
    tiff_path = tmp_path / "candidate.tif"
    tiff_path.write_bytes(b"synthetic test bytes")
    expected_hash = hashlib.sha256(tiff_path.read_bytes()).hexdigest()
    report = _report(tiff_path, built=True, sha256=expected_hash)
    report["submission_artifact"]["validation"]["transform"][0] += 1.0
    report_path.write_text(json.dumps(report), encoding="utf-8")

    build_pages(output_dir, report_path, tiff_path)
    index = (output_dir / "index.html").read_text(encoding="utf-8")
    assert "Download research-only GeoTIFF" not in index
    assert "No downloadable GeoTIFF is verified against this report" in index


def test_site_does_not_link_a_stale_or_hash_mismatched_tiff(tmp_path: Path):
    output_dir = tmp_path / "site"
    report_path = tmp_path / "report.json"
    tiff_path = tmp_path / "candidate.tif"
    tiff_path.write_bytes(b"stale bytes")
    report_path.write_text(
        json.dumps(_report(tiff_path, built=False, sha256="0" * 64)),
        encoding="utf-8",
    )
    build_pages(output_dir, report_path, tiff_path)
    submission = (output_dir / "submission.html").read_text(encoding="utf-8")
    assert "No verified GeoTIFF is available for download" in submission
    assert "Download research-only candidate.tif" not in submission

    report_path.write_text(
        json.dumps(_report(tiff_path, built=True, sha256="0" * 64)),
        encoding="utf-8",
    )
    build_pages(output_dir, report_path, tiff_path)
    index = (output_dir / "index.html").read_text(encoding="utf-8")
    assert "Download research-only GeoTIFF" not in index
    assert "No downloadable GeoTIFF is verified against this report" in index
