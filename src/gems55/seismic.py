"""Licence-clean earthquake point geometry for H55-S1.

The event geometry comes from the CC BY 4.0 Nevada relocated catalog. The local
triangle-area background test is a project-specific, unverified 2-D adaptation; it
must not be represented as the published 3-D tetrahedron method.
"""
from __future__ import annotations

import csv
import gzip
import hashlib
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
import rasterio
from pyproj import Transformer
from scipy import ndimage
from scipy.spatial import cKDTree

CATALOG_MD5 = "38fa663f473378b61c74b597c53c416b"
CATALOG_BYTES = 13_833_354
MINE_EVENT_TYPES = frozenset(
    {
        "explosion",
        "quarry blast",
        "nuclear explosion",
        "chemical explosion",
        "mining explosion",
        "mine collapse",
        "quarry",
        "anthropogenic event",
    }
)


@dataclass(frozen=True)
class H55Config:
    geothermal_buffer_m: float = 2_000.0
    anthropogenic_buffer_m: float = 3_000.0
    dedupe_cell_m: float = 250.0
    dedupe_window_days: float = 90.0
    background_neighbour_k: int = 20
    background_surrogates: int = 32
    background_p_max: float = 0.20
    seed_cell_m: float = 1_000.0
    neighbourhood_radius_m: float = 5_000.0
    min_events: int = 10
    min_years: int = 3
    min_linearity: float = 0.60
    min_length_m: float = 1_500.0
    bootstrap_replicates: int = 24
    max_bootstrap_angle_p90_deg: float = 30.0
    random_seed: int = 5501


@dataclass(frozen=True)
class CatalogFrame:
    evid: np.ndarray
    time_days: np.ndarray
    year: np.ndarray
    x_m: np.ndarray
    y_m: np.ndarray
    depth_km: np.ndarray
    magnitude: np.ndarray
    row: np.ndarray
    col: np.ndarray
    metadata: dict[str, Any]

    def subset(self, keep: np.ndarray) -> CatalogFrame:
        keep = np.asarray(keep)
        return CatalogFrame(
            evid=self.evid[keep],
            time_days=self.time_days[keep],
            year=self.year[keep],
            x_m=self.x_m[keep],
            y_m=self.y_m[keep],
            depth_km=self.depth_km[keep],
            magnitude=self.magnitude[keep],
            row=self.row[keep],
            col=self.col[keep],
            metadata=dict(self.metadata),
        )

    def __len__(self) -> int:
        return int(self.evid.size)


@dataclass(frozen=True)
class AxisSegments:
    x_m: np.ndarray
    y_m: np.ndarray
    ux: np.ndarray
    uy: np.ndarray
    lo_m: np.ndarray
    hi_m: np.ndarray
    quality: np.ndarray
    linearity: np.ndarray
    n_events: np.ndarray
    n_years: np.ndarray
    p_area_median: np.ndarray
    bootstrap_angle_p90_deg: np.ndarray
    metadata: dict[str, Any]

    def __len__(self) -> int:
        return int(self.x_m.size)


def _md5_and_size_gzip(path: Path) -> tuple[str, int]:
    digest = hashlib.md5()
    size = 0
    with gzip.open(path, "rb") as stream:
        for chunk in iter(lambda: stream.read(1 << 20), b""):
            digest.update(chunk)
            size += len(chunk)
    return digest.hexdigest(), size


def _origin_day_and_year(text: str) -> tuple[float, int]:
    dt = datetime.fromisoformat(text).replace(tzinfo=timezone.utc)
    return dt.timestamp() / 86_400.0, dt.year


