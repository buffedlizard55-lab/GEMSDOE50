from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

import numpy as np
import rasterio
from scipy.spatial import cKDTree

from .catalog import CatalogEvents
from .raster import check_same_grid


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
    surface_root_spacing_m: float = 100.0
    min_surface_sample_fraction: float = 0.90
    max_surface_residual_m: float = 5.0
    # Explicit diagnostic approximation only: the catalog depth datum is described as
    # mean sea level, while the 3DEP mosaic can contain source DEMs in different vertical
    # datums. A zero offset is NOT a verified datum transformation and blocks slot use.
    assumed_navd88_minus_msl_m: float = 0.0
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


def _sample_surface_bilinear(
    surface_m: np.ndarray,
    surface_valid: np.ndarray,
    transform: rasterio.Affine,
    x: np.ndarray,
    y: np.ndarray,
) -> np.ndarray:
    """Bilinearly sample the cell-centred DEM, requiring all four neighbours valid."""
    x = np.asarray(x, dtype=np.float64)
    y = np.asarray(y, dtype=np.float64)
    col_corner, row_corner = (~transform) @ (x, y)
    col_center = np.asarray(col_corner) - 0.5
    row_center = np.asarray(row_corner) - 0.5
    col0 = np.floor(col_center).astype(np.int64)
    row0 = np.floor(row_center).astype(np.int64)
    dx = col_center - col0
    dy = row_center - row0

    height, width = surface_m.shape
    inside = (row0 >= 0) & (col0 >= 0) & (row0 + 1 < height) & (col0 + 1 < width)
    result = np.full(x.shape, np.nan, dtype=np.float64)
    selected = np.flatnonzero(inside)
    if selected.size == 0:
        return result

    r = row0.flat[selected]
    c = col0.flat[selected]
    corners_valid = (
        surface_valid[r, c]
        & surface_valid[r, c + 1]
        & surface_valid[r + 1, c]
        & surface_valid[r + 1, c + 1]
    )
    selected = selected[corners_valid]
    if selected.size == 0:
        return result

    r = row0.flat[selected]
    c = col0.flat[selected]
    fx = dx.flat[selected]
    fy = dy.flat[selected]
    z00 = surface_m[r, c]
    z01 = surface_m[r, c + 1]
    z10 = surface_m[r + 1, c]
    z11 = surface_m[r + 1, c + 1]
    result.flat[selected] = (
        z00 * (1.0 - fx) * (1.0 - fy)
        + z01 * fx * (1.0 - fy)
        + z10 * (1.0 - fx) * fy
        + z11 * fx * fy
    )
    return result


