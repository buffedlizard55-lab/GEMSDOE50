"""Independent format + uniqueness gate for the H57 deliverable.

Reads the delivered bytes back and re-derives every claim:
  * the portal's own range test as a plain ``min()/max()`` over the raster
  * single band, float32, EPSG:32611, official shape and geotransform
  * zero positive cells outside the supplied study footprint
  * zero positive cells on the supplied catalogue
  * zero exact overlap with the registered prior-artifact positive union, and the
    fraction of dots that are within 2 px of that union
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

GRID = {
    "crs": "EPSG:32611",
    "width": 3292,
    "height": 3730,
    "transform": (100.0, 0.0, 243350.0, 0.0, -100.0, 4508550.0),
}


def sha256_of(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for blk in iter(lambda: fh.read(1 << 20), b""):
            h.update(blk)
    return h.hexdigest()


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--nan-tif", required=True)
    ap.add_argument("--out", default="evidence/h57_check.json")
    ap.add_argument("--label-union", default="registry/prior_positive_union.npz")
    args = ap.parse_args()

    import rasterio
    from scipy import ndimage

    res: dict[str, object] = {"schema": "gemsdoe50.h57.check.v1", "file": args.nan_tif}
    with rasterio.open(args.nan_tif) as src:
        arr = src.read(1)
        res["format"] = {
            "driver": src.driver,
            "count_is_1": src.count == 1,
            "dtype_is_float32": src.dtypes[0] == "float32",
            "crs_matches": src.crs is not None and src.crs.to_string() == GRID["crs"],
            "shape_matches": (src.width, src.height) == (GRID["width"], GRID["height"]),
            "transform_matches": tuple(round(float(v), 6) for v in tuple(src.transform)[:6])
            == GRID["transform"],
        }
    finite = np.isfinite(arr)
    vals = arr[finite]
    res["format"].update(
        {
            "finite_cells": int(finite.sum()),
            "nan_cells": int((~finite).sum()),
            "min_finite": float(vals.min()),
            "max_finite": float(vals.max()),
            "outside_unit_interval": int(((vals < 0) | (vals > 1)).sum()),
            "plain_minmax_in_range": bool(float(vals.min()) >= 0.0 and float(vals.max()) <= 1.0),
            "nan_only_outside_footprint": None,
        }
    )

    labels, footprint = None, None
    with rasterio.open("data/grid/labels.tif") as src:
        labels = src.read(1)
    footprint = labels != -1
    catalogue = labels == 1
    pos = np.nan_to_num(arr, nan=0.0) > 0
    res["format"]["nan_only_outside_footprint"] = bool(np.array_equal(~finite, ~footprint))
    z = np.load(args.label_union)
    shape = tuple(int(x) for x in z["shape"])
    union = np.unpackbits(z["packed"])[: shape[0] * shape[1]].reshape(shape).astype(bool)
    exact = int((pos & union).sum())
    d = ndimage.distance_transform_edt(~union)
    within2 = int((pos & (d <= 2)).sum())
    res["positive_cells"] = int(pos.sum())
    res["dots_on_provided_catalogue"] = int((pos & catalogue).sum())
    res["nonzero_outside_footprint"] = int((pos & ~footprint).sum())

    # ---- coarse block signatures, the repository's cross-artifact measure ------
    sig_path = Path("registry/prior_artifact_signatures.npz")
    block_iou = None
    if sig_path.exists():
        zz = np.load(sig_path)
        _h, _w = (int(x) for x in zz["grid_shape"])
        factors = [int(x) for x in zz["factors"]]
        coarse = zz["coarse_shapes"]
        block_iou = {"n_compared": len(zz["names"]), "method": "IoU on occupied "
                     "block signatures, bit-unpacked from registry/prior_artifact_signatures.npz"}
        for bi, factor in enumerate(factors):
            bh, bw = int(coarse[bi, 0]), int(coarse[bi, 1])
            mine = pos[: bh * factor, : bw * factor].reshape(bh, factor, bw, factor).any(axis=(1, 3))
            rows = zz[f"masks_block{factor}"]
            worst_iou, worst_name = 1.0, None
            for i, nm in enumerate(zz["names"]):
                other = np.unpackbits(rows[i])[: bh * bw].reshape(bh, bw).astype(bool)
                inter = int((mine & other).sum())
                un = int((mine | other).sum())
                iou = inter / un if un else 1.0
                if iou < worst_iou:
                    worst_iou, worst_name = iou, str(nm)
            block_iou[f"worst_block{factor}_iou"] = worst_iou
            block_iou[f"worst_block{factor}_prior"] = worst_name
    res["uniqueness"] = {
        "schema": "exact-cell novelty against the registered prior-artifact support",
        "n_priors_in_union": len(z["names"]),
        "prior_union_cells": int(union.sum()),
        "exact_overlap_cells": exact,
        "overlap_within_2px_cells": within2,
        "novel_fraction_at_2px": float(1.0 - within2 / max(int(pos.sum()), 1)),
        "self_sha256": sha256_of(Path(args.nan_tif)),
        "note": "the 2 px figure is a proximity statistic, not a novelty guarantee: the "
                "prior union's 2 px neighbourhood covers 85.2 % of the study footprint, so a "
                "uniform draw of the same mass would also be 'novel' only ~15 % of the time",
    }
    if block_iou is not None:
        res["uniqueness"].update(block_iou)
    res["all_checks_pass"] = bool(
        all(res["format"][k] for k in ("count_is_1", "dtype_is_float32", "crs_matches", "shape_matches", "transform_matches"))
        and res["format"]["plain_minmax_in_range"]
        and res["format"]["outside_unit_interval"] == 0
        and res["nonzero_outside_footprint"] == 0
        and res["dots_on_provided_catalogue"] == 0
        and exact == 0
    )
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out).write_text(json.dumps(res, indent=1))
    print(json.dumps(res, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
