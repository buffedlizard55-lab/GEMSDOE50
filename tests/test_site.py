import json
import subprocess
import sys
from pathlib import Path


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
            "translation_controls": {"pooled_dti_q95": 0.09, "scores": [{"id": "translate-01", "pooled_dti": 0.08}]},
            "time_shuffle_controls": {"count": 1, "pooled_dti_q95": 0.08,
                                      "scores": [{"id": "time-shuffle-01", "pooled_dti": 0.07}]},
            "smoothed_density_controls": {"pooled_dti": {"smoothed-density-1km": 0.10,
                                                            "smoothed-density-2km": 0.09},
                                          "candidate_beats_both": True},
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
    assert index.index("Download the H53-A no-go research TIFF") < index.index("<h1>Test new evidence")
    assert "H53-A is NO-GO / NO SLOT" in index
    assert "NO SLOT" in results and "0.000000" in results
    assert "smoothed-density-1km" in results and "smoothed-density-2km" in results
    assert "Separate H50-S1 research record — historical proxy only" in results
    assert "NO SLOT" in submission and "do not upload" in submission
    assert "GEMSDOE50-H53-PROBE-TMI-POINTLINEATION-20261007" in submission
    assert "0 accepted" in methods


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
    assert "H53-A no-go research TIFF" in index
    assert "Older H51 files and metrics are retained as experiment history" in index
    assert "Historical H51 evidence (archive only)" in results
    assert "Separate H50-S1 research line" in results
    assert "not an organizer score" in results
    assert "Historical H51 candidate TIFFs" in results
    assert "Archived H51 design notes" in results
    assert "H51 file archive (not the current recommendation)" in results
    assert "Submit it in five steps" not in results
    assert "How to submit" not in results
    assert "all-finite twin" not in results
    assert "GEMSDOE50-H51-SCARPRADIO-OFFCAT" not in index
    assert "GEMSDOE50-H51-SCARPRADIO-OFFCAT" not in submission
    assert "SLOT-ELIGIBLE" in submission and "NO SLOT" in submission
    assert "H52-A" in methods  # retained in the historical H51 methods block
    assert "not as current submission advice" in results
