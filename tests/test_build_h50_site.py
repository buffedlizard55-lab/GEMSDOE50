import hashlib
import json
from pathlib import Path

import numpy as np
import rasterio
from rasterio.transform import Affine

from scripts import build_h50_site


def _report(tiff_path: Path, *, built: bool, sha256: str) -> dict:
    split_path = tiff_path.parent / "holdout.json"
    transform = Affine(100, 0, 500000, 0, -100, 4100000)
    values = np.array([[1.0, 0.0], [np.nan, np.nan]], dtype=np.float32)
    with rasterio.open(
        tiff_path,
        "w",
        driver="GTiff",
        width=2,
        height=2,
        count=1,
        dtype="float32",
        crs="EPSG:32611",
        transform=transform,
        nodata=np.nan,
    ) as output:
        output.write(values, 1)

    grid = {
        "crs": "EPSG:32611",
        "height": 2,
        "official_label_raster_sha256": "b" * 64,
        "template_sha256": "a" * 64,
        "transform": list(transform),
        "width": 2,
    }
    split_path.write_text(json.dumps({"grid": grid}), encoding="utf-8")
    actual_bytes = tiff_path.stat().st_size
    bounds = [500000.0, 4099800.0, 500200.0, 4100000.0]
    byte_validation = {
        "sha256": sha256,
        "bytes": actual_bytes,
        "positive_cells": 1,
        "minimum_valid_value": 0.0,
        "maximum_valid_value": 1.0,
        "range_pass": True,
        "nodata_mask_matches_template": True,
        "band_count": 1,
        "dtype": "float32",
        "crs": grid["crs"],
        "width": grid["width"],
        "height": grid["height"],
        "transform": grid["transform"],
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
            "smoothed_density_controls": {
                "pooled_dti": {
                    "smoothed-density-300m": 0.08,
                    "smoothed-density-1km": 0.07,
                    "smoothed-density-2km": 0.06,
                },
            },
        },
        "submission_artifact": {
            "built": built,
            "unique_name": tiff_path.name,
            "optional_note": "research diagnostic only",
            "sha256": sha256,
            "bytes": actual_bytes,
            "positive_cells": 1,
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


def _build_with_report(monkeypatch, output_dir: Path, report_path: Path, tiff_path: Path, report: dict) -> None:
    monkeypatch.setattr(build_h50_site, "PINNED_SPLIT_PATH", report_path.parent / "holdout.json")
    report_path.write_text(json.dumps(report), encoding="utf-8")
    build_h50_site.build_pages(output_dir, report_path, tiff_path)


def test_site_only_links_artifact_when_report_hash_matches_and_keeps_science_gate_separate(
    monkeypatch, tmp_path: Path
):
    output_dir = tmp_path / "site"
    report_path = tmp_path / "report.json"
    tiff_path = tmp_path / "candidate.tif"
    provisional = _report(tiff_path, built=True, sha256="")
    digest = hashlib.sha256(tiff_path.read_bytes()).hexdigest()
    provisional["submission_artifact"]["sha256"] = digest
    provisional["submission_artifact"]["validation"]["sha256"] = digest
    _build_with_report(monkeypatch, output_dir, report_path, tiff_path, provisional)

    index = (output_dir / "index.html").read_text(encoding="utf-8")
    results = (output_dir / "results.html").read_text(encoding="utf-8")
    methods = (output_dir / "methods.html").read_text(encoding="utf-8")
    submission = (output_dir / "submission.html").read_text(encoding="utf-8")

    assert "Download verified H50-S1 research TIFF" in index
    assert digest in index
    assert "Scientific and provenance eligibility" in results
    assert "NO_SLOT" in results
    assert "intersect plausible planes with the exact-grid USGS 3DEP terrain elevation surface" in methods
    assert "intersect plausible planes with z=0" not in methods
    assert "0.2778 score-to-artifact association remains unresolved" in index
    assert "0.3195" in index
    assert "No upload was performed" in submission


def test_site_refuses_a_hash_matching_tiff_with_off_grid_validation_metadata(monkeypatch, tmp_path: Path):
    output_dir = tmp_path / "site"
    report_path = tmp_path / "report.json"
    tiff_path = tmp_path / "candidate.tif"
    report = _report(tiff_path, built=True, sha256="")
    digest = hashlib.sha256(tiff_path.read_bytes()).hexdigest()
    report["submission_artifact"]["sha256"] = digest
    report["submission_artifact"]["validation"]["sha256"] = digest
    report["submission_artifact"]["validation"]["transform"][0] += 1.0

    _build_with_report(monkeypatch, output_dir, report_path, tiff_path, report)
    index = (output_dir / "index.html").read_text(encoding="utf-8")
    assert "Download verified H50-S1 research TIFF" not in index
    assert "No verified H50-S1 download available" in index


def test_site_does_not_link_a_stale_or_hash_mismatched_tiff(monkeypatch, tmp_path: Path):
    output_dir = tmp_path / "site"
    report_path = tmp_path / "report.json"
    tiff_path = tmp_path / "candidate.tif"
    stale = _report(tiff_path, built=False, sha256="0" * 64)
    _build_with_report(monkeypatch, output_dir, report_path, tiff_path, stale)
    submission = (output_dir / "submission.html").read_text(encoding="utf-8")
    assert "No verified, downloadable H50-S1 GeoTIFF is available" in submission
    assert "Download research-only candidate.tif" not in submission

    current = _report(tiff_path, built=True, sha256="0" * 64)
    _build_with_report(monkeypatch, output_dir, report_path, tiff_path, current)
    index = (output_dir / "index.html").read_text(encoding="utf-8")
    assert "Download verified H50-S1 research TIFF" not in index
    assert "No verified H50-S1 download available" in index