def _read_relocated_catalog(path: Path) -> dict[str, np.ndarray]:
    md5, byte_count = _md5_and_size_gzip(path)
    if md5 != CATALOG_MD5 or byte_count != CATALOG_BYTES:
        raise ValueError(
            f"relocated catalog identity mismatch: md5={md5}, bytes={byte_count}"
        )
    columns: dict[str, list] = {
        "evid": [],
        "time_days": [],
        "year": [],
        "lat": [],
        "lon": [],
        "depth_km": [],
        "magnitude": [],
        "reloc": [],
    }
    with gzip.open(path, "rt", encoding="utf-8", errors="strict") as stream:
        header = stream.readline().strip().split()
        if [h.lower() for h in header] != [
            "evid",
            "otime",
            "lat",
            "lon",
            "dep",
            "mag",
            "reloc",
        ]:
            raise ValueError(f"unexpected relocated-catalog header: {header!r}")
        for line_number, line in enumerate(stream, start=2):
            line = line.strip()
            if not line:
                continue
            quoted = line.split('"')
            if len(quoted) != 3:
                raise ValueError(f"catalog line {line_number}: malformed quoted origin time")
            left = quoted[0].split()
            right = quoted[2].split()
            if len(left) != 1 or len(right) != 5:
                raise ValueError(f"catalog line {line_number}: schema drift")
            day, year = _origin_day_and_year(quoted[1].strip())
            columns["evid"].append(int(left[0]))
            columns["time_days"].append(day)
            columns["year"].append(year)
            columns["lat"].append(float(right[0]))
            columns["lon"].append(float(right[1]))
            columns["depth_km"].append(float(right[2]))
            columns["magnitude"].append(float(right[3]))
            columns["reloc"].append(int(right[4]))
    return {
        "evid": np.asarray(columns["evid"], dtype=np.int64),
        "time_days": np.asarray(columns["time_days"], dtype=np.float64),
        "year": np.asarray(columns["year"], dtype=np.int16),
        "lat": np.asarray(columns["lat"], dtype=np.float64),
        "lon": np.asarray(columns["lon"], dtype=np.float64),
        "depth_km": np.asarray(columns["depth_km"], dtype=np.float32),
        "magnitude": np.asarray(columns["magnitude"], dtype=np.float32),
        "reloc": np.asarray(columns["reloc"], dtype=np.uint8),
    }


def _read_hot_centres(path: Path) -> np.ndarray:
    points: set[tuple[float, float]] = set()
    with path.open("rt", encoding="utf-8", newline="") as stream:
        for row in csv.DictReader(stream):
            if (row.get("thermalclass") or "").strip() != "Hot":
                continue
            try:
                x = float(row["utm_x"])
                y = float(row["utm_y"])
            except (KeyError, TypeError, ValueError):
                continue
            if np.isfinite(x) and np.isfinite(y):
                points.add((x, y))
    return np.asarray(sorted(points), dtype=np.float64).reshape(-1, 2)


def _read_anthropogenic_centres(path: Path) -> tuple[np.ndarray, dict[str, int]]:
    points: set[tuple[float, float]] = set()
    counts: dict[str, int] = {}
    transformer = Transformer.from_crs("EPSG:4326", "EPSG:32611", always_xy=True)
    with gzip.open(path, "rt", encoding="utf-8", newline="") as stream:
        for row in csv.DictReader(stream):
            event_type = (row.get("type") or "").strip().lower()
            if event_type not in MINE_EVENT_TYPES:
                continue
            try:
                lon = float(row["longitude"])
                lat = float(row["latitude"])
            except (KeyError, TypeError, ValueError):
                continue
            if not (np.isfinite(lon) and np.isfinite(lat)):
                continue
            x, y = transformer.transform(lon, lat)
            points.add((round(float(x), 3), round(float(y), 3)))
            counts[event_type] = counts.get(event_type, 0) + 1
    return np.asarray(sorted(points), dtype=np.float64).reshape(-1, 2), counts


def _remove_near(xy: np.ndarray, centres: np.ndarray, radius_m: float) -> np.ndarray:
    if centres.size == 0:
        return np.ones(xy.shape[0], dtype=bool)
    distance, _ = cKDTree(centres).query(xy, k=1)
    return distance > radius_m


def _sequence_thin(frame: CatalogFrame, config: H55Config) -> tuple[CatalogFrame, dict]:
    ix = np.floor(frame.x_m / config.dedupe_cell_m).astype(np.int64)
    iy = np.floor(frame.y_m / config.dedupe_cell_m).astype(np.int64)
    it = np.floor(frame.time_days / config.dedupe_window_days).astype(np.int64)
    # Last sort key is primary. Within each space-time group, largest magnitude and then
    # smallest event ID appears first.
    order = np.lexsort((frame.evid, -frame.magnitude, it, iy, ix))
    first = np.ones(order.size, dtype=bool)
    if order.size > 1:
        a, b = order[1:], order[:-1]
        first[1:] = (ix[a] != ix[b]) | (iy[a] != iy[b]) | (it[a] != it[b])
    selected = np.sort(order[first])
    return frame.subset(selected), {
        "rule": "largest magnitude per 250 m UTM cell per 90-day Unix-epoch window; event-id tie break",
        "events_in": len(frame),
        "events_out": int(selected.size),
        "events_removed": int(len(frame) - selected.size),
    }


