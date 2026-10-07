#!/usr/bin/env python3
"""Validate H52 (H51 union H52-A) on the frozen spatial holdout, against H51 directly.

This is the gate named in ``docs/h52a-protocol.md``: H52 may be recommended for a submission
slot only if it beats the frozen H51 incumbent, fold by fold, on the off-catalogue instrument,
not only in the pooled number already reported in ``evidence/build_h52.json``.

Output: ``evidence/holdout_h52.json``.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import rasterio
from scipy.ndimage import distance_transform_edt

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "src"))

from gems51 import emit, instruments
from gems51 import grid as g51
from gemsdoe50 import common, holdout

SGMC = REPO / "data" / "external" / "derived_sgmc_faults_100m_u8.tif"
SPEC = REPO / "evidence" / "holdout-v1.json"
BUILD = REPO / "evidence" / "build_h52.json"
BOOTSTRAP = 5000


def core_mask(block, shape: tuple[int, int]) -> np.ndarray:
    r0, r1, c0, c1 = block.metadata["core_bounds"]
    mask = np.zeros(shape, dtype=bool)
    mask[r0:r1, c0:c1] = True
    return mask


def main() -> int:
    build = json.loads(BUILD.read_text(encoding="utf-8"))

    with rasterio.open(REPO / build["outputs"]["primary"]["path"]) as ds:
        values = ds.read(1)
    support = np.isfinite(values) & (values > 0)

    with rasterio.open(REPO / build["inputs"]["h51_file"]["path"]) as ds:
        h51 = ds.read(1)
    h51_support = np.isfinite(h51) & (h51 > 0)

    valid = g51.load_footprint()
    labels = g51.load_labels()
    spec = holdout.load_split_spec(SPEC)
    blocks, _area_report = holdout.build_spatial_blocks(valid, labels, spec)
    catalogue_distance = distance_transform_edt(~labels)
    off_catalogue = (catalogue_distance > 3) & valid
    sgmc, _ = g51.load_raster(SGMC)
    sgmc_off = (sgmc > 0) & off_catalogue
    rng = np.random.default_rng(5208)

    folds = []
    for block in blocks:
        core = core_mask(block, valid.shape)
        fold_sgmc = sgmc_off & core
        mass_h52 = int(np.count_nonzero(support & core))
        mass_h51 = int(np.count_nonzero(h51_support & core))
        h52_score = instruments.score(support, fold_sgmc, mass=max(mass_h52, 1))
        h51_score = instruments.score(h51_support, fold_sgmc, mass=max(mass_h51, 1))
        control, _ = emit.pack(
            np.where(off_catalogue & core, rng.random(valid.shape).astype(np.float32), 0.0),
            mass_h52, valid=off_catalogue & core, suppression_px=3.0)
        control_score = instruments.score(control, fold_sgmc, mass=max(mass_h52, 1))
        folds.append({
            "id": block.metadata["id"],
            "core_bounds": block.metadata["core_bounds"],
            "h52_dots_in_core": mass_h52,
            "h51_dots_in_core": mass_h51,
            "offcatalogue_truth_cells_in_core": int(np.count_nonzero(fold_sgmc)),
            "h52_credit_per_dot": h52_score["credit_per_dot"],
            "h51_credit_per_dot": h51_score["credit_per_dot"],
            "h52_dti": h52_score["dti"],
            "h51_dti": h51_score["dti"],
            "random_control_credit_per_dot": control_score["credit_per_dot"],
            "h52_minus_h51_credit_per_dot": h52_score["credit_per_dot"] - h51_score["credit_per_dot"],
            "h52_minus_h51_dti": h52_score["dti"] - h51_score["dti"],
            "h52_minus_control_credit_per_dot": h52_score["credit_per_dot"] - control_score["credit_per_dot"],
        })
        print(f"fold {block.metadata['id']}: h52_dti={h52_score['dti']:.4f} "
              f"h51_dti={h51_score['dti']:.4f} delta={folds[-1]['h52_minus_h51_dti']:+.4f} "
              f"ctrl_cpdot={control_score['credit_per_dot']:.4f}", flush=True)

    # Per-subtile paired deltas (H52 vs H51) for a block-bootstrap confidence interval.
    deltas_vs_h51, deltas_vs_control, tile_rows = [], [], []
    for block in blocks:
        for tile_id, rows, cols, _eligible, _truth in block.subtile_masks:
            tile = np.zeros(valid.shape, dtype=bool)
            tile[rows[0]:rows[1], cols[0]:cols[1]] = True
            tile_sgmc = sgmc_off & tile
            mass_h52 = int(np.count_nonzero(support & tile))
            mass_h51 = int(np.count_nonzero(h51_support & tile))
            if not np.any(tile_sgmc) or mass_h52 == 0:
                continue
            h52_score = instruments.score(support, tile_sgmc, mass=mass_h52)
            h51_score = instruments.score(h51_support, tile_sgmc, mass=max(mass_h51, 1))
            control, _ = emit.pack(
                np.where(off_catalogue & tile, rng.random(valid.shape).astype(np.float32), 0.0),
                mass_h52, valid=off_catalogue & tile, suppression_px=3.0)
            control_score = instruments.score(control, tile_sgmc, mass=mass_h52)
            deltas_vs_h51.append(h52_score["credit_per_dot"] - h51_score["credit_per_dot"])
            deltas_vs_control.append(h52_score["credit_per_dot"] - control_score["credit_per_dot"])
            tile_rows.append({"id": tile_id, "h52_dots": mass_h52, "h51_dots": mass_h51,
                              "h52_credit_per_dot": h52_score["credit_per_dot"],
                              "h51_credit_per_dot": h51_score["credit_per_dot"],
                              "control_credit_per_dot": control_score["credit_per_dot"]})
    deltas_vs_h51 = np.asarray(deltas_vs_h51, dtype=float)
    deltas_vs_control = np.asarray(deltas_vs_control, dtype=float)

    def bootstrap_ci(deltas: np.ndarray) -> list[float]:
        if deltas.size == 0:
            return [0.0, 0.0]
        draws = rng.integers(0, deltas.size, size=(BOOTSTRAP, deltas.size))
        means = deltas[draws].mean(axis=1)
        return [float(np.quantile(means, 0.025)), float(np.quantile(means, 0.975))]

    ci_h51 = bootstrap_ci(deltas_vs_h51)
    ci_control = bootstrap_ci(deltas_vs_control)

    pooled_mass = int(support.sum())
    pooled_h52 = instruments.score(support, sgmc_off, mass=pooled_mass)
    pooled_h51 = instruments.score(h51_support, sgmc_off, mass=int(h51_support.sum()))
    control, _ = emit.pack(np.where(off_catalogue, rng.random(valid.shape).astype(np.float32), 0.0),
                           pooled_mass, valid=off_catalogue, suppression_px=3.0)
    pooled_control = instruments.score(control, sgmc_off, mass=pooled_mass)

    folds_h52_beats_h51 = int(sum(1 for f in folds if f["h52_minus_h51_dti"] > 0))
    folds_h52_beats_control = int(sum(1 for f in folds if f["h52_minus_control_credit_per_dot"] > 0))

    report = {
        "schema": "gems52.holdout-validation.v1",
        "built_utc": common.utc_now() if hasattr(common, "utc_now") else build["built_utc"],
        "candidate": build["name"],
        "candidate_sha256": build["outputs"]["primary"]["sha256"],
        "incumbent": build["inputs"]["h51_file"]["path"],
        "incumbent_sha256": build["inputs"]["h51_file"]["sha256"],
        "frozen_split": {
            "spec": "evidence/holdout-v1.json",
            "split_sha256": common.sha256_file(SPEC),
            "macrofolds": [b.metadata["id"] for b in blocks],
            "subtiles": len(tile_rows),
            "rules": spec["rules"],
        },
        "folds": folds,
        "folds_h52_beats_h51_on_dti": folds_h52_beats_h51,
        "folds_h52_beats_random_control": folds_h52_beats_control,
        "folds_total": len(folds),
        "pooled_offcatalogue": {
            "h52": pooled_h52, "h51": pooled_h51, "random_control": pooled_control,
            "h52_mass": pooled_mass, "h51_mass": int(h51_support.sum()),
        },
        "subtile_bootstrap_vs_h51": {
            "units": len(tile_rows),
            "paired_delta_mean": float(deltas_vs_h51.mean()) if deltas_vs_h51.size else 0.0,
            "percentile_ci_95": ci_h51,
            "lower_bound_above_zero": bool(deltas_vs_h51.size and ci_h51[0] > 0.0),
        },
        "subtile_bootstrap_vs_control": {
            "units": len(tile_rows),
            "paired_delta_mean": float(deltas_vs_control.mean()) if deltas_vs_control.size else 0.0,
            "percentile_ci_95": ci_control,
            "lower_bound_above_zero": bool(deltas_vs_control.size and ci_control[0] > 0.0),
        },
        "gate": {
            "rule": "docs/h52a-protocol.md promotion gate: pooled SGMC-off credit-per-dot beats "
                    "H51's; >=3/4 macrofolds positive vs a matched random control; uniqueness "
                    "passes; byte-valid",
            "pooled_beats_h51": bool(pooled_h52["credit_per_dot"] > pooled_h51["credit_per_dot"]),
            "folds_beats_h51_at_least_3_of_4": bool(folds_h52_beats_h51 >= 3),
            "folds_beats_control_at_least_3_of_4": bool(folds_h52_beats_control >= 3),
        },
        "honest_note": (
            "The frozen harness scores held-out cores against the provided catalogue labels. H52 "
            "emits nothing within 300 m of those labels by design, so this is scored on the "
            "off-catalogue SGMC instrument, not on the frozen harness's own (catalogue) truth, "
            "exactly as H51 was. This is a local proxy, never an organizer score."
        ),
    }
    out = REPO / "evidence" / "holdout_h52.json"
    out.write_text(json.dumps(report, indent=1), encoding="utf-8")
    print(json.dumps({"folds_h52_beats_h51": folds_h52_beats_h51,
                      "folds_h52_beats_control": folds_h52_beats_control,
                      "folds_total": report["folds_total"],
                      "pooled_beats_h51": report["gate"]["pooled_beats_h51"],
                      "subtile_delta_vs_h51_mean": report["subtile_bootstrap_vs_h51"]["paired_delta_mean"],
                      "subtile_ci95_vs_h51": ci_h51}, indent=1))
    print(f"wrote {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
