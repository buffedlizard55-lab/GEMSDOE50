#!/usr/bin/env python3
"""Build and falsify H55-S1, then write unique research-only competition-grid TIFFs.

This script never uploads to DrivenData. A TIFF is emitted even when the frozen no-slot gate
fails, because the artifact is useful for audit; the report and website must preserve the decision.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
import rasterio
from scipy import ndimage

from gems51.emit import pack
from gems55.ridge import build_ridge_evidence, snapped_corridor_field
from gems55.seismic import (
    H55Config,
    build_catalog_frame,
    fit_axes,
    make_density_field,
    normalized_triangle_filter,
)
from gemsdoe50.common import jsonable, sha256_file
from gemsdoe50.holdout import SpatialBlock, build_spatial_blocks, load_split_spec
from gemsdoe50.metric import distance_weighted_tversky

MASS = 35_000
WIDTHS_M = (300.0, 600.0, 1_000.0)
PRIMARY_WIDTH_M = 600.0
BOOTSTRAP_REPLICATES = 5_000
RNG_SEED = 5_501


def _git_commit() -> str | None:
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "HEAD"], text=True, stderr=subprocess.DEVNULL
        ).strip()
    except (OSError, subprocess.CalledProcessError):
        return None


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(jsonable(payload), indent=2, sort_keys=True, allow_nan=False) + "\n",
        encoding="utf-8",
    )


def _load_binary(path: Path, expected_shape: tuple[int, int]) -> tuple[np.ndarray, dict]:
    with rasterio.open(path) as ds:
        if ds.shape != expected_shape or ds.count != 1:
            raise ValueError(f"unexpected comparator grid: {path}")
        raw = ds.read(1)
    mask = np.isfinite(raw) & (raw > 0)
    return mask, {
        "path": str(path),
        "sha256": sha256_file(path),
        "bytes": path.stat().st_size,
        "positive_cells": int(mask.sum()),
    }


def _components(
    prediction: np.ndarray,
    truth: np.ndarray,
    *,
    truth_eval: np.ndarray | None = None,
    prediction_eval: np.ndarray | None = None,
) -> dict[str, Any]:
    result = distance_weighted_tversky(
        truth,
        prediction.astype(np.float32),
        truth_eval_mask=truth_eval,
        prediction_eval_mask=prediction_eval,
    )
    out = result.as_dict()
    out["credit_per_dot"] = float(result.tp_weight) / max(result.prediction_cells, 1)
    out["covered_fraction"] = float(result.tp_weight) / max(result.truth_cells, 1)
    return out


def _core_mask(block: SpatialBlock, shape: tuple[int, int]) -> np.ndarray:
    r0, r1, c0, c1 = map(int, block.metadata["core_bounds"])
    core = np.zeros(shape, dtype=bool)
    core[r0:r1, c0:c1] = True
    return core


def _method_scores(
    methods: dict[str, np.ndarray],
    truth: np.ndarray,
    allowed: np.ndarray,
    blocks: list[SpatialBlock],
) -> dict[str, Any]:
    """Score SGMC-off truth on the geometry of the frozen macrofold cores.

    ``block.truth`` remains the supplied-catalogue truth used to freeze the split. It is
    deliberately *not* substituted for the off-catalogue SGMC instrument here.
    """
    out: dict[str, Any] = {}
    cores = {block.block_id: _core_mask(block, truth.shape) for block in blocks}
    for name, support in methods.items():
        folds: dict[str, Any] = {}
        for block in blocks:
            core = cores[block.block_id]
            folds[block.block_id] = _components(
                support,
                truth,
                truth_eval=truth & core,
                prediction_eval=allowed & core,
            )
        out[name] = {
            "pooled": _components(support, truth),
            "folds": folds,
        }
    return out


def _bootstrap_primary(
    candidate: np.ndarray,
    incumbent: np.ndarray,
    truth: np.ndarray,
    allowed: np.ndarray,
    blocks: list[SpatialBlock],
) -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    deltas: list[float] = []
    for block in blocks:
        for tile_id, tile_rows, tile_cols, _eligible, _catalogue_truth in block.subtile_masks:
            halo = 3
            r0, r1 = max(0, tile_rows[0] - halo), min(truth.shape[0], tile_rows[1] + halo)
            c0, c1 = max(0, tile_cols[0] - halo), min(truth.shape[1], tile_cols[1] + halo)
            crop = np.s_[r0:r1, c0:c1]
            tile = np.zeros((r1 - r0, c1 - c0), dtype=bool)
            tile[
                tile_rows[0] - r0 : tile_rows[1] - r0,
                tile_cols[0] - c0 : tile_cols[1] - c0,
            ] = True
            tile_truth_crop = truth[crop] & tile
            eligible_crop = allowed[crop] & tile
            cand = _components(
                candidate[crop],
                truth[crop],
                truth_eval=tile_truth_crop,
                prediction_eval=eligible_crop,
            )
            inc = _components(
                incumbent[crop],
                truth[crop],
                truth_eval=tile_truth_crop,
                prediction_eval=eligible_crop,
            )
            delta = cand["credit_per_dot"] - inc["credit_per_dot"]
            deltas.append(delta)
            rows.append(
                {
                    "id": tile_id,
                    "candidate_credit_per_dot": cand["credit_per_dot"],
                    "incumbent_credit_per_dot": inc["credit_per_dot"],
                    "paired_delta_credit_per_dot": delta,
                    "candidate_dti": cand["score"],
                    "incumbent_dti": inc["score"],
                }
            )
    values = np.asarray(deltas, dtype=np.float64)
    rng = np.random.default_rng(55_007)
    sampled = values[
        rng.integers(0, values.size, size=(BOOTSTRAP_REPLICATES, values.size))
    ].mean(axis=1)
    ci = [float(np.quantile(sampled, 0.025)), float(np.quantile(sampled, 0.975))]
    return {
        "units": "sixteen frozen spatial subtiles",
        "replicates": BOOTSTRAP_REPLICATES,
        "seed": 55_007,
        "paired_mean_credit_per_dot": float(values.mean()),
        "percentile_ci_95": ci,
        "subtiles": rows,
    }


def _translate_no_wrap(mask: np.ndarray, dr: int, dc: int, allowed: np.ndarray) -> np.ndarray:
    result = np.zeros(mask.shape, dtype=bool)
    h, w = mask.shape
    sr0, sr1 = max(0, -dr), min(h, h - dr)
    sc0, sc1 = max(0, -dc), min(w, w - dc)
    if sr0 < sr1 and sc0 < sc1:
        result[sr0 + dr : sr1 + dr, sc0 + dc : sc1 + dc] = mask[sr0:sr1, sc0:sc1]
    return result & allowed


def _controls(
    primary: np.ndarray,
    random_support: np.ndarray,
    truth: np.ndarray,
    allowed: np.ndarray,
) -> dict[str, Any]:
    offsets = ((-100, 0), (100, 0), (0, -100), (0, 100))
    translations = []
    for dr, dc in offsets:
        support = _translate_no_wrap(primary, dr, dc, allowed)
        translations.append(
            {
                "row_shift_px": dr,
                "col_shift_px": dc,
                "shift_m": [dr * 100, dc * 100],
                "mass": int(support.sum()),
                "score": _components(support, truth),
            }
        )
    return {
        "matched_random": {
            "mass": int(random_support.sum()),
            "score": _components(random_support, truth),
        },
        "translations": translations,
    }


def _write_tiff(
    template_path: Path,
    output: Path,
    support: np.ndarray,
    valid: np.ndarray,
    *,
    zero_outside: bool,
) -> dict[str, Any]:
    output.parent.mkdir(parents=True, exist_ok=True)
    with rasterio.open(template_path) as src:
        profile = src.profile.copy()
    values = support.astype(np.float32)
    if zero_outside:
        values[~valid] = 0.0
        nodata = None
    else:
        values[~valid] = np.nan
        nodata = np.nan
    profile.update(
        driver="GTiff",
        count=1,
        dtype="float32",
        nodata=nodata,
        compress="DEFLATE",
        predictor=3,
        tiled=True,
        blockxsize=256,
        blockysize=256,
    )
    with rasterio.open(output, "w", **profile) as dst:
        dst.write(values, 1)
        dst.set_band_description(1, "H55-S1 binary probability")
        dst.update_tags(
            hypothesis="H55-S1",
            outside_footprint="0" if zero_outside else "NaN",
            probability_range="[0,1]",
        )
    with rasterio.open(output) as ds:
        reread = ds.read(1)
        if ds.count != 1 or ds.shape != support.shape:
            raise ValueError("written TIFF schema mismatch")
        finite = reread[np.isfinite(reread)]
        if finite.size == 0 or float(finite.min()) < 0 or float(finite.max()) > 1:
            raise ValueError("Predicted values must be in range [0, 1]")
        if zero_outside and not np.all(np.isfinite(reread)):
            raise ValueError("zero-outside portal-safe TIFF contains non-finite values")
        metadata = {
            "path": str(output),
            "bytes": output.stat().st_size,
            "sha256": sha256_file(output),
            "shape": [ds.height, ds.width],
            "count": ds.count,
            "dtype": str(ds.dtypes[0]),
            "crs": str(ds.crs),
            "transform": list(ds.transform)[:6],
            "nodata": "NaN" if ds.nodata is not None and np.isnan(ds.nodata) else ds.nodata,
            "finite_min": float(finite.min()),
            "finite_max": float(finite.max()),
            "finite_cells": int(finite.size),
            "nonfinite_cells": int(np.count_nonzero(~np.isfinite(reread))),
            "positive_cells": int(np.count_nonzero(reread > 0)),
            "unique_finite_values": np.unique(finite).tolist(),
            "all_values_in_closed_unit_interval": True,
            "all_values_finite": bool(np.all(np.isfinite(reread))),
        }
    return metadata


def run(args: argparse.Namespace) -> dict[str, Any]:
    paths = {name: Path(getattr(args, name)) for name in (
        "catalog", "template", "labels", "hot_points", "comcat", "lidar", "radiometric",
        "sgmc", "incumbent", "split", "prior_union"
    )}
    input_hashes = {name: sha256_file(path) for name, path in paths.items()}
    with rasterio.open(paths["template"]) as ds:
        template = ds.read(1)
        valid = np.isfinite(template)
        transform = ds.transform
        shape = ds.shape
        crs = str(ds.crs)
        pixel_size = abs(float(ds.transform.a))
    if pixel_size != 100.0:
        raise ValueError(f"H55 is frozen for a 100 m grid, got {pixel_size}")
    with rasterio.open(paths["labels"]) as ds:
        if ds.shape != shape or str(ds.crs) != crs or ds.transform != transform:
            raise ValueError("label grid mismatch")
        labels = np.isfinite(ds.read(1)) & (ds.read(1) > 0)
    known_distance = ndimage.distance_transform_edt(~labels, sampling=(pixel_size, pixel_size))
    scientific_allowed = valid & (known_distance > 300.0)
    del known_distance

    with np.load(paths["prior_union"], allow_pickle=False) as union_file:
        union_shape = tuple(int(value) for value in union_file["shape"])
        if union_shape != shape:
            raise ValueError("prior-positive union grid mismatch")
        prior_union = np.unpackbits(union_file["packed"])[: int(np.prod(shape))]
        prior_union = prior_union.astype(bool).reshape(shape)
        prior_union_count = int(union_file["positive_cells"])
        if int(prior_union.sum()) != prior_union_count:
            raise ValueError("prior-positive union count mismatch")
        prior_union_artifacts = int(union_file["names"].size)
    # Comparing to prior files is allowed; copying their prediction pixels is not. This
    # negative mask makes exact candidate/prior intersection impossible by construction.
    novel_allowed = scientific_allowed & ~prior_union

    with rasterio.open(paths["sgmc"]) as ds:
        if ds.shape != shape or str(ds.crs) != crs or ds.transform != transform:
            raise ValueError("SGMC proxy grid mismatch")
        sgmc = ds.read(1)
    truth = scientific_allowed & (sgmc > 0)

    split_spec = load_split_spec(paths["split"])
    # Reconstruct the registered split from the exact truth used when its geometry was
    # frozen. The off-catalogue SGMC proxy is evaluated only inside those fixed cores.
    blocks, split_realized = build_spatial_blocks(valid, labels, split_spec)

    config = H55Config()
    frame = build_catalog_frame(
        paths["catalog"], paths["template"], paths["hot_points"], paths["comcat"], config
    )
    geometry_frame, p_area, background_report = normalized_triangle_filter(
        frame, valid, transform, config
    )
    segments = fit_axes(geometry_frame, p_area, config)
    if len(segments) == 0:
        raise ValueError("no H55 axes passed the preregistered filters")

    evidence = build_ridge_evidence(paths["lidar"], paths["radiometric"], valid)
    supports: dict[str, np.ndarray] = {}
    fields: dict[str, np.ndarray] = {}
    corridor_reports: dict[str, Any] = {}
    pack_reports: dict[str, Any] = {}
    for width in WIDTHS_M:
        name = f"H55-S1-{int(width)}m"
        field, corridor_report = snapped_corridor_field(
            segments, evidence, transform, valid, novel_allowed, width
        )
        support, pack_report = pack(
            field, MASS, valid=novel_allowed, suppression_px=3.0, seed=RNG_SEED
        )
        supports[name] = support
        fields[name] = field
        corridor_reports[name] = corridor_report
        pack_reports[name] = pack_report
        print(
            f"{name}: segments={len(segments)}, field={np.count_nonzero(field)}, "
            f"dots={support.sum()}",
            flush=True,
        )

    density_supports: dict[str, np.ndarray] = {}
    density_reports: dict[str, Any] = {}
    for sigma_m in (1_000.0, 2_000.0):
        name = f"density-{int(sigma_m)}m"
        field = make_density_field(geometry_frame, shape, valid, sigma_m, pixel_size)
        field[~novel_allowed] = 0.0
        support, pack_report = pack(
            field, MASS, valid=novel_allowed, suppression_px=3.0, seed=RNG_SEED
        )
        density_supports[name] = support
        density_reports[name] = {"sigma_m": sigma_m, "pack": pack_report}

    incumbent, _incumbent_meta = _load_binary(paths["incumbent"], shape)
    incumbent &= scientific_allowed
    random_field = np.zeros(shape, dtype=np.float32)
    rng = np.random.default_rng(RNG_SEED)
    random_field[novel_allowed] = rng.random(int(novel_allowed.sum()), dtype=np.float32)
    random_support, random_pack = pack(
        random_field, MASS, valid=novel_allowed, suppression_px=3.0, seed=RNG_SEED
    )
    del random_field

    methods = {**supports, **density_supports, "Candidate-B-incumbent": incumbent, "matched-random": random_support}
    scores = _method_scores(methods, truth, scientific_allowed, blocks)
    primary_name = f"H55-S1-{int(PRIMARY_WIDTH_M)}m"
    bootstrap = _bootstrap_primary(
        supports[primary_name], incumbent, truth, scientific_allowed, blocks
    )
    controls = _controls(supports[primary_name], random_support, truth, novel_allowed)

    width_gates: dict[str, Any] = {}
    density_names = sorted(density_supports)
    for width in WIDTHS_M:
        name = f"H55-S1-{int(width)}m"
        fold_density_delta = {}
        for block in blocks:
            candidate_credit = scores[name]["folds"][block.block_id]["credit_per_dot"]
            best_density_credit = max(
                scores[density]["folds"][block.block_id]["credit_per_dot"]
                for density in density_names
            )
            fold_density_delta[block.block_id] = candidate_credit - best_density_credit
        width_gates[name] = {
            "pooled_dti": scores[name]["pooled"]["score"],
            "pooled_delta_vs_best_density": scores[name]["pooled"]["score"] - max(
                scores[density]["pooled"]["score"] for density in density_names
            ),
            "fold_credit_per_dot_delta_vs_best_density": fold_density_delta,
            "positive_density_delta_all_four_folds": all(v > 0 for v in fold_density_delta.values()),
            "exact_mass": bool(int(supports[name].sum()) == MASS),
        }
    primary_incumbent_fold_delta = {
        block.block_id: (
            scores[primary_name]["folds"][block.block_id]["credit_per_dot"]
            - scores["Candidate-B-incumbent"]["folds"][block.block_id]["credit_per_dot"]
        )
        for block in blocks
    }
    gate_components = {
        "all_widths_positive_pooled_delta_vs_density": all(
            record["pooled_delta_vs_best_density"] > 0 for record in width_gates.values()
        ),
        "all_widths_positive_credit_per_dot_vs_density_in_4_of_4_folds": all(
            record["positive_density_delta_all_four_folds"] for record in width_gates.values()
        ),
        "all_widths_exact_matched_mass": all(record["exact_mass"] for record in width_gates.values()),
        "primary_pooled_dti_above_incumbent": bool(
            scores[primary_name]["pooled"]["score"]
            > scores["Candidate-B-incumbent"]["pooled"]["score"]
        ),
        "primary_credit_per_dot_above_incumbent_in_at_least_3_of_4_folds": bool(
            sum(value > 0 for value in primary_incumbent_fold_delta.values()) >= 3
        ),
        "paired_subtile_bootstrap_lower_bound_positive": bool(
            bootstrap["percentile_ci_95"][0] > 0
        ),
        "primary_above_all_four_translations": bool(
            scores[primary_name]["pooled"]["score"]
            > max(row["score"]["score"] for row in controls["translations"])
        ),
        "primary_above_matched_random": bool(
            scores[primary_name]["pooled"]["score"]
            > controls["matched_random"]["score"]["score"]
        ),
    }
    numeric_pass = all(gate_components.values())
    scientific_components = {
        "external_geometry_license_verified": True,
        "formal_aftershock_declustering_validated": False,
        "mine_injection_inventory_complete": False,
        "event_specific_uncertainty_available": False,
        "comcat_exclusion_redistribution_status_resolved": False,
    }
    overall_pass = numeric_pass and all(scientific_components.values())

    support_hash = hashlib.sha256(
        np.packbits(supports[primary_name].ravel()).tobytes()
    ).hexdigest()
    slug = support_hash[:8]
    output_dir = Path(args.output_dir)
    emitted_mass = int(supports[primary_name].sum())
    stem = f"gemsdoe50-h55-seisgeom-ridgesnap-{emitted_mass}-20261007-{slug}"
    zero_path = output_dir / f"{stem}-zeros.tif"
    nan_path = output_dir / f"{stem}-nan.tif"
    zero_meta = _write_tiff(paths["template"], zero_path, supports[primary_name], valid, zero_outside=True)
    nan_meta = _write_tiff(paths["template"], nan_path, supports[primary_name], valid, zero_outside=False)
    if np.any(supports[primary_name] & ~novel_allowed):
        raise ValueError(
            "final support overlaps a prior positive pixel, the supplied-fault exclusion, or invalid cells"
        )

    pairwise = {}
    for name, mask in {**density_supports, "Candidate-B-incumbent": incumbent}.items():
        intersection = int(np.count_nonzero(supports[primary_name] & mask))
        union = int(np.count_nonzero(supports[primary_name] | mask))
        pairwise[name] = {
            "intersection_positive_cells": intersection,
            "jaccard": intersection / union if union else 1.0,
            "exact_pixel_match": bool(np.array_equal(supports[primary_name], mask)),
        }

    report: dict[str, Any] = {
        "schema": "gemsdoe50.h55-evaluation.v1",
        "project": "GEMSDOE50",
        "hypothesis": "H55-S1 — thinned epicentre triangle/covariance axes snapped across-axis to independent ridges",
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "git_commit_at_build": _git_commit(),
        "status": "UNIQUE_RESEARCH_ARTIFACT_NOT_SUBMITTED",
        "submission_status": "No DrivenData upload or weekly slot was used.",
        "input_sha256": input_hashes,
        "prior_pixel_exclusion": {
            "source": str(paths["prior_union"]),
            "registered_file_hashes": prior_union_artifacts,
            "union_positive_cells": prior_union_count,
            "candidate_exact_overlap_with_union": int(
                np.count_nonzero(supports[primary_name] & prior_union)
            ),
            "rule": (
                "Prior predictions are comparison-only; every prior positive pixel is excluded "
                "from final candidate placement."
            ),
        },
        "registered_protocol": {
            "preregistration": "docs/research/h55-hypotheses-preregistered.md",
            "exact_addendum": "docs/research/h55-protocol-addendum.md",
            "config": asdict(config),
            "prediction_mass": MASS,
            "width_sensitivities_m": list(WIDTHS_M),
            "primary_width_m": PRIMARY_WIDTH_M,
            "unverified_adaptation_notice": (
                "The normalized 2-D triangle-area test is unverified and is not the published "
                "3-D tetrahedron test of Ouillon/Sornette."
            ),
        },
        "catalog_processing": frame.metadata,
        "background_test": background_report,
        "axis_fit": segments.metadata,
        "ridge_evidence": evidence.metadata,
        "corridors": corridor_reports,
        "packing": {**pack_reports, **density_reports, "matched-random": random_pack},
        "holdout": {
            "split_spec_sha256": input_hashes["split"],
            "realization": split_realized,
            "truth": "derived SGMC fault cells more than 300 m from the supplied catalogue",
            "truth_cells": int(truth.sum()),
            "metric": "official 300 m distance-weighted Tversky proxy calculation",
            "method_scores": scores,
            "width_gates": width_gates,
            "primary_fold_credit_per_dot_delta_vs_incumbent": primary_incumbent_fold_delta,
            "paired_subtile_bootstrap": bootstrap,
            "controls": controls,
        },
        "decision": {
            "numeric_pass": bool(numeric_pass),
            "numeric_components": gate_components,
            "scientific_components": scientific_components,
            "pass": bool(overall_pass),
            "decision": "ELIGIBLE_FOR_REVIEW" if overall_pass else "NO_SLOT",
            "reason": (
                "A unique TIFF is an audit artifact, not a recommendation. A slot is protected "
                "unless every frozen numeric and scientific/compliance gate passes."
            ),
        },
        "artifacts": {
            "recommended_portal_safe_zero_outside": zero_meta,
            "sample_semantics_nan_outside": nan_meta,
            "positive_mask_sha256": support_hash,
            "short_submission_note": (
                "H55-S1: space-time-thinned relocated-earthquake point geometry; recurrent 2-D "
                "covariance axes, width sensitivity, and cross-axis LiDAR/radiometric ridge snap; "
                f"known-fault 300 m exclusion; {emitted_mass:,} binary cells (35,000-cell target "
                "not reached under frozen spacing)."
            ),
            "range_guard": "Every finite value re-read in [0,1]; zero-outside twin is entirely finite.",
        },
        "novelty_local_comparators": pairwise,
        "limitations": [
            "The SGMC raster is an imperfect public proxy, not hidden competition truth.",
            "The 250 m/90-day largest-event rule is deterministic sequence thinning, not a validated ETAS/Reasenberg/Gardner-Knopoff declustering model.",
            "The relocated catalog contains no per-event covariance; corridor widths are sensitivity assumptions.",
            "GDR hot features and explicit ComCat anthropogenic events do not form a complete mine/injection inventory.",
            "Mixed-network ComCat contributor-specific redistribution status remains unresolved.",
            "A 2-D epicentre axis is not proof of a surface fault or geothermal productivity.",
            "Complete prior-corpus byte/pixel novelty must still be run before any slot review.",
        ],
    }
    report_path = Path(args.report)
    _write_json(report_path, report)
    print(f"H55 report: {report_path}", flush=True)
    print(f"Recommended TIFF: {zero_path}", flush=True)
    print(f"Primary pooled proxy DTI: {scores[primary_name]['pooled']['score']:.6f}", flush=True)
    print(f"Incumbent pooled proxy DTI: {scores['Candidate-B-incumbent']['pooled']['score']:.6f}", flush=True)
    print(f"Frozen decision: {report['decision']['decision']}", flush=True)
    return report


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--catalog", default="data/external/nvreloc_catalog_newmag.txt.gz")
    parser.add_argument("--template", default="data/grid/sample_submission.tif")
    parser.add_argument("--labels", default="data/grid/labels.tif")
    parser.add_argument("--hot-points", default="data/external/gdr_wellspring_in_footprint.csv")
    parser.add_argument("--comcat", default="data/external/usgs_comcat_earthquakes.csv.gz")
    parser.add_argument("--lidar", default="data/external/lidar_scarp_features_u8.tif")
    parser.add_argument("--radiometric", default="data/external/geodawn_rad_u8.tif")
    parser.add_argument("--sgmc", default="data/external/derived_sgmc_faults_100m_u8.tif")
    parser.add_argument("--incumbent", default="docs/downloads/gems51-scarpradio-offcat-35000-20261006-ecf058ea-nan.tif")
    parser.add_argument("--split", default="evidence/holdout-v1.json")
    parser.add_argument("--prior-union", default="registry/prior_positive_union.npz")
    parser.add_argument("--output-dir", default="docs/downloads")
    parser.add_argument("--report", default="evidence/results/h55s1-evaluation-20261007.json")
    args = parser.parse_args()
    run(args)


if __name__ == "__main__":
    main()