def build_catalog_frame(
    catalog_gz: str | Path,
    template: str | Path,
    hot_points_csv: str | Path,
    comcat_gz: str | Path,
    config: H55Config | None = None,
) -> CatalogFrame:
    """Load, screen, project, and sequence-thin the relocated earthquake catalog."""
    config = config or H55Config()
    source = _read_relocated_catalog(Path(catalog_gz))
    transformer = Transformer.from_crs("EPSG:4326", "EPSG:32611", always_xy=True)
    x, y = transformer.transform(source["lon"], source["lat"])
    x = np.asarray(x, dtype=np.float64)
    y = np.asarray(y, dtype=np.float64)

    with rasterio.open(template) as ds:
        valid = np.isfinite(ds.read(1))
        inverse = ~ds.transform
        width, height = ds.width, ds.height
        template_crs = str(ds.crs)
    col_f, row_f = inverse * (x, y)
    row = np.floor(row_f).astype(np.int32)
    col = np.floor(col_f).astype(np.int32)
    in_bounds = (row >= 0) & (row < height) & (col >= 0) & (col < width)
    in_footprint = np.zeros(row.shape, dtype=bool)
    idx = np.flatnonzero(in_bounds)
    in_footprint[idx] = valid[row[idx], col[idx]]
    base = (
        (source["reloc"] == 1)
        & in_footprint
        & np.isfinite(source["depth_km"])
        & (source["depth_km"] >= 0.0)
        & (source["depth_km"] <= 25.0)
    )
    base_indices = np.flatnonzero(base)
    xy = np.column_stack((x[base], y[base]))

    hot = _read_hot_centres(Path(hot_points_csv))
    keep_hot = _remove_near(xy, hot, config.geothermal_buffer_m)
    blast, type_counts = _read_anthropogenic_centres(Path(comcat_gz))
    keep_blast = _remove_near(xy, blast, config.anthropogenic_buffer_m)
    keep_local = keep_hot & keep_blast
    selected = base_indices[keep_local]

    frame = CatalogFrame(
        evid=source["evid"][selected],
        time_days=source["time_days"][selected],
        year=source["year"][selected],
        x_m=x[selected],
        y_m=y[selected],
        depth_km=source["depth_km"][selected],
        magnitude=source["magnitude"][selected],
        row=row[selected],
        col=col[selected],
        metadata={},
    )
    thinned, thin_report = _sequence_thin(frame, config)
    thinned.metadata.update(
        {
            "source": "Trugman (2024) Nevada relocated catalog, Zenodo 11167510",
            "license": "CC BY 4.0",
            "source_rows": int(source["evid"].size),
            "relocated_in_finite_footprint_nonnegative_depth": int(base.sum()),
            "hot_centres": int(hot.shape[0]),
            "events_removed_hot_2km": int(np.count_nonzero(~keep_hot)),
            "anthropogenic_event_centres": int(blast.shape[0]),
            "anthropogenic_type_counts": type_counts,
            "events_removed_anthropogenic_3km": int(np.count_nonzero(~keep_blast)),
            "events_after_site_screens": int(selected.size),
            "sequence_thinning": thin_report,
            "template_crs": template_crs,
            "config": asdict(config),
            "limitations": [
                "GDR hot points are an incomplete geothermal-operation/injection screen.",
                "ComCat explicit blast/mine/quarry event locations are an incomplete mining screen.",
                "The mixed-network ComCat export's contributor-specific redistribution status is unresolved.",
                "The relocated catalog has no event-specific location covariance.",
            ],
        }
    )
    return thinned


def _normalised_triangle_stat(xy: np.ndarray, k: int) -> np.ndarray:
    if xy.shape[0] <= k:
        raise ValueError(f"need more than {k} points for the normalized triangle statistic")
    distance, neighbours = cKDTree(xy).query(xy, k=k + 1)
    a = xy[neighbours[:, 1]] - xy
    b = xy[neighbours[:, 2]] - xy
    area = 0.5 * np.abs(a[:, 0] * b[:, 1] - a[:, 1] * b[:, 0])
    return area / np.maximum(distance[:, k] ** 2, 1e-12)