def _surface_trace_from_plane(
    xyz: np.ndarray,
    surface_m: np.ndarray,
    surface_valid: np.ndarray,
    surface_transform: rasterio.Affine,
    config: LineamentConfig,
) -> tuple[np.ndarray, np.ndarray, float, float, float, float, float] | None:
    """Numerically intersect a fitted 3-D plane with a terrain-elevation raster.

    Event coordinates use x/y in projected metres and z=-depth in metres (positive up,
    relative to the catalog's stated mean-sea-level reference). For each along-strike
    position, the routine brackets and solves the plane equation against bilinearly
    sampled DEM elevations. The DEM's vertical datum is not transformed here; the
    configured zero-offset NAVD88/MSL approximation is explicitly diagnostic only.

    Returns the surface polyline, strike axis, planarity, 95th-percentile horizontal
    extrapolation, median positive-down depth, valid root fraction, and maximum residual.
    """
    values, vectors = _principal_axis(xyz)
    center = np.mean(xyz, axis=0)
    normal = vectors[:, -1]
    horizontal_norm = float(np.linalg.norm(normal[:2]))
    if horizontal_norm < config.min_horizontal_plane_normal:
        return None

    strike_axis = np.array([-normal[1], normal[0]], dtype=np.float64) / horizontal_norm
    dip_axis = normal[:2] / horizontal_norm
    planarity = float(1.0 - values[-1] / max(values[-2], 1e-12))
    planarity = float(np.clip(planarity, 0.0, 1.0))

    projections = (xyz[:, :2] - center[:2]) @ strike_axis
    lo, hi = np.percentile(projections, [5.0, 95.0])
    if not np.isfinite(lo + hi) or hi <= lo:
        return None
    sample_count = max(2, int(np.ceil((hi - lo) / config.raster_step_m)) + 1)
    along = np.linspace(lo, hi, sample_count, dtype=np.float64)

    root_step = max(float(config.surface_root_spacing_m), 1.0)
    root_intervals = max(1, int(np.ceil(config.max_surface_extrapolation_m / root_step)))
    cross_strike = np.linspace(
        -config.max_surface_extrapolation_m,
        config.max_surface_extrapolation_m,
        2 * root_intervals + 1,
        dtype=np.float64,
    )
    line_x = (
        center[0]
        + along[:, None] * strike_axis[0]
        + cross_strike[None, :] * dip_axis[0]
    )
    line_y = (
        center[1]
        + along[:, None] * strike_axis[1]
        + cross_strike[None, :] * dip_axis[1]
    )
    sampled_dem = _sample_surface_bilinear(
        surface_m,
        surface_valid,
        surface_transform,
        line_x.ravel(),
        line_y.ravel(),
    ).reshape(line_x.shape)
    # Convert NAVD88-like DEM values to the catalog's depth reference using only the
    # explicit approximation in config. A verified local datum grid is still required.
    sampled_msl = sampled_dem - config.assumed_navd88_minus_msl_m
    residual = (
        horizontal_norm * cross_strike[None, :]
        + normal[2] * (sampled_msl - center[2])
    )

    dem_at_center = _sample_surface_bilinear(
        surface_m,
        surface_valid,
        surface_transform,
        np.asarray([center[0]]),
        np.asarray([center[1]]),
    )[0]
    if np.isfinite(dem_at_center):
        center_msl = dem_at_center - config.assumed_navd88_minus_msl_m
        flat_terrain_guess = -normal[2] * (center_msl - center[2]) / horizontal_norm
    else:
        flat_terrain_guess = 0.0

    root_q = np.full(along.size, np.nan, dtype=np.float64)
    root_residual = np.full(along.size, np.nan, dtype=np.float64)
    for index in range(along.size):
        f = residual[index]
        finite_pairs = np.isfinite(f[:-1]) & np.isfinite(f[1:])
        crosses = finite_pairs & (
            (f[:-1] == 0.0)
            | (f[1:] == 0.0)
            | ((f[:-1] < 0.0) & (f[1:] > 0.0))
            | ((f[:-1] > 0.0) & (f[1:] < 0.0))
        )
        candidates = np.flatnonzero(crosses)
        if candidates.size == 0:
            continue
        bracket_midpoints = 0.5 * (cross_strike[candidates] + cross_strike[candidates + 1])
        bracket_index = int(candidates[np.argmin(np.abs(bracket_midpoints - flat_terrain_guess))])
        q_left = float(cross_strike[bracket_index])
        q_right = float(cross_strike[bracket_index + 1])
        f_left = float(f[bracket_index])
        f_right = float(f[bracket_index + 1])

        if f_left == 0.0:
            q = q_left
        elif f_right == 0.0:
            q = q_right
        else:
            q = 0.5 * (q_left + q_right)
            for _ in range(24):
                q = 0.5 * (q_left + q_right)
                xq = center[0] + along[index] * strike_axis[0] + q * dip_axis[0]
                yq = center[1] + along[index] * strike_axis[1] + q * dip_axis[1]
                dem_q = _sample_surface_bilinear(
                    surface_m,
                    surface_valid,
                    surface_transform,
                    np.asarray([xq]),
                    np.asarray([yq]),
                )[0]
                if not np.isfinite(dem_q):
                    break
                f_mid = float(
                    horizontal_norm * q
                    + normal[2]
                    * (dem_q - config.assumed_navd88_minus_msl_m - center[2])
                )
                if abs(f_mid) <= config.max_surface_residual_m:
                    break
                if (f_left <= 0.0 and f_mid >= 0.0) or (f_left >= 0.0 and f_mid <= 0.0):
                    q_right, f_right = q, f_mid
                else:
                    q_left, f_left = q, f_mid

        xq = center[0] + along[index] * strike_axis[0] + q * dip_axis[0]
        yq = center[1] + along[index] * strike_axis[1] + q * dip_axis[1]
        dem_q = _sample_surface_bilinear(
            surface_m,
            surface_valid,
            surface_transform,
            np.asarray([xq]),
            np.asarray([yq]),
        )[0]
        if not np.isfinite(dem_q) or abs(q) > config.max_surface_extrapolation_m:
            continue
        final_residual = abs(
            horizontal_norm * q
            + normal[2]
            * (dem_q - config.assumed_navd88_minus_msl_m - center[2])
        )
        if final_residual <= config.max_surface_residual_m:
            root_q[index] = q
            root_residual[index] = final_residual

    root_valid = np.isfinite(root_q)
    support_fraction = float(root_valid.mean()) if root_valid.size else 0.0
    if not np.any(root_valid):
        return None

    trace_xy = (
        center[:2]
        + along[root_valid, None] * strike_axis[None, :]
        + root_q[root_valid, None] * dip_axis[None, :]
    )
    extrapolation_p95 = float(np.percentile(np.abs(root_q[root_valid]), 95.0))
    median_depth_km = float(np.median(-xyz[:, 2]) / 1000.0)
    maximum_residual = float(np.max(root_residual[root_valid]))
    return (
        trace_xy,
        strike_axis,
        planarity,
        extrapolation_p95,
        median_depth_km,
        support_fraction,
        maximum_residual,
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


def extract_h50s1_lineaments(
    events: CatalogEvents,
    template_path: str,
    surface_dem_path: str,
    config: LineamentConfig | None = None,
) -> LineamentResult:
    """Fit stable local relocated-event planes and intersect them with terrain.

    The operation is unsupervised and does not read fault labels. It requires
    waveform-relocated events, multi-year support, a compact planar cluster,
    coherent horizontal strike, and bootstrap orientation stability. The 3-D plane is
    intersected with bilinearly sampled DEM elevations; it is not projected to a sea-level
    ``z=0`` plane. No location-uncertainty weighting or earthquake declustering is applied,
    and the NAVD88/MSL datum offset is only approximated as zero. The result is a research
    diagnostic, not a validated or slot-eligible surface-fault trace.
    """
    config = config or LineamentConfig()
    with rasterio.open(template_path) as template, rasterio.open(surface_dem_path) as dem_ds:
        check_same_grid(template, dem_ds)
        if template.count != 1 or dem_ds.count != 1:
            raise ValueError("H50-S1 requires single-band template and DEM rasters")
        height, width = template.height, template.width
        transform = template.transform
        template_raw = template.read(1, masked=True)
        valid = np.isfinite(np.asarray(template_raw.filled(np.nan))) & ~np.ma.getmaskarray(template_raw)
        dem_raw = dem_ds.read(1, masked=True)
        surface_m = np.asarray(dem_raw.filled(np.nan), dtype=np.float64)
        surface_valid = np.isfinite(surface_m) & ~np.ma.getmaskarray(dem_raw)
        dem_transform = dem_ds.transform
        if not np.any(surface_valid):
            raise ValueError("surface DEM has no finite, unmasked elevation cells")
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
    # The catalog documents depth as positive below mean sea level; use positive-up z.
    z = -np.asarray(events.depth_km[keep], dtype=np.float64) * 1000.0
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
        "rejected_no_surface_intersection": 0,
        "rejected_insufficient_surface_support": 0,
        "rejected_surface_residual": 0,
        "rejected_deep_or_large_extrapolation": 0,
        "rejected_misaligned_strike": 0,
        "rejected_unstable_bootstrap": 0,
        "accepted_segments": 0,
        "robust_inlier_observations_across_fits": 0,
    }
    accepted_scores: list[float] = []
    inlier_fractions: list[float] = []
    surface_support_fractions: list[float] = []
    surface_extrapolations: list[float] = []
    surface_residuals: list[float] = []

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

        trace = _surface_trace_from_plane(
            xyz,
            surface_m,
            surface_valid,
            dem_transform,
            config,
        )
        if trace is None:
            counts["rejected_no_surface_intersection"] += 1
            continue
        (
            line_xy,
            trace_axis,
            planarity,
            extrapolation_m,
            median_depth_km,
            surface_support,
            surface_residual_m,
        ) = trace
        if surface_support < config.min_surface_sample_fraction:
            counts["rejected_insufficient_surface_support"] += 1
            continue
        if surface_residual_m > config.max_surface_residual_m:
            counts["rejected_surface_residual"] += 1
            continue
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
        projections = (xy - np.mean(xy, axis=0, keepdims=True)) @ trace_axis
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
                * strike_alignment
                * surface_support,
                0.0,
                1.0,
            )
        )
        if quality <= 0:
            continue

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
            surface_support_fractions.append(surface_support)
            surface_extrapolations.append(extrapolation_m)
            surface_residuals.append(surface_residual_m)

    metadata: dict[str, Any] = {
        "method": "H50-S1 local relocated-event planes intersected with 3DEP terrain elevations",
        "config": asdict(config),
        "relocated_events_in_grid": int(x.size),
        "seed_cells": int(seed_indices.size),
        "counts": counts,
        "surface_projection": {
            "elevation_sign": "DEM elevation positive up; catalog depth positive down, converted as z=-depth_m",
            "catalog_vertical_reference": "mean sea level, per Trugman catalog paper",
            "dem_vertical_reference": "3DEP dynamic mosaic sources are not confirmed here to share one vertical datum",
            "assumed_navd88_minus_msl_m": config.assumed_navd88_minus_msl_m,
            "datum_conversion_verified": False,
            "surface_support_fraction_mean": (
                float(np.mean(surface_support_fractions)) if surface_support_fractions else 0.0
            ),
            "surface_extrapolation_p95_m_median": (
                float(np.median(surface_extrapolations)) if surface_extrapolations else 0.0
            ),
            "surface_residual_m_max": max(surface_residuals, default=0.0),
        },
        "positive_score_cells": int(np.count_nonzero(score > 0)),
        "score_max": float(score.max(initial=0.0)),
        "accepted_quality_mean": float(np.mean(accepted_scores)) if accepted_scores else 0.0,
        "accepted_quality_median": float(np.median(accepted_scores)) if accepted_scores else 0.0,
        "robust_inlier_fraction_mean_across_fits": (
            float(np.mean(inlier_fractions)) if inlier_fractions else 0.0
        ),
        "candidate_cells_outside_template_valid": int(np.count_nonzero((score > 0) & ~valid)),
        "scientific_limitations": [
            "No event-specific location-uncertainty covariance is present in the input table.",
            "No standard declustering is applied; aftershock/swarms may dominate local fits.",
            "No event-type, injection-site, geothermal-well, mine, or quarry exclusion layer is applied.",
            "Catalog depth and exported DEM vertical datums are not exactly reconciled; zero offset is an assumption.",
            "DEM surface descriptors can include non-fault terrain breaks; this candidate uses elevation only.",
        ],
        "note": (
            "Terrain intersection replaces the invalid sea-level z=0 projection, but the current "
            "NAVD88/mean-sea-level zero-offset assumption and missing event uncertainty, declustering, "
            "event-type/site filters prevent any claim of a validated surface-fault trace or submission eligibility."
        ),
    }
    score[~valid] = 0.0
    return LineamentResult(score=score, metadata=metadata)
