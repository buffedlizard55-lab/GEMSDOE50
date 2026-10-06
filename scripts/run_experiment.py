#!/usr/bin/env python3
"""Run the frozen H50-S1 experiment and write an auditable research-only GeoTIFF."""

from __future__ import annotations

import argparse
import json
import subprocess
from dataclasses import replace
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
from scipy.ndimage import distance_transform_edt

from gemsdoe50.catalog import read_nevada_catalog
from gemsdoe50.common import jsonable, md5_file, sha256_array, sha256_file
from gemsdoe50.evaluation import (
    PREDICTION_MASS,
    TIME_SHUFFLE_CONTROLS,
    _top_n_prediction,
    evaluate_hypothesis,
    read_baseline_raster,
    spatial_jaccard,
)
from gemsdoe50.geometry import LineamentConfig, extract_h50s1_lineaments
from gemsdoe50.holdout import build_spatial_blocks, load_split_spec
from gemsdoe50.raster import load_labels, load_template, write_submission

CATALOG_EXPECTED_MD5 = "38fa663f473378b61c74b597c53c416b"
CATALOG_EXPECTED_BYTES = 13_833_354
BASELINE_PINS = {
    "H32-D": {
        "file": "h32d.tif",
        "sha256": "f81e26d7712d1a4a9d3d5393037b09849400c3976d1ebd40e2760a586f2adc2f",
        "repo": "buffedlizard55-lab/GEMSDOE32",
        "commit": "51ccc787e1059dc2e440cd94863c7d2670b3b88d",
    },
    "H47-S3": {
        "file": "h47s3.tif",
        "sha256": "f3f840b7880b7540ac6260b6b791ea55b2a875646c28401b01960096dc2da291",
        "repo": "buffedlizard55-lab/GEMSDOE47",
        "commit": "97c8acdf3b0aaf151cdab606da0ac15f1a8132b8",
    },
    "H48-DS": {
        "file": "h48ds.tif",
        "sha256": "fe68ae6f57be013e26d20006551b43cd84bb5fe4a0b07d1d10ce4725c90fd16c",
        "repo": "buffedlizard55-lab/GEMSDOE48",
        "commit": "d064aeeec467ce5de6cf0ecd86872af6561e509f",
    },
    "H50-prior": {
        "file": "h50prev.tif",
        "sha256": "79e260ae223d7dfd96413da28a9c6fed30107285ab843795181a5c9e5dff7262",
        "repo": "buffedlizard55-lab/GEMSDOE50",
        "commit": "80d6186dee89ba0eacedd29dc0a7455c5fad4e47",
    },
}


def write_json(path: str | Path, payload: dict[str, Any]) -> None:
    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(jsonable(payload), indent=2, sort_keys=True, allow_nan=False) + "\n",
        encoding="utf-8",
    )


def _git_commit() -> str | None:
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "HEAD"], text=True, stderr=subprocess.DEVNULL
        ).strip()
    except (OSError, subprocess.CalledProcessError):
        return None


def _verify_frozen_realization(
    path: str | Path,
    realized: dict[str, Any],
    *,
    split_sha256: str,
    template_sha256: str,
    labels_sha256: str,
) -> str:
    realization_path = Path(path)
    if not realization_path.is_file():
        raise FileNotFoundError(
            f"frozen mask report is missing: {realization_path}; freeze and commit it before DTI"
        )
    frozen = json.loads(realization_path.read_text(encoding="utf-8"))
    if frozen.get("dti_computed") is not False:
        raise ValueError(
            "the committed frozen mask report must explicitly state dti_computed=false"
        )
    checks = {
        "split_spec_sha256": split_sha256,
        "template_raster_sha256": template_sha256,
        "label_raster_sha256": labels_sha256,
        "valid_mask_sha256": realized["valid_mask_sha256"],
        "truth_raster_mask_sha256": realized["truth_raster_mask_sha256"],
        "macrofolds": realized["macrofolds"],
    }
    for key, expected in checks.items():
        if frozen.get(key) != expected:
            raise ValueError(f"frozen holdout realization mismatch at {key}")
    return sha256_file(realization_path)


