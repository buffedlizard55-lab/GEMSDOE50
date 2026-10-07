"""H53-A: survey-normalized shallow-temperature point geometry tied to TMI lineaments.

This module deliberately treats thermal probes as marked points and requires a local PCA
lineation plus an independent TMI orientation match. It does not build a heat-density surface
as the candidate. Data loading is separate from holdout scoring so the frozen protocol can be
audited and tested without ever passing labels into this feature builder.
"""
from __future__ import annotations

from dataclasses import dataclass
from io import BytesIO
from pathlib import Path
from typing import Any
from zipfile import ZipFile

import numpy as np
import rasterio
import shapefile
from pyproj import Transformer
from rasterio.transform import rowcol
from scipy.ndimage import distance_transform_edt, gaussian_filter
from scipy.spatial import cKDTree
from scipy.stats import rankdata

from gems51.structfield import layer_lineament


@dataclass(frozen=True)
class ProbePoints:
    """GDR probe locations transformed to the prediction grid."""

    area: np.ndarray
    row: np.ndarray
    col: np.ndarray
    x: np.ndarray
    y: np.ndarray
    anomaly: np.ndarray

    def __len__(self) -> int:
        return int(self.row.size)


@dataclass(frozen=True)
class TmiLineaments:
    """Relative lineament strength/orientation from the quantized TMI_up150 layer."""

    strength: np.ndarray
    angle: np.ndarray
    coherence: np.ndarray
    ridge_mask: np.ndarray
    distance_px: np.ndarray
    nearest_row: np.ndarray
    nearest_col: np.ndarray
    threshold: float


