#!/usr/bin/env python3
"""Score the exact submitted bytes on both proxy frames, and compare with the
matched controls at the same dot count."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import rasterio

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from gems50 import grid, validate  # noqa: E402

WORK = Path("/tmp/gems50")
sys.path.insert(0, str(Path(__file__).resolve().parent))
from validate_fields import emit_budget, sgmc_off_catalogue  # noqa: E402

SUB = Path(sys.argv[1] if len(sys.argv) > 1 else WORK / "submission.tif")


def main() -> int:
    fp = np.load(WORK / "footprint.npy")
    with rasterio.open("/tmp/gems_work/labels.tif") as s:
        cat = s.read(1) == 1
    with rasterio.open(SUB) as s:
        mine = np.isfinite(s.read(1)) & (s.read(1) > 0)
    n = int(mine.sum())
    print(f"submission dots: {n:,}")

    fold_labels = validate.folds(grid.SHAPE, 2, 2, fp)
    f1 = []
    for f in range(4):
        t, dom = validate.scored_truth_frame(cat, fold_labels, f, min_distance_px=10.0)
        dom = dom & (fold_labels == f)
        r = validate.evaluate(mine, t, dom)
        f1.append(r["dti"])
        print(f"  F1 fold {f}: truth {int(t.sum()):>6d} px  DTI {r['dti']:.5f}  "
              f"(tp {r['tp_w']:.1f}, fp {r['fp_w']:.1f})")
    truth_sgmc, cat2 = sgmc_off_catalogue()
    from scipy.ndimage import distance_transform_edt
    dom_sgmc = fp & (distance_transform_edt(~cat2) > 2.0)
    truth_sgmc &= dom_sgmc
    r2 = validate.evaluate(mine, truth_sgmc, dom_sgmc)
    print(f"  F2 SGMC off-catalogue: truth {int(truth_sgmc.sum()):,} px  DTI {r2['dti']:.5f} "
          f"(tp {r2['tp_w']:.1f}, fp {r2['fp_w']:.1f})")

    # matched controls at the identical dot count
    controls = {}
    rng = np.random.default_rng(101)
    rand_mask = (rng.random(grid.SHAPE) < 0.02).astype(np.float32) * fp
    from scipy.ndimage import gaussian_filter
    dens = gaussian_filter(rand_mask, 0.0)
    with rasterio.open("/tmp/gems_work/sample_submission.tif") as s:
        pass
    # uniform-random dots
    dots_rand = emit_budget((rng.random(grid.SHAPE) < 0.5).astype(np.float32) * fp, n, fp)
    rc = [validate.evaluate(dots_rand, t, validate.scored_truth_frame(cat, fold_labels, f, 10.0)[1]
                            & (fold_labels == f))["dti"] for f in range(4)]
    r2c = validate.evaluate(dots_rand, truth_sgmc, dom_sgmc)
    controls["uniform_random_same_count"] = dict(F1_mean=float(np.mean(rc)), F2=float(r2c["dti"]))
    print(f"  control uniform-random at {n:,} dots: F1 {np.mean(rc):.5f}  F2 {r2c['dti']:.5f}")

    out = dict(submission=str(SUB), dots=n, F1_mean=float(np.mean(f1)), F1_folds=f1,
               F2_dti=float(r2["dti"]), F2_tp=float(r2["tp_w"]), F2_fp=float(r2["fp_w"]),
               controls=controls)
    (WORK / "submission_validation.json").write_text(json.dumps(out, indent=1))
    print(json.dumps(out, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
