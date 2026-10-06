#!/usr/bin/env python3
"""Quantify the TPw bug that was fixed in ``gems50.metric.score`` on 2026-10-06.

The previous implementation queried predictions against their *nearest* truth pixel and
took the per-truth maximum only over that subset, instead of the published rule
``TP_w = sum_g max_x p(x) k(d(x,g))`` over every prediction inside the kernel.  It
under-counted TP_w and therefore under-reported DTI.  This script re-scores the merged
repository's own submission and the family's reference files with the fixed rule, so the
size of the correction is on the record rather than in a chat log.
"""
from __future__ import annotations

import glob
import json
import sys
from pathlib import Path

import numpy as np
import rasterio

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "src"))

from gems50 import grid_io, metric  # noqa: E402


def old_tpw(pred: np.ndarray, truth: np.ndarray) -> float:
    """The pre-fix rule: each prediction credits only its NEAREST truth pixel."""
    from scipy.spatial import cKDTree

    p_idx = np.argwhere(np.isfinite(pred) & (pred > 0))
    t_idx = np.argwhere(truth)
    if p_idx.size == 0 or t_idx.size == 0:
        return 0.0
    p_vals = pred[tuple(p_idx.T)]
    d_p2t, i_p2t = cKDTree(t_idx).query(p_idx, k=1)
    contrib = p_vals * metric.kernel(d_p2t)
    cred = np.zeros(t_idx.shape[0])
    for j in np.argsort(-contrib):
        if contrib[j] <= 0.0:
            break
        g = i_p2t[j]
        cred[g] = max(cred[g], contrib[j])
    return float(cred.sum())


def main() -> int:
    truth = grid_io.load_labels()
    valid = grid_io.load_valid_mask()
    files = sorted(glob.glob(str(REPO / "docs/downloads/*.tif"))) + \
            sorted(glob.glob(str(REPO / "downloads/*.tif")))
    out = {"metric": "fixed: TP_w = sum_g max_x p(x) k(d(x,g)) over all predictions in the kernel",
           "truth": "labels.tif (the given catalogue raster)", "files": {}}
    for f in files:
        try:
            with rasterio.open(f) as src:
                a = np.nan_to_num(src.read(1)).astype(np.float32)
        except Exception as exc:  # pragma: no cover
            out["files"][Path(f).name] = {"error": str(exc)}
            continue
        r = metric.score(a, truth, domain=valid)
        t_old = old_tpw(a, truth & valid)
        t_new = float(r["tp_w"])
        dti_old = metric.tversky_index(t_old, float(r["fp_w"]), float(truth.sum()) - t_old)
        out["files"][Path(f).name] = {
            "mass": int((a > 0).sum()), "dti_fixed": float(r["dti"]), "tp_w_fixed": t_new,
            "tp_w_old_rule": t_old, "tp_w_understated_by": t_new - t_old,
            "tp_w_relative_error_old": (t_new - t_old) / t_new if t_new else None,
            "dti_old_rule": float(dti_old), "dti_absolute_correction": float(r["dti"]) - float(dti_old),
            "fp_w": float(r["fp_w"]), "fn_w": float(r["fn_w"])}
        print(f"  {Path(f).name:56s} mass={int((a>0).sum()):7d} DTI(fixed)={float(r['dti']):.4f}")
    (REPO / "evidence").mkdir(exist_ok=True)
    (REPO / "evidence" / "metric_bug_impact.json").write_text(json.dumps(out, indent=1))
    print("wrote evidence/metric_bug_impact.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
