from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

import numpy as np
import rasterio
from pyproj import Transformer

from .common import sha256_file


@dataclass(frozen=True)
class CatalogEvents:
    evid: np.ndarray
    year: np.ndarray
    latitude: np.ndarray
    longitude: np.ndarray
    depth_km: np.ndarray
    magnitude: np.ndarray
    relocated: np.ndarray
    x_m: np.ndarray
    y_m: np.ndarray
    row: np.ndarray
    col: np.ndarray
    metadata: dict[str, Any]


def _parse_documented_record(
    line: str, line_number: int
) -> tuple[int, int, float, float, float, float, int]:
    """Parse the exact documented seven-column record.

    The Zenodo header is ``evid otime lat lon dep mag reloc``. Since ``otime`` is
    quoted and contains a space, the post-quote suffix has five tokens. This
    parser handles that exact schema and emits a clear error for any drift.
    """
    fields = line.split('"')
    if len(fields) != 3:
        raise ValueError(f"catalog line {line_number}: expected one quoted origin time")
    left, right = fields[0].split(), fields[2].split()
    if len(left) != 1 or len(right) != 5:
        raise ValueError(
            f"catalog line {line_number}: expected 1 id + quoted time + 5 values, "
            f"got {len(left)} + quoted + {len(right)}"
        )
    evid = int(left[0])
    origin_time = fields[1].strip()
    try:
        year = datetime.fromisoformat(origin_time).year
    except ValueError as exc:
        raise ValueError(
            f"catalog line {line_number}: invalid origin time {origin_time!r}"
        ) from exc
    latitude, longitude, depth_km, magnitude = map(float, right[:4])
    relocated = int(right[4])
    if relocated not in (0, 1):
        raise ValueError(f"catalog line {line_number}: reloc must be 0 or 1, got {relocated}")
    if not (-90 <= latitude <= 90 and -180 <= longitude <= 180):
        raise ValueError(f"catalog line {line_number}: invalid geographic coordinates")
    return evid, year, latitude, longitude, depth_km, magnitude, relocated


def read_nevada_catalog(
    catalog_path: str | Path,
    template_path: str | Path,
    *,
    require_sha256: str | None = None,
) -> CatalogEvents:
    """Read and project the published Nevada catalog, retaining points in-grid.

    The catalog format is checked against its published seven-column header.
    Geographic filtering is done against the finite cells of the submission
    template; no fault labels are read by this function.
    """
    catalog_path = Path(catalog_path)
    if require_sha256:
        actual = sha256_file(catalog_path)
        if actual.lower() != require_sha256.lower():
            raise ValueError(f"catalog SHA-256 mismatch: expected {require_sha256}, got {actual}")

    with rasterio.open(template_path) as template:
        height, width = template.height, template.width
        transform = template.transform
        crs = template.crs
        template_valid = np.isfinite(template.read(1))
        if crs is None:
            raise ValueError("template raster has no CRS")

    rows: list[int] = []
    years: list[int] = []
    latitudes: list[float] = []
    longitudes: list[float] = []
    depths: list[float] = []
    magnitudes: list[float] = []
    relocated: list[int] = []
    source_count = 0
    first_nonempty = True
    with catalog_path.open("rt", encoding="utf-8-sig", errors="strict") as stream:
        for line_number, line in enumerate(stream, start=1):
            line = line.strip()
            if not line:
                continue
            if first_nonempty:
                first_nonempty = False
                header = line.split()
                expected = ["evid", "otime", "lat", "lon", "dep", "mag", "reloc"]
                if [v.lower() for v in header] != expected:
                    raise ValueError(
                        "unexpected catalog header; expected "
                        + " ".join(expected)
                        + f", got {line!r}"
                    )
                continue
            source_count += 1
            evid, year, lat, lon, depth, mag, reloc = _parse_documented_record(line, line_number)
            if not all(np.isfinite(v) for v in (lat, lon, depth, mag)):
                raise ValueError(f"catalog line {line_number}: non-finite measurement")
            rows.append(evid)
            years.append(year)
            latitudes.append(lat)
            longitudes.append(lon)
            depths.append(depth)
            magnitudes.append(mag)
            relocated.append(reloc)

    if first_nonempty:
        raise ValueError("catalog file is empty")
    if source_count == 0:
        raise ValueError("catalog contains a header but no events")

    evid_a = np.asarray(rows, dtype=np.int64)
    year_a = np.asarray(years, dtype=np.int16)
    lat_a = np.asarray(latitudes, dtype=np.float64)
    lon_a = np.asarray(longitudes, dtype=np.float64)
    depth_a = np.asarray(depths, dtype=np.float32)
    mag_a = np.asarray(magnitudes, dtype=np.float32)
    reloc_a = np.asarray(relocated, dtype=np.uint8)

    transformer = Transformer.from_crs("EPSG:4326", crs, always_xy=True)
    x_all, y_all = transformer.transform(lon_a, lat_a)
    x_all = np.asarray(x_all, dtype=np.float64)
    y_all = np.asarray(y_all, dtype=np.float64)
    col_f, row_f = (~transform) @ (x_all, y_all)
    col_all = np.floor(col_f).astype(np.int64)
    row_all = np.floor(row_f).astype(np.int64)
    in_bounds = (row_all >= 0) & (row_all < height) & (col_all >= 0) & (col_all < width)
    indices = np.flatnonzero(in_bounds)
    in_template = np.zeros(source_count, dtype=bool)
    in_template[indices] = template_valid[row_all[indices], col_all[indices]]
    keep = in_template
    if not np.any(keep):
        raise ValueError("no Nevada catalog events fall within finite submission-template cells")

    counts = {
        "catalog_sha256": sha256_file(catalog_path),
        "source_event_rows": int(source_count),
        "in_template_valid_cells": int(keep.sum()),
        "outside_template_or_nodata": int((~keep).sum()),
        "relocated_source_rows": int(np.count_nonzero(reloc_a == 1)),
        "nonrelocated_source_rows": int(np.count_nonzero(reloc_a == 0)),
        "relocated_in_template": int(np.count_nonzero(keep & (reloc_a == 1))),
        "nonrelocated_in_template": int(np.count_nonzero(keep & (reloc_a == 0))),
        "year_min": int(year_a.min()),
        "year_max": int(year_a.max()),
        "in_template_year_min": int(year_a[keep].min()),
        "in_template_year_max": int(year_a[keep].max()),
        "unique_relocated_years_in_template": int(np.unique(year_a[keep & (reloc_a == 1)]).size),
        "unique_event_ids": int(np.unique(evid_a).size),
        "duplicate_event_id_rows": int(evid_a.size - np.unique(evid_a).size),
        "negative_depth_rows": int(np.count_nonzero(depth_a < 0)),
        "negative_magnitude_rows": int(np.count_nonzero(mag_a < 0)),
        "depth_km_min": float(depth_a.min()),
        "depth_km_max": float(depth_a.max()),
        "magnitude_min": float(mag_a.min()),
        "magnitude_max": float(mag_a.max()),
        "relocated_in_grid_negative_depth_rows": int(
            np.count_nonzero(keep & (reloc_a == 1) & (depth_a < 0))
        ),
    }

    return CatalogEvents(
        evid=evid_a[keep],
        year=year_a[keep],
        latitude=lat_a[keep],
        longitude=lon_a[keep],
        depth_km=depth_a[keep],
        magnitude=mag_a[keep],
        relocated=reloc_a[keep],
        x_m=x_all[keep],
        y_m=y_all[keep],
        row=row_all[keep].astype(np.int32),
        col=col_all[keep].astype(np.int32),
        metadata=counts,
    )
