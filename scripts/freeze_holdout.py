#!/usr/bin/env python3
"""Materialize and hash the registered holdout masks before any DTI is computed."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from gemsdoe50.common import jsonable, sha256_file
from gemsdoe50.holdout import build_spatial_blocks, load_split_spec
from gemsdoe50.raster import load_labels, load_template


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--template", required=True)
    parser.add_argument("--labels", required=True)
    parser.add_argument("--split", default="evidence/holdout-v1.json")
    parser.add_argument("--output", default="evidence/holdout-realized-v1.json")
    args = parser.parse_args()

    spec = load_split_spec(args.split)
    expected_template = spec["grid"]["template_sha256"]
    expected_labels = spec["grid"]["official_label_raster_sha256"]
    actual_template = sha256_file(args.template)
    actual_labels = sha256_file(args.labels)
    if actual_template != expected_template:
        raise SystemExit(f"template SHA-256 mismatch: {actual_template}")
    if actual_labels != expected_labels:
        raise SystemExit(f"label SHA-256 mismatch: {actual_labels}")

    _, valid, _ = load_template(args.template)
    truth, label_metadata = load_labels(args.labels, args.template, valid)
    blocks, realized = build_spatial_blocks(valid, truth, spec)
    realized.update(
        {
            "status": "FROZEN_MASKS_BEFORE_ANY_DTI",
            "dti_computed": False,
            "split_spec_sha256": sha256_file(args.split),
            "template_raster_sha256": actual_template,
            "label_raster_sha256": actual_labels,
            "label_metadata": label_metadata,
            "mask_pixel_size_m": float(spec["grid"]["pixel_size_m"]),
            "erode_heldout_core_pixels": int(spec["rules"]["heldout_core_erode_pixels"]),
            "buffer_visible_labels_pixels": int(
                spec["rules"]["visible_training_label_buffer_pixels"]
            ),
            "mass_budget": int(spec["rules"]["prediction_mass_total"]),
            "macrofold_count": len(blocks),
        }
    )
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(jsonable(realized), indent=2, sort_keys=True, allow_nan=False) + "\n",
        encoding="utf-8",
    )
    print(f"Wrote frozen holdout masks: {output}")
    print(f"SHA-256: {sha256_file(output)}")
    print(f"Eligible cells: {sum(block.metadata['eligible_cells'] for block in blocks)}")
    print(f"Held-out label cells: {sum(block.metadata['truth_cells'] for block in blocks)}")


if __name__ == "__main__":
    main()
