#!/usr/bin/env python3
"""Baseline-only audit for the frozen H53-A spatial-holdout protocol.

This command must run and write its report before `h53_build.py` or `h53_validate.py` are
used. It contains no H53 candidate/control code and never reads the hidden competition labels.
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import rasterio
from scipy.ndimage import binary_dilation, distance_transform_edt

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "src"))

from gemsdoe50.common import sha256_file
from gemsdoe50.holdout import build_spatial_blocks, load_split_spec
from gemsdoe50.metric import distance_weighted_tversky
from gems51 import grid as g

SPEC = REPO / "evidence" / "holdout-v1.json"
SGMC_PATH = REPO / "data" / "external" / "derived_sgmc_faults_100m_u8.tif"
EXPECTED = {
    "H51-A scarp-radiometric": {
        "path": REPO / "docs/downloads/gems51-scarpradio-offcat-35000-20261006-ecf058ea-nan.tif",
        "sha256": "8f8708d2872b66d71925707e0aede23eebcf217dfd2e57d6e61186f32e686f5d",
    },
    "H50 prior seismicity": {
        "path": REPO / "docs/downloads/gems50-seislin-44709-20261006T2041Z-79e260ae.tif",
        "sha256": "79e260ae223d7dfd96413da28a9c6fed30107285ab843795181a5c9e5dff7262",
    },
    "H51 corridor consensus": {
        "path": REPO / "docs/downloads/gemsdoe50-h51-corridor-consensus-mix-20261007T0200Z.tif",
        "sha256": "a26055834f8e6cc57cc33e96a4a5a26a1adeaafbeec490135af84c6ccd4d1da0",
    },
    "GEMSDOE32 H33-2-B2 (comparison only)": {
        "path": REPO / ".arena/review/gemsdoe32-h33-h33-2-b2-nan.tif",
        "sha256": "baeae3219bba6a19bc8cfe79224e28555c50184b7c1ca65c2a822f54807c77dd",
    },
}


def _read_support(path: Path, template: rasterio.DatasetReader) -> tuple[np.ndarray, dict]:
    with rasterio.open(path) as ds:
        if (ds.width, ds.height) != (template.width, template.height):
            raise ValueError(f"{path}: shape differs from official grid")
        if ds.crs != template.crs or not ds.transform.almost_equals(template.transform):
            raise ValueError(f"{path}: CRS/transform differs from official grid")
        values = ds.read(1)
        finite = np.isfinite(values)
        nonbinary = int(np.count_nonzero(finite & (values != 0) & (values != 1)))
        support = finite & (values > 0)
        return support, {
            "path": str(path.relative_to(REPO)) if path.is_relative_to(REPO) else str(path),
            "dtype": ds.dtypes[0],
            "nodata": ds.nodata,
            "positive_cells": int(support.sum()),
            "nonbinary_finite_cells": nonbinary,
        }


def _clean_json(value):
    if isinstance(value, dict):
        return {str(key): _clean_json(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_clean_json(item) for item in value]
    if isinstance(value, np.ndarray):
        return _clean_json(value.tolist())
    if isinstance(value, np.generic):
        return _clean_json(value.item())
    if isinstance(value, float) and not np.isfinite(value):
        return None
    return value


def _score(truth: np.ndarray, prediction: np.ndarray, evaluation: np.ndarray) -> dict:
    """Score an evaluation block with an exact three-pixel context halo."""
    halo_structure = np.zeros((7, 7), dtype=bool)
    yy, xx = np.ogrid[-3:4, -3:4]
    halo_structure[(yy * yy + xx * xx) <= 9] = True
    context = binary_dilation(evaluation, structure=halo_structure)
    truth_context = truth & context
    prediction_context = prediction & context
    result = distance_weighted_tversky(
        truth_context,
        prediction_context.astype(np.float32),
        truth_eval_mask=evaluation,
        prediction_eval_mask=evaluation,
        pixel_size_m=100.0,
        radius_m=300.0,
        alpha=0.2,
        beta=0.8,
    )
    return result.as_dict()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=REPO / "evidence/h53-baseline-20261007.json")
    args = parser.parse_args()

    if not SPEC.is_file() or not SGMC_PATH.is_file():
        raise FileNotFoundError("frozen holdout spec or pinned SGMC proxy raster is missing")
    with rasterio.open(REPO / "data/grid/sample_submission.tif") as template:
        valid = np.isfinite(template.read(1))
        labels, _ = g.load_raster(REPO / "data/grid/labels.tif")
        labels = labels == 1
        spec = load_split_spec(SPEC)
        blocks, realized = build_spatial_blocks(valid, labels, spec)
        if realized["valid_mask_sha256"] != spec["grid"]["valid_mask_sha256"]:
            raise ValueError("sample-grid valid mask differs from the registered holdout")
        sgmc, _ = g.load_raster(SGMC_PATH)
        catalogue_distance = distance_transform_edt(~labels, sampling=(100.0, 100.0))
        off_catalogue = (catalogue_distance > 300.0) & valid
        truth = (sgmc > 0) & off_catalogue

        cores: dict[str, np.ndarray] = {}
        for block in blocks:
            r0, r1, c0, c1 = map(int, block.metadata["core_bounds"])
            core = np.zeros(valid.shape, dtype=bool)
            core[r0:r1, c0:c1] = True
            core &= valid
            cores[str(block.metadata["id"])] = core
        union_core = np.logical_or.reduce(list(cores.values()))

        baselines: dict[str, dict] = {}
        supports: dict[str, np.ndarray] = {}
        for name, item in EXPECTED.items():
            path = Path(item["path"])
            if not path.is_file():
                raise FileNotFoundError(f"registered baseline missing: {path}")
            digest = sha256_file(path)
            if digest != item["sha256"]:
                raise ValueError(f"registered baseline hash mismatch for {name}: {digest}")
            support, raster_info = _read_support(path, template)
            supports[name] = support
            folds = {}
            for fold_id, mask in cores.items():
                folds[fold_id] = _score(truth, support, mask)
            pooled = _score(truth, support, union_core)
            baselines[name] = {
                "sha256": digest,
                "raster": raster_info,
                "native_positive_cells_total": int(support.sum()),
                "positive_cells_in_valid_footprint": int((support & valid).sum()),
                "positive_cells_within_300m_catalogue_buffer": int((support & valid & ~off_catalogue).sum()),
                "folds": folds,
                "pooled_union_of_cores": pooled,
                "matched_mass_by_fold": {
                    fold_id: int((support & mask).sum())
                    for fold_id, mask in cores.items()
                },
                "offcatalogue_positive_cells_by_fold": {
                    fold_id: int((support & mask & off_catalogue).sum())
                    for fold_id, mask in cores.items()
                },
            }

    # Fixed deterministic tie-break, independent of any H53 candidate result.
    incumbent = sorted(
        baselines,
        key=lambda name: (-baselines[name]["pooled_union_of_cores"]["score"], name),
    )[0]
    report = {
        "schema": "gemsdoe50.h53-baseline-audit.v1",
        "status": "BASELINE_FROZEN_AWAITING_H53",
        "built_utc": datetime.now(timezone.utc).isoformat(),
        "purpose": "Candidate-independent ranking of the preregistered incumbent set; no H53 DTI computed.",
        "frozen_split": {
            "spec_path": str(SPEC.relative_to(REPO)),
            "spec_sha256": sha256_file(SPEC),
            "template_sha256": spec["grid"]["template_sha256"],
            "valid_mask_sha256": realized["valid_mask_sha256"],
            "catalogue_label_sha256": spec["grid"]["official_label_raster_sha256"],
            "fold_cores": {key: [int(v) for v in next(b.metadata["core_bounds"] for b in blocks
                                                       if b.metadata["id"] == key)]
                           for key in cores},
            "subtile_ids": [tile[0] for block in blocks for tile in block.subtile_masks],
        },
        "proxy_truth": {
            "path": str(SGMC_PATH.relative_to(REPO)),
            "sha256": sha256_file(SGMC_PATH),
            "definition": "SGMC positive cells >300 m from the provided catalogue; proxy only, not hidden truth.",
            "truth_cells_total": int(truth.sum()),
        },
        "metric": {"name": "official distance-weighted Tversky", "alpha": 0.2, "beta": 0.8,
                   "radius_m": 300.0, "block_context_halo_px": 3},
        "registered_baselines": baselines,
        "incumbent": {
            "name": incumbent,
            "sha256": baselines[incumbent]["sha256"],
            "pooled_dti": baselines[incumbent]["pooled_union_of_cores"]["score"],
            "full_grid_positive_cells": baselines[incumbent]["native_positive_cells_total"],
            "matched_mass_by_fold": baselines[incumbent]["matched_mass_by_fold"],
        },
        "note": "No candidate features, H53 maps, hidden labels, or leaderboard values were read.",
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(_clean_json(report), indent=2, allow_nan=False) + "\n", encoding="utf-8")
    print(json.dumps({"incumbent": incumbent,
                      "pooled_dti": report["incumbent"]["pooled_dti"],
                      "matched_mass_by_fold": report["incumbent"]["matched_mass_by_fold"],
                      "output": str(args.output)}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
