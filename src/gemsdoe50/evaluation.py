from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np
import rasterio

from .common import sha256_array, sha256_file
from .holdout import SpatialBlock
from .metric import DTIComponents, distance_weighted_tversky
from .raster import check_same_grid

PREDICTION_MASS = 37612
BOOTSTRAP_REPLICATES = 5000
TRANSLATION_CONTROLS = 32


def allocate_largest_remainder(total: int, weights: list[int]) -> list[int]:
    if total < 0 or any(weight < 0 for weight in weights):
        raise ValueError("total and allocation weights must be non-negative")
    weight_sum = sum(weights)
    if not weights or weight_sum == 0:
        return [0 for _ in weights]
    exact = np.asarray(weights, dtype=np.float64) * (total / weight_sum)
    result = np.floor(exact).astype(np.int64)
    remainder = int(total - result.sum())
    if remainder:
        fractions = exact - result
        order = np.argsort(-fractions, kind="stable")
        result[order[:remainder]] += 1
    return [int(value) for value in result]


def _top_n_prediction(
    score: np.ndarray,
    eligible: np.ndarray,
    mass: int,
    *,
    seed: int,
) -> np.ndarray:
    """Select up to ``mass`` positive-score pixels; ties are seeded and reproducible."""
    score = np.asarray(score, dtype=np.float32)
    eligible = np.asarray(eligible, dtype=bool)
    if score.shape != eligible.shape:
        raise ValueError("score and eligible mask shapes differ")
    result = np.zeros(score.shape, dtype=np.float32)
    if mass <= 0:
        return result
    candidate_indices = np.flatnonzero(eligible & np.isfinite(score) & (score > 0))
    if candidate_indices.size == 0:
        return result
    if candidate_indices.size <= mass:
        result.flat[candidate_indices] = 1.0
        return result
    values = score.flat[candidate_indices]
    cutoff_index = values.size - mass
    cutoff = np.partition(values, cutoff_index)[cutoff_index]
    above = candidate_indices[values > cutoff]
    tied = candidate_indices[values == cutoff]
    needed = mass - above.size
    if needed > 0:
        rng = np.random.default_rng(seed)
        selected_ties = rng.choice(tied, size=needed, replace=False)
        chosen = np.concatenate((above, selected_ties))
    else:
        chosen = above[:mass]
    result.flat[chosen] = 1.0
    return result


def _sum_components(components: list[DTIComponents]) -> dict[str, Any]:
    if not components:
        return {
            "score": 0.0,
            "tp_weight": 0.0,
            "fp_weight": 0.0,
            "fn_weight": 0.0,
            "truth_cells": 0,
            "prediction_cells": 0,
        }
    tp = float(sum(item.tp_weight for item in components))
    fp = float(sum(item.fp_weight for item in components))
    fn = float(sum(item.fn_weight for item in components))
    alpha = components[0].alpha
    beta = components[0].beta
    denominator = tp + alpha * fp + beta * fn + 1e-9
    return {
        "score": float(tp / denominator) if denominator > 0 else 0.0,
        "tp_weight": tp,
        "fp_weight": fp,
        "fn_weight": fn,
        "truth_cells": int(sum(item.truth_cells for item in components)),
        "prediction_cells": int(sum(item.prediction_cells for item in components)),
        "alpha": alpha,
        "beta": beta,
        "radius_m": components[0].radius_m,
    }


def _crop(mask: np.ndarray, rows: tuple[int, int], cols: tuple[int, int]) -> np.ndarray:
    return mask[rows[0] : rows[1], cols[0] : cols[1]]


