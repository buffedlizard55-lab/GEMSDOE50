from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

import numpy as np
import rasterio
from scipy.spatial import cKDTree

from .catalog import CatalogEvents


@dataclass(frozen=True)
class LineamentConfig:
    """Fixed, label-blind parameters for the first H50-S1 implementation."""

    radius_m: float = 2500.0
    seed_cell_m: float = 500.0
    dedupe_cell_m: float = 250.0
    min_events: int = 10
    min_years: int = 2
    min_horizontal_length_m: float = 1500.0
    min_linearity: float = 0.70
    max_horizontal_width_m: float = 1200.0
    min_planarity_3d: float = 0.45
    min_horizontal_plane_normal: float = 0.20
    min_trace_strike_alignment: float = 0.65
    max_median_depth_km: float = 20.0
    max_surface_extrapolation_m: float = 10000.0
    bootstrap_replicates: int = 24
    max_bootstrap_angle_p90_deg: float = 35.0
    raster_step_m: float = 50.0
    raster_sigma_m: float = 100.0
    max_raster_halo_cells: int = 1
    robust_max_iterations: int = 3
    robust_mad_multiplier: float = 3.0
    random_seed: int = 5001


@dataclass(frozen=True)
class LineamentResult:
    score: np.ndarray
    metadata: dict[str, Any]


