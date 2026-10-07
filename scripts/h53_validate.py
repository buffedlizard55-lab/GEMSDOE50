#!/usr/bin/env python3
"""Evaluate H53-A against the hash-frozen spatial incumbent and registered controls.

The candidate is scored only after `h53_baseline_audit.py` has frozen the comparator. This is a
local SGMC-off proxy evaluation, never a hidden-label or leaderboard score. A failed candidate is
still reported; no slot is used or authorized by this script.
"""
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import rasterio
from scipy.ndimage import binary_dilation, distance_transform_edt

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "src"))

from gems51 import emit
from gems51 import grid as g
from gemsdoe50.common import sha256_array, sha256_file
from gemsdoe50.h53 import (
    build_probe_density,
    build_probe_lineation,
    build_tmi_lineaments,
    deduplicate_area_cells,
    read_probe_points,
    warm_probe_marks,
)
from gemsdoe50.holdout import build_spatial_blocks, load_split_spec
from gemsdoe50.metric import distance_weighted_tversky

BASELINE_PATH = REPO / "evidence/h53-baseline-20261007.json"
BUILD_PATH = REPO / "evidence/h53-build-20261007.json"
SGMC_PATH = REPO / "data/external/derived_sgmc_faults_100m_u8.tif"
PROBE_ZIP = REPO / ".arena/public-inputs/2m_temperature_probe_INGENIOUS_regional_data.zip"
GEODAWN_TMI = REPO / ".arena/public-inputs/geodawn_extensions_u8.tif"
SPEC_PATH = REPO / "evidence/holdout-v1.json"
EXPECTED_BASELINE_SHA = "acd05c2a55d4d5a64a297075907bd53b5c0d52a78f655ddf3d34bc1d4d85f7bb"
EXPECTED_PROBE_SHA = "1301f70d230058e616ea5d34d1c7a32fabf7d49198172f376c59c89bd652eca3"
EXPECTED_TMI_SHA = "a35a9c6d2a14786f4dab85481ee59769213072f5dab5b2535ea82ae4d9bb7d9b"


def _score_block(truth: np.ndarray, prediction: np.ndarray, evaluation: np.ndarray) -> dict:
    yy, xx = np.ogrid[-3:4, -3:4]
    structure = (yy * yy + xx * xx) <= 9
    halo = binary_dilation(evaluation, structure=structure)
    result = distance_weighted_tversky(
        truth & halo,
        (prediction & halo).astype(np.float32),
        truth_eval_mask=evaluation,
        prediction_eval_mask=evaluation,
        pixel_size_m=100.0,
        radius_m=300.0,
        alpha=0.2,
        beta=0.8,
    )
    return result.as_dict()


def _read_support(path: Path, template: rasterio.DatasetReader, *, submission_valid: np.ndarray | None = None) -> tuple[np.ndarray, dict]:
    with rasterio.open(path) as ds:
        if (ds.width, ds.height) != (template.width, template.height):
            raise ValueError("prediction shape differs from official template")
        if ds.crs != template.crs or not ds.transform.almost_equals(template.transform):
            raise ValueError("prediction CRS/transform differs from official template")
        values = ds.read(1)
        finite = np.isfinite(values)
        if submission_valid is not None:
            submission_valid = np.asarray(submission_valid, dtype=bool)
            if submission_valid.shape != values.shape:
                raise ValueError("submission valid-mask shape mismatch")
            if not finite[submission_valid].all():
                raise ValueError("submission has non-finite values inside the valid study footprint")
            if finite[~submission_valid].any():
                raise ValueError("official format requires null/NaN outside the study bounds")
            checked = values[submission_valid]
        else:
            checked = values[finite]
        if np.any((checked < 0.0) | (checked > 1.0)):
            raise ValueError("prediction TIFF contains in-footprint values outside [0,1]")
        return finite & (values > 0.0), {
            "path": str(path.relative_to(REPO)),
            "sha256": sha256_file(path),
            "dtype": ds.dtypes[0],
            "nodata": ds.nodata,
            "min_finite": float(values[finite].min()) if finite.any() else None,
            "max_finite": float(values[finite].max()) if finite.any() else None,
            "all_finite": bool(finite.all()),
            "finite_pixels": int(finite.sum()),
            "positive_cells": int(np.count_nonzero(finite & (values > 0.0))),
            "unique_finite_values": np.unique(values[finite]).tolist(),
            "finite_outside_valid_footprint": (int(np.count_nonzero(finite & ~submission_valid))
                                                if submission_valid is not None else None),
            "in_valid_min": (float(values[submission_valid].min()) if submission_valid is not None else None),
            "in_valid_max": (float(values[submission_valid].max()) if submission_valid is not None else None),
            "all_finite_in_valid_footprint": (bool(finite[submission_valid].all())
                                               if submission_valid is not None else None),
        }


