#!/usr/bin/env python3
"""Fusion experiment at equal dot budget on both validation frames.

Components are smoothed to the metric's own scale (a corridor whose location
uncertainty is ~300 m should be represented as a ~300 m ridge, not a 1-px line), then
fused.  Everything is scored at equal dot budget, so only *placement* is compared.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from gems50 import emitter, grid, validate  # noqa: E402
sys.path.insert(0, str(Path(__file__).resolve().parent))
from validate_fields import catalogue, emit_budget, sgmc_off_catalogue  # noqa: E402

WORK = Path("/tmp/gems50")
CACHE = WORK / "cache"
BUDGETS = (20_000, 44_090, 70_000)


def smooth(a: np.ndarray, sigma: float = 2.5) -> np.ndarray:
    from scipy.ndimage import gaussian_filter

    return gaussian_filter(a.astype(np.float32), sigma)


def main() -> int:
    fp = np.load(WORK / "footprint.npy")
    comp = {k: smooth(np.load(CACHE / f"comp_{k}.npy")) for k in
            ("struct", "scarp", "seis", "cont")}
    for k, v in comp.items():
        v[~fp] = 0.0
        comp[k] = v / max(v.max(), 1e-9)
        print(f"{k:8s} max {comp[k].max():.3f} mean {comp[k][fp].mean():.5f}")

    cat = catalogue()
    fold_labels = validate.folds(grid.SHAPE, 2, 2, fp)
    truths, domains = {}, {}
    for f in range(4):
        t, dom = validate.scored_truth_frame(cat, fold_labels, f, min_distance_px=10.0)
        truths[f] = t
        domains[f] = dom & (fold_labels == f)
    truth_sgmc, cat2 = sgmc_off_catalogue()
    from scipy.ndimage import distance_transform_edt
    d_cat = distance_transform_edt(~cat2)
    dom_sgmc = fp & (d_cat > 2.0)
    truth_sgmc = truth_sgmc & dom_sgmc
    print("F2 truth px", int(truth_sgmc.sum()), " F1 truth px",
          int(sum(t.sum() for t in truths.values())))

    candidates = {
        "scarp": comp["scarp"],
        "struct": comp["struct"],
        "seis": comp["seis"],
        "scarp+struct": np.maximum(comp["scarp"], 0.7 * comp["struct"]),
        "scarp+0.5struct": comp["scarp"] + 0.5 * comp["struct"],
        "scarp+seis": np.maximum(comp["scarp"], 1.0 * comp["seis"]),
        "scarp+struct+seis": np.maximum(np.maximum(comp["scarp"], 0.7 * comp["struct"]),
                                        1.0 * comp["seis"]),
        "geo_mean_all": (np.maximum(comp["scarp"], 1e-6)
                         * np.maximum(comp["struct"], 1e-6)
                         * np.maximum(comp["seis"], 1e-6)) ** (1 / 3),
        "rank_sum": (comp["scarp"] + comp["struct"] + comp["seis"]) / 3.0,
        "scarp+cont": np.maximum(comp["scarp"], 0.5 * comp["cont"]),
    }

    results = {}
    for name, fld in candidates.items():
        fld = fld * fp
        row = {}
        for n in BUDGETS:
            dots = emit_budget(fld, n, fp)
            f1 = [validate.evaluate(dots, truths[f], domains[f])["dti"] for f in range(4)]
            r2 = validate.evaluate(dots, truth_sgmc, dom_sgmc)
            row[n] = dict(dots=int(dots.sum()), F1=float(np.mean(f1)),
                          F2=r2["dti"], F2_tp=r2["tp_w"], F2_fp=r2["fp_w"])
            print(f"{name:20s} n={n:>6d} dots={int(dots.sum()):>6d} "
                  f"F1 {np.mean(f1):.5f} F2 {r2['dti']:.5f}")
        results[name] = row
    (WORK / "fusion_experiment.json").write_text(json.dumps(results, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
