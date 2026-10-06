import json
import subprocess
import sys
from pathlib import Path


def test_static_site_builds_clear_no_slot_pages_from_report(tmp_path: Path):
    output = tmp_path / "site"
    report_path = tmp_path / "report.json"
    tiff_path = tmp_path / "candidate.tif"
    tiff_path.write_bytes(b"test placeholder")
    report = {
        "evaluation": {
            "method_results": {
                "H50-S1": {
                    "pooled": {
                        "score": 0.12,
                        "truth_cells": 100,
                        "prediction_cells": 40,
                        "tp_weight": 25,
                        "fp_weight": 20,
                        "fn_weight": 75,
                    },
                    "folds": [
                        {"id": "NW", "dti": 0.1, "prediction_cells": 10, "truth_cells": 25},
                    ],
                },
                "H32-D": {
                    "pooled": {
                        "score": 0.11,
                        "truth_cells": 100,
                        "prediction_cells": 40,
                        "tp_weight": 22,
                        "fp_weight": 24,
                        "fn_weight": 78,
                    },
                    "folds": [
                        {"id": "NW", "dti": 0.12, "prediction_cells": 10, "truth_cells": 25},
                    ],
                },
            },
            "incumbent_method": "H32-D",
            "candidate_minus_incumbent_pooled_dti": 0.01,
            "promotion_gate": {
                "pass": False,
                "decision": "NO_SLOT",
                "components": {"test_gate": False},
            },
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
        },
        "submission_artifact": {
            "unique_name": "candidate.tif",
            "optional_note": "research only",
            "sha256": "abc123",
        },
    }
    report_path.write_text(json.dumps(report), encoding="utf-8")
    script = Path(__file__).parents[1] / "scripts" / "build_h50_site.py"
    subprocess.run(
        [
            sys.executable,
            str(script),
            "--output-dir",
            str(output),
            "--report",
            str(report_path),
            "--tiff",
            str(tiff_path),
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    for name in ("index.html", "results.html", "methods.html", "submission.html"):
        assert (output / name).is_file()
    results = (output / "results.html").read_text(encoding="utf-8")
    submission = (output / "submission.html").read_text(encoding="utf-8")
    assert "NO SLOT" in results
    assert "do not use a weekly submission slot" in submission
    assert "candidate.tif" in submission