def read_probe_points(
    archive_path: str | Path,
    *,
    transform: rasterio.Affine,
    valid: np.ndarray,
    target_crs: str = "EPSG:32611",
) -> tuple[ProbePoints, dict[str, Any]]:
    """Read only the GDR temperature-probe shapefile and transform its NAD83 points.

    The workbook and derived sibling CSV are intentionally not read. `F2mDAB` is retained as
    supplied; no undocumented distance-to-fault, catalogue, or label-derived field is consumed.
    """
    archive_path = Path(archive_path)
    valid = np.asarray(valid, dtype=bool)
    if valid.ndim != 2:
        raise ValueError("valid footprint must be a 2-D mask")
    if not archive_path.is_file():
        raise FileNotFoundError(archive_path)

    with ZipFile(archive_path) as archive:
        shp_names = [name for name in archive.namelist() if name.lower().endswith(".shp")]
        if len(shp_names) != 1:
            raise ValueError(f"expected exactly one shapefile in {archive_path}, found {len(shp_names)}")
        shp_name = shp_names[0]
        stem = shp_name[:-4]
        members = {name.lower(): name for name in archive.namelist()}
        suffixes = (".shp", ".shx", ".dbf")
        payloads: dict[str, bytes] = {}
        for suffix in suffixes:
            key = (stem + suffix).lower()
            if key not in members:
                raise ValueError(f"shapefile component missing: {stem + suffix}")
            payloads[suffix] = archive.read(members[key])
        reader = shapefile.Reader(
            shp=BytesIO(payloads[".shp"]),
            shx=BytesIO(payloads[".shx"]),
            dbf=BytesIO(payloads[".dbf"]),
            encoding="utf-8",
        )
        field_names = [str(field[0]) for field in reader.fields[1:]]
        required = {"Area", "F2mDAB"}
        missing = required.difference(field_names)
        if missing:
            raise ValueError(f"temperature-probe DBF lacks required fields {sorted(missing)}")
        to_grid = Transformer.from_crs("EPSG:4269", target_crs, always_xy=True)
        xs: list[float] = []
        ys: list[float] = []
        rows: list[int] = []
        cols: list[int] = []
        areas: list[str] = []
        anomalies: list[float] = []
        total = 0
        invalid_fields = 0
        outside = 0
        src_utm_diff: list[float] = []
        index = {name: idx for idx, name in enumerate(field_names)}
        has_utm = "UTM_E" in index and "UTM_N" in index
        for record in reader.iterShapeRecords():
            total += 1
            values = record.record
            shape_points = record.shape.points
            if not shape_points:
                invalid_fields += 1
                continue
            try:
                lon, lat = map(float, shape_points[0])
                anomaly = float(values[index["F2mDAB"]])
                area = str(values[index["Area"]]).strip()
                if not area or not np.isfinite(anomaly):
                    raise ValueError
            except (TypeError, ValueError, IndexError):
                invalid_fields += 1
                continue
            x, y = to_grid.transform(lon, lat)
            if has_utm:
                try:
                    src_x = float(values[index["UTM_E"]])
                    src_y = float(values[index["UTM_N"]])
                    if np.isfinite(src_x) and np.isfinite(src_y):
                        src_utm_diff.append(float(np.hypot(x - src_x, y - src_y)))
                except (TypeError, ValueError):
                    pass
            row, col = rowcol(transform, x, y)
            row, col = int(row), int(col)
            if not (0 <= row < valid.shape[0] and 0 <= col < valid.shape[1]) or not valid[row, col]:
                outside += 1
                continue
            xs.append(float(x))
            ys.append(float(y))
            rows.append(row)
            cols.append(col)
            areas.append(area)
            anomalies.append(anomaly)

    if not rows:
        raise ValueError("no finite GDR probe points fall inside the valid prediction footprint")
    points = ProbePoints(
        area=np.asarray(areas, dtype=str),
        row=np.asarray(rows, dtype=np.int32),
        col=np.asarray(cols, dtype=np.int32),
        x=np.asarray(xs, dtype=np.float64),
        y=np.asarray(ys, dtype=np.float64),
        anomaly=np.asarray(anomalies, dtype=np.float32),
    )
    audit = {
        "archive": str(archive_path),
        "shapefile_member": shp_name,
        "source_crs": "EPSG:4269 (NAD83 geographic; archive .prj inspected)",
        "target_crs": target_crs,
        "records_total": total,
        "records_valid_in_footprint": len(points),
        "records_invalid_or_missing": invalid_fields,
        "records_outside_footprint": outside,
        "area_groups_before_deduplication": int(np.unique(points.area).size),
        "utm_coordinate_crosscheck_n": len(src_utm_diff),
        "utm_coordinate_crosscheck_median_m": float(np.median(src_utm_diff)) if src_utm_diff else None,
        "utm_coordinate_crosscheck_p95_m": float(np.percentile(src_utm_diff, 95)) if src_utm_diff else None,
        "source_units_for_F2mDAB": "not specified in the inspected archive README; use only relative within-Area ranking",
    }
    return points, audit


def deduplicate_area_cells(points: ProbePoints) -> tuple[ProbePoints, dict[str, Any]]:
    """Reduce same-Area/same-grid-cell duplicates to their median anomaly."""
    grouped: dict[tuple[str, int, int], list[int]] = {}
    for idx, key in enumerate(zip(points.area, points.row, points.col, strict=True)):
        grouped.setdefault((str(key[0]), int(key[1]), int(key[2])), []).append(idx)
    areas: list[str] = []
    rows: list[int] = []
    cols: list[int] = []
    xs: list[float] = []
    ys: list[float] = []
    anomalies: list[float] = []
    for (area, row, col), ids in sorted(grouped.items()):
        areas.append(area)
        rows.append(row)
        cols.append(col)
        xs.append(float(np.median(points.x[ids])))
        ys.append(float(np.median(points.y[ids])))
        anomalies.append(float(np.median(points.anomaly[ids])))
    result = ProbePoints(
        area=np.asarray(areas, dtype=str),
        row=np.asarray(rows, dtype=np.int32),
        col=np.asarray(cols, dtype=np.int32),
        x=np.asarray(xs, dtype=np.float64),
        y=np.asarray(ys, dtype=np.float64),
        anomaly=np.asarray(anomalies, dtype=np.float32),
    )
    return result, {
        "input_points": len(points),
        "unique_area_grid_cells": len(result),
        "duplicate_area_grid_rows_collapsed": len(points) - len(result),
    }


