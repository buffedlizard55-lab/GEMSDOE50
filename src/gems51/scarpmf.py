"""Azimuth-specific matched filter for a scarp step on detrended elevation (H52-A).

This differs from `gems51.structfield.layer_lineament`, which is an **orientation-agnostic**
structure-tensor gradient-magnitude detector (it reports a strike *after* detection, from the
local gradient, and is blind to the expected cross-section shape of a scarp). Here a bank of
explicit, rotated step-profile kernels is correlated with the DEM, so the detector (a) only
responds to a profile shaped like a fault scarp (flat - step - flat, not a generic edge or a
ridge), and (b) is evaluated at a fixed set of candidate azimuths rather than taking whatever
direction the local gradient happens to point. Both are stated as this project's own design,
not a published algorithm.

Detrending: `det = dem - gaussian_filter(dem, sigma=trend_sigma_px)`. This project does not have
access to the official `det_elev` feature band (`training_features.tif` could not be re-acquired
this session — see `docs/h52a-protocol.md`), so this is an explicit, own-construction proxy for
it, built only from the publicly described `dem_mean` descriptor.
"""
from __future__ import annotations

import numpy as np
from scipy import ndimage

TREND_SIGMA_PX = 15.0         # ~1.5 km regional-trend removal (preregistered)
STEP_LENGTH_PX = 7            # along-strike kernel extent (700 m)
STEP_WIDTH_PX = 5             # across-strike kernel extent (500 m)
AZIMUTHS_DEG = tuple(range(0, 180, 15))  # 12 candidate strikes, 15 degree steps


def detrend(dem: np.ndarray, valid: np.ndarray, sigma_px: float = TREND_SIGMA_PX) -> np.ndarray:
    filled = np.where(valid, dem, 0.0).astype(np.float32)
    weight = valid.astype(np.float32)
    trend_num = ndimage.gaussian_filter(filled, sigma_px, mode="nearest")
    trend_den = np.maximum(ndimage.gaussian_filter(weight, sigma_px, mode="nearest"), 1e-6)
    trend = trend_num / trend_den
    return np.where(valid, dem - trend, 0.0).astype(np.float32)


def _step_kernel(azimuth_deg: float, length_px: int = STEP_LENGTH_PX,
                  width_px: int = STEP_WIDTH_PX) -> np.ndarray:
    """A [-1 .. 0 .. +1] step profile across `azimuth_deg`, uniform along strike."""
    size = max(length_px, width_px) * 2 + 1
    yy, xx = np.meshgrid(np.arange(-(size // 2), size // 2 + 1),
                          np.arange(-(size // 2), size // 2 + 1), indexing="ij")
    theta = np.radians(azimuth_deg)
    # unit vector perpendicular to the strike (the "across strike" direction)
    nx, ny = np.cos(theta + np.pi / 2.0), np.sin(theta + np.pi / 2.0)
    across = xx * nx + yy * ny
    along = xx * (-ny) + yy * nx
    kernel = np.where(across > 0.5, 1.0, np.where(across < -0.5, -1.0, 0.0))
    kernel = np.where(np.abs(along) <= length_px / 2.0, kernel, 0.0)
    kernel = np.where(np.abs(across) <= width_px / 2.0, kernel, 0.0)
    kernel = kernel.astype(np.float32)
    total = np.abs(kernel).sum()
    return kernel / total if total > 0 else kernel


def matched_filter(det: np.ndarray, valid: np.ndarray,
                    azimuths_deg: tuple[int, ...] = AZIMUTHS_DEG) -> dict:
    """Max-over-azimuth matched-filter response, plus the winning azimuth per cell."""
    best = np.zeros(det.shape, dtype=np.float32)
    best_azimuth = np.zeros(det.shape, dtype=np.float32)
    data = np.where(valid, det, 0.0).astype(np.float32)
    for az in azimuths_deg:
        kernel = _step_kernel(az)
        response = np.abs(ndimage.correlate(data, kernel, mode="constant"))
        take = response > best
        best = np.where(take, response, best)
        best_azimuth = np.where(take, float(az), best_azimuth)
    best = np.where(valid, best, 0.0)
    values = best[valid & (best > 0)]
    peak = float(np.percentile(values, 98.0)) if values.size else 0.0
    peak = peak if peak > 0 else float(best.max())
    normed = np.clip(best / peak, 0.0, 1.0) if peak > 0 else best
    return {"strength": normed.astype(np.float32), "azimuth_deg": best_azimuth.astype(np.float32),
            "azimuths_tested": list(azimuths_deg), "raw_peak_p98": peak}
