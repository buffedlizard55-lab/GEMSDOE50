import hashlib
import json
import subprocess
import sys
from pathlib import Path

import numpy as np
import rasterio
from rasterio.transform import Affine

from scripts import build_h50_site


def _h53_evidence(tmp_path: Path, output: Path) -> Path:
    root = Path(__file__).parents[1]
    evidence = tmp_path / "evidence"
    evidence.mkdir(parents=True, exist_ok=True)
    for name in ("h53-build-20261007.json", "h53-validation-20261007.json"):
        (evidence / name).write_bytes((root / "evidence" / name).read_bytes())
    build = json.loads((evidence / "h53-build-20261007.json").read_text(encoding="utf-8"))
    artifact = output / build["candidate"]["artifact"]["path"]
    artifact.parent.mkdir(parents=True, exist_ok=True)
    artifact.write_bytes(b"no-go fixture placeholder")
    return evidence


def test_static_site_builds_clear_no_slot_pages_from_report(tmp_path: Path):
    output = tmp_path / "site"
    evidence = _h53_evidence(tmp_path, output)
    report_path = tmp_path / "report.json"
    report = {
        "evaluation": {
            "method_results": {
                "H50-S1": {
                    "pooled": {"score": 0.12, "truth_cells": 100, "prediction_cells": 40,
                               "tp_weight": 25, "fp_weight": 20, "fn_weight": 75},
                    "folds": [{"id": "NW", "dti": 0.1, "prediction_cells": 10, "truth_cells": 25}],
                },
                "H32-D": {
                    "pooled": {"score": 0.11, "truth_cells": 100, "prediction_cells": 40,
                               "tp_weight": 22, "fp_weight": 24, "fn_weight": 78},
                    "folds": [{"id": "NW", "dti": 0.12, "prediction_cells": 10, "truth_cells": 25}],
                },
            },
            "incumbent_method": "H32-D",
            "candidate_minus_incumbent_pooled_dti": 0.01,
            "promotion_gate": {"pass": False, "decision": "NO_SLOT", "components": {"test_gate": False}},
            "subtile_bootstrap": {"percentile_ci_95": [-0.01, 0.02]},
            "translation_controls": {
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
                    "smoothed-density-300m": 0.13,
                    "smoothed-density-1km": 0.10,
                    "smoothed-density-2km": 0.09,
                },
                "candidate_beats_all": False,
            },
        },
        "submission_artifact": {
            "unique_name": "candidate.tif",
            "optional_note": "research only",
            "sha256": "abc123",
        },
        "submission_artifact": {"unique_name": "candidate.tif", "optional_note": "research only",
                                "sha256": "abc123"},
    }
    report_path.write_text(json.dumps(report), encoding="utf-8")
    script = Path(__file__).parents[1] / "scripts" / "build_h50_site.py"
    subprocess.run(
        [sys.executable, str(script), "--output-dir", str(output), "--report", str(report_path),
         "--evidence-dir", str(evidence)],
        check=True, capture_output=True, text=True,
    )
    for name in ("index.html", "results.html", "methods.html", "submission.html"):
        assert (output / name).is_file()
    index = (output / "index.html").read_text(encoding="utf-8")
    results = (output / "results.html").read_text(encoding="utf-8")
    methods = (output / "methods.html").read_text(encoding="utf-8")
    submission = (output / "submission.html").read_text(encoding="utf-8")
    assert "NO SLOT" in results
    assert "smoothed-density-300m" in results
    assert "smoothed-density-1km" in results
    assert "smoothed-density-2km" in results
    assert "Do not upload on a failed gate" in submission
    assert "candidate.tif" in submission
    assert "No verified H50-S1 download available" in index