def warm_probe_marks(
    points: ProbePoints,
    *,
    minimum_area_points: int = 12,
    within_area_quantile: float = 0.75,
) -> tuple[np.ndarray, np.ndarray, dict[str, Any]]:
    """Select positive, within-area upper-quartile marks and return their normalized ranks."""
    if not 0.0 < within_area_quantile < 1.0:
        raise ValueError("within_area_quantile must be between zero and one")
    warm = np.zeros(len(points), dtype=bool)
    ranks = np.zeros(len(points), dtype=np.float32)
    records: list[dict[str, Any]] = []
    for area in sorted(np.unique(points.area).tolist()):
        ids = np.flatnonzero(points.area == area)
        vals = points.anomaly[ids].astype(np.float64)
        if ids.size < minimum_area_points:
            records.append({"area": str(area), "n": int(ids.size), "used": False,
                            "reason": "below_minimum_area_points"})
            continue
        threshold = float(np.quantile(vals, within_area_quantile))
        area_ranks = rankdata(vals, method="average") / max(float(ids.size), 1.0)
        ranks[ids] = area_ranks.astype(np.float32)
        mask = (vals > 0.0) & (vals >= threshold)
        warm[ids] = mask
        records.append({"area": str(area), "n": int(ids.size), "used": True,
                        "q75_F2mDAB": threshold, "positive_upper_quartile_n": int(mask.sum())})
    return warm, ranks, {
        "minimum_area_points": minimum_area_points,
        "within_area_quantile": within_area_quantile,
        "warm_points": int(warm.sum()),
        "areas": records,
    }


def _components(points_xy: np.ndarray, radius_m: float) -> list[np.ndarray]:
    """Connected components of a radius graph, returned as local row-index arrays."""
    n = int(points_xy.shape[0])
    if n == 0:
        return []
    parent = np.arange(n, dtype=np.int32)
    rank = np.zeros(n, dtype=np.int8)

    def find(value: int) -> int:
        while parent[value] != value:
            parent[value] = parent[parent[value]]
            value = int(parent[value])
        return value

    def union(a: int, b: int) -> None:
        ra, rb = find(a), find(b)
        if ra == rb:
            return
        if rank[ra] < rank[rb]:
            ra, rb = rb, ra
        parent[rb] = ra
        if rank[ra] == rank[rb]:
            rank[ra] += 1

    pairs = cKDTree(points_xy).query_pairs(radius_m, output_type="ndarray")
    for a, b in pairs:
        union(int(a), int(b))
    groups: dict[int, list[int]] = {}
    for idx in range(n):
        groups.setdefault(find(idx), []).append(idx)
    return [np.asarray(group, dtype=np.int32) for group in groups.values()]


def axial_angle_difference(a: float | np.ndarray, b: float | np.ndarray) -> np.ndarray:
    """Smallest absolute angle difference for unoriented axes (period π)."""
    delta = np.asarray(a, dtype=np.float64) - np.asarray(b, dtype=np.float64)
    return np.abs((delta + np.pi / 2.0) % np.pi - np.pi / 2.0)


