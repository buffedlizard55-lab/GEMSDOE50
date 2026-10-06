#!/usr/bin/env python3
"""Independent audit of a submitted GeoTIFF: format, uniqueness, and instruments.

Uniqueness is measured against every prior submission raster this sandbox can retrieve
(the sibling repositories' ``docs/downloads`` trees).  Two statistics are reported because
they fail differently: the largest Pearson correlation between the two value fields inside
the survey footprint, and the largest Jaccard overlap of the two supports.

The three instruments are reported with their known biases attached (see
``scripts/validate_candidate.py`` and the README) -- the catalogue instrument is an
*anti*-instrument for this competition and is printed only so that it cannot be mistaken
for evidence of skill.
"""
from __future__ import annotations

import argparse
import glob
import json
import sys
from pathlib import Path

import numpy as np
import rasterio

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "src"))

from gems50 import emission  # noqa: E402
from gems50 import dti as metric  # noqa: E402
from gems50 import grid_io as grid  # noqa: E402

PRIOR_GLOBS = [
    "docs/downloads/*.tif",          # this repository (including the sibling session's file)
    "downloads/*.tif",
    "/tmp/ref/*/docs/downloads/*.tif",
    "/tmp/ref/*/docs/research/quarantine/*.tif",
    "/tmp/ref/*/data/bridge/*.tif",
    "/tmp/ref/*/inputs/*.tif",
]


def prior_files(exclude: Path) -> list[Path]:
    seen, out = set(), []
    for pat in PRIOR_GLOBS:
        for f in glob.glob(pat):
            p = Path(f)
            try:
                if p.resolve() == exclude.resolve() or p.name in seen:
                    continue
            except OSError:
                continue
            seen.add(p.name)
            out.append(p)
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("tif")
    ap.add_argument("--out", default=None)
    args = ap.parse_args()
    tif = Path(args.tif)
    g = grid.load_grid()
    valid = grid.load_valid_mask()
    labels = grid.load_labels()

    audit = emission.audit_submission(tif)
    with rasterio.open(tif) as s:
        a = np.nan_to_num(s.read(1))
    sup = a > 0.5
    assert sup.shape == g.shape, f"shape {sup.shape} != grid {g.shape}"

    max_r, max_r_file, max_j, max_j_file = 0.0, None, 0.0, None
    n_priors = 0
    for f in prior_files(tif):
        try:
            with rasterio.open(f) as s:
                if (s.height, s.width) != g.shape or s.count != 1:
                    continue
                b = np.nan_to_num(s.read(1))
        except Exception:
            continue
        n_priors += 1
        bs = b > 0.5 if b.max() > 1e-9 else np.zeros_like(sup)
        if b.max() <= 1e-9:
            continue
        av, bv = a[valid], b[valid]
        if av.std() > 0 and bv.std() > 0:
            r = float(np.corrcoef(av, bv)[0, 1])
            if abs(r) > abs(max_r):
                max_r, max_r_file = r, f.name
        inter = int((sup & bs).sum())
        union = int((sup | bs).sum())
        if union:
            j = inter / union
            if j > max_j:
                max_j, max_j_file = j, f.name

    sgmc_off = None
    with rasterio.open(REPO / "data/external/derived_sgmc_faults_100m_u8.tif") as s:
        from scipy.ndimage import distance_transform_edt
        d_lab = distance_transform_edt(~labels)
        sgmc = s.read(1) > 0
    sgmc_off = sgmc & (d_lab > 3) & valid
    scores = {}
    for name, truth in (("catalogue", labels), ("sgmc_off_catalogue", sgmc_off)):
        r = metric.dti_parts(sup.astype(np.float32), truth)
        scores[name] = {"credit_per_px": r.tpw / max(int(sup.sum()), 1), "tpw": r.tpw,
                        "truth_px": r.truth_cells, "covered_frac": r.tpw / max(r.truth_cells, 1)}

    out = {
        "file": tif.name, "format": audit, "mass": int(sup.sum()),
        "uniqueness": {"n_prior_rasters_compared": n_priors,
                       "max_abs_pearson": abs(max_r), "max_abs_pearson_file": max_r_file,
                       "max_jaccard": max_j, "max_jaccard_file": max_j_file,
                       "is_unique_by_correlation": bool(abs(max_r) < 0.5),
                       "is_unique_by_jaccard": bool(max_j < 0.5)},
        "instruments": scores,
    }
    if args.out:
        Path(args.out).write_text(json.dumps(out, indent=1))
    print(json.dumps(out, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
