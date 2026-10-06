from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np
import rasterio

from .common import sha256_array, sha256_file


def check_same_grid(
    reference: rasterio.io.DatasetReader, candidate: rasterio.io.DatasetReader
) -> None:
    attrs = ("width", "height", "count", "crs", "transform")
    mismatches = []
    for attr in attrs:
        if getattr(reference, attr) != getattr(candidate, attr):
            mismatches.append(
                f"{attr}: reference={getattr(reference, attr)!r}, candidate={getattr(candidate, attr)!r}"
            )
    if mismatches:
        raise ValueError("raster grid mismatch: " + "; ".join(mismatches))


def load_template(template_path: str | Path) -> tuple[dict[str, Any], np.ndarray, np.ndarray]:
    with rasterio.open(template_path) as ds:
        template = ds.read(1)
        valid = np.isfinite(template)
        profile = ds.profile.copy()
        profile["transform"] = ds.transform
        profile["crs"] = ds.crs
        profile["height"] = ds.height
        profile["width"] = ds.width
        profile["count"] = 1
    if not np.any(valid):
        raise ValueError("submission template contains no valid cells")
    return profile, valid, template


def load_labels(
    label_path: str | Path,
    template_path: str | Path,
    valid_template: np.ndarray,
) -> tuple[np.ndarray, dict[str, Any]]:
    with rasterio.open(template_path) as template_ds, rasterio.open(label_path) as label_ds:
        check_same_grid(template_ds, label_ds)
        raw = label_ds.read(1, masked=True)
        label_values = np.asarray(raw.filled(0))
        label_mask = ~np.ma.getmaskarray(raw)
        if not np.array_equal(label_mask, valid_template):
            raise ValueError(
                "label valid-data mask does not exactly match the pinned template mask"
            )
        unique = np.unique(label_values[label_mask])
        if not np.all(np.isin(unique, [0, 1])):
            raise ValueError(f"expected binary labels 0/1 on valid cells; found {unique[:20]!r}")
        truth = (label_values == 1) & label_mask
        metadata = {
            "positive_label_cells": int(np.count_nonzero(truth)),
            "valid_cells": int(np.count_nonzero(label_mask)),
            "valid_mask_sha256": sha256_array(label_mask.astype(np.uint8)),
            "label_dtype": label_ds.dtypes[0],
            "label_nodata": label_ds.nodata,
        }
    return truth, metadata


def write_submission(
    template_path: str | Path,
    output_path: str | Path,
    predictions: np.ndarray,
    valid_mask: np.ndarray,
) -> dict[str, Any]:
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with rasterio.open(template_path) as template_ds:
        if predictions.shape != (template_ds.height, template_ds.width):
            raise ValueError("prediction array shape does not match the template")
        if valid_mask.shape != predictions.shape:
            raise ValueError("valid mask shape does not match the prediction")
        profile = template_ds.profile.copy()
        profile.update(
            driver="GTiff",
            count=1,
            dtype="float32",
            nodata=np.nan,
            compress="LZW",
            predictor=3,
            tiled=True,
            blockxsize=256,
            blockysize=256,
        )
        profile.pop("photometric", None)
        raster = np.full(predictions.shape, np.nan, dtype=np.float32)
        raster[valid_mask] = np.asarray(predictions, dtype=np.float32)[valid_mask]
        if np.any(~np.isfinite(raster[valid_mask])):
            raise ValueError("predictions must be finite in every valid template cell")
        if np.any((raster[valid_mask] < 0) | (raster[valid_mask] > 1)):
            raise ValueError("predictions must be within [0, 1] in every valid cell")
        with rasterio.open(output_path, "w", **profile) as destination:
            destination.write(raster, 1)
    return validate_submission(output_path, template_path)


def validate_submission(
    submission_path: str | Path,
    template_path: str | Path,
) -> dict[str, Any]:
    """Reopen the output bytes and test the actual competition raster contract."""
    with rasterio.open(template_path) as template_ds, rasterio.open(submission_path) as sub_ds:
        if (sub_ds.width, sub_ds.height) != (template_ds.width, template_ds.height):
            raise ValueError("submission width/height differ from the template")
        if sub_ds.count != 1:
            raise ValueError(f"submission must have one band, got {sub_ds.count}")
        if sub_ds.dtypes != ("float32",):
            raise ValueError(f"submission must be float32, got {sub_ds.dtypes}")
        if sub_ds.crs != template_ds.crs or sub_ds.transform != template_ds.transform:
            raise ValueError("submission CRS/transform differs from the template")
        if sub_ds.bounds != template_ds.bounds:
            raise ValueError("submission bounds differ from the template")
        template = template_ds.read(1)
        expected_valid = np.isfinite(template)
        data = sub_ds.read(1)
        valid = np.isfinite(data)
        if not np.array_equal(valid, expected_valid):
            raise ValueError(
                "submission nodata mask does not match the template's finite footprint"
            )
        values = data[valid]
        if values.size == 0:
            raise ValueError("submission contains no finite prediction cells")
        if not np.all(np.isfinite(values)):
            raise ValueError("submission contains NaN/inf inside the valid footprint")
        minimum = float(values.min())
        maximum = float(values.max())
        if minimum < 0.0 or maximum > 1.0:
            raise ValueError(f"submission value range outside [0, 1]: [{minimum}, {maximum}]")
        positive = int(np.count_nonzero(values > 0))
        result = {
            "path": str(submission_path),
            "sha256": sha256_file(submission_path),
            "bytes": Path(submission_path).stat().st_size,
            "width": sub_ds.width,
            "height": sub_ds.height,
            "band_count": sub_ds.count,
            "dtype": sub_ds.dtypes[0],
            "crs": sub_ds.crs.to_string() if sub_ds.crs else None,
            "transform": list(sub_ds.transform),
            "bounds": list(sub_ds.bounds),
            "nodata": "NaN" if np.isnan(sub_ds.nodata) else sub_ds.nodata,
            "valid_cells": int(values.size),
            "nodata_cells": int(data.size - values.size),
            "positive_cells": positive,
            "minimum_valid_value": minimum,
            "maximum_valid_value": maximum,
            "range_pass": True,
            "nodata_mask_matches_template": True,
        }
    return result