def _write_validated_candidate(tmp: Path) -> tuple[Path, dict[str, object]]:
    tiff_path = tmp / "candidate.tif"
    transform = Affine(100, 0, 500000, 0, -100, 4100000)
    data = np.array([[1.0, 0.0], [np.nan, np.nan]], dtype=np.float32)
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
    ) as dst:
        dst.write(data, 1)
    digest = hashlib.sha256(tiff_path.read_bytes()).hexdigest()
    spec_path = tmp / "holdout.json"
    spec = {
        "grid": {
            "width": 2,
            "height": 2,
            "crs": "EPSG:32611",
            "transform": list(transform),
            "template_sha256": "a" * 64,
            "official_label_raster_sha256": "b" * 64,
        }
    }
    spec_path.write_text(json.dumps(spec), encoding="utf-8")
    report = {
        "registered_split": {"spec_sha256": hashlib.sha256(spec_path.read_bytes()).hexdigest()},
        "data": {
            "competition_training_rasters": {
                "template_sha256": "a" * 64,
                "labels_sha256": "b" * 64,
            }
        },
        "evaluation": {"promotion_gate": {"pass": True}},
        "submission_artifact": {
            "built": True,
            "unique_name": tiff_path.name,
            "sha256": digest,
            "bytes": tiff_path.stat().st_size,
            "validation": {
                "sha256": digest,
                "bytes": tiff_path.stat().st_size,
                "range_pass": True,
                "nodata_mask_matches_template": True,
                "band_count": 1,
                "dtype": "float32",
                "crs": "EPSG:32611",
                "positive_cells": 1,
                "minimum_valid_value": 0.0,
                "maximum_valid_value": 1.0,
                "width": 2,
                "height": 2,
                "transform": list(transform),
                "bounds": [500000.0, 4099800.0, 500200.0, 4100000.0],
            },
        },
    }
    return tiff_path, report


def test_site_verifies_report_hash_grid_and_actual_tiff_bytes(monkeypatch, tmp_path: Path):
    tiff_path, report = _write_validated_candidate(tmp_path)
    monkeypatch.setattr(build_h50_site, "PINNED_SPLIT_PATH", tmp_path / "holdout.json")

    assert build_h50_site.verify_h50_artifact(report, tiff_path) is True

    tiff_path.write_bytes(tiff_path.read_bytes() + b"tamper")
    assert build_h50_site.verify_h50_artifact(report, tiff_path) is False


def test_site_never_links_artifact_when_holdout_gate_failed(monkeypatch, tmp_path: Path):
    tiff_path, report = _write_validated_candidate(tmp_path)
    monkeypatch.setattr(build_h50_site, "PINNED_SPLIT_PATH", tmp_path / "holdout.json")
    report["evaluation"]["promotion_gate"]["pass"] = False

    assert build_h50_site.verify_h50_artifact(report, tiff_path) is False