def normalized_triangle_filter(
    frame: CatalogFrame,
    valid: np.ndarray,
    transform: rasterio.Affine,
    config: H55Config | None = None,
) -> tuple[CatalogFrame, np.ndarray, dict]:
    """Remove Poisson-like background with a local-density-normalized triangle test.

    This test is the project's own unverified 2-D adaptation, not a published transfer of
    the 3-D tetrahedron test.
    """
    config = config or H55Config()
    xy = np.column_stack((frame.x_m, frame.y_m))
    observed = _normalised_triangle_stat(xy, config.background_neighbour_k)
    valid_cells = np.argwhere(np.asarray(valid, dtype=bool))
    if valid_cells.size == 0:
        raise ValueError("template has no finite cells")
    rng = np.random.default_rng(config.random_seed)
    reference: list[np.ndarray] = []
    for _ in range(config.background_surrogates):
        cells = valid_cells[rng.integers(0, valid_cells.shape[0], size=len(frame))]
        jitter_row = rng.random(len(frame))
        jitter_col = rng.random(len(frame))
        rows = cells[:, 0] + jitter_row
        cols = cells[:, 1] + jitter_col
        xs, ys = transform * (cols, rows)
        random_xy = np.column_stack((xs, ys))
        reference.append(_normalised_triangle_stat(random_xy, config.background_neighbour_k))
    ref = np.sort(np.concatenate(reference))
    p_area = np.searchsorted(ref, observed, side="right") / float(ref.size)
    keep = p_area <= config.background_p_max
    report = {
        "status": "UNVERIFIED_2D_ADAPTATION",
        "method": (
            "area(event, nn1, nn2) / distance(event, nn20)^2; reference CDF from "
            "uniform random catalogs on finite template cells"
        ),
        "events_in": len(frame),
        "surrogate_catalogs": config.background_surrogates,
        "surrogate_points_total": int(ref.size),
        "p_threshold": config.background_p_max,
        "events_kept": int(keep.sum()),
        "fraction_kept": float(keep.mean()),
        "observed_stat_quantiles": [
            float(v) for v in np.quantile(observed, [0.05, 0.5, 0.95])
        ],
        "reference_stat_quantiles": [
            float(v) for v in np.quantile(ref, [0.05, 0.5, 0.95])
        ],
    }
    kept = frame.subset(keep)
    kept.metadata.update(frame.metadata)
    kept.metadata["background_test"] = report
    return kept, p_area[keep], report


def _axis_angle_deg(a: np.ndarray, b: np.ndarray) -> float:
    dot = float(np.clip(abs(np.dot(a, b)), 0.0, 1.0))
    return float(np.degrees(np.arccos(dot)))


