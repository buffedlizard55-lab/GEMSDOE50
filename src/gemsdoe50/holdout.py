from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
from scipy.ndimage import distance_transform_edt

from .common import sha256_array


@dataclass(frozen=True)
class SpatialBlock:
    block_id: str
    rows: tuple[int, int]
    cols: tuple[int, int]
    eligible: np.ndarray
    truth: np.ndarray
    subtile_masks: tuple[tuple[str, tuple[int, int], tuple[int, int], np.ndarray, np.ndarray], ...]
    metadata: dict[str, Any]


def load_split_spec(path: str | Path) -> dict[str, Any]:
    spec = json.loads(Path(path).read_text(encoding="utf-8"))
    if spec.get("schema") != "gemsdoe50.spatial-holdout.v1":
        raise ValueError(f"unknown holdout schema: {spec.get('schema')!r}")
    return spec


def build_spatial_blocks(
    valid_mask: np.ndarray,
    truth_mask: np.ndarray,
    split_spec: dict[str, Any],
) -> tuple[list[SpatialBlock], dict[str, Any]]:
    """Deterministically reconstruct the frozen four macrofold holdout."""
    valid_mask = np.asarray(valid_mask, dtype=bool)
    truth_mask = np.asarray(truth_mask, dtype=bool)
    if valid_mask.shape != truth_mask.shape:
        raise ValueError("valid and truth mask shape mismatch")
    grid = split_spec["grid"]
    if [valid_mask.shape[1], valid_mask.shape[0]] != [grid["width"], grid["height"]]:
        raise ValueError("valid mask shape differs from the frozen split grid")
    if sha256_array(valid_mask.astype(np.uint8)) != grid["valid_mask_sha256"]:
        raise ValueError("valid-mask hash does not match the frozen split specification")

    erosion = int(split_spec["rules"]["heldout_core_erode_pixels"])
    buffer_px = int(split_spec["rules"]["visible_training_label_buffer_pixels"])
    pixel_m = float(grid["pixel_size_m"])
    blocks: list[SpatialBlock] = []
    block_records: list[dict[str, Any]] = []
    height, width = valid_mask.shape
    for fold in split_spec["macrofolds"]:
        r0, r1 = map(int, fold["rows"])
        c0, c1 = map(int, fold["cols"])
        if not (0 <= r0 < r1 <= height and 0 <= c0 < c1 <= width):
            raise ValueError(f"invalid macrofold bounds for {fold['id']}")
        fold_mask = np.zeros(valid_mask.shape, dtype=bool)
        fold_mask[r0:r1, c0:c1] = True
        core = np.zeros(valid_mask.shape, dtype=bool)
        core[r0 + erosion : r1 - erosion, c0 + erosion : c1 - erosion] = True
        core &= valid_mask
        truth_core = truth_mask & core

        visible_truth = truth_mask & ~fold_mask
        if np.any(visible_truth):
            distance_to_visible_m = distance_transform_edt(
                ~visible_truth, sampling=(pixel_m, pixel_m)
            )
            visible_buffer = distance_to_visible_m <= buffer_px * pixel_m
            del distance_to_visible_m
        else:
            visible_buffer = np.zeros(valid_mask.shape, dtype=bool)
        eligible = core & ~visible_buffer
        subtile_rows = list(map(int, fold["subtile_row_bounds"]))
        subtile_cols = list(map(int, fold["subtile_col_bounds"]))
        subtile_masks: list[
            tuple[str, tuple[int, int], tuple[int, int], np.ndarray, np.ndarray]
        ] = []
        subtile_area_records: list[dict[str, Any]] = []
        for ri in range(len(subtile_rows) - 1):
            for ci in range(len(subtile_cols) - 1):
                sr0, sr1 = subtile_rows[ri], subtile_rows[ri + 1]
                sc0, sc1 = subtile_cols[ci], subtile_cols[ci + 1]
                tile = np.zeros(valid_mask.shape, dtype=bool)
                tile[sr0:sr1, sc0:sc1] = True
                tile_eligible = eligible & tile
                tile_truth = truth_core & tile
                tile_id = f"{fold['id']}-{ri}{ci}"
                subtile_masks.append((tile_id, (sr0, sr1), (sc0, sc1), tile_eligible, tile_truth))
                subtile_area_records.append(
                    {
                        "id": tile_id,
                        "rows": [sr0, sr1],
                        "cols": [sc0, sc1],
                        "eligible_cells": int(np.count_nonzero(tile_eligible)),
                        "truth_cells": int(np.count_nonzero(tile_truth)),
                        "eligible_mask_sha256": sha256_array(tile_eligible.astype(np.uint8)),
                        "truth_mask_sha256": sha256_array(tile_truth.astype(np.uint8)),
                    }
                )
        meta = {
            "id": fold["id"],
            "rows": [r0, r1],
            "cols": [c0, c1],
            "core_bounds": [r0 + erosion, r1 - erosion, c0 + erosion, c1 - erosion],
            "visible_training_label_buffer_pixels": buffer_px,
            "visible_training_label_buffer_m": buffer_px * pixel_m,
            "eligible_cells": int(np.count_nonzero(eligible)),
            "truth_cells": int(np.count_nonzero(truth_core)),
            "eligible_mask_sha256": sha256_array(eligible.astype(np.uint8)),
            "truth_mask_sha256": sha256_array(truth_core.astype(np.uint8)),
            "subtiles": subtile_area_records,
        }
        block_records.append(meta)
        blocks.append(
            SpatialBlock(
                block_id=str(fold["id"]),
                rows=(r0, r1),
                cols=(c0, c1),
                eligible=eligible,
                truth=truth_core,
                subtile_masks=tuple(subtile_masks),
                metadata=meta,
            )
        )

    realized = {
        "valid_mask_sha256": sha256_array(valid_mask.astype(np.uint8)),
        "truth_raster_mask_sha256": sha256_array(truth_mask.astype(np.uint8)),
        "shape": [int(height), int(width)],
        "macrofolds": block_records,
    }
    return blocks, realized