def _evaluate_method(
    score_map: np.ndarray,
    blocks: list[SpatialBlock],
    fold_budgets: list[int],
    *,
    seed: int,
    include_subtiles: bool = True,
) -> dict[str, Any]:
    fold_results: list[dict[str, Any]] = []
    fold_components: list[DTIComponents] = []
    subtile_scores: dict[str, float] = {}
    subtile_components: dict[str, DTIComponents] = {}

    for fold_idx, (block, budget) in enumerate(zip(blocks, fold_budgets, strict=True)):
        score_crop = _crop(score_map, block.rows, block.cols)
        eligible_crop = _crop(block.eligible, block.rows, block.cols)
        truth_crop = _crop(block.truth, block.rows, block.cols)
        prediction_crop = _top_n_prediction(
            score_crop,
            eligible_crop,
            budget,
            seed=seed + fold_idx * 101,
        )
        components = distance_weighted_tversky(truth_crop, prediction_crop)
        fold_components.append(components)
        fold_results.append(
            {
                "id": block.block_id,
                "budget": int(budget),
                "eligible_cells": int(np.count_nonzero(eligible_crop)),
                "truth_cells": components.truth_cells,
                "prediction_cells": components.prediction_cells,
                "dti": components.score,
                "tp_weight": components.tp_weight,
                "fp_weight": components.fp_weight,
                "fn_weight": components.fn_weight,
            }
        )

        if include_subtiles:
            halo_px = 3  # 300 m support on the registered 100 m grid.
            for tile_record in block.subtile_masks:
                tile_id, tile_rows, tile_cols, tile_eligible, tile_truth = tile_record
                halo_rows = (
                    max(block.rows[0], tile_rows[0] - halo_px),
                    min(block.rows[1], tile_rows[1] + halo_px),
                )
                halo_cols = (
                    max(block.cols[0], tile_cols[0] - halo_px),
                    min(block.cols[1], tile_cols[1] + halo_px),
                )
                truth_halo = _crop(block.truth, halo_rows, halo_cols)
                prediction_halo = prediction_crop[
                    halo_rows[0] - block.rows[0] : halo_rows[1] - block.rows[0],
                    halo_cols[0] - block.cols[0] : halo_cols[1] - block.cols[0],
                ]
                truth_eval = _crop(tile_truth, halo_rows, halo_cols)
                prediction_eval = _crop(tile_eligible, halo_rows, halo_cols)
                tile_components = distance_weighted_tversky(
                    truth_halo,
                    prediction_halo,
                    truth_eval_mask=truth_eval,
                    prediction_eval_mask=prediction_eval,
                )
                subtile_scores[tile_id] = tile_components.score
                subtile_components[tile_id] = tile_components

    pooled = _sum_components(fold_components)
    return {
        "pooled": pooled,
        "folds": fold_results,
        "subtile_scores": subtile_scores,
        "_subtile_components": subtile_components,
    }


def _translate_no_wrap(array: np.ndarray, dr: int, dc: int) -> np.ndarray:
    shifted = np.zeros_like(array)
    height, width = array.shape
    src_r0, src_r1 = max(0, -dr), min(height, height - dr)
    src_c0, src_c1 = max(0, -dc), min(width, width - dc)
    if src_r0 < src_r1 and src_c0 < src_c1:
        shifted[src_r0 + dr : src_r1 + dr, src_c0 + dc : src_c1 + dc] = array[
            src_r0:src_r1, src_c0:src_c1
        ]
    return shifted


def _translation_offsets(count: int = TRANSLATION_CONTROLS) -> list[tuple[int, int]]:
    rng = np.random.default_rng(505006)
    offsets: list[tuple[int, int]] = []
    while len(offsets) < count:
        angle = rng.uniform(0.0, 2.0 * np.pi)
        distance = rng.integers(50, 201)
        dr = round(distance * np.sin(angle))
        dc = round(distance * np.cos(angle))
        if (dr, dc) != (0, 0) and (dr, dc) not in offsets:
            offsets.append((dr, dc))
    return offsets