def _pack_local(
    belief: np.ndarray,
    mass: int,
    *,
    allowed: np.ndarray,
    core_bounds: tuple[int, int, int, int],
    seed: int,
) -> tuple[np.ndarray, dict]:
    """Pack in a cropped 3-pixel context window; exactly preserves the full-grid metric kernel."""
    r0, r1, c0, c1 = core_bounds
    pad = 3
    sr0, sr1 = max(0, r0 - pad), min(belief.shape[0], r1 + pad)
    sc0, sc1 = max(0, c0 - pad), min(belief.shape[1], c1 + pad)
    local_belief = belief[sr0:sr1, sc0:sc1]
    local_allowed = allowed[sr0:sr1, sc0:sc1].copy()
    local_core = np.zeros(local_allowed.shape, dtype=bool)
    local_core[r0 - sr0:r1 - sr0, c0 - sc0:c1 - sc0] = True
    local_allowed &= local_core
    packed, info = emit.pack(
        local_belief,
        mass,
        valid=local_allowed,
        suppression_px=3.0,
        seed=seed,
    )
    full = np.zeros(belief.shape, dtype=bool)
    full[sr0:sr1, sc0:sc1] = packed
    return full, info


def _clean(value):
    if isinstance(value, dict):
        return {str(key): _clean(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_clean(item) for item in value]
    if isinstance(value, np.ndarray):
        return _clean(value.tolist())
    if isinstance(value, np.generic):
        return _clean(value.item())
    if isinstance(value, float) and not np.isfinite(value):
        return None
    return value


def main() -> int:
    if not BASELINE_PATH.is_file() or not BUILD_PATH.is_file():
        raise FileNotFoundError("run h53_baseline_audit.py and h53_build.py first")
    baseline_sha = sha256_file(BASELINE_PATH)
    if baseline_sha != EXPECTED_BASELINE_SHA:
        raise ValueError(f"frozen baseline report hash mismatch: {baseline_sha}")
    baseline = json.loads(BASELINE_PATH.read_text(encoding="utf-8"))
    build = json.loads(BUILD_PATH.read_text(encoding="utf-8"))
    if baseline.get("status") != "BASELINE_FROZEN_AWAITING_H53":
        raise ValueError("baseline is not in the registered frozen state")
    if build.get("schema") != "gemsdoe50.h53-build.v1":
        raise ValueError("H53 build evidence schema mismatch")

    for path, expected, label in [
        (PROBE_ZIP, EXPECTED_PROBE_SHA, "GDR probe archive"),
        (GEODAWN_TMI, EXPECTED_TMI_SHA, "GeoDAWN TMI extension"),
    ]:
        actual = sha256_file(path)
        if actual != expected:
            raise ValueError(f"{label} hash mismatch: {actual}")

    artifact_path = REPO / "docs/downloads" / build["candidate"]["filename"]
    with rasterio.open(REPO / "data/grid/sample_submission.tif") as template:
        valid = np.isfinite(template.read(1))
        transform = template.transform
        shape = valid.shape
        support, raster_info = _read_support(artifact_path, template, submission_valid=valid)
        labels, _ = g.load_raster(REPO / "data/grid/labels.tif")
        labels = labels == 1
        spec = load_split_spec(SPEC_PATH)
        blocks, realized = build_spatial_blocks(valid, labels, spec)
        sgmc, _ = g.load_raster(SGMC_PATH)

        cores: dict[str, np.ndarray] = {}
        core_bounds: dict[str, tuple[int, int, int, int]] = {}
        subtile_bounds: list[tuple[str, tuple[int, int, int, int]]] = []
        for block in blocks:
            r0, r1, c0, c1 = map(int, block.metadata["core_bounds"])
            core = np.zeros(shape, dtype=bool)
            core[r0:r1, c0:c1] = True
            core &= valid
            fold_id = str(block.metadata["id"])
            cores[fold_id] = core
            core_bounds[fold_id] = (r0, r1, c0, c1)
            for tile_id, rows, cols, _eligible, _truth in block.subtile_masks:
                tr0, tr1 = rows
                tc0, tc1 = cols
                subtile_bounds.append((tile_id, (int(tr0), int(tr1), int(tc0), int(tc1))))
        pooled_core = np.logical_or.reduce(list(cores.values()))

    # Rebuild the feature score surface without labels/SGMC; it must reproduce the frozen build hash.
    raw_points, source_audit = read_probe_points(
        PROBE_ZIP, transform=transform, valid=valid, target_crs="EPSG:32611"
    )
    points, dedup_audit = deduplicate_area_cells(raw_points)
    warm, ranks, mark_audit = warm_probe_marks(points, minimum_area_points=12, within_area_quantile=0.75)
    with rasterio.open(GEODAWN_TMI) as ds:
        tmi = ds.read(4)
    lineaments = build_tmi_lineaments(
        tmi, valid, scales=(2.0, 5.0, 10.0), coherence_sigma=3.0,
        ridge_quantile=0.95, coherence_min=0.25,
    )
    lineation, lineation_audit = build_probe_lineation(
        points, ranks, warm, lineaments, transform=transform, valid=valid,
        pixel_size_m=100.0, cluster_radius_m=1500.0, minimum_cluster_points=5,
        minimum_axis_ratio=3.0, minimum_length_m=800.0, maximum_length_m=20_000.0,
        max_tmi_distance_px=5.0, max_angle_deg=30.0,
        minimum_tmi_alignment=0.50, corridor_sigma_px=1.5,
    )
    rebuilt_field_sha = sha256_array(lineation)
    if rebuilt_field_sha != build["candidate"]["field_sha256"]:
        raise ValueError("recomputed H53-A score surface differs from the frozen build receipt")

    incumbent_name = baseline["incumbent"]["name"]
    incumbent_record = baseline["registered_baselines"][incumbent_name]
    incumbent_path = REPO / incumbent_record["raster"]["path"]
    if sha256_file(incumbent_path) != baseline["incumbent"]["sha256"]:
        raise ValueError("incumbent artifact hash differs from the baseline-only audit")
    with rasterio.open(REPO / "data/grid/sample_submission.tif") as template:
        incumbent_support, incumbent_raster_info = _read_support(incumbent_path, template)

    catalogue_distance = distance_transform_edt(~labels, sampling=(100.0, 100.0))
    off_catalogue = (catalogue_distance > 300.0) & valid
    del catalogue_distance
    truth = (sgmc > 0) & off_catalogue

    # Verify the comparator has not drifted since the independent baseline-only scoring pass.
    incumbent_folds = {
        fold_id: _score_block(truth, incumbent_support, mask)
        for fold_id, mask in cores.items()
    }
    incumbent_pooled = _score_block(truth, incumbent_support, pooled_core)
    for fold_id, current in incumbent_folds.items():
        frozen = incumbent_record["folds"][fold_id]["score"]
        if abs(current["score"] - frozen) > 1e-12:
            raise ValueError(f"incumbent fold score drift for {fold_id}: {current['score']} != {frozen}")
    if abs(incumbent_pooled["score"] - baseline["incumbent"]["pooled_dti"]) > 1e-12:
        raise ValueError("incumbent pooled score differs from the candidate-independent audit")

    candidate_native_folds = {
        fold_id: _score_block(truth, support, mask)
        for fold_id, mask in cores.items()
    }
    candidate_native_pooled = _score_block(truth, support, pooled_core)
    matched_mass = {fold_id: int(incumbent_support[mask].sum()) for fold_id, mask in cores.items()}
    candidate_native_mass_by_fold = {fold_id: int(support[mask].sum()) for fold_id, mask in cores.items()}
    candidate_matched_support = np.zeros(shape, dtype=bool)
    candidate_matched_pack = {}
    for fold_index, (fold_id, core) in enumerate(cores.items()):
        r0, r1, c0, c1 = core_bounds[fold_id]
        local, pack_info = _pack_local(
            lineation, matched_mass[fold_id], allowed=off_catalogue & core,
            core_bounds=(r0, r1, c0, c1), seed=5301 + fold_index,
        )
        candidate_matched_support |= local
        candidate_matched_pack[fold_id] = {
            "requested_mass": matched_mass[fold_id],
            "emitted_mass": int(local.sum()),
            "mass_match": int(local.sum()) == matched_mass[fold_id],
            "pack": pack_info,
        }
    candidate_matched_mass_by_fold = {
        fold_id: int(candidate_matched_support[mask].sum()) for fold_id, mask in cores.items()
    }
    candidate_matched_folds = {
        fold_id: _score_block(truth, candidate_matched_support, mask)
        for fold_id, mask in cores.items()
    }
    candidate_matched_pooled = _score_block(truth, candidate_matched_support, pooled_core)

    # Build the pre-registered smoothed-density and TMI-only controls from the same input files.
    density_500 = build_probe_density(points, warm, ranks, valid, sigma_px=5.0)
    density_1000 = build_probe_density(points, warm, ranks, valid, sigma_px=10.0)
    tmi_only = np.where(lineaments.ridge_mask, lineaments.strength, 0.0).astype(np.float32)
    tmi_only[~valid] = 0.0
    controls = {
        "probe_density_500m": density_500,
        "probe_density_1km": density_1000,
        "tmi_only": tmi_only,
    }
    control_reports: dict[str, dict] = {}
    for control_name, field in controls.items():
        packed = np.zeros(shape, dtype=bool)
        fold_rows = {}
        for fold_index, (fold_id, core) in enumerate(cores.items()):
            r0, r1, c0, c1 = core_bounds[fold_id]
            amount = matched_mass[fold_id]
            local, pack_info = _pack_local(
                field, amount, allowed=off_catalogue & core,
                core_bounds=(r0, r1, c0, c1), seed=5301 + fold_index,
            )
            packed |= local
            fold_rows[fold_id] = {
                "requested_mass": amount,
                "emitted_mass": int(local.sum()),
                "mass_match": int(local.sum()) == amount,
                "dti": _score_block(truth, local, core),
                "pack": pack_info,
            }
        pooled = _score_block(truth, packed, pooled_core)
        control_reports[control_name] = {
            "folds": fold_rows,
            "pooled_equal_incumbent_native_mass": pooled,
            "total_emitted_cells": int(packed.sum()),
            "all_fold_masses_match": all(row["mass_match"] for row in fold_rows.values()),
            "beats_incumbent_pooled": pooled["score"] > incumbent_pooled["score"],
        }

    random_controls = []
    for draw, seed in enumerate((5301, 5302, 5303, 5304, 5305), start=1):
        rng = np.random.default_rng(seed)
        field = rng.random(shape, dtype=np.float32)
        packed = np.zeros(shape, dtype=bool)
        fold_rows = {}
        for fold_index, (fold_id, core) in enumerate(cores.items()):
            r0, r1, c0, c1 = core_bounds[fold_id]
            amount = matched_mass[fold_id]
            local, pack_info = _pack_local(
                field, amount, allowed=off_catalogue & core,
                core_bounds=(r0, r1, c0, c1), seed=seed + fold_index,
            )
            packed |= local
            fold_rows[fold_id] = {
                "requested_mass": amount,
                "emitted_mass": int(local.sum()),
                "mass_match": int(local.sum()) == amount,
                "dti": _score_block(truth, local, core),
                "pack": pack_info,
            }
        pooled = _score_block(truth, packed, pooled_core)
        random_controls.append({
            "draw": draw,
            "seed": seed,
            "folds": fold_rows,
            "pooled_equal_incumbent_native_mass": pooled,
            "total_emitted_cells": int(packed.sum()),
            "all_fold_masses_match": all(row["mass_match"] for row in fold_rows.values()),
        })

    # All 16 registered subtiles are reported; informative units are those with proxy truth and
    # incumbent mass. The bootstrap samples these spatial units, never individual pixels.
    tile_rows = []
    for tile_id, bounds in subtile_bounds:
        tr0, tr1, tc0, tc1 = bounds
        mask = np.zeros(shape, dtype=bool)
        mask[tr0:tr1, tc0:tc1] = True
        mask &= pooled_core
        candidate = _score_block(truth, candidate_matched_support, mask)
        incumbent = _score_block(truth, incumbent_support, mask)
        row = {
            "id": tile_id,
            "truth_cells": int((truth & mask).sum()),
            "candidate_mass": int((candidate_matched_support & mask).sum()),
            "incumbent_mass": int((incumbent_support & mask).sum()),
            "candidate_dti": candidate["score"],
            "incumbent_dti": incumbent["score"],
            "paired_delta": candidate["score"] - incumbent["score"],
        }
        row["informative"] = row["truth_cells"] > 0 and row["incumbent_mass"] > 0
        tile_rows.append(row)
    informative_deltas = np.asarray([row["paired_delta"] for row in tile_rows if row["informative"]], dtype=float)
    rng = np.random.default_rng(5307)
    if informative_deltas.size:
        draws = rng.integers(0, informative_deltas.size, size=(5000, informative_deltas.size))
        bootstrap_means = informative_deltas[draws].mean(axis=1)
        bootstrap_ci = [float(np.quantile(bootstrap_means, 0.025)),
                        float(np.quantile(bootstrap_means, 0.975))]
    else:
        bootstrap_ci = [0.0, 0.0]

    prior_hashes = {name: item["sha256"] for name, item in baseline["registered_baselines"].items()}
    hash_unique = raster_info["sha256"] not in set(prior_hashes.values())
    overlaps = {}
    with rasterio.open(REPO / "data/grid/sample_submission.tif") as template:
        for name, record in baseline["registered_baselines"].items():
            prior_support, _ = _read_support(REPO / record["raster"]["path"], template)
            overlaps[name] = int((support & prior_support).sum())
    provenance_clear = False  # official source binaries could not be byte-matched from this run
    candidate_mass_gate = bool(
        int(support.sum()) == int(build["candidate"]["requested_native_budget"])
        and candidate_matched_mass_by_fold == matched_mass
        and all(row["mass_match"] for row in candidate_matched_pack.values())
    )
    fold_deltas = {
        fold_id: candidate_matched_folds[fold_id]["score"] - incumbent_folds[fold_id]["score"]
        for fold_id in cores
    }
    max_uniform = max(
        row["pooled_equal_incumbent_native_mass"]["score"] for row in random_controls
    )
    controls_beaten = all(
        result["all_fold_masses_match"] and
        candidate_matched_pooled["score"] > result["pooled_equal_incumbent_native_mass"]["score"]
        for result in control_reports.values()
    ) and max_uniform < candidate_matched_pooled["score"]
    candidate_promotes = bool(
        provenance_clear
        and candidate_mass_gate
        and candidate_matched_pooled["score"] >= incumbent_pooled["score"] + 0.005
        and candidate_native_pooled["score"] > incumbent_pooled["score"]
        and all(delta > 0 for delta in fold_deltas.values())
        and bootstrap_ci[0] > 0.0
        and controls_beaten
        and hash_unique
    )

    report = {
        "schema": "gemsdoe50.h53-validation.v1",
        "built_utc": datetime.now(timezone.utc).isoformat(),
        "status": "NO_SLOT" if not candidate_promotes else "PROMOTION_GATE_PASSED_REQUIRES_HUMAN_RULE_CHECK",
        "decision": {
            "candidate_promotes": candidate_promotes,
            "slot_decision": "NO SLOT; do not submit or spend a weekly scoring slot",
            "why": [
                "the frozen detector accepted zero probe/TMI lineations and emitted zero pixels",
                "the candidate does not meet the preregistered incumbent-matched mass",
                "the no-go raster does not beat the frozen incumbent or controls",
                "official-source mirror bytes are not byte-matched to the official downloads",
            ],
            "candidate_mass_gate_passed": candidate_mass_gate,
            "all_data_permissions_and_provenance_verified": provenance_clear,
            "controls_beaten": controls_beaten,
        },
        "candidate": {
            "name": build["candidate"]["name"],
            "artifact": raster_info,
            "field_sha256_recomputed": rebuilt_field_sha,
            "lineation_audit_recomputed": lineation_audit,
            "native_mass_by_fold": candidate_native_mass_by_fold,
            "native_pooled_dti": candidate_native_pooled,
            "native_folds": candidate_native_folds,
            "equal_mass_pooled_dti": candidate_matched_pooled,
            "equal_mass_folds": candidate_matched_folds,
            "equal_mass_pack_by_fold": candidate_matched_pack,
            "equal_mass_gate": {"requested_full_grid": build["candidate"]["requested_native_budget"],
                                "emitted_full_grid": int(support.sum()),
                                "requested_by_fold": matched_mass,
                                "emitted_by_fold": candidate_matched_mass_by_fold,
                                "passed": candidate_mass_gate},
            "artifact_sha_unique_against_registered_baselines": hash_unique,
            "overlap_pixels_with_registered_baselines": overlaps,
        },
        "frozen_incumbent": {
            "name": incumbent_name,
            "sha256": baseline["incumbent"]["sha256"],
            "artifact": incumbent_raster_info,
            "native_positive_cells": int(incumbent_support.sum()),
            "native_pooled_dti": incumbent_pooled,
            "folds": incumbent_folds,
            "matched_mass_by_fold": matched_mass,
            "fold_dti_deltas_candidate_minus_incumbent": fold_deltas,
            "beats_incumbent": candidate_native_pooled["score"] > incumbent_pooled["score"],
        },
        "registered_controls": control_reports,
        "matched_uniform_controls": random_controls,
        "uniform_control_max_pooled_dti": max_uniform,
        "subtile_bootstrap": {
            "registered_units": len(tile_rows),
            "informative_units": int(informative_deltas.size),
            "draws": 5000,
            "seed": 5307,
            "paired_delta_mean": float(informative_deltas.mean()) if informative_deltas.size else 0.0,
            "percentile_ci_95": bootstrap_ci,
            "lower_bound_above_zero": bool(bootstrap_ci[0] > 0.0),
            "tiles": tile_rows,
        },
        "inputs_and_holdout": {
            "baseline_report_sha256": baseline_sha,
            "build_report_sha256": sha256_file(BUILD_PATH),
            "split_spec_sha256": sha256_file(SPEC_PATH),
            "realized_valid_mask_sha256": realized["valid_mask_sha256"],
            "sgmc_proxy_sha256": sha256_file(SGMC_PATH),
            "probe_archive_sha256": sha256_file(PROBE_ZIP),
            "geodawn_extension_sha256": sha256_file(GEODAWN_TMI),
            "probe_source_audit": source_audit,
            "probe_dedup_audit": dedup_audit,
            "warm_mark_audit": mark_audit,
            "proxy_truth": "SGMC positive cells >300 m from provided catalogue; not hidden expert labels",
            "official_binary_provenance_clear": False,
        },
        "human_review_notes": [
            "The `H50 prior seismicity` file is used only as a frozen comparator, not claimed as a novel validated strategy; H51-B seismicity controls/confounds remain unresolved.",
            "No hidden test labels, live leaderboard page, or organizer score was accessed.",
            "A local proxy result cannot establish that the user-provided 0.2778 or 0.3774 scores are correct or identify their TIFFs.",
        ],
    }
    out = REPO / "evidence/h53-validation-20261007.json"
    out.write_text(json.dumps(_clean(report), indent=2, allow_nan=False) + "\n", encoding="utf-8")
    print(json.dumps({
        "decision": report["decision"]["slot_decision"],
        "candidate_positive_cells": int(support.sum()),
        "candidate_dti": candidate_native_pooled["score"],
        "incumbent": incumbent_name,
        "incumbent_dti": incumbent_pooled["score"],
        "incumbent_fold_dti": {k: round(v["score"], 6) for k, v in incumbent_folds.items()},
        "candidate_matched_fold_dti": {k: round(v["score"], 6) for k, v in candidate_matched_folds.items()},
        "controls": {k: round(v["pooled_equal_incumbent_native_mass"]["score"], 6)
                     for k, v in control_reports.items()},
        "max_uniform_control_dti": round(max_uniform, 6),
        "subtile_ci95": bootstrap_ci,
        "output": str(out),
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