def build_tmi_lineaments(
    tmi_u8: np.ndarray,
    valid: np.ndarray,
    *,
    scales: tuple[float, ...] = (2.0, 5.0, 10.0),
    coherence_sigma: float = 3.0,
    ridge_quantile: float = 0.95,
    coherence_min: float = 0.25,
) -> TmiLineaments:
    """Build relative TMI lineaments without treating uint8 ranks as physical units."""
    tmi = np.asarray(tmi_u8)
    valid = np.asarray(valid, dtype=bool)
    if tmi.shape != valid.shape:
        raise ValueError("TMI and valid footprint shapes differ")
    tmi_valid = valid & np.isfinite(tmi) & (tmi > 0)
    if not tmi_valid.any():
        raise ValueError("TMI band has no valid cells inside the sample footprint")
    filled_value = float(np.median(tmi[tmi_valid]))
    filled = np.where(tmi_valid, tmi.astype(np.float32), filled_value)
    strength, angle, coherence = layer_lineament(
        filled, tmi_valid, scales=scales, coherence_sigma=coherence_sigma
    )
    threshold = float(np.quantile(strength[tmi_valid], ridge_quantile))
    ridge = tmi_valid & (strength >= threshold) & (coherence >= coherence_min)
    if not ridge.any():
        raise ValueError("no TMI lineament ridge cells meet the frozen threshold")
    distance_px, nearest = distance_transform_edt(~ridge, return_indices=True)
    return TmiLineaments(
        strength=np.asarray(strength, dtype=np.float32),
        angle=np.asarray(angle, dtype=np.float32),
        coherence=np.asarray(coherence, dtype=np.float32),
        ridge_mask=ridge,
        distance_px=distance_px.astype(np.float32),
        nearest_row=nearest[0].astype(np.int32),
        nearest_col=nearest[1].astype(np.int32),
        threshold=threshold,
    )


def _burn_gaussian_segment(
    output: np.ndarray,
    start: np.ndarray,
    end: np.ndarray,
    weight: float,
    transform: rasterio.Affine,
    valid: np.ndarray,
    *,
    sigma_px: float,
    pixel_size_m: float,
) -> None:
    """Max-combine one axis-aligned Gaussian corridor, limited to 3 sigma."""
    if weight <= 0 or not np.isfinite(weight):
        return
    buffer_m = 3.0 * sigma_px * pixel_size_m
    x0, y0 = map(float, start)
    x1, y1 = map(float, end)
    col0 = int(np.floor((min(x0, x1) - buffer_m - transform.c) / transform.a))
    col1 = int(np.floor((max(x0, x1) + buffer_m - transform.c) / transform.a)) + 1
    row0 = int(np.floor((transform.f - (max(y0, y1) + buffer_m)) / -transform.e))
    row1 = int(np.floor((transform.f - (min(y0, y1) - buffer_m)) / -transform.e)) + 1
    row0, row1 = max(row0, 0), min(row1, output.shape[0])
    col0, col1 = max(col0, 0), min(col1, output.shape[1])
    if row0 >= row1 or col0 >= col1:
        return
    rr, cc = np.mgrid[row0:row1, col0:col1]
    xx = transform.c + (cc + 0.5) * transform.a
    yy = transform.f + (rr + 0.5) * transform.e
    vx, vy = x1 - x0, y1 - y0
    denom = max(vx * vx + vy * vy, 1e-12)
    fraction = np.clip(((xx - x0) * vx + (yy - y0) * vy) / denom, 0.0, 1.0)
    dx = xx - (x0 + fraction * vx)
    dy = yy - (y0 + fraction * vy)
    distance = np.hypot(dx, dy)
    sigma_m = sigma_px * pixel_size_m
    local = weight * np.exp(-0.5 * (distance / sigma_m) ** 2)
    keep = (distance <= buffer_m) & valid[row0:row1, col0:col1]
    view = output[row0:row1, col0:col1]
    np.maximum(view, np.where(keep, local, 0.0).astype(np.float32), out=view)


