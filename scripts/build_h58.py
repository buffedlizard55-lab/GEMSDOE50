#!/usr/bin/env python3
"""Archived H58-S1 build/validation workflow — NO-GO / NO SLOT; not a submission builder.

H58-S1 was a historical ComCat earthquake point-geometry experiment: declustering,
site screening, local 2-D covariance axes, uncertainty-width corridors, off-catalogue
scoring, a 3 px spacing design rule, ridge placement, and prior-pixel exclusion. Its
frozen scientific/control gates returned NO SLOT; mixed-network ComCat rights remain
unresolved, and the written TIFFs measured only 1 px minimum nearest-neighbour spacing.
Do not upload, repackage, relabel, or rerun this as H58-S1. H55 used a relocated catalogue
and failed its gate; H56 used ComCat lineations only as a LiDAR corroboration.

The shared emitter has since changed. Running this historical workflow would produce
new research bytes, not reproduce the archived TIFFs or authorize a candidate. This code
never uploads to DrivenData, grants a portal name/note, clears source rights, or changes
the NO-GO decision. Do not run it to create a new submission; any new lead requires a
separate charter-compliant preregistration and all gates.

For audit, the frozen constants are recorded in ``src/gemsdoe50/h58.py`` and the
historical preregistration in ``docs/research/h58-hypotheses-preregistered.md``. The
workflow hash-pins inputs; screens and declusters ComCat (unverified 2-D adaptation);
fits local covariance axes; builds corridors; measures placement options and controls;
re-reads format/uniqueness; and records local proxy results. The exact Euclidean emitter
now enforces a 3 px minimum on future runs, but that rule does not prove disjoint metric
kernel footprints or the simplified hidden-score identity.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import time
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
import rasterio
from scipy import ndimage

REPO = Path(__file__).resolve().parents[1]
import sys

sys.path.insert(0, str(REPO / "src"))

from gems55.ridge import build_ridge_evidence
from gemsdoe50 import h56, h58
from gemsdoe50.common import jsonable, sha256_file
from gemsdoe50.holdout import build_spatial_blocks, load_split_spec
from gemsdoe50.metric import distance_weighted_tversky

R_PX = 3.0  # the metric's own 300 m support at 100 m pixels
BOOTSTRAP_REPLICATES = 5_000
BOOTSTRAP_SEED = 55_007


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


def _core_mask(block, shape: tuple[int, int]) -> np.ndarray:
    r0, r1, c0, c1 = map(int, block.metadata["core_bounds"])
    core = np.zeros(shape, dtype=bool)
    core[r0:r1, c0:c1] = True
    return core


def _write_tiff(
    template_path: Path,
    output: Path,
    support: np.ndarray,
    valid: np.ndarray,
    *,
    zero_outside: bool,
) -> dict[str, Any]:
    """Write one float32 band on the official grid and re-read it from disk.

    The re-read is the direct guard against the portal's historical
    ``Predicted values must be in range [0, 1]`` rejection: a non-finite cell
    makes a plain min/max validator see NaN, and ``NaN <= 1`` is false.
    """
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
        dst.set_band_description(1, "H58-S1 binary probability")
        dst.update_tags(
            hypothesis="H58-S1",
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


def _translate_no_wrap(mask: np.ndarray, dr: int, dc: int, allowed: np.ndarray) -> np.ndarray:
    result = np.zeros(mask.shape, dtype=bool)
    h, w = mask.shape
    sr0, sr1 = max(0, -dr), min(h, h - dr)
    sc0, sc1 = max(0, -dc), min(w, w - dc)
    if sr0 < sr1 and sc0 < sc1:
        result[sr0 + dr : sr1 + dr, sc0 + dc : sc1 + dc] = mask[sr0:sr1, sc0:sc1]
    return result & allowed


def _support_field(rows: np.ndarray, cols: np.ndarray, shape: tuple[int, int]) -> np.ndarray:
    field = np.zeros(shape, dtype=bool)
    field[rows, cols] = True
    return field


def run(args: argparse.Namespace) -> dict[str, Any]:
    t0 = time.time()
    paths = {
        name: Path(getattr(args, name))
        for name in (
            "comcat", "template", "labels", "sgmc", "lidar", "radiometric",
            "incumbent", "split", "prior_union",
        )
    }
    for name, path in paths.items():
        if not path.exists():
            raise FileNotFoundError(f"missing input {name}: {path}")
    input_hashes = {name: sha256_file(path) for name, path in paths.items()}

    with rasterio.open(paths["template"]) as ds:
        template = ds.read(1)
        valid = np.isfinite(template)
        transform = ds.transform
        shape = ds.shape
        crs = str(ds.crs)
        pixel_size = abs(float(ds.transform.a))
    if pixel_size != 100.0:
        raise ValueError(f"H58 is frozen for a 100 m grid, got {pixel_size}")
    with rasterio.open(paths["labels"]) as ds:
        if ds.shape != shape or str(ds.crs) != crs or ds.transform != transform:
            raise ValueError("label grid mismatch")
        labels = ds.read(1)
    catalogue = labels == 1
    known_distance = ndimage.distance_transform_edt(~catalogue, sampling=(pixel_size, pixel_size))
    domain = valid & (known_distance > 300.0)  # off-catalogue scoring domain (>300 m)
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
    # Comparing to prior files is allowed; copying their prediction pixels is not.
    # This negative mask makes exact candidate/prior intersection impossible by construction.
    novel_allowed = domain & ~prior_union

    with rasterio.open(paths["sgmc"]) as ds:
        if ds.shape != shape or str(ds.crs) != crs or ds.transform != transform:
            raise ValueError("SGMC proxy grid mismatch")
        sgmc = ds.read(1)
    truth = domain & (sgmc > 0)  # independent off-catalogue proxy truth
    print(
        f"[{time.time()-t0:6.1f}s] valid={int(valid.sum()):,} domain={int(domain.sum()):,} "
        f"truth(sgmc_off)={int(truth.sum()):,} novel_allowed={int(novel_allowed.sum()):,}",
        flush=True,
    )

    # --- ComCat point-geometry pipeline ---
    frame, cat_report = h58.build_event_frame(
        paths["comcat"],
        paths["template"],
        hot_points_csv=args.hot_points,
        sequence_thin=args.sequence_thin,
    )
    belief, lineations, belief_report = h58.corridor_belief(frame, shape, transform)
    belief[~domain] = 0.0
    print(
        f"[{time.time()-t0:6.1f}s] events={len(frame):,} lineations={len(lineations):,} "
        f"corridor>0.05 over {belief_report['corridor_cells_gt_0.05']:.4f} of the grid",
        flush=True,
    )

    # --- independent ridge evidence for the placement step ---
    evidence = build_ridge_evidence(paths["lidar"], paths["radiometric"], valid)
    print(
        f"[{time.time()-t0:6.1f}s] ridge evidence: topo cells={evidence.metadata['finite_topographic_cells']:,} "
        f"radio cells={evidence.metadata['finite_radiometric_cells']:,}",
        flush=True,
    )

    # --- mass sweep ---
    sweep: dict[str, dict] = {}
    for n in h58.MASSES:
        em = h56.emit_blue_noise(belief, novel_allowed, n_target=n, min_sep_px=R_PX, seed=h58.EMIT_SEED)
        s = h56.score_dots(truth, em.rows, em.cols)
        ctrl = [
            h56.score_dots(
                truth, u.rows, u.cols
            )["dti"]
            for u in (
                h56.emit_blue_noise(
                    np.ones(shape, dtype=np.float32), novel_allowed,
                    n_target=n, min_sep_px=R_PX, seed=sd,
                )
                for sd in (1, 2, 3)
            )
        ]
        uni = float(np.mean(ctrl))
        # The model must price the *realized* emission: when the corridor support caps
        # the requested mass, the shipped artifact carries the realized dots only.
        model = h58.modelled_hidden_dti(s["credit_per_dot"], int(em.rows.size))
        sweep[str(n)] = {
            "n_requested": n,
            "n_dots": int(em.rows.size),
            "sgmc_off": s,
            "uniform_mean": uni,
            "uniform_draws": ctrl,
            "lift_over_uniform": s["dti"] / uni if uni else None,
            "model": model,
        }
        print(
            f"[{time.time()-t0:6.1f}s]  N={n:>7,}  realized={em.rows.size:>7,}  sgmc {s['dti']:.4f} "
            f"(uniform {uni:.4f}, lift {s['dti']/uni:.2f}x)  c/dot {s['credit_per_dot']:.4f}  "
            f"-> modelled hidden {model['dti_modelled']:.3f}",
            flush=True,
        )
    best_n = max(
        sweep, key=lambda k: (sweep[k]["model"]["dti_modelled"], -abs(int(k) - 100_000))
    )
    print(f"[{time.time()-t0:6.1f}s] frozen rule selects N={best_n}", flush=True)

    # --- final emission + placement step ---
    em = h56.emit_blue_noise(
        belief, novel_allowed, n_target=int(best_n), min_sep_px=R_PX, seed=h58.EMIT_SEED
    )
    before = h56.score_dots(truth, em.rows, em.cols)["dti"]
    snap_targets = {
        "belief_ridge": np.where(novel_allowed, ndimage.gaussian_filter(belief.astype(np.float64), 1.0), 0.0),
        "geophysics_ridge": np.where(novel_allowed, evidence.score.astype(np.float64), 0.0),
    }
    snap_rows = {"none": {"dti": before, "moved": 0}}
    best_target, best_dti, best_rc = "none", before, (em.rows, em.cols)
    for tname, tfield in snap_targets.items():
        r, c, info = h56.snap_to_ridge(em.rows, em.cols, tfield, max_snap_px=R_PX)
        d = h56.score_dots(truth, r, c)["dti"]
        snap_rows[tname] = {"dti": float(d), "moved": int(info["snapped"]),
                            "fraction_moved": float(info["snap_fraction"])}
        if d > best_dti:
            best_target, best_dti, best_rc = tname, d, (r, c)
    rows, cols = best_rc
    rows, cols = h56.dedupe(np.asarray(rows), np.asarray(cols))
    snap_info = {
        "chosen": best_target,
        "before": float(before),
        "after": float(best_dti),
        "used": best_target != "none",
        "candidates": snap_rows,
        "note": "snaps may move a dot only onto a novel_allowed pixel; the uniqueness-by-construction "
                "guarantee is preserved",
    }
    print(
        f"[{time.time()-t0:6.1f}s] placement: unsnapped {before:.4f}; "
        + ", ".join(f"{k} {v['dti']:.4f}" for k, v in snap_rows.items())
        + f"; chosen {best_target}; {rows.size:,} dots",
        flush=True,
    )

    candidate = _support_field(rows, cols, shape)
    if np.any(candidate & ~novel_allowed):
        raise ValueError(
            "final support overlaps a prior positive pixel, the supplied-fault exclusion, or invalid cells"
        )
    exact_prior_overlap = int(np.count_nonzero(candidate & prior_union))
    on_catalogue = int(np.count_nonzero(candidate & (ndimage.distance_transform_edt(~catalogue) <= 3.0)))
    if exact_prior_overlap != 0 or on_catalogue != 0:
        raise ValueError("uniqueness-by-construction or off-catalogue guard failed")

    # --- falsification controls at the selected mass ---
    mass = int(rows.size)
    density_scores = {}
    density_supports = {}
    for sigma_m in (1_000.0, 2_000.0):
        field = h58.density_control_field(frame, shape, novel_allowed, sigma_m, pixel_size)
        dem = h56.emit_blue_noise(field, novel_allowed, n_target=mass, min_sep_px=R_PX, seed=h58.EMIT_SEED)
        density_supports[f"density-{int(sigma_m)}m"] = _support_field(dem.rows, dem.cols, shape)
        density_scores[f"density-{int(sigma_m)}m"] = h56.score_dots(
            truth, dem.rows, dem.cols
        )
        print(
            f"[{time.time()-t0:6.1f}s] control density-{int(sigma_m)}m: {density_scores[f'density-{int(sigma_m)}m']['dti']:.4f}",
            flush=True,
        )
    rand_em = h56.emit_blue_noise(
        np.ones(shape, dtype=np.float32), novel_allowed, n_target=mass, min_sep_px=R_PX, seed=99
    )
    random_support = _support_field(rand_em.rows, rand_em.cols, shape)
    random_score = h56.score_dots(truth, rand_em.rows, rand_em.cols)

    with rasterio.open(paths["incumbent"]) as ds:
        incumbent = np.isfinite(ds.read(1)) & (ds.read(1) > 0)
    incumbent &= domain
    incumbent_score = h56.score_dots(truth, *np.nonzero(incumbent))

    translations = []
    for dr, dc in ((-100, 0), (100, 0), (0, -100), (0, 100)):
        shifted = _translate_no_wrap(candidate, dr, dc, novel_allowed)
        rr, cc = np.nonzero(shifted)
        translations.append(
            {
                "row_shift_px": dr,
                "col_shift_px": dc,
                "shift_m": [dr * 100, dc * 100],
                "mass": int(shifted.sum()),
                "score": h56.score_dots(truth, rr, cc)["dti"],
            }
        )

    # --- frozen four-macrofold holdout (SGMC-off truth inside the frozen cores) ---
    split_spec = load_split_spec(paths["split"])
    blocks, split_realized = build_spatial_blocks(valid, catalogue, split_spec)
    cores = {block.block_id: _core_mask(block, shape) for block in blocks}

    def _scored(mask: np.ndarray, block_id: str) -> dict[str, Any]:
        return _components(
            mask, truth, truth_eval=truth & cores[block_id], prediction_eval=domain & cores[block_id]
        )

    folds: dict[str, Any] = {}
    for block in blocks:
        cand = _scored(candidate, block.block_id)
        inc = _scored(incumbent, block.block_id)
        dens_fold = {
            name: _scored(density_supports[name], block.block_id) for name in density_supports
        }
        best_density = max(dens_fold.values(), key=lambda d: d["credit_per_dot"])
        rng = np.random.default_rng(abs(hash(block.block_id)) % 2**31)
        flat = np.flatnonzero((domain & cores[block.block_id]).ravel())
        pick = rng.choice(flat, size=min(mass, flat.size), replace=False)
        rr, cc = np.unravel_index(pick, shape)
        uni_field = np.zeros(shape, dtype=bool)
        uni_field[rr, cc] = True
        uni = _scored(uni_field, block.block_id)
        folds[block.block_id] = {
            "candidate": cand,
            "incumbent": inc,
            "best_density": best_density,
            "uniform": uni,
            "candidate_minus_incumbent_credit_per_dot": cand["credit_per_dot"] - inc["credit_per_dot"],
            "candidate_minus_density_credit_per_dot": cand["credit_per_dot"] - best_density["credit_per_dot"],
        }
        print(
            f"[{time.time()-t0:6.1f}s]   fold {block.block_id}: cand {cand['score']:.4f}  "
            f"incumbent {inc['score']:.4f}  density {best_density['score']:.4f}  "
            f"uniform {uni['score']:.4f}",
            flush=True,
        )

    # paired 16-subtile bootstrap, candidate minus incumbent credit per dot
    subtile_rows = []
    deltas = []
    for block in blocks:
        for tile_id, tile_rows, tile_cols, _eligible, _catalogue_truth in block.subtile_masks:
            tile = np.zeros(shape, dtype=bool)
            tile[tile_rows[0] : tile_rows[1], tile_cols[0] : tile_cols[1]] = True
            cand = _components(
                candidate, truth, truth_eval=truth & tile, prediction_eval=domain & tile
            )
            inc = _components(
                incumbent, truth, truth_eval=truth & tile, prediction_eval=domain & tile
            )
            delta = cand["credit_per_dot"] - inc["credit_per_dot"]
            deltas.append(delta)
            subtile_rows.append(
                {
                    "id": tile_id,
                    "candidate_credit_per_dot": cand["credit_per_dot"],
                    "incumbent_credit_per_dot": inc["credit_per_dot"],
                    "paired_delta_credit_per_dot": delta,
                }
            )
    values = np.asarray(deltas, dtype=np.float64)
    rng = np.random.default_rng(BOOTSTRAP_SEED)
    sampled = values[rng.integers(0, values.size, size=(BOOTSTRAP_REPLICATES, values.size))].mean(axis=1)
    bootstrap = {
        "units": "sixteen frozen spatial subtiles",
        "replicates": BOOTSTRAP_REPLICATES,
        "seed": BOOTSTRAP_SEED,
        "paired_mean_credit_per_dot": float(values.mean()),
        "percentile_ci_95": [float(np.quantile(sampled, 0.025)), float(np.quantile(sampled, 0.975))],
        "subtiles": subtile_rows,
    }

    # --- pooled cross-check of the two instruments ---
    pooled = h56.score_dots(truth, rows, cols)
    pooled_masked = _components(candidate, truth)["score"]
    if abs(pooled["dti"] - pooled_masked) > 1e-6:
        raise ValueError(
            f"instrument disagreement: score_dots {pooled['dti']} vs distance_weighted_tversky {pooled_masked}"
        )

    # --- 1-pixel enrichment diagnostic (docs/research/h56-diagnosis.md section 9) ---
    truth_distance = ndimage.distance_transform_edt(~truth)
    dot_distance = truth_distance[rows, cols]
    chance_rate = float((truth_distance[domain] <= 1.0).mean())
    observed_rate = float((dot_distance <= 1.0).mean())
    enrichment_1px = {
        "observed_fraction_within_1px": observed_rate,
        "chance_fraction_within_1px": chance_rate,
        "enrichment": observed_rate / chance_rate if chance_rate else None,
        "median_dot_distance_px": float(np.median(dot_distance)),
    }

    # --- decision gates (preregistered) ---
    best_density_pooled = max(density_scores.values(), key=lambda s: s["dti"])
    incumbent_fold_wins = sum(
        1 for f in folds.values() if f["candidate_minus_incumbent_credit_per_dot"] > 0
    )
    uniform_fold_wins = sum(
        1 for f in folds.values() if f["candidate"]["score"] > f["uniform"]["score"]
    )
    gate_components = {
        "exact_requested_mass": bool(mass == int(best_n)),
        "pooled_dti_above_best_density_control": bool(pooled["dti"] > best_density_pooled["dti"]),
        "pooled_dti_above_matched_random": bool(pooled["dti"] > random_score["dti"]),
        "pooled_dti_above_all_translations": bool(
            pooled["dti"] > max(t["score"] for t in translations)
        ),
        "credit_per_dot_above_incumbent_in_at_least_3_of_4_folds": bool(incumbent_fold_wins >= 3),
        "pooled_credit_per_dot_above_incumbent": bool(
            pooled["credit_per_dot"] > incumbent_score["credit_per_dot"]
        ),
        "paired_subtile_bootstrap_lower_bound_positive": bool(bootstrap["percentile_ci_95"][0] > 0),
        "beats_uniform_in_all_four_folds": bool(uniform_fold_wins == 4),
    }
    numeric_pass = all(gate_components.values())
    scientific_components = {
        "formal_aftershock_declustering_validated": False,  # triangle test is an unverified 2-D adaptation
        "mine_injection_inventory_complete": False,  # type filter + explicit events only; no GDR CSV here
        "event_specific_uncertainty_covariance": False,  # scalar horizontalError, not a covariance
        "comcat_contributor_rights_resolved": False,  # flagged conflict: H52 review vs registry/README
    }
    overall_pass = numeric_pass and all(scientific_components.values())

    # --- write the artifacts ---
    support_hash = hashlib.sha256(np.packbits(candidate.ravel()).tobytes()).hexdigest()
    slug = support_hash[:8]
    stamp = time.strftime("%Y%m%dT%H%M%SZ", time.gmtime())
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    stem = f"gemsdoe50-h58-seislineage-{mass}-{stamp}-{slug}"
    zero_path = output_dir / f"{stem}-allfinite.tif"
    nan_path = output_dir / f"{stem}-nan.tif"
    zip_path = output_dir / f"{stem}-allfinite.zip"
    zero_meta = _write_tiff(paths["template"], zero_path, candidate, valid, zero_outside=True)
    nan_meta = _write_tiff(paths["template"], nan_path, candidate, valid, zero_outside=False)
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.write(zero_path, zero_path.name)
    zip_sha = sha256_file(zip_path)

    pairwise = {}
    for name, mask in {**density_supports, "matched-random": random_support, "H56-incumbent": incumbent}.items():
        inter = int(np.count_nonzero(candidate & mask))
        union = int(np.count_nonzero(candidate | mask))
        pairwise[name] = {
            "intersection_positive_cells": inter,
            "jaccard": inter / union if union else 1.0,
            "exact_pixel_match": bool(np.array_equal(candidate, mask)),
        }

    report: dict[str, Any] = {
        "schema": "gemsdoe50.h58-evaluation.v1",
        "project": "GEMSDOE50",
        "hypothesis": (
            "H58-S1 — ComCat epicentre point-geometry lineations as the primary field: "
            "declustered (2-D triangle-area adaptation), site-screened, 2-D covariance "
            "eigenstructure, corridors with catalogue-error half-widths, off-catalogue "
            "scoring, blue-noise emission at the metric support, cross-axis ridge snap"
        ),
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "git_commit_at_build": _git_commit(),
        "status": "UNIQUE_RESEARCH_ARTIFACT_NOT_SUBMITTED",
        "submission_status": "No DrivenData upload or weekly slot was used.",
        "input_sha256": input_hashes,
        "frozen_constants": {
            "min_mag": h58.MIN_MAG,
            "max_depth_km": h58.MAX_DEPTH_KM,
            "max_horizontal_error_km": h58.MAX_HORIZONTAL_ERROR_KM,
            "anthropogenic_buffer_m": h58.ANTHROPOGENIC_BUFFER_M,
            "triangle_quantile": h58.TRIANGLE_QUANTILE,
            "triangle_seed": h58.TRIANGLE_SEED,
            "lineation_k": h58.LINEATION_K,
            "lineation_min_events": h58.LINEATION_MIN_EVENTS,
            "lineation_min_elongation": h58.LINEATION_MIN_ELONGATION,
            "lineation_min_sigma1_m": h58.LINEATION_MIN_SIGMA1_M,
            "emit_min_sep_px": h58.EMIT_MIN_SEP_PX,
            "emit_seed": h58.EMIT_SEED,
            "masses": list(h58.MASSES),
            "selected_mass": int(best_n),
            "G_hidden_px": h58.G_HIDDEN,
            "transfer_factor": h58.TRANSFER,
        },
        "preregistration": "docs/research/h58-hypotheses-preregistered.md",
        "unverified_adaptation_notice": (
            "The 2-D triangle-area background test is an unverified project adaptation, not the "
            "published 3-D tetrahedron test of Ouillon & Sornette (2011), and the corridor width "
            "uses a scalar horizontalError, not a per-event covariance (not ACLUD)."
        ),
        "catalog_processing": cat_report,
        "belief": belief_report,
        "ridge_evidence": evidence.metadata,
        "mass_sweep": sweep,
        "placement_step": snap_info,
        "prior_pixel_exclusion": {
            "source": str(paths["prior_union"]),
            "registered_file_hashes": prior_union_artifacts,
            "union_positive_cells": prior_union_count,
            "candidate_exact_overlap_with_union": exact_prior_overlap,
            "candidate_dots_within_300m_of_catalogue": on_catalogue,
            "rule": (
                "Prior predictions are comparison-only; every prior positive pixel is excluded "
                "from final candidate placement."
            ),
        },
        "holdout": {
            "split_spec": str(paths["split"]),
            "split_spec_sha256": input_hashes["split"],
            "realization": split_realized,
            "truth": "derived SGMC fault cells more than 300 m from the supplied catalogue",
            "truth_cells": int(truth.sum()),
            "metric": "official 300 m distance-weighted Tversky proxy calculation",
            "instrument_crosscheck": {
                "score_dots_pooled": pooled["dti"],
                "distance_weighted_tversky_pooled": pooled_masked,
                "agree": True,
            },
            "pooled": {
                "candidate": pooled,
                "incumbent_H56": incumbent_score,
                "matched_random": random_score,
                "best_density_control": best_density_pooled,
                "density_controls": density_scores,
                "translations": translations,
                "enrichment_1px": enrichment_1px,
            },
            "folds": folds,
            "paired_subtile_bootstrap": bootstrap,
        },
        "decision": {
            "numeric_pass": bool(numeric_pass),
            "numeric_components": gate_components,
            "scientific_components": scientific_components,
            "pass": bool(overall_pass),
            "decision": "ELIGIBLE_FOR_REVIEW" if overall_pass else "NO_SLOT",
            "reason": (
                "A unique TIFF is an audit artifact, not a recommendation. A weekly slot is "
                "protected unless every frozen numeric and scientific/compliance gate passes."
            ),
        },
        "artifacts": {
            "stem": stem,
            "historical_allfinite_audit_only": zero_meta,
            "sample_semantics_nan_outside": nan_meta,
            "zip": {"path": str(zip_path), "bytes": zip_path.stat().st_size, "sha256": zip_sha},
            "positive_mask_sha256": support_hash,
            "portal_name_authorized": False,
            "portal_note_authorized": False,
            "range_guard": "All-finite research twin was re-read in [0,1]; format validity is not submission eligibility.",
        },
        "novelty_local_comparators": pairwise,
        "limitations": [
            "The SGMC raster is an imperfect public proxy, not hidden competition truth.",
            "The 2-D triangle-area test is an unverified adaptation, not the published 3-D tetrahedron test.",
            "The ComCat horizontalError is a scalar, not a per-event covariance; widths are prior assumptions.",
            (
                "The GDR-1391 hot-feature CSV is absent in this environment; the injection/geothermal "
                "site screen is incomplete (ComCat type filter + explicit anthropogenic buffer only)."
            ),
            (
                "Mixed-network ComCat contributor-specific rights are a flagged intra-repo conflict; "
                "no upload is permitted under the conservative reading."
            ),
            (
                "A 2-D epicentre axis can represent a dipping structure, swarm, induced sequence, or "
                "location artifact rather than a surface trace."
            ),
            (
                "Full-resolution uniqueness against every prior artifact is run separately by "
                "scripts/h58_uniqueness.py before any slot review."
            ),
        ],
    }
    report_path = Path(args.report)
    _write_json(report_path, report)
    _write_json(Path(args.holdout_out), {
        "artifact": stem,
        "sha256_allfinite": zero_meta["sha256"],
        "n_dots": mass,
        "split_spec": str(paths["split"]),
        "split_spec_sha256": input_hashes["split"],
        "truth": "SGMC off-catalogue proxy inside the frozen macrofold cores",
        "folds": folds,
        "pooled": report["holdout"]["pooled"],
        "paired_subtile_bootstrap": bootstrap,
        "instrument_crosscheck": report["holdout"]["instrument_crosscheck"],
    })
    print(f"[{time.time()-t0:6.1f}s] H58 report: {report_path}", flush=True)
    print(f"[{time.time()-t0:6.1f}s] recommended TIFF: {zero_path}", flush=True)
    print(f"[{time.time()-t0:6.1f}s] pooled proxy DTI: {pooled['dti']:.6f} "
          f"(incumbent {incumbent_score['dti']:.6f}, density {best_density_pooled['dti']:.6f}, "
          f"random {random_score['dti']:.6f})", flush=True)
    print(f"[{time.time()-t0:6.1f}s] frozen decision: {report['decision']['decision']}", flush=True)
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--comcat", default="data/external/usgs_comcat_earthquakes.csv.gz")
    parser.add_argument("--template", default="data/grid/sample_submission.tif")
    parser.add_argument("--labels", default="data/grid/labels.tif")
    parser.add_argument("--sgmc", default="data/external/derived_sgmc_faults_100m_u8.tif")
    parser.add_argument("--lidar", default=".arena/inputs/lidar_scarp_features_u8.tif")
    parser.add_argument("--radiometric", default=".arena/inputs/geodawn_rad_u8.tif")
    parser.add_argument("--hot-points", default="data/external/gdr_wellspring_in_footprint.csv")
    parser.add_argument("--incumbent", default="docs/downloads/gemsdoe50-h56-scarpdisperse-90000-allfinite.tif")
    parser.add_argument("--split", default="evidence/holdout-v1.json")
    parser.add_argument("--prior-union", default="registry/prior_positive_union.npz")
    parser.add_argument("--sequence-thin", action="store_true",
                        help="sensitivity only: additionally apply 250 m / 90-day largest-magnitude "
                             "sequence thinning before the triangle test")
    parser.add_argument("--output-dir", default="docs/downloads")
    parser.add_argument("--report", default="evidence/h58_build.json")
    parser.add_argument("--holdout-out", default="evidence/h58_holdout.json")
    args = parser.parse_args()
    run(args)


if __name__ == "__main__":
    main()
