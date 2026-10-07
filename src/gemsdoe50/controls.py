from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np
import rasterio
from scipy.ndimage import gaussian_filter

from .catalog import CatalogEvents
from .common import sha256_array

SMOOTHED_DENSITY_CONTROL_NAME = "Smoothed-density-300m"
SMOOTHED_DENSITY_SIGMA_M = 300.0


def build_smoothed_density_control(
    events: CatalogEvents,
    template_path: str | Path,
    *,
    sigma_m: float = SMOOTHED_DENSITY_SIGMA_M,
) -> tuple[np.ndarray, dict[str, Any]]:
    """Build a label-blind Gaussian density control from the same relocated events.

    The count raster is smoothed with a Gaussian whose standard deviation is ``sigma_m``
    and normalized to [0, 1]. It is not a fault detector; it tests whether local plane
    geometry adds value beyond a simple seismicity-density surface.
    """
    if sigma_m <= 0:
        raise ValueError("density-control sigma must be positive")
    with rasterio.open(template_path) as template:
        height, width = template.height, template.width
        transform = template.transform
        template_raw = template.read(1, masked=True)
        valid = np.isfinite(np.asarray(template_raw.filled(np.nan))) & ~np.ma.getmaskarray(template_raw)
        pixel_m = float(abs(transform.a))
        if not np.isclose(pixel_m, abs(transform.e)) or pixel_m <= 0:
            raise ValueError("density control requires square, positive-size pixels")
        if abs(transform.b) > 1e-9 or abs(transform.d) > 1e-9:
            raise ValueError("density control requires a north-up grid")

    relocated = np.asarray(events.relocated == 1, dtype=bool)
    rows = np.asarray(events.row[relocated], dtype=np.int64)
    cols = np.asarray(events.col[relocated], dtype=np.int64)
    in_bounds = (rows >= 0) & (rows < height) & (cols >= 0) & (cols < width)
    rows, cols = rows[in_bounds], cols[in_bounds]
    finite_cells = valid[rows, cols]
    rows, cols = rows[finite_cells], cols[finite_cells]
    if rows.size == 0:
        raise ValueError("no relocated events fall on finite template cells for density control")

    counts = np.zeros((height, width), dtype=np.float32)
    np.add.at(counts, (rows, cols), 1.0)
    sigma_px = sigma_m / pixel_m
    density = gaussian_filter(counts, sigma=sigma_px, mode="constant", cval=0.0, truncate=4.0)
    density[~valid] = 0.0
    maximum = float(density.max(initial=0.0))
    if maximum <= 0 or not np.isfinite(maximum):
        raise ValueError("smoothed relocated-event density is empty or non-finite")
    score = np.asarray(density / maximum, dtype=np.float32)
    score[~valid] = 0.0
    if np.any(~np.isfinite(score)) or np.any((score < 0) | (score > 1)):
        raise ValueError("density-control scores must be finite and within [0, 1]")

    metadata = {
        "name": SMOOTHED_DENSITY_CONTROL_NAME,
        "definition": "relocated-event cell counts convolved by a normalized Gaussian, then divided by its maximum",
        "events_used": int(rows.size),
        "events_not_used": int(np.count_nonzero(events.relocated == 1) - rows.size),
        "sigma_m": float(sigma_m),
        "sigma_px": float(sigma_px),
        "maximum_before_normalization": maximum,
        "positive_cells": int(np.count_nonzero(score > 0)),
        "score_map_sha256": sha256_array(score),
        "note": "Matched control: same relocated-event input pool as H50-S1; no declustering or event-type/site exclusions.",
    }
    return score, metadata