def _principal_axis(points: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    centered = points - np.mean(points, axis=0, keepdims=True)
    covariance = centered.T @ centered / max(1, points.shape[0] - 1)
    values, vectors = np.linalg.eigh(covariance)
    order = np.argsort(values)[::-1]
    return values[order], vectors[:, order]


def _robust_plane_inliers(
    xyz: np.ndarray,
    *,
    min_events: int,
    max_iterations: int,
    mad_multiplier: float,
) -> np.ndarray:
    """Iteratively trim orthogonal plane residual outliers using a MAD cutoff."""
    selected = np.arange(xyz.shape[0], dtype=np.int64)
    for _ in range(max_iterations):
        if selected.size < min_events:
            return np.empty(0, dtype=np.int64)
        points = xyz[selected]
        _, vectors = _principal_axis(points)
        center = np.mean(points, axis=0)
        normal = vectors[:, -1]
        residuals = np.abs((xyz - center) @ normal)
        current = residuals[selected]
        median = float(np.median(current))
        mad = float(np.median(np.abs(current - median)))
        robust_scale = max(1.4826 * mad, 1.0)
        threshold = median + mad_multiplier * robust_scale
        updated = selected[current <= threshold]
        if updated.size < min_events:
            return np.empty(0, dtype=np.int64)
        if updated.size == selected.size:
            break
        selected = updated
    return selected


def _surface_trace_from_plane(
    xyz: np.ndarray,
    min_horizontal_normal: float,
) -> tuple[np.ndarray, np.ndarray, float, float, float] | None:
    """Return the fitted plane's z=0 intersection line and geometric diagnostics.

    ``z`` is positive-down depth in metres. The 3-D plane is fitted to local
    hypocenters; its intersection with z=0 is used as the projected trace. A
    nearly horizontal plane has no stable surface intersection and is rejected.
    """
    values, vectors = _principal_axis(xyz)
    center = np.mean(xyz, axis=0)
    normal = vectors[:, -1]
    horizontal = normal[:2]
    horizontal_norm = float(np.linalg.norm(horizontal))
    if horizontal_norm < min_horizontal_normal:
        return None
    planarity = float(1.0 - values[-1] / max(values[-2], 1e-12))
    planarity = float(np.clip(planarity, 0.0, 1.0))
    signed_offset_m = float(normal[2] * center[2] / (horizontal_norm**2))
    surface_center = center[:2] + horizontal * signed_offset_m
    strike_axis = np.array([-normal[1], normal[0]], dtype=np.float64) / horizontal_norm
    extrapolation_m = float(abs(normal[2] * center[2] / horizontal_norm))
    return (
        surface_center,
        strike_axis,
        planarity,
        extrapolation_m,
        float(np.median(xyz[:, 2]) / 1000.0),
    )


def _bootstrap_trace_angle_p90(
    xyz: np.ndarray,
    axis: np.ndarray,
    rng: np.random.Generator,
    replicates: int,
    min_horizontal_normal: float,
) -> float:
    if xyz.shape[0] < 5:
        return 90.0
    n = xyz.shape[0]
    angles: list[float] = []
    for _ in range(replicates):
        sample = xyz[rng.integers(0, n, size=n)]
        try:
            _, vectors = _principal_axis(sample)
        except np.linalg.LinAlgError:
            angles.append(90.0)
            continue
        normal = vectors[:, -1]
        horizontal_norm = float(np.linalg.norm(normal[:2]))
        if horizontal_norm < min_horizontal_normal:
            angles.append(90.0)
            continue
        strike = np.array([-normal[1], normal[0]], dtype=np.float64) / horizontal_norm
        dot = float(np.clip(abs(np.dot(strike, axis)), 0.0, 1.0))
        angles.append(float(np.degrees(np.arccos(dot))))
    return float(np.percentile(angles, 90))


def _deduplicate_by_year_and_space(
    event_indices: np.ndarray,
    x: np.ndarray,
    y: np.ndarray,
    years: np.ndarray,
    cell_m: float,
) -> np.ndarray:
    ix = np.floor(x[event_indices] / cell_m).astype(np.int64)
    iy = np.floor(y[event_indices] / cell_m).astype(np.int64)
    keys = np.rec.fromarrays((years[event_indices], ix, iy), names="year,x,y")
    _, first = np.unique(keys, return_index=True)
    return event_indices[np.sort(first)]


def extract_h50s1_lineaments(
    events: CatalogEvents,
    template_path: str,
    config: LineamentConfig | None = None,
) -> LineamentResult:
    """Fit stable local relocated-event planes and rasterize their z=0 traces.

    The operation is unsupervised and does not read fault labels. It requires
    waveform-relocated events, multi-year support, a compact planar cluster,
    a coherent horizontal strike, a shallow/plausible plane-to-surface
    extrapolation, and bootstrap orientation stability. The output is a
    conservative 2-D proxy, not a claim that hypocenters directly mark surface
    traces.
    """
    config = config or LineamentConfig()
    with rasterio.open(template_path) as template:
        height, width = template.height, template.width
        transform = template.transform
        valid = np.isfinite(template.read(1))
        if not np.isclose(abs(transform.a), abs(transform.e)):
            raise ValueError("H50-S1 requires square, north-up pixels")
        pixel_m = float(abs(transform.a))
        if abs(transform.b) > 1e-9 or abs(transform.d) > 1e-9:
            raise ValueError("H50-S1 requires a north-up raster grid")
        x0, y0 = float(transform.c), float(transform.f)

    keep = events.relocated == 1
    if np.count_nonzero(keep) < config.min_events:
        raise ValueError(
            f"only {np.count_nonzero(keep)} relocated events fall in-grid; "
            f"need at least {config.min_events}"
        )
    x = np.asarray(events.x_m[keep], dtype=np.float64)
    y = np.asarray(events.y_m[keep], dtype=np.float64)
    z = np.asarray(events.depth_km[keep], dtype=np.float64) * 1000.0
    year = np.asarray(events.year[keep], dtype=np.int16)

    # One seed per occupied 500 m cell limits redundant local fits without
    # discarding the underlying observations used by each neighborhood fit.
    seed_cols = np.floor((x - x0) / config.seed_cell_m).astype(np.int64)
    seed_rows = np.floor((y0 - y) / config.seed_cell_m).astype(np.int64)
    seed_key_width = int(np.ceil(width * pixel_m / config.seed_cell_m)) + 1
    seed_keys = seed_rows * seed_key_width + seed_cols
    _, seed_first = np.unique(seed_keys, return_index=True)
    seed_indices = np.sort(seed_first)
    seed_xy = np.column_stack((x[seed_indices], y[seed_indices]))
    tree = cKDTree(np.column_stack((x, y)))

    score = np.zeros((height, width), dtype=np.float32)
    counts: dict[str, int] = {
        "seed_cells": int(seed_indices.size),
        "neighborhoods_queried": 0,
        "rejected_too_few_events": 0,
        "rejected_too_few_years": 0,
        "rejected_robust_too_few_inliers": 0,
        "rejected_short": 0,
        "rejected_low_linearity": 0,
        "rejected_too_wide": 0,
        "rejected_low_planarity": 0,
        "rejected_invalid_surface_plane": 0,
        "rejected_deep_or_large_extrapolation": 0,
        "rejected_misaligned_strike": 0,
        "rejected_unstable_bootstrap": 0,
        "accepted_segments": 0,
        "robust_inlier_observations_across_fits": 0,
    }
    accepted_scores: list[float] = []
    inlier_fractions: list[float] = []

    for seed_id, seed in enumerate(seed_xy):
        neighborhood = np.asarray(tree.query_ball_point(seed, r=config.radius_m), dtype=np.int64)
        counts["neighborhoods_queried"] += 1
        if neighborhood.size < config.min_events:
            counts["rejected_too_few_events"] += 1
            continue
        neighborhood = _deduplicate_by_year_and_space(
            neighborhood, x, y, year, config.dedupe_cell_m
        )
        if neighborhood.size < config.min_events:
            counts["rejected_too_few_events"] += 1
            continue
        xyz_all = np.column_stack((x[neighborhood], y[neighborhood], z[neighborhood]))
        inliers = _robust_plane_inliers(
            xyz_all,
            min_events=config.min_events,
            max_iterations=config.robust_max_iterations,
            mad_multiplier=config.robust_mad_multiplier,
        )
        if inliers.size < config.min_events:
            counts["rejected_robust_too_few_inliers"] += 1
            continue
        inlier_fraction = inliers.size / neighborhood.size
        inlier_fractions.append(float(inlier_fraction))
        neighborhood = neighborhood[inliers]
        counts["robust_inlier_observations_across_fits"] += int(neighborhood.size)
        years_here = np.unique(year[neighborhood])
        if years_here.size < config.min_years:
            counts["rejected_too_few_years"] += 1
            continue

        xy = np.column_stack((x[neighborhood], y[neighborhood]))
        xyz = np.column_stack((x[neighborhood], y[neighborhood], z[neighborhood]))
        values_2d, vectors_2d = _principal_axis(xy)
        if values_2d[0] <= 0:
            counts["rejected_short"] += 1
            continue
        linearity = float((values_2d[0] - values_2d[1]) / max(values_2d[0] + values_2d[1], 1e-12))
        width_m = float(4.0 * np.sqrt(max(values_2d[1], 0.0)))
        if linearity < config.min_linearity:
            counts["rejected_low_linearity"] += 1
            continue
        if width_m > config.max_horizontal_width_m:
            counts["rejected_too_wide"] += 1
            continue

        trace = _surface_trace_from_plane(xyz, config.min_horizontal_plane_normal)
        if trace is None:
            counts["rejected_invalid_surface_plane"] += 1
            continue
        trace_center, trace_axis, planarity, extrapolation_m, median_depth_km = trace
        if planarity < config.min_planarity_3d:
            counts["rejected_low_planarity"] += 1
            continue
        if (
            median_depth_km > config.max_median_depth_km
            or extrapolation_m > config.max_surface_extrapolation_m
        ):
            counts["rejected_deep_or_large_extrapolation"] += 1
            continue

        strike_alignment = float(abs(np.dot(vectors_2d[:, 0], trace_axis)))
        if strike_alignment < config.min_trace_strike_alignment:
            counts["rejected_misaligned_strike"] += 1
            continue
        projections = (xy - trace_center) @ trace_axis
        lo, hi = np.percentile(projections, [5.0, 95.0])
        length_m = float(hi - lo)
        if length_m < config.min_horizontal_length_m:
            counts["rejected_short"] += 1
            continue

        local_rng = np.random.default_rng(config.random_seed + seed_id)
        angle_p90 = _bootstrap_trace_angle_p90(
            xyz,
            trace_axis,
            local_rng,
            config.bootstrap_replicates,
            config.min_horizontal_plane_normal,
        )
        if angle_p90 > config.max_bootstrap_angle_p90_deg:
            counts["rejected_unstable_bootstrap"] += 1
            continue

        temporal_support = min(1.0, years_here.size / 3.0)
        event_support = min(1.0, neighborhood.size / 25.0)
        length_support = min(1.0, length_m / 3000.0)
        stability = max(0.0, 1.0 - angle_p90 / 60.0)
        quality = float(
            np.clip(
                linearity
                * planarity
                * temporal_support
                * event_support
                * length_support
                * stability
                * strike_alignment,
                0.0,
                1.0,
            )
        )
        if quality <= 0:
            continue

        sample_t = np.arange(lo, hi + config.raster_step_m, config.raster_step_m)
        line_xy = trace_center[None, :] + sample_t[:, None] * trace_axis[None, :]
        line_col = np.floor((line_xy[:, 0] - x0) / pixel_m).astype(np.int64)
        line_row = np.floor((y0 - line_xy[:, 1]) / pixel_m).astype(np.int64)
        offsets = range(-config.max_raster_halo_cells, config.max_raster_halo_cells + 1)
        rr_parts: list[np.ndarray] = []
        cc_parts: list[np.ndarray] = []
        vv_parts: list[np.ndarray] = []
        for dr in offsets:
            for dc in offsets:
                distance = np.hypot(dr * pixel_m, dc * pixel_m)
                if distance > config.max_raster_halo_cells * pixel_m + 1e-9:
                    continue
                weight = quality * np.exp(-0.5 * (distance / max(config.raster_sigma_m, 1.0)) ** 2)
                rr = line_row + dr
                cc = line_col + dc
                inside = (rr >= 0) & (rr < height) & (cc >= 0) & (cc < width)
                if np.any(inside):
                    rr_parts.append(rr[inside])
                    cc_parts.append(cc[inside])
                    vv_parts.append(np.full(np.count_nonzero(inside), weight, dtype=np.float32))
        if rr_parts:
            rr_all = np.concatenate(rr_parts)
            cc_all = np.concatenate(cc_parts)
            vv_all = np.concatenate(vv_parts)
            valid_points = valid[rr_all, cc_all]
            np.maximum.at(score, (rr_all[valid_points], cc_all[valid_points]), vv_all[valid_points])
            counts["accepted_segments"] += 1
            accepted_scores.append(quality)

    metadata: dict[str, Any] = {
        "method": "H50-S1 local relocated-event planes projected to their z=0 intersection",
        "config": asdict(config),
        "relocated_events_in_grid": int(x.size),
        "seed_cells": int(seed_indices.size),
        "counts": counts,
        "positive_score_cells": int(np.count_nonzero(score > 0)),
        "score_max": float(score.max(initial=0.0)),
        "accepted_quality_mean": float(np.mean(accepted_scores)) if accepted_scores else 0.0,
        "accepted_quality_median": float(np.median(accepted_scores)) if accepted_scores else 0.0,
        "robust_inlier_fraction_mean_across_fits": (
            float(np.mean(inlier_fractions)) if inlier_fractions else 0.0
        ),
        "candidate_cells_outside_template_valid": int(np.count_nonzero((score > 0) & ~valid)),
        "note": (
            "The plane-to-surface projection is a heuristic, not a verified surface trace. "
            "The catalog lacks event-specific location-error covariance; all geometry is "
            "therefore a research proxy and must pass the frozen mapped-trace holdout."
        ),
    }
    score[~valid] = 0.0
    return LineamentResult(score=score, metadata=metadata)