def build_probe_lineation(
    points: ProbePoints,
    ranks: np.ndarray,
    warm: np.ndarray,
    lineaments: TmiLineaments,
    *,
    transform: rasterio.Affine,
    valid: np.ndarray,
    pixel_size_m: float = 100.0,
    cluster_radius_m: float = 1500.0,
    minimum_cluster_points: int = 5,
    minimum_axis_ratio: float = 3.0,
    minimum_length_m: float = 800.0,
    maximum_length_m: float = 20_000.0,
    max_tmi_distance_px: float = 5.0,
    max_angle_deg: float = 30.0,
    minimum_tmi_alignment: float = 0.50,
    corridor_sigma_px: float = 1.5,
) -> tuple[np.ndarray, dict[str, Any]]:
    """Build survey-bounded warm-probe PCA axes that align with TMI lineaments."""
    valid = np.asarray(valid, dtype=bool)
    warm = np.asarray(warm, dtype=bool)
    ranks = np.asarray(ranks, dtype=np.float32)
    if warm.shape != (len(points),) or ranks.shape != (len(points),):
        raise ValueError("warm/rank arrays must have one value per probe")
    if lineaments.strength.shape != valid.shape:
        raise ValueError("lineament/footprint shape mismatch")
    output = np.zeros(valid.shape, dtype=np.float32)
    records: list[dict[str, Any]] = []
    cos_limit = np.deg2rad(max_angle_deg)
    cluster_id = 0
    for area in sorted(np.unique(points.area[warm]).tolist()):
        area_ids = np.flatnonzero(warm & (points.area == area))
        if area_ids.size == 0:
            continue
        xy = np.column_stack([points.x[area_ids], points.y[area_ids]])
        for component in _components(xy, cluster_radius_m):
            cluster_id += 1
            ids = area_ids[component]
            base = {"cluster_id": cluster_id, "area": str(area), "n_points": int(ids.size)}
            if ids.size < minimum_cluster_points:
                records.append({**base, "accepted": False, "reason": "too_few_points"})
                continue
            cluster_xy = xy[component]
            center = cluster_xy.mean(axis=0)
            centered = cluster_xy - center
            cov = centered.T @ centered / max(float(ids.size), 1.0)
            eigenvalues, eigenvectors = np.linalg.eigh(cov)
            major = eigenvectors[:, -1]
            ratio = float(eigenvalues[-1] / max(float(eigenvalues[-2]), 1e-9))
            projections = centered @ major
            lo, hi = np.percentile(projections, [5.0, 95.0])
            length = float(hi - lo)
            if ratio < minimum_axis_ratio:
                records.append({**base, "accepted": False, "reason": "low_axis_ratio",
                                "axis_ratio": ratio, "length_m": length})
                continue
            if not minimum_length_m <= length <= maximum_length_m:
                records.append({**base, "accepted": False, "reason": "axis_length_out_of_range",
                                "axis_ratio": ratio, "length_m": length})
                continue
            start = center + lo * major
            end = center + hi * major
            n_samples = max(2, int(np.ceil(length / pixel_size_m)) + 1)
            fractions = np.linspace(0.0, 1.0, n_samples)
            sample_xy = start[None, :] + fractions[:, None] * (end - start)[None, :]
            sample_rows, sample_cols = rowcol(transform, sample_xy[:, 0], sample_xy[:, 1])
            sample_rows = np.asarray(sample_rows, dtype=np.int64)
            sample_cols = np.asarray(sample_cols, dtype=np.int64)
            inside = ((sample_rows >= 0) & (sample_rows < valid.shape[0]) &
                      (sample_cols >= 0) & (sample_cols < valid.shape[1]))
            nearest_rows = np.zeros(n_samples, dtype=np.int64)
            nearest_cols = np.zeros(n_samples, dtype=np.int64)
            distance_px = np.full(n_samples, np.inf, dtype=np.float32)
            nearest_angle = np.zeros(n_samples, dtype=np.float32)
            ids_inside = np.flatnonzero(inside)
            if ids_inside.size:
                rr, cc = sample_rows[ids_inside], sample_cols[ids_inside]
                nearest_rows[ids_inside] = lineaments.nearest_row[rr, cc]
                nearest_cols[ids_inside] = lineaments.nearest_col[rr, cc]
                distance_px[ids_inside] = lineaments.distance_px[rr, cc]
                nearest_angle[ids_inside] = lineaments.angle[
                    nearest_rows[ids_inside], nearest_cols[ids_inside]
                ]
            axis_angle = float(np.arctan2(major[1], major[0]))
            angle_delta = axial_angle_difference(axis_angle, nearest_angle)
            aligned = inside & (distance_px <= max_tmi_distance_px) & (angle_delta <= cos_limit)
            alignment_fraction = float(aligned.mean())
            if alignment_fraction < minimum_tmi_alignment:
                records.append({**base, "accepted": False, "reason": "weak_tmi_alignment",
                                "axis_ratio": ratio, "length_m": length,
                                "tmi_alignment_fraction": alignment_fraction})
                continue
            mean_tmi_strength = float(np.mean(
                lineaments.strength[nearest_rows[aligned], nearest_cols[aligned]]
            )) if np.any(aligned) else 0.0
            anomaly_rank = float(np.median(ranks[ids]))
            weight = float(np.clip(anomaly_rank * alignment_fraction * mean_tmi_strength, 0.0, 1.0))
            _burn_gaussian_segment(output, start, end, weight, transform, valid,
                                   sigma_px=corridor_sigma_px, pixel_size_m=pixel_size_m)
            records.append({**base, "accepted": True, "axis_ratio": ratio, "length_m": length,
                            "tmi_alignment_fraction": alignment_fraction,
                            "median_area_anomaly_rank": anomaly_rank,
                            "mean_aligned_tmi_strength": mean_tmi_strength,
                            "weight": weight,
                            "axis_start_xy_m": [float(start[0]), float(start[1])],
                            "axis_end_xy_m": [float(end[0]), float(end[1])]})
    output[~valid] = 0.0
    return output, {
        "cluster_radius_m": cluster_radius_m,
        "minimum_cluster_points": minimum_cluster_points,
        "minimum_axis_ratio": minimum_axis_ratio,
        "axis_length_m": [minimum_length_m, maximum_length_m],
        "maximum_tmi_distance_px": max_tmi_distance_px,
        "maximum_angle_deg": max_angle_deg,
        "minimum_tmi_alignment_fraction": minimum_tmi_alignment,
        "corridor_sigma_px": corridor_sigma_px,
        "ridge_threshold_p95": lineaments.threshold,
        "ridge_pixels": int(lineaments.ridge_mask.sum()),
        "clusters_tested": len(records),
        "clusters_accepted": int(sum(bool(item["accepted"]) for item in records)),
        "clusters": records,
        "positive_score_cells": int(np.count_nonzero(output > 0)),
        "score_max": float(output.max(initial=0.0)),
    }


def build_probe_density(
    points: ProbePoints,
    warm: np.ndarray,
    ranks: np.ndarray,
    valid: np.ndarray,
    *,
    sigma_px: float,
) -> np.ndarray:
    """Matched control: Gaussian-smoothed warm-probe marks, with no point geometry."""
    if sigma_px <= 0:
        raise ValueError("sigma_px must be positive")
    valid = np.asarray(valid, dtype=bool)
    field = np.zeros(valid.shape, dtype=np.float32)
    np.add.at(field, (points.row[warm], points.col[warm]), ranks[warm])
    field = gaussian_filter(field, sigma=sigma_px, mode="constant", cval=0.0)
    field[~valid] = 0.0
    maximum = float(field.max(initial=0.0))
    if maximum > 0:
        field /= maximum
    return field


def build_tmi_only_control(lineaments: TmiLineaments, valid: np.ndarray) -> np.ndarray:
    """Control: TMI lineament strength without the thermal-probe point pattern."""
    valid = np.asarray(valid, dtype=bool)
    out = np.where(lineaments.ridge_mask, lineaments.strength, 0.0).astype(np.float32)
    out[~valid] = 0.0
    maximum = float(out.max(initial=0.0))
    if maximum > 0:
        out /= maximum
    return out