def _h51_evidence(tmp: Path) -> Path:
    evidence = tmp / "evidence"
    evidence.mkdir(parents=True, exist_ok=True)
    build = {
        "name": "gems51-test-35000",
        "built_utc": "2026-10-06T23:00:00Z",
        "outputs": {
            "primary": {"path": "docs/downloads/gems51-test-35000-nan.tif", "bytes": 1, "sha256": "a" * 64,
                        "crs": "EPSG:32611", "shape": [3730, 3292], "dtype": "float32", "count": 1,
                        "transform": [100.0, 0.0, 243350.0, 0.0, -100.0, 4508550.0],
                        "cells_finite": 5_167_373, "cells_nan": 7_111_787, "outside_unit_interval": 0,
                        "outside_footprint_nonzero": 0, "footprint_min": 0.0, "footprint_max": 1.0,
                        "footprint_nonzero": 35000},
            "allfinite": {"path": "docs/downloads/gems51-test-35000-allfinite.tif", "bytes": 1,
                          "sha256": "b" * 64, "cells_finite": 12_279_160, "cells_nan": 0, "min": 0.0,
                          "max": 1.0, "outside_unit_interval": 0, "outside_footprint_nonzero": 0,
                          "footprint_nonzero": 35000},
            "zip": {"path": "docs/downloads/gems51-test-35000-nan.zip", "bytes": 1, "sha256": "c" * 64,
                    "contains": "gems51-test-35000-nan.tif"},
        },
        "instruments": {
            "candidate": {"catalogue": {"dti": 0.0, "credit_per_dot": 0.0, "truth_cells": 60988,
                                        "covered_fraction": 0.0, "tp_weight": 0.0},
                          "sgmc_off": {"dti": 0.1, "credit_per_dot": 0.19, "truth_cells": 61664,
                                       "covered_fraction": 0.1, "tp_weight": 6610.0},
                          "monte_cristo": {"dti": 0.002, "credit_per_dot": 0.0005, "truth_cells": 242,
                                           "covered_fraction": 0.08, "tp_weight": 18.9}},
            "random_control": {"catalogue": {"dti": 0.0, "credit_per_dot": 0.0, "truth_cells": 60988,
                                             "covered_fraction": 0.0, "tp_weight": 0.0},
                               "sgmc_off": {"dti": 0.07, "credit_per_dot": 0.116, "truth_cells": 61664,
                                            "covered_fraction": 0.06, "tp_weight": 4063.0},
                               "monte_cristo": {"dti": 0.005, "credit_per_dot": 0.001, "truth_cells": 242,
                                                "covered_fraction": 0.14, "tp_weight": 34.9}},
            "translation_controls": {},
        },
        "mass_rule": {"rule": "amendment A2", "marginal_transfer": 0.28, "chosen_mass": 35000,
                      "rows": [{"mass": 10000, "sgmc_credit_per_dot": 0.2093, "within_10pct_of_best": True,
                                "mc_tp_weight": 5.5, "mc_random_control": 7.8,
                                "beats_mc_control_by_20pct": False, "kept": False},
                               {"mass": 35000, "sgmc_credit_per_dot": 0.1889, "within_10pct_of_best": True,
                                "mc_tp_weight": 18.9, "mc_random_control": 12.7,
                                "beats_mc_control_by_20pct": True, "kept": True}]},
        "mass_sweep": {"35000": {"n_dots": 35000, "instruments": {
            "sgmc_off": {"credit_per_dot": 0.1889}, "monte_cristo": {"tp_weight": 18.9}}}},
        "uniqueness": {"n_prior_artifacts": 50, "max_jaccard": 0.66,
                       "max_jaccard_against": "gems16-h16-1.tif", "max_overlap_of_mine": 0.9,
                       "max_overlap_against": "13gems.tif"},
        "field": {"definition": "0.75 * scarp-focused topographic + 0.55 * radiometric",
                  "families": {"topographic_scarp": {"n_layers": 7, "class": "measured-here"},
                               "radiometric": {"n_layers": 14, "class": "measured-here"}}},
        "seismicity_family": {"catalog_qc": {"uncertainty": {
            "documented_in_survey": 10107, "modelled_in_survey": 61215,
            "calibration": {"model": "log10(h_err_m) = ...", "fit_population": 141888, "fit_r2": 0.715,
                            "footprint_holdout": {"median_observed_m": 4810.0, "median_predicted_m": 3064.0,
                                                  "within_factor_2_fraction": 0.504}}}},
            "corridors": {"width_rule": "max(2 sigma, 300 m)"}},
    }
    (evidence / "build_h51.json").write_text(json.dumps(build), encoding="utf-8")
    (evidence / "holdout_h51.json").write_text(json.dumps({
        "folds_positive": 4, "folds_total": 4,
        "folds": [{"id": "NW", "candidate_dots_in_core": 12015, "candidate_credit_per_dot": 0.1494,
                   "random_control_credit_per_dot": 0.0974, "candidate_minus_control": 0.052}],
        "subtile_bootstrap": {"percentile_ci_95": [0.0406, 0.0785], "paired_delta_mean": 0.0583},
    }), encoding="utf-8")
    (evidence / "mc_sensitivity_h51.json").write_text(json.dumps({
        "masses": {"35000": {"candidate_mc_tp_weight": 18.9, "mc_control_mean": 16.6, "mc_control_sd": 3.4,
                             "candidate_mc_percentile_vs_controls": 0.71, "candidate_sgmc_credit_per_dot": 0.1889,
                             "sgmc_control_mean": 0.1174, "sgmc_control_sd": 0.0021}}}), encoding="utf-8")
    (evidence / "uniqueness_h51.json").write_text(json.dumps({
        "prior_vs_prior_null": {"32": {"median": 0.825, "max": 1.0}, "8": {"median": 0.454, "max": 1.0}},
        "exact_pixel_vs_local_priors": [{"share_of_mine": 0.0272}],
    }), encoding="utf-8")
    return evidence


