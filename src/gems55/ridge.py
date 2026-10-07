"""Independent geophysical ridge evidence and dynamic cross-axis snapping."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
import rasterio
from scipy import ndimage

from .seismic import AxisSegments


@dataclass(frozen=True)
class RidgeEvidence:
    score: np.ndarray
    topographic: np.ndarray
    radiometric: np.ndarray
    topographic_strike_deg: np.ndarray
    topographic_strike_valid: np.ndarray
    metadata: dict[str, Any]


def _decode_u8_square(q: np.ndarray, maximum: float) -> np.ndarray:
    result = np.full(q.shape, np.nan, dtype=np.float32)
    keep = q > 0
    result[keep] = (((q[keep].astype(np.float32) - 1.0) / 254.0) ** 2) * maximum
    return result


def _robust_unit(field: np.ndarray, valid: np.ndarray) -> tuple[np.ndarray, float]:
    out = np.zeros(field.shape, dtype=np.float32)
    keep = valid & np.isfinite(field) & (field > 0)
    if not np.any(keep):
        return out, 0.0
    scale = float(np.percentile(field[keep], 99.0))
    if scale <= 0 or not np.isfinite(scale):
        return out, scale
    out[keep] = np.clip(field[keep] / scale, 0.0, 1.0)
    return out, scale


def build_ridge_evidence(
    lidar_path: str | Path,
    radiometric_path: str | Path,
    valid: np.ndarray,
) -> RidgeEvidence:
    """Build a label-blind 70/30 terrain/radiometric lineament ridge score."""
    valid = np.asarray(valid, dtype=bool)
    with rasterio.open(lidar_path) as ds:
        if ds.count < 11 or ds.shape != valid.shape:
            raise ValueError("unexpected LiDAR descriptor stack")
        step_q = ds.read(3)
        lap_q = ds.read(4)
        relief_q = ds.read(9)
        coherence_q = ds.read(10)
        strike_q = ds.read(11)
    step = _decode_u8_square(step_q, 1.0)
    lap = _decode_u8_square(lap_q, 0.05)
    relief = _decode_u8_square(relief_q, 300.0)
    coherence = np.full(coherence_q.shape, np.nan, dtype=np.float32)
    keep_coherence = coherence_q > 0
    coherence[keep_coherence] = (
        coherence_q[keep_coherence].astype(np.float32) - 1.0
    ) / 254.0
    topo_valid = (
        valid
        & np.isfinite(step)
        & np.isfinite(lap)
        & np.isfinite(relief)
        & np.isfinite(coherence)
    )
    topo_raw = np.zeros(valid.shape, dtype=np.float32)
    topo_raw[topo_valid] = (
        np.sqrt(np.clip(step[topo_valid], 0.0, 1.0))
        * np.sqrt(0.5 + 0.5 * np.clip(lap[topo_valid] / 0.05, 0.0, 1.0))
        * np.clip(coherence[topo_valid], 0.0, 1.0)
        * (0.75 + 0.25 * np.clip(relief[topo_valid] / 300.0, 0.0, 1.0))
    )
    topographic, topo_scale = _robust_unit(topo_raw, topo_valid)

    strike = np.zeros(valid.shape, dtype=np.float32)
    strike_valid = valid & (strike_q > 0)
    strike[strike_valid] = (
        (strike_q[strike_valid].astype(np.float32) - 1.0) / 254.0 * 180.0
    )

    with rasterio.open(radiometric_path) as ds:
        if ds.count < 4 or ds.shape != valid.shape:
            raise ValueError("unexpected GeoDAWN radiometric stack")
        bands = [ds.read(i).astype(np.float32) for i in range(1, 5)]
    radiometric_valid = valid.copy()
    decoded: list[np.ndarray] = []
    for band in bands:
        present = band > 0
        radiometric_valid &= present
        value = np.zeros(band.shape, dtype=np.float32)
        value[present] = (band[present] - 1.0) / 254.0
        decoded.append(value)
    scale_responses: list[np.ndarray] = []
    for sigma in (1.5, 3.0):
        response = np.zeros(valid.shape, dtype=np.float32)
        for value in decoded:
            smooth = ndimage.gaussian_filter(value, sigma=sigma, mode="nearest")
            gy, gx = np.gradient(smooth)
            response += np.hypot(gx, gy).astype(np.float32)
        scale_responses.append(response)
    radio_raw = np.sqrt(np.maximum(scale_responses[0] * scale_responses[1], 0.0))
    local_background = ndimage.median_filter(radio_raw, size=9, mode="nearest")
    radio_raw = np.maximum(radio_raw - local_background, 0.0)
    radiometric, radio_scale = _robust_unit(radio_raw, radiometric_valid)

    score = 0.70 * topographic + 0.30 * radiometric
    score[~valid] = 0.0
    return RidgeEvidence(
        score=score.astype(np.float32, copy=False),
        topographic=topographic,
        radiometric=radiometric,
        topographic_strike_deg=strike,
        topographic_strike_valid=strike_valid,
        metadata={
            "method": "independent terrain/radiometric ridge evidence",
            "weights": {"topographic": 0.70, "radiometric": 0.30},
            "terrain_bands": ["step_max", "lapneg_max", "relief", "coh100", "strike"],
            "radiometric_bands": ["K", "Th", "U", "TC"],
            "radiometric_scales_pixels": [1.5, 3.0],
            "robust_percentile": 99.0,
            "terrain_p99_scale": topo_scale,
            "radiometric_p99_scale": radio_scale,
            "finite_topographic_cells": int(topo_valid.sum()),
            "finite_radiometric_cells": int(radiometric_valid.sum()),
        },
    )


def _sample_bilinear(field: np.ndarray, rows: np.ndarray, cols: np.ndarray) -> np.ndarray:
    return ndimage.map_coordinates(
        field,
        [rows, cols],
        order=1,
        mode="constant",
        cval=0.0,
        prefilter=False,
    )


def _axial_difference_deg(a: float, b: np.ndarray) -> np.ndarray:
    difference = np.abs(b - a) % 180.0
    return np.minimum(difference, 180.0 - difference)


def _dynamic_path(local: np.ndarray, continuity_penalty: float = 0.08) -> np.ndarray:
    """Viterbi path with maximum two-bin cross-axis motion per sample."""
    n_step, n_offset = local.shape
    score = np.full((n_step, n_offset), -np.inf, dtype=np.float64)
    previous = np.full((n_step, n_offset), -1, dtype=np.int16)
    score[0] = local[0]
    for t in range(1, n_step):
        for current in range(n_offset):
            lo = max(0, current - 2)
            hi = min(n_offset, current + 3)
            predecessor = np.arange(lo, hi)
            candidate = score[t - 1, lo:hi] - continuity_penalty * np.abs(
                predecessor - current
            )
            winner = int(np.argmax(candidate))
            score[t, current] = local[t, current] + candidate[winner]
            previous[t, current] = int(predecessor[winner])
    path = np.empty(n_step, dtype=np.int16)
    path[-1] = int(np.argmax(score[-1]))
    for t in range(n_step - 1, 0, -1):
        path[t - 1] = previous[t, path[t]]
    return path


def snapped_corridor_field(
    segments: AxisSegments,
    evidence: RidgeEvidence,
    transform: rasterio.Affine,
    valid: np.ndarray,
    allowed: np.ndarray,
    half_width_m: float,
    sample_spacing_m: float = 100.0,
    pixel_m: float = 100.0,
) -> tuple[np.ndarray, dict[str, Any]]:
    """Snap only across each seismic axis, then broaden by the assumed corridor width."""
    valid = np.asarray(valid, dtype=bool)
    allowed = np.asarray(allowed, dtype=bool)
    if valid.shape != evidence.score.shape or allowed.shape != valid.shape:
        raise ValueError("ridge/valid/allowed shape mismatch")
    max_shift_pixels = round(half_width_m / pixel_m)
    offsets = np.arange(-max_shift_pixels, max_shift_pixels + 1, dtype=np.int16)
    inverse = ~transform
    centreline = np.zeros(valid.shape, dtype=np.float32)
    visited = 0
    valid_path_cells = 0
    shifts: list[float] = []

    for i in range(len(segments)):
        length = float(segments.hi_m[i] - segments.lo_m[i])
        n_sample = max(2, int(np.ceil(length / sample_spacing_m)) + 1)
        along = np.linspace(segments.lo_m[i], segments.hi_m[i], n_sample)
        base_x = segments.x_m[i] + along * segments.ux[i]
        base_y = segments.y_m[i] + along * segments.uy[i]
        # Unit cross-axis normal in projected coordinates.
        nx = -segments.uy[i]
        ny = segments.ux[i]
        candidate_x = base_x[:, None] + offsets[None, :] * pixel_m * nx
        candidate_y = base_y[:, None] + offsets[None, :] * pixel_m * ny
        candidate_col, candidate_row = inverse * (candidate_x, candidate_y)
        ridge = _sample_bilinear(evidence.score, candidate_row, candidate_col)
        strike = _sample_bilinear(
            evidence.topographic_strike_deg, candidate_row, candidate_col
        )
        strike_available = _sample_bilinear(
            evidence.topographic_strike_valid.astype(np.float32),
            candidate_row,
            candidate_col,
        ) > 0.5
        axis_strike = float(np.degrees(np.arctan2(segments.ux[i], segments.uy[i])) % 180.0)
        angle = _axial_difference_deg(axis_strike, strike)
        orientation = np.zeros(ridge.shape, dtype=np.float32)
        orientation[strike_available] = np.cos(
            np.deg2rad(2.0 * angle[strike_available])
        ).astype(np.float32)
        local = ridge + 0.25 * orientation
        path = _dynamic_path(local, continuity_penalty=0.08)
        rr = candidate_row[np.arange(n_sample), path]
        cc = candidate_col[np.arange(n_sample), path]
        row_i = np.floor(rr).astype(np.int64)
        col_i = np.floor(cc).astype(np.int64)
        in_bounds = (
            (row_i >= 0)
            & (row_i < valid.shape[0])
            & (col_i >= 0)
            & (col_i < valid.shape[1])
        )
        ok_index = np.flatnonzero(in_bounds)
        if ok_index.size:
            ok = valid[row_i[ok_index], col_i[ok_index]]
            ok_index = ok_index[ok]
        if ok_index.size:
            quality = float(segments.quality[i])
            np.maximum.at(
                centreline,
                (row_i[ok_index], col_i[ok_index]),
                np.float32(quality),
            )
            valid_path_cells += int(ok_index.size)
        visited += int(n_sample)
        shifts.extend((offsets[path] * pixel_m).astype(float).tolist())

    sigma_pixels = half_width_m / pixel_m / 2.355
    corridor = ndimage.gaussian_filter(
        centreline, sigma=sigma_pixels, mode="constant", cval=0.0
    )
    maximum = float(corridor.max(initial=0.0))
    if maximum > 0:
        corridor /= maximum
    field = corridor * (0.5 + 0.5 * evidence.score)
    field[~valid | ~allowed] = 0.0
    field_max = float(field.max(initial=0.0))
    if field_max > 0:
        field /= field_max
    shifts_array = np.asarray(shifts, dtype=np.float64)
    report = {
        "method": "cross-axis dynamic ridge snap plus Gaussian uncertainty corridor",
        "segments": len(segments),
        "half_width_m": float(half_width_m),
        "sample_spacing_m": float(sample_spacing_m),
        "offset_candidates": int(offsets.size),
        "path_samples": visited,
        "valid_path_samples": valid_path_cells,
        "unique_centerline_cells": int(np.count_nonzero(centreline)),
        "corridor_positive_cells_before_mask": int(np.count_nonzero(corridor)),
        "field_positive_allowed_cells": int(np.count_nonzero(field)),
        "median_absolute_snap_m": (
            float(np.median(np.abs(shifts_array))) if shifts_array.size else None
        ),
        "p90_absolute_snap_m": (
            float(np.percentile(np.abs(shifts_array), 90)) if shifts_array.size else None
        ),
        "continuity_penalty_per_pixel": 0.08,
        "maximum_offset_change_per_sample_pixels": 2,
        "orientation_weight": 0.25,
        "sigma_pixels": float(sigma_pixels),
    }
    return field.astype(np.float32, copy=False), report