def _write_outputs(
    *,
    catalog_path: Path,
    template_path: Path,
    labels_path: Path,
    split_path: Path,
    realization_path: Path,
    prior_dir: Path,
    output_tiff: Path,
    report_path: Path,
    shuffle_count: int,
) -> dict[str, Any]:
    spec = load_split_spec(split_path)
    template_sha = sha256_file(template_path)
    labels_sha = sha256_file(labels_path)
    if template_sha != spec["grid"]["template_sha256"]:
        raise ValueError(f"submission template SHA-256 mismatch: {template_sha}")
    if labels_sha != spec["grid"]["official_label_raster_sha256"]:
        raise ValueError(f"label raster SHA-256 mismatch: {labels_sha}")
    if catalog_path.stat().st_size != CATALOG_EXPECTED_BYTES:
        raise ValueError(f"catalog byte count mismatch: {catalog_path.stat().st_size}")
    catalog_md5 = md5_file(catalog_path)
    if catalog_md5 != CATALOG_EXPECTED_MD5:
        raise ValueError(f"catalog MD5 mismatch: {catalog_md5}")
    catalog_sha = sha256_file(catalog_path)
    split_sha = sha256_file(split_path)

    _, valid_mask, _ = load_template(template_path)
    truth_mask, label_metadata = load_labels(labels_path, template_path, valid_mask)
    blocks, realized = build_spatial_blocks(valid_mask, truth_mask, spec)
    realized_sha = _verify_frozen_realization(
        realization_path,
        realized,
        split_sha256=split_sha,
        template_sha256=template_sha,
        labels_sha256=labels_sha,
    )

    # No DTI has been evaluated before this point: both the split geometry and
    # realized mask hashes are frozen in committed JSON files and reverified.
    events = read_nevada_catalog(
        catalog_path,
        template_path,
    )
    catalog_metadata = dict(events.metadata)
    catalog_metadata.update(
        {
            "catalog_md5": catalog_md5,
            "catalog_sha256": catalog_sha,
            "catalog_bytes": catalog_path.stat().st_size,
            "zenodo_doi": "10.5281/zenodo.11167510",
            "license": "CC BY 4.0",
            "attribution": "Trugman, D. T. (2024), Relocated Earthquake Catalog for Nevada (2008–2023), Zenodo v2.",
        }
    )

    config = LineamentConfig()
    candidate_result = extract_h50s1_lineaments(events, str(template_path), config)
    candidate_scores = candidate_result.score

    time_shuffle_maps: dict[str, np.ndarray] = {}
    time_shuffle_metadata: dict[str, Any] = {}
    rng = np.random.default_rng(505011)
    relocated_indices = np.flatnonzero(events.relocated == 1)
    if shuffle_count != TIME_SHUFFLE_CONTROLS:
        raise ValueError(
            f"the preregistered protocol requires exactly {TIME_SHUFFLE_CONTROLS} "
            "time-shuffle controls"
        )
    for replicate in range(shuffle_count):
        shuffled_year = events.year.copy()
        shuffled_year[relocated_indices] = rng.permutation(shuffled_year[relocated_indices])
        shuffled_events = replace(events, year=shuffled_year)
        # Reuse the candidate's bootstrap seed so time-label assignment is the
        # only stochastic control change for a given spatial seed cell.
        shuffled_result = extract_h50s1_lineaments(
            shuffled_events,
            str(template_path),
            config,
        )
        name = f"time-shuffle-{replicate + 1:02d}"
        time_shuffle_maps[name] = shuffled_result.score
        time_shuffle_metadata[name] = {
            "score_map_sha256": sha256_array(shuffled_result.score),
            "positive_score_cells": shuffled_result.metadata["positive_score_cells"],
            "counts": shuffled_result.metadata["counts"],
        }
        print(
            f"{name}: segments={shuffled_result.metadata['counts']['accepted_segments']}, "
            f"positive_cells={shuffled_result.metadata['positive_score_cells']}",
            flush=True,
        )
        del shuffled_result, shuffled_events, shuffled_year

    baseline_maps: dict[str, np.ndarray] = {}
    baseline_metadata: dict[str, Any] = {}
    input_hashes = {
        "catalog": catalog_sha,
        "template": template_sha,
        "labels": labels_sha,
        "holdout_spec": split_sha,
        "holdout_realized": realized_sha,
    }
    for name, pin in BASELINE_PINS.items():
        path = prior_dir / pin["file"]
        actual_sha = sha256_file(path)
        if actual_sha != pin["sha256"]:
            raise ValueError(f"{name} baseline SHA-256 mismatch: {actual_sha}")
        raster, metadata = read_baseline_raster(path, template_path)
        baseline_maps[name] = raster
        metadata.update({"source_repo": pin["repo"], "source_commit": pin["commit"]})
        baseline_metadata[name] = metadata
        input_hashes[name] = actual_sha

    evaluation = evaluate_hypothesis(
        candidate_scores,
        baseline_maps,
        blocks,
        split_sha256=split_sha,
        input_hashes=input_hashes,
        time_shuffle_maps=time_shuffle_maps,
    )
    evaluation["time_shuffle_run_metadata"] = time_shuffle_metadata

    # Final raster predicts candidate traces only, excludes the complete known
    # catalogue buffered by 300 m, and uses a fixed, binary 37,612-pixel budget.
    distance_to_known_m = distance_transform_edt(
        ~truth_mask, sampling=(spec["grid"]["pixel_size_m"], spec["grid"]["pixel_size_m"])
    )
    known_buffer = distance_to_known_m <= spec["rules"]["visible_training_label_buffer_m"]
    final_eligible = valid_mask & ~known_buffer
    final_predictions = _top_n_prediction(
        candidate_scores,
        final_eligible,
        PREDICTION_MASS,
        seed=5001,
    )
    raster_validation = write_submission(
        template_path,
        output_tiff,
        final_predictions,
        valid_mask,
    )
    if np.any((final_predictions > 0) & known_buffer):
        raise ValueError("final prediction overlaps the known-fault 300 m exclusion buffer")

    prior_jaccard = {
        name: spatial_jaccard(final_predictions, baseline_maps[name], valid_mask)
        for name in baseline_maps
    }
    final_positive = int(np.count_nonzero(final_predictions > 0))

    report = {
        "project": "GEMSDOE50",
        "hypothesis": "H50-S1 — relocated Nevada hypocenter planes projected to z=0 lineaments",
        "status": "RESEARCH_ONLY_NOT_SUBMITTED"
        if final_positive
        else "NO_CANDIDATE_PIXELS_NOT_SUBMITTED",
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "git_commit": _git_commit(),
        "registered_split": {
            "spec_path": str(split_path),
            "spec_sha256": split_sha,
            "realized_path": str(realization_path),
            "realized_sha256": realized_sha,
            "valid_mask_sha256": realized["valid_mask_sha256"],
            "fold_mask_hashes": [
                {
                    "id": fold["id"],
                    "eligible_mask_sha256": fold["eligible_mask_sha256"],
                    "truth_mask_sha256": fold["truth_mask_sha256"],
                }
                for fold in realized["macrofolds"]
            ],
        },
        "data": {
            "catalog": catalog_metadata,
            "competition_training_rasters": {
                "template_sha256": template_sha,
                "labels_sha256": labels_sha,
                "label_metadata": label_metadata,
                "provenance_caveat": (
                    "Competition rasters were downloaded from public Dropbox mirrors using hashes "
                    "recorded in a source bridge manifest. Hash agreement confirms the pinned bytes, "
                    "but this session did not authenticate to DrivenData or independently redownload "
                    "the official originals."
                ),
            },
            "prior_artifacts": baseline_metadata,
        },
        "candidate_extraction": candidate_result.metadata,
        "evaluation": evaluation,
        "submission_artifact": {
            **raster_validation,
            "unique_name": output_tiff.name,
            "optional_note": (
                "Relocated Nevada event-plane lineaments; 300 m known-fault exclusion; "
                "research proxy, not organizer-scored."
            ),
            "known_fault_buffer_m": spec["rules"]["visible_training_label_buffer_m"],
            "prediction_mass_budget": PREDICTION_MASS,
            "positive_cells": final_positive,
            "nonempty_candidate": bool(final_positive > 0),
            "positive_mask_jaccard_vs_prior": prior_jaccard,
            "exact_prediction_mask_match_vs_prior": {
                name: bool(prior_jaccard[name] == 1.0) for name in prior_jaccard
            },
        },
        "external_data_license": {
            "catalog": "CC BY 4.0",
            "catalog_doi": "10.5281/zenodo.11167510",
            "commercial_use_permitted_by_license": True,
            "shareable_with_organizers": True,
            "attribution": "Trugman (2024), Relocated Earthquake Catalog for Nevada (2008–2023), Zenodo v2, https://doi.org/10.5281/zenodo.11167510, CC BY 4.0.",
            "competition_rule_source": "https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/",
            "limitation": "The catalog does not provide event-specific location covariance; do not treat coordinate decimal precision as accuracy.",
        },
        "decision": evaluation["promotion_gate"],
        "submission_status": "No DrivenData upload or weekly slot was used.",
    }
    write_json(report_path, report)
    print(f"Report: {report_path}")
    print(f"Report SHA-256: {sha256_file(report_path)}")
    print(f"GeoTIFF: {output_tiff}")
    print(f"GeoTIFF SHA-256: {raster_validation['sha256']}")
    print(f"Pooled DTI: {evaluation['method_results']['H50-S1']['pooled']['score']:.6f}")
    print(f"Incumbent: {evaluation['incumbent_method']}")
    print(f"Gate: {evaluation['promotion_gate']['decision']}")
    return report


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--catalog", required=True)
    parser.add_argument("--template", required=True)
    parser.add_argument("--labels", required=True)
    parser.add_argument("--split", default="evidence/holdout-v1.json")
    parser.add_argument("--realized", default="evidence/holdout-realized-v1.json")
    parser.add_argument("--prior-dir", default=".arena/run/prior")
    parser.add_argument(
        "--output-tiff",
        default="docs/downloads/gemsdoe50-h50s1-relocated-planes-20261006-research.tif",
    )
    parser.add_argument(
        "--report",
        default="evidence/results/h50s1-evaluation-20261006.json",
    )
    parser.add_argument("--time-shuffles", type=int, default=TIME_SHUFFLE_CONTROLS)
    args = parser.parse_args()
    _write_outputs(
        catalog_path=Path(args.catalog),
        template_path=Path(args.template),
        labels_path=Path(args.labels),
        split_path=Path(args.split),
        realization_path=Path(args.realized),
        prior_dir=Path(args.prior_dir),
        output_tiff=Path(args.output_tiff),
        report_path=Path(args.report),
        shuffle_count=args.time_shuffles,
    )


if __name__ == "__main__":
    main()