def fit_axes(
    frame: CatalogFrame,
    p_area: np.ndarray,
    config: H55Config | None = None,
) -> AxisSegments:
    """Fit recurrent, elongated local epicentre covariance axes."""
    config = config or H55Config()
    xy = np.column_stack((frame.x_m, frame.y_m))
    tree = cKDTree(xy)
    seed_cells = np.floor(xy / config.seed_cell_m).astype(np.int64)
    _, seed_index = np.unique(seed_cells, axis=0, return_index=True)
    seed_index = np.sort(seed_index)
    rows: list[tuple[float, ...]] = []
    rejected = {
        "too_few_events": 0,
        "too_few_years": 0,
        "low_linearity": 0,
        "short": 0,
        "unstable_bootstrap": 0,
    }
    for seed in seed_index:
        nb = np.asarray(
            tree.query_ball_point(xy[seed], r=config.neighbourhood_radius_m), dtype=np.int64
        )
        if nb.size < config.min_events:
            rejected["too_few_events"] += 1
            continue
        n_years = int(np.unique(frame.year[nb]).size)
        if n_years < config.min_years:
            rejected["too_few_years"] += 1
            continue
        points = xy[nb]
        centre = np.mean(points, axis=0)
        delta = points - centre
        covariance = delta.T @ delta / max(points.shape[0] - 1, 1)
        values, vectors = np.linalg.eigh(covariance)
        lambda2, lambda1 = float(values[0]), float(values[1])
        linearity = (lambda1 - lambda2) / max(lambda1 + lambda2, 1e-12)
        if linearity < config.min_linearity:
            rejected["low_linearity"] += 1
            continue
        axis = vectors[:, 1]
        along = delta @ axis
        lo, hi = np.quantile(along, [0.05, 0.95])
        length = float(hi - lo)
        if length < config.min_length_m:
            rejected["short"] += 1
            continue
        local_rng = np.random.default_rng(config.random_seed + int(seed))
        bootstrap_angles: list[float] = []
        for _ in range(config.bootstrap_replicates):
            sample = points[local_rng.integers(0, points.shape[0], size=points.shape[0])]
            centered = sample - np.mean(sample, axis=0)
            sample_cov = centered.T @ centered / max(sample.shape[0] - 1, 1)
            sample_axis = np.linalg.eigh(sample_cov)[1][:, 1]
            bootstrap_angles.append(_axis_angle_deg(axis, sample_axis))
        p90 = float(np.percentile(bootstrap_angles, 90))
        if p90 > config.max_bootstrap_angle_p90_deg:
            rejected["unstable_bootstrap"] += 1
            continue
        components = np.array(
            [
                np.clip(linearity, 1e-3, 1.0),
                np.clip(nb.size / 25.0, 1e-3, 1.0),
                np.clip(n_years / 5.0, 1e-3, 1.0),
                np.clip(length / 5_000.0, 1e-3, 1.0),
                np.clip(1.0 - p90 / 30.0, 1e-3, 1.0),
                np.clip(1.0 - float(np.median(p_area[nb])), 1e-3, 1.0),
            ],
            dtype=np.float64,
        )
        quality = float(np.exp(np.mean(np.log(components))))
        rows.append(
            (
                float(centre[0]),
                float(centre[1]),
                float(axis[0]),
                float(axis[1]),
                float(lo),
                float(hi),
                quality,
                float(linearity),
                float(nb.size),
                float(n_years),
                float(np.median(p_area[nb])),
                p90,
            )
        )
    if rows:
        values = np.asarray(rows, dtype=np.float64)
        arrays = [values[:, i] for i in range(values.shape[1])]
    else:
        arrays = [np.zeros(0, dtype=np.float64) for _ in range(12)]
    metadata = {
        "method": "full 2-D covariance of recurrent local epicentre neighborhoods",
        "config": asdict(config),
        "events": len(frame),
        "seed_cells": int(seed_index.size),
        "accepted_segments": len(rows),
        "rejected": rejected,
        "median_segment_length_m": (
            float(np.median(arrays[5] - arrays[4])) if rows else None
        ),
        "median_linearity": float(np.median(arrays[7])) if rows else None,
        "median_quality": float(np.median(arrays[6])) if rows else None,
        "limitation": (
            "2-D epicentre axes are corridor priors, not mapped traces; the source table has no "
            "event-specific location covariance."
        ),
    }
    return AxisSegments(
        x_m=arrays[0],
        y_m=arrays[1],
        ux=arrays[2],
        uy=arrays[3],
        lo_m=arrays[4],
        hi_m=arrays[5],
        quality=arrays[6],
        linearity=arrays[7],
        n_events=arrays[8].astype(np.int32),
        n_years=arrays[9].astype(np.int16),
        p_area_median=arrays[10],
        bootstrap_angle_p90_deg=arrays[11],
        metadata=metadata,
    )


def make_density_field(
    frame: CatalogFrame,
    shape: tuple[int, int],
    valid: np.ndarray,
    sigma_m: float,
    pixel_m: float = 100.0,
) -> np.ndarray:
    """Gaussian count-density control from exactly the background-filtered points."""
    counts = np.zeros(shape, dtype=np.float32)
    np.add.at(counts, (frame.row, frame.col), 1.0)
    field = ndimage.gaussian_filter(
        counts, sigma=sigma_m / pixel_m, mode="constant", cval=0.0
    )
    field[~np.asarray(valid, dtype=bool)] = 0.0
    maximum = float(field.max(initial=0.0))
    if maximum > 0:
        field /= maximum
    return field.astype(np.float32, copy=False)
