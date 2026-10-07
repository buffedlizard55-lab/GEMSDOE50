"""Measure the *delivered* H59 revision-2 raster on the frozen frames.

The screen scripts measure candidate fields; this one measures the bytes that are
actually offered for download, so every number quoted on the site can be traced to
the artifact itself rather than to the experiment that inspired it. It needs only
committed inputs: the raster, ``data/grid/labels.tif`` and the SGMC proxy raster.

Frames
------
``S_raw``      SGMC fault pixels inside the footprint, more than 300 m (1 px buffer)
               from the supplied catalogue.
``S_matched``  the same, with every 8-connected component of 500 px or more removed,
               because the supplied catalogue contains no component that large while
               the raw proxy contains twelve (docs/research/h59-proxy-gap.md).
``L``          the supplied catalogue itself — a negative control.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from gems59.frames import load_labels, load_sgmc_offcatalogue, macrofolds
from gems59.metric import evaluate

MAX_COMPONENT_PX = 500


def matched_frame(raw: np.ndarray) -> np.ndarray:
    from scipy import ndimage

    lab, n = ndimage.label(raw, structure=np.ones((3, 3), int))
    if n == 0:
        return raw
    sizes = np.bincount(lab.ravel())
    keep = np.flatnonzero(sizes < MAX_COMPONENT_PX)
    keep = keep[keep > 0]
    return np.isin(lab, keep)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--tif", required=True)
    ap.add_argument("--out", default=str(ROOT / "evidence/h59_delivered_metrics.json"))
    args = ap.parse_args()

    import rasterio

    with rasterio.open(args.tif) as src:
        pred = src.read(1)
    labels, footprint = load_labels()
    catalogue = (labels == 1) & footprint
    raw = load_sgmc_offcatalogue() & footprint
    matched = matched_frame(raw)

    fold_map, fold_names = macrofolds(footprint)
    out: dict = {"tif": args.tif, "positive_cells": int((pred > 0).sum()), "frames": {}}
    for name, truth in (("S_matched", matched), ("S_raw", raw), ("L", catalogue)):
        parts = evaluate(pred, truth)
        folds = {}
        for i, fname in enumerate(fold_names):
            fm = fold_map == i
            p = evaluate(pred, truth & fm)
            folds[fname] = {"dti": p.dti, "truth_px": int((truth & fm).sum())}
        out["frames"][name] = {
            "truth_px": int(truth.sum()),
            "dti": parts.dti, "tp_w": parts.tp_w, "fp_w": parts.fp_w, "fn_w": parts.fn_w,
            "coverage": parts.tp_w / max(int(truth.sum()), 1),
            "pred_side_credit": parts.fp_w, "folds": folds,
        }
        print(f"{name:10s} truth={int(truth.sum()):7,d} DTI={parts.dti:.5f} "
              f"T={parts.tp_w:9.1f} FP_w={parts.fp_w:9.1f} "
              f"coverage={parts.tp_w / max(int(truth.sum()), 1):.4f}")
    fm_ = out["frames"]["S_matched"]
    c = fm_["coverage"]
    zero_fp = c / (0.8 + 0.2 * c)
    out["required_coverage_for_target"] = {
        "target": 0.3774,
        "required_coverage": 0.3774 * 0.8 / (1.0 - 0.2 * 0.3774),
        "formula": "solve c/(0.8+0.2c) = target for the coverage a perfect-precision "
                   "prediction would need",
    }
    out["zero_false_positive_limit"] = {
        "formula": "c/(0.8+0.2c) with c = coverage of the frame's truth; the score a "
                   "prediction with no false-positive mass would earn at that coverage",
        "value": zero_fp,
        "reading": "the score this artifact would earn if none of its dots missed, on this frame",
    }
    print(f"zero-FP limit on S_matched: {zero_fp:.5f} at coverage {fm_['coverage']:.4f}")
    print(f"coverage a perfect-precision submission needs for 0.3774: "
          f"{out['required_coverage_for_target']['required_coverage']:.4f}")
    Path(args.out).write_text(json.dumps(out, indent=1), encoding="utf-8")
    print("wrote", args.out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