def evaluate_hypothesis(
    candidate_scores: np.ndarray,
    baseline_maps: dict[str, np.ndarray],
    blocks: list[SpatialBlock],
    *,
    split_sha256: str,
    input_hashes: dict[str, str],
    time_shuffle_maps: dict[str, np.ndarray] | None = None,
    seed: int = 5001,
) -> dict[str, Any]:
    """Run frozen equal-mass fold scoring and the spatial-translation control."""
    if not blocks:
        raise ValueError("no holdout blocks")
    total_area = sum(int(np.count_nonzero(block.eligible)) for block in blocks)
    if total_area <= 0:
        raise ValueError("holdout split has no eligible valid cells")
    fold_areas = [int(np.count_nonzero(block.eligible)) for block in blocks]
    fold_budgets = allocate_largest_remainder(PREDICTION_MASS, fold_areas)

    maps: dict[str, np.ndarray] = {"H50-S1": candidate_scores}
    maps.update(baseline_maps)
    time_shuffle_maps = time_shuffle_maps or {}
    for name, raster in maps.items():
        if raster.shape != candidate_scores.shape:
            raise ValueError(f"{name} raster shape does not match the candidate")
        if np.any(~np.isfinite(raster)) or np.any((raster < 0) | (raster > 1)):
            raise ValueError(f"{name} raster values must be finite and in [0, 1]")
    for name, raster in time_shuffle_maps.items():
        if raster.shape != candidate_scores.shape:
            raise ValueError(f"{name} raster shape does not match the candidate")
        if np.any(~np.isfinite(raster)) or np.any((raster < 0) | (raster > 1)):
            raise ValueError(f"{name} raster values must be finite and in [0, 1]")

    method_results: dict[str, dict[str, Any]] = {}
    internal_subtiles: dict[str, dict[str, DTIComponents]] = {}
    for method_idx, (name, score_map) in enumerate(maps.items()):
        result = _evaluate_method(score_map, blocks, fold_budgets, seed=seed + method_idx * 10000)
        internal_subtiles[name] = result.pop("_subtile_components")
        method_results[name] = result

    baseline_names = list(baseline_maps)
    if not baseline_names:
        raise ValueError("at least one frozen baseline raster is required")
    incumbent_name = max(baseline_names, key=lambda name: method_results[name]["pooled"]["score"])
    incumbent = method_results[incumbent_name]
    candidate = method_results["H50-S1"]
    paired_fold_deltas = [
        candidate_fold["dti"] - incumbent_fold["dti"]
        for candidate_fold, incumbent_fold in zip(
            candidate["folds"], incumbent["folds"], strict=True
        )
    ]

    # Four 2x2 subtiles per macrofold are the preregistered bootstrap units.
    candidate_subtiles = internal_subtiles["H50-S1"]
    incumbent_subtiles = internal_subtiles[incumbent_name]
    subtile_ids = sorted(set(candidate_subtiles) & set(incumbent_subtiles))
    subtile_deltas = np.asarray(
        [
            candidate_subtiles[tile_id].score - incumbent_subtiles[tile_id].score
            for tile_id in subtile_ids
        ],
        dtype=np.float64,
    )
    if subtile_deltas.size == 0:
        bootstrap_ci = [0.0, 0.0]
    else:
        rng = np.random.default_rng(505007)
        samples = rng.integers(
            0,
            subtile_deltas.size,
            size=(BOOTSTRAP_REPLICATES, subtile_deltas.size),
        )
        bootstrap_means = subtile_deltas[samples].mean(axis=1)
        bootstrap_ci = [
            float(np.quantile(bootstrap_means, 0.025)),
            float(np.quantile(bootstrap_means, 0.975)),
        ]

    control_scores: list[dict[str, Any]] = []
    for control_idx, (dr, dc) in enumerate(_translation_offsets()):
        shifted = _translate_no_wrap(candidate_scores, dr, dc)
        control = _evaluate_method(
            shifted, blocks, fold_budgets, seed=seed + 700000 + control_idx * 10000
        )
        control_scores.append(
            {
                "id": f"translate-{control_idx + 1:02d}",
                "row_shift_px": dr,
                "col_shift_px": dc,
                "pooled_dti": control["pooled"]["score"],
                "fold_dti": [fold["dti"] for fold in control["folds"]],
            }
        )
        del shifted
    control_values = np.asarray([item["pooled_dti"] for item in control_scores])
    control_q95 = float(np.quantile(control_values, 0.95)) if control_values.size else 0.0

    time_control_scores: list[dict[str, Any]] = []
    for control_idx, (control_name, control_map) in enumerate(time_shuffle_maps.items()):
        control = _evaluate_method(
            control_map,
            blocks,
            fold_budgets,
            seed=seed + 800000 + control_idx * 10000,
            include_subtiles=False,
        )
        time_control_scores.append(
            {
                "id": control_name,
                "pooled_dti": control["pooled"]["score"],
                "fold_dti": [fold["dti"] for fold in control["folds"]],
            }
        )
    time_control_values = np.asarray([item["pooled_dti"] for item in time_control_scores])
    time_control_q95 = (
        float(np.quantile(time_control_values, 0.95)) if time_control_values.size else 0.0
    )

    delta = candidate["pooled"]["score"] - incumbent["pooled"]["score"]
    pass_components = {
        "pooled_delta_at_least_0_005": bool(delta >= 0.005),
        "positive_fold_deltas_at_least_3_of_4": bool(sum(d > 0 for d in paired_fold_deltas) >= 3),
        "paired_block_bootstrap_lower_bound_above_zero": bool(bootstrap_ci[0] > 0),
        "beats_95th_percentile_translation_control": bool(
            candidate["pooled"]["score"] > control_q95
        ),
        "beats_95th_percentile_time_shuffle_control": bool(
            not time_control_values.size or candidate["pooled"]["score"] > time_control_q95
        ),
    }
    gate_pass = all(pass_components.values())

    # Strip non-JSON internal objects, keeping all measured sub-tile deltas.
    subtile_report = [
        {
            "id": tile_id,
            "candidate_dti": candidate_subtiles[tile_id].score,
            "incumbent_dti": incumbent_subtiles[tile_id].score,
            "paired_delta": candidate_subtiles[tile_id].score - incumbent_subtiles[tile_id].score,
        }
        for tile_id in subtile_ids
    ]
    return {
        "metric": {
            "name": "distance-weighted Tversky index",
            "alpha": 0.2,
            "beta": 0.8,
            "radius_m": 300.0,
            "kernel": "max(1 - distance_m / 300, 0)",
            "epsilon": 1e-9,
        },
        "split_sha256": split_sha256,
        "input_sha256": input_hashes,
        "prediction_mass_budget": PREDICTION_MASS,
        "fold_budgets": {
            block.block_id: budget for block, budget in zip(blocks, fold_budgets, strict=True)
        },
        "eligible_cells_by_fold": {
            block.block_id: area for block, area in zip(blocks, fold_areas, strict=True)
        },
        "method_results": method_results,
        "incumbent_method": incumbent_name,
        "candidate_minus_incumbent_pooled_dti": delta,
        "paired_fold_deltas": {
            fold["id"]: value
            for fold, value in zip(candidate["folds"], paired_fold_deltas, strict=True)
        },
        "subtile_bootstrap": {
            "units": "sixteen 2x2 spatial subtiles (four per macrofold)",
            "replicates": BOOTSTRAP_REPLICATES,
            "seed": 505007,
            "percentile_ci_95": bootstrap_ci,
            "subtiles": subtile_report,
        },
        "translation_controls": {
            "count": len(control_scores),
            "offset_range_px": [50, 200],
            "seed": 505006,
            "scores": control_scores,
            "pooled_dti_q95": control_q95,
        },
        "time_shuffle_controls": {
            "count": len(time_control_scores),
            "method": "shuffle origin-year labels among relocated in-grid events, refit identical geometry pipeline",
            "scores": time_control_scores,
            "pooled_dti_q95": time_control_q95,
            "score_map_sha256": {
                name: sha256_array(array.astype(np.float32))
                for name, array in time_shuffle_maps.items()
            },
        },
        "promotion_gate": {
            "pass": gate_pass,
            "components": pass_components,
            "decision": "ELIGIBLE_FOR_REVIEW_ONLY" if gate_pass else "NO_SLOT",
            "note": "A local proxy pass does not equal portal acceptance or predict private-test performance.",
        },
        "audit": {
            "candidate_score_map_sha256": sha256_array(candidate_scores.astype(np.float32)),
            "baseline_raster_sha256": {
                name: sha256_array(array.astype(np.float32))
                for name, array in baseline_maps.items()
            },
            "baseline_source_hashes": {name: input_hashes.get(name) for name in baseline_maps},
        },
    }


def read_baseline_raster(
    path: str | Path,
    template_path: str | Path,
) -> tuple[np.ndarray, dict[str, Any]]:
    with rasterio.open(template_path) as template_ds, rasterio.open(path) as ds:
        check_same_grid(template_ds, ds)
        raw = ds.read(1, masked=True)
        values = np.asarray(raw.filled(0), dtype=np.float32)
        values[~np.isfinite(values)] = 0.0
        if np.any((values < 0) | (values > 1)):
            raise ValueError(f"baseline {path} has values outside [0, 1]")
        metadata = {
            "path": str(path),
            "sha256": sha256_file(path),
            "bytes": Path(path).stat().st_size,
            "positive_cells": int(np.count_nonzero(values > 0)),
            "unique_values": np.unique(values).tolist()[:20],
        }
    return values, metadata


def spatial_jaccard(left: np.ndarray, right: np.ndarray, valid_mask: np.ndarray) -> float:
    a = (np.asarray(left) > 0) & valid_mask
    b = (np.asarray(right) > 0) & valid_mask
    union = np.count_nonzero(a | b)
    return float(np.count_nonzero(a & b) / union) if union else 1.0