def test_site_keeps_h51_visible_only_as_historical_evidence(tmp_path: Path):
    output = tmp_path / "site"
    evidence = _h53_evidence(tmp_path, output)
    _h51_evidence(tmp_path)
    archived_tiff = output / "downloads" / "gemsdoe50-h51-corridor-consensus-mix-20261007T0200Z.tif"
    archived_tiff.parent.mkdir(parents=True, exist_ok=True)
    archived_tiff.write_bytes(b"historical H51 fixture")
    report_path = tmp_path / "report.json"
    report_path.write_text("{}", encoding="utf-8")
    script = Path(__file__).parents[1] / "scripts" / "build_h50_site.py"
    subprocess.run([sys.executable, str(script), "--output-dir", str(output), "--report",
                    str(report_path), "--evidence-dir", str(evidence)],
                   check=True, capture_output=True, text=True)
    index = (output / "index.html").read_text(encoding="utf-8")
    results = (output / "results.html").read_text(encoding="utf-8")
    methods = (output / "methods.html").read_text(encoding="utf-8")
    submission = (output / "submission.html").read_text(encoding="utf-8")
    # Merged design: the index page opens with the H51 candidate panel and the two-candidate table
    # (both with one-click downloads) before the executive summary; the high-contrast one-click band
    # now lives on the submission page.
    assert "RESEARCH-ONLY FILE — SOURCE-RIGHTS GATE OPEN" in submission
    assert "gems51-test-35000-nan.tif" in index and "gems51-test-35000-nan.zip" in index
    assert "two-candidate" in index or "Two candidate GeoTIFFs" in index
    assert index.index("Download .tif") < index.index("<h2>Executive summary</h2>")
    assert "GEMSDOE50-H51-SCARPRADIO-OFFCAT" in submission
    assert "Manual H51 submission workflow (currently blocked)" in submission
    assert "NO SLOT" in submission
    assert "Spatially blocked validation" in results and "4/4" in results
    assert "weak guard" in results
    assert "null distribution" in results
    assert "H52-A" in methods
    assert "organizer-scored" in index  # the page must say the numbers are local, not organizer scores


def test_site_promotes_the_h53_candidate_when_its_files_exist(tmp_path: Path):
    repo = Path(__file__).parents[1]
    output = tmp_path / "site"
    (output / "downloads").mkdir(parents=True)
    # Pre-create the H53 deliverables so the generator's existence gates pass.
    ship = json.loads((repo / "evidence" / "h53_ship.json").read_text(encoding="utf-8"))
    for key in ("tif", "allfinite", "zip"):
        leaf = Path(ship["outputs"][key]).name
        (output / "downloads" / leaf).write_bytes(b"h53 placeholder")
        ship["outputs"][key] = f"downloads/{leaf}"
    evidence = _h51_evidence(tmp_path)
    (evidence / "h53_ship.json").write_text(json.dumps(ship), encoding="utf-8")
    (evidence / "h53_check_submission.json").write_text(
        (repo / "evidence" / "h53_check_submission.json").read_text(encoding="utf-8"),
        encoding="utf-8")
    (evidence / "h53_validation_final.json").write_text(
        (repo / "evidence" / "h53_validation_final.json").read_text(encoding="utf-8"),
        encoding="utf-8")
    tiff = tmp_path / "candidate.tif"
    tiff.write_bytes(b"placeholder")
    report_path = tmp_path / "report.json"
    report_path.write_text("{}", encoding="utf-8")
    script = repo / "scripts" / "build_h50_site.py"
    subprocess.run([sys.executable, str(script), "--output-dir", str(output), "--report",
                    str(report_path), "--tiff", str(tiff), "--evidence-dir", str(evidence),
                    "--h53-ship", str(evidence / "h53_ship.json"),
                    "--h53-check", str(evidence / "h53_check_submission.json"),
                    "--h53-final", str(evidence / "h53_validation_final.json")],
                   check=True, capture_output=True, text=True)
    index = (output / "index.html").read_text(encoding="utf-8")
    results = (output / "results.html").read_text(encoding="utf-8")
    methods = (output / "methods.html").read_text(encoding="utf-8")
    submission = (output / "submission.html").read_text(encoding="utf-8")
    assert "Download the H53 candidate GeoTIFF" in index
    assert "Three candidate GeoTIFFs on this branch" in index
    assert "C · H53 TMI" in index
    assert "GEMSDOE50-H53-TMICONJ-OFFCAT" in submission
    assert "How to submit the H53 file" in submission
    assert "H53 measured results" in results
    assert "H53 method, in one page" in methods
    assert "H53-B fixed seismicity corridors" in methods
