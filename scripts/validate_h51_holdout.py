#!/usr/bin/env python3
"""Validate the H51 candidate on the repository's frozen *spatial* holdout, blocked.

Two questions are answered here, and they are different:

1. **The frozen harness's own question.** ``evidence/holdout-v1.json`` scores a held-out
   spatial core against the *provided catalogue* labels, because that is the only label set
   the repository holds. H51 deliberately emits everything more than 300 m away from those
   labels, so this harness must return ~0 for H51. Reporting it is the honest way to show
   that the frozen harness cannot rank H51 — it measures the opposite of H51's objective.
2. **The goal-aligned, spatially blocked question.** Using the same frozen fold geometry and
   the same 16 subtiles, does H51's advantage over a matched-mass random control on the
   off-catalogue instrument hold *inside every block*, or only in one region?

Output: ``evidence/holdout_h51.json``.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
from scipy.ndimage import distance_transform_edt

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "src"))

from gems51 import emit, instruments
from gems51 import grid as g51
from gemsdoe50 import common, holdout

SGMC = REPO / "data" / "external" / "derived_sgmc_faults_100m_u8.tif"
SPEC = REPO / "evidence" / "holdout-v1.json"
BUILD = REPO / "evidence" / "build_h51.json"
BOOTSTRAP = 5000


def core_mask(block, shape: tuple[int, int]) -> np.ndarray:
    r0, r1, c0, c1 = block.metadata["core_bounds"]
    mask = np.zeros(shape, dtype=bool)
    mask[r0:r1, c0:c1] = True
    return mask


def main() -> int:
    build = json.loads(BUILD.read_text(encoding="utf-8"))
    import rasterio

    with rasterio.open(REPO / build["outputs"]["primary"]["path"]) as ds:
        values = ds.read(1)
    support = np.isfinite(values) & (values > 0)

    valid = g51.load_footprint()
    labels = g51.load_labels()
    spec = holdout.load_split_spec(SPEC)
    blocks, area_report = holdout.build_spatial_blocks(valid, labels, spec)
    catalogue_distance = distance_transform_edt(~labels)
    off_catalogue = (catalogue_distance > 3) & valid
    sgmc, _ = g51.load_raster(SGMC)
    sgmc_off = (sgmc > 0) & off_catalogue
    rng = np.random.default_rng(5106)

    folds = []
    mass_total = 0
    for block in blocks:
        core = core_mask(block, valid.shape)
        mass_here = int(np.count_nonzero(support & core))
        mass_total += mass_here
        fold_sgmc = sgmc_off & core
        candidate = instruments.score(support, fold_sgmc, mass=max(mass_here, 1))
        control, _ = emit.pack(
            np.where(off_catalogue & core, rng.random(valid.shape).astype(np.float32), 0.0),
            mass_here, valid=off_catalogue & core, suppression_px=3.0)
        control_score = instruments.score(control, fold_sgmc, mass=max(mass_here, 1))
        catalogue_in_core = block.truth
        folds.append({
            "id": block.metadata["id"],
            "core_bounds": block.metadata["core_bounds"],
            "candidate_dots_in_core": mass_here,
            "frozen_harness_truth": "provided catalogue labels inside the eroded core",
            "frozen_harness_candidate_dti": instruments.score(
                support, catalogue_in_core, mass=max(mass_here, 1))["dti"],
            "offcatalogue_truth_cells_in_core": int(np.count_nonzero(fold_sgmc)),
            "candidate_credit_per_dot": candidate["credit_per_dot"],
            "random_control_credit_per_dot": control_score["credit_per_dot"],
            "candidate_minus_control": candidate["credit_per_dot"] - control_score["credit_per_dot"],
        })
        print(f"fold {block.metadata['id']}: dots={mass_here:,} "
              f"cand={candidate['credit_per_dot']:.4f} ctrl={control_score['credit_per_dot']:.4f} "
              f"delta={folds[-1]['candidate_minus_control']:+.4f}", flush=True)
    # Per-subtile paired deltas on the off-catalogue instrument (matched mass inside the tile).
    deltas, tile_rows = [], []
    for block in blocks:
        for tile_id, rows, cols, _eligible, _truth in block.subtile_masks:
            tile = np.zeros(valid.shape, dtype=bool)
            tile[rows[0]:rows[1], cols[0]:cols[1]] = True
            tile_sgmc = sgmc_off & tile
            mass_here = int(np.count_nonzero(support & tile))
            if not np.any(tile_sgmc) or mass_here == 0:
                continue
            candidate = instruments.score(support, tile_sgmc, mass=mass_here)
            control, _ = emit.pack(
                np.where(off_catalogue & tile, rng.random(valid.shape).astype(np.float32), 0.0),
                mass_here, valid=off_catalogue & tile, suppression_px=3.0)
            control_score = instruments.score(control, tile_sgmc, mass=mass_here)
            deltas.append(candidate["credit_per_dot"] - control_score["credit_per_dot"])
            tile_rows.append({"id": tile_id, "dots": mass_here,
                              "candidate_credit_per_dot": candidate["credit_per_dot"],
                              "control_credit_per_dot": control_score["credit_per_dot"]})
    deltas = np.asarray(deltas, dtype=float)
    if deltas.size:
        draws = rng.integers(0, deltas.size, size=(BOOTSTRAP, deltas.size))
        means = deltas[draws].mean(axis=1)
        ci = [float(np.quantile(means, 0.025)), float(np.quantile(means, 0.975))]
    else:
        ci = [0.0, 0.0]

    pooled_sgmc = sgmc_off.copy()
    pooled_candidate = instruments.score(support, pooled_sgmc, mass=max(mass_total, 1))
    control, _ = emit.pack(
        np.where(off_catalogue, rng.random(valid.shape).astype(np.float32), 0.0),
        mass_total, valid=off_catalogue, suppression_px=3.0)
    pooled_control = instruments.score(control, pooled_sgmc, mass=max(mass_total, 1))

    report = {
        "schema": "gems51.holdout-validation.v1",
        "built_utc": common.utc_now() if hasattr(common, "utc_now") else build["built_utc"],
        "candidate": build["name"],
        "candidate_sha256": build["outputs"]["primary"]["sha256"],
        "frozen_split": {
            "spec": "evidence/holdout-v1.json",
            "split_sha256": common.sha256_file(SPEC),
            "macrofolds": [b.metadata["id"] for b in blocks],
            "subtiles": int(area_report.get("subtile_count", len(tile_rows))) if isinstance(area_report, dict) else len(tile_rows),
            "rules": spec["rules"],
        },
        "folds": folds,
        "pooled_offcatalogue": {
            "candidate": pooled_candidate,
            "random_control": pooled_control,
            "mass": mass_total,
        },
        "subtile_bootstrap": {
            "units": len(tile_rows),
            "paired_delta_mean": float(deltas.mean()) if deltas.size else 0.0,
            "percentile_ci_95": ci,
            "lower_bound_above_zero": bool(deltas.size and ci[0] > 0.0),
            "table": tile_rows,
        },
        "folds_positive": int(sum(1 for f in folds if f["candidate_minus_control"] > 0)),
        "folds_total": len(folds),
        "honest_note": (
            "The frozen H50-S1 harness scores held-out cores against the provided catalogue "
            "labels. H51 emits nothing within 300 m of those labels by design, so its "
            "frozen-harness DTI is ~0 by construction; that is a property of the harness's "
            "truth choice, not evidence about H51. The goal-aligned blocked test is the "
            "off-catalogue instrument below, where every fold must beat its matched random "
            "control for the candidate to be considered spatially stable."
        ),
    }
    out = REPO / "evidence" / "holdout_h51.json"
    out.write_text(json.dumps(report, indent=1), encoding="utf-8")
    print(json.dumps({"folds_positive": report["folds_positive"],
                      "folds_total": report["folds_total"],
                      "subtile_delta_mean": report["subtile_bootstrap"]["paired_delta_mean"],
                      "subtile_ci95": ci,
                      "pooled_candidate_cpdot": pooled_candidate["credit_per_dot"],
                      "pooled_control_cpdot": pooled_control["credit_per_dot"]}, indent=1))
    print(f"wrote {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
