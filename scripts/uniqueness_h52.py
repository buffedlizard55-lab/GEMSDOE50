"""Uniqueness + format gate for the shipped H52 raster.

Two questions are answered, separately and without over-claiming.

* **Format.** Re-read the written bytes and check every clause of the published
  submission format, including the failure mode that produced the portal error
  ``Predicted values must be in range [0, 1]``.
* **Uniqueness.** Compare the emitted pixels with every prior artifact that can
  be obtained locally, at exact-pixel and 2 px tolerance, and report the
  *worst* prior (the most similar one) rather than an average. Also report the
  fraction exactly reproduced from the union of priors — the number that says
  whether the file is "just the union".

    python scripts/uniqueness_h52.py --raster FILE --prior-glob 'DIR/*.tif'
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
import rasterio
from scipy.ndimage import binary_dilation


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def read_binary(path: Path) -> np.ndarray | None:
    try:
        with rasterio.open(path) as ds:
            a = ds.read(1)
    except (OSError, rasterio.errors.RasterioError):
        return None
    if a.shape != (3730, 3292):
        return None
    return np.nan_to_num(a.astype(np.float64), nan=0.0, posinf=1.0, neginf=0.0) > 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--raster", required=True, type=Path)
    ap.add_argument("--template", type=Path, default=Path("data/grid/sample_submission.tif"))
    ap.add_argument("--labels", type=Path, default=Path("data/grid/labels.tif"))
    ap.add_argument("--prior", type=Path, nargs="*", default=[])
    ap.add_argument("--out", type=Path, default=Path("evidence/h52_uniqueness.json"))
    args = ap.parse_args()

    with rasterio.open(args.raster) as ds:
        raster = ds.read(1)
        profile = ds.profile
        nodata = ds.nodata
    finite = np.isfinite(raster)
    emitted = finite & (raster > 0)

    with rasterio.open(args.template) as ds:
        template_finite = np.isfinite(ds.read(1))
    with rasterio.open(args.labels) as ds:
        labels = ds.read(1)

    fmt = {
        "driver": profile["driver"],
        "count_is_1": profile["count"] == 1,
        "dtype_is_float32": str(raster.dtype) == "float32",
        "same_shape": raster.shape == labels.shape,
        "finite_cells": int(finite.sum()),
        "nan_cells": int((~finite).sum()),
        "min_finite": float(raster[finite].min()) if finite.any() else None,
        "max_finite": float(raster[finite].max()) if finite.any() else None,
        "outside_unit_interval": int(((raster[finite] < 0.0) | (raster[finite] > 1.0)).sum()),
        "nan_only_outside_template_footprint": bool(
            not np.any(emitted & ~template_finite) and np.array_equal(finite | template_finite, template_finite)
        ),
        "positive_cells": int(emitted.sum()),
        "values_outside_footprint_nonzero": int((emitted & ~template_finite).sum()),
        "nodata_is_large_negative_sentinel": (
            nodata is not None and np.isfinite(nodata) and float(nodata) < -1e30
        ),
        "dots_on_provided_catalogue": int((emitted & (labels == 1)).sum()),
    }
    fmt["all_format_checks_pass"] = bool(
        fmt["driver"] == "GTiff" and fmt["count_is_1"] and fmt["dtype_is_float32"]
        and fmt["same_shape"] and fmt["outside_unit_interval"] == 0
        and fmt["values_outside_footprint_nonzero"] == 0
        and not fmt["nodata_is_large_negative_sentinel"]
        and fmt["dots_on_provided_catalogue"] == 0
    )

    # never compare the artifact with itself (or a byte-identical copy of it)
    self_resolved = Path(args.raster).resolve()
    self_sha = sha256_file(Path(args.raster))

    prior_info = []
    skipped_self = []
    seen_sha = set()
    union = np.zeros(raster.shape, bool)
    worst_name, worst_exact, worst_2px = None, -1.0, -1.0
    for p in sorted(args.prior):
        p = Path(p)
        try:
            if p.resolve() == self_resolved:
                skipped_self.append(p.name)
                continue
        except OSError:
            continue
        p_sha = sha256_file(p)
        if p_sha == self_sha:
            skipped_self.append(p.name)
            continue
        if p_sha in seen_sha:
            continue          # same bytes reachable through two globs
        seen_sha.add(p_sha)
        m = read_binary(p)
        if m is None or not m.any():
            continue
        if np.array_equal(m, emitted):
            # same pixels in a different container (e.g. the all-finite twin)
            skipped_self.append(p.name + " (identical support)")
            continue
        union |= m
        dil = binary_dilation(m, np.ones((3, 3), bool), iterations=2)
        exact = float((emitted & m).sum()) / emitted.sum()
        tol = float((emitted & dil).sum()) / emitted.sum()
        prior_info.append({
            "file": Path(p).name,
            "prior_dots": int(m.sum()),
            "exact_overlap_fraction": round(exact, 6),
            "overlap_within_2px_fraction": round(tol, 6),
            "novel_fraction_at_2px": round(1.0 - tol, 6),
        })
        if tol > worst_2px:
            worst_name, worst_exact, worst_2px = Path(p).name, exact, tol

    uniq = {
        "n_priors_compared": len(prior_info),
        "excluded_self_copies": skipped_self,
        "prior_union_cells": int(union.sum()),
        "union_is_smaller_than_footprint": bool(union.sum() < template_finite.sum()),
        "worst_prior_file": worst_name,
        "worst_prior_exact_overlap_fraction": round(worst_exact, 6),
        "worst_prior_overlap_within_2px_fraction": round(worst_2px, 6),
        "min_novel_fraction_at_2px": round(1.0 - worst_2px, 6) if worst_2px >= 0 else None,
        "reproduced_from_prior_union_fraction": round(float((emitted & union).sum()) / emitted.sum(), 6),
        "self_sha256": sha256_file(args.raster),
        "priors": prior_info,
    }
    report = {"schema": "gemsdoe50.h52.uniqueness.v1", "raster": str(args.raster), "format": fmt, "uniqueness": uniq}
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(report, indent=1))
    print(json.dumps({"format": fmt, "uniqueness": {k: v for k, v in uniq.items() if k != "priors"}}, indent=1))
    return 0 if fmt["all_format_checks_pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
