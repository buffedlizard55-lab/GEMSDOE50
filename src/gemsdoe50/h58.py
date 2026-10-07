"""H58 — ComCat epicentre point-geometry lineations as the primary prediction field.

This module implements the owner-mandated method as a *standalone* submission
candidate (H55 used the relocated catalogue and failed; H56 used ComCat
lineations only as a 0.25-weight corroboration on the LiDAR scarp belief; no
shipped artifact makes ComCat point geometry the primary field):

1.  Epicentres come from the public USGS ANSS ComCat extract
    (``data/external/usgs_comcat_earthquakes.csv.gz``, hash-pinned below).
    Official service URL: https://earthquake.usgs.gov/fdsnws/event/1/query
    Licence: USGS-authored data are U.S. public domain
    (https://www.usgs.gov/information-policies-and-instructions/copyrights-and-credits);
    the extract is mixed-contributor (nc 62.8 %, nn 35.0 %, ci 1.6 %, us 0.5 %),
    so contributor-specific sponsor-sharing status is recorded as a flagged
    conflict between ``docs/research/comcat-license-review-20261007.md``
    (cleared with attribution) and ``registry/sources.json`` /
    ``data/external/README.md`` (unresolved).  A research artifact that is
    never uploaded is permitted under either reading.
2.  Known injection/mining/anthropogenic activity is removed twice: the ComCat
    ``type`` filter drops every non-tectonic event type (545 rows in this
    extract), and a 3 km buffer around the explicit anthropogenic event
    centres removes nearby tectonic events.  A GDR-1391 hot-feature 2 km
    screen is applied when the CSV is present and recorded as a limitation
    when it is not (it is absent in this sandbox).
3.  Clustered events are separated from an uncorrelated background by the
    2-D triangle-area analogue of the Ouillon & Sornette (2011) tetrahedron
    test (``h56.triangle_area_keep``).  That 2-D reduction is this project's
    own and is **unverified** against published results; it is labelled as
    such everywhere it is used and is not the published 3-D algorithm, and it
    is not ACLUD (Wang et al. 2013, arXiv:1304.6912).
4.  For each retained epicentre, the full 2-D covariance of its k nearest
    neighbours is eigendecomposed; neighbourhoods are kept only when they are
    linear (sigma1/sigma2 above a floor), well sampled (enough events, long
    enough principal axis), and thinner than their own location error
    (the 2-D reduction of the published 3-D rule lambda_3 < Delta^2).
5.  Each accepted neighbourhood becomes a corridor oriented along its
    principal axis whose half-width is the catalogue's own epicentral
    uncertainty (``horizontalError``; median 0.36 km in this extract).  At
    100 m pixels that is several pixels: a **corridor prior, not a trace**.

Smoothed earthquake density is never an input here; it is only a matched
falsification control built from exactly the same declustered events.
"""
from __future__ import annotations

import gzip
from dataclasses import dataclass
from datetime import timezone
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import rasterio
from pyproj import Transformer
from scipy import ndimage
from scipy.spatial import cKDTree

from . import h56

#: SHA-256 of the committed ComCat extract (measured 2026-10-07 in this sandbox).
COMCAT_SHA256 = "19e726c8d0640ad0bdf9c239ae4a855dc1fef18956cfcc7ec9f34b45eb314c82"

#: ComCat ``type`` values treated as explicit anthropogenic/blast sites for the
#: 3 km site screen (H55 precedent; the event-type filter is separate).
ANTHROPOGENIC_TYPES = frozenset(
    {
        "explosion",
        "quarry blast",
        "nuclear explosion",
        "chemical explosion",
        "mining explosion",
        "mine collapse",
        "quarry",
        "acoustic noise",
        "sonic boom",
        "rockslide",
        "anthropogenic event",
    }
)

#: Frozen H58 processing constants (preregistered in
#: docs/research/h58-hypotheses-preregistered.md before this code ran).
MIN_MAG = 1.5
MAX_DEPTH_KM = 25.0
MAX_HORIZONTAL_ERROR_KM = 10.0
ANTHROPOGENIC_BUFFER_M = 3_000.0
HOT_FEATURE_BUFFER_M = 2_000.0
TRIANGLE_QUANTILE = 0.95
TRIANGLE_SEED = 20_261_007
LINEATION_K = 10
LINEATION_MIN_EVENTS = 6
LINEATION_MIN_ELONGATION = 3.0
LINEATION_MIN_SIGMA1_M = 800.0
EMIT_MIN_SEP_PX = 3.0
EMIT_SEED = 571_007
MASSES = (30_000, 45_000, 60_000, 75_000, 90_000, 110_000, 130_000, 160_000, 220_000)
G_HIDDEN = 12_226
TRANSFER = 4.2
SGMC_OFF_TRUTH_PX = 61_664  # calibrated off-catalogue frame size (docs/research/h56-diagnosis.md)


@dataclass(frozen=True)
class EventFrame:
    """Screened, projected, declustered ComCat events in grid metres."""

    x_m: np.ndarray
    y_m: np.ndarray
    sigma_km: np.ndarray
    row: np.ndarray
    col: np.ndarray
    mag: np.ndarray
    time_days: np.ndarray
    year: np.ndarray
    metadata: dict[str, Any]

    def __len__(self) -> int:
        return int(self.x_m.size)


def load_comcat(path: str | Path) -> tuple[pd.DataFrame, dict[str, Any]]:
    """Read the hash-pinned ComCat extract; refuse to run on drifted bytes."""
    import hashlib

    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            digest.update(block)
    sha = digest.hexdigest()
    if sha != COMCAT_SHA256:
        raise ValueError(f"ComCat extract hash mismatch: {sha} != {COMCAT_SHA256}")
    df = pd.read_csv(path)
    required = {"time", "latitude", "longitude", "depth", "mag", "type", "horizontalError"}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"ComCat extract missing columns: {sorted(missing)}")
    report = {
        "path": str(path),
        "sha256": sha,
        "rows": len(df),
        "first": str(df["time"].iloc[0]),
        "last": str(df["time"].iloc[-1]),
        "source": "https://earthquake.usgs.gov/fdsnws/event/1/query (ANSS ComCat)",
        "bbox": {
            "minlatitude": 37.27,
            "maxlatitude": 40.79,
            "minlongitude": -120.10,
            "maxlongitude": -116.08,
        },
    }
    return df, report


def _parse_time_days(series: pd.Series) -> tuple[np.ndarray, np.ndarray]:
    dt = pd.to_datetime(series, format="ISO8601", utc=True)
    days = dt.dt.tz_localize(None).map(lambda t: t.to_pydatetime().replace(tzinfo=timezone.utc).timestamp() / 86_400.0)
    return days.to_numpy(dtype=np.float64), dt.dt.year.to_numpy(dtype=np.int16)


def build_event_frame(
    comcat_path: str | Path,
    template_path: str | Path,
    *,
    hot_points_csv: str | Path | None = None,
    sequence_thin: bool = False,
) -> tuple[EventFrame, dict[str, Any]]:
    """Screen, project, site-filter, and decluster the ComCat epicentres.

    The returned frame is the *declustered* (triangle-test-kept) event set; the
    report records every filter count so nothing is silent.
    """
    df, cat_report = load_comcat(comcat_path)
    with rasterio.open(template_path) as ds:
        template = ds.read(1)
        valid = np.isfinite(template)
        transform = ds.transform
        shape = ds.shape
    height, width = shape

    # --- tectonic / magnitude / location-quality screen (h56.select_tectonic) ---
    df, tectonic_report = h56.select_tectonic(
        df, min_mag=MIN_MAG, max_h_err_km=MAX_HORIZONTAL_ERROR_KM
    )
    df = df[np.isfinite(df["depth"]) & (df["depth"] < MAX_DEPTH_KM)].reset_index(drop=True)
    depth_report = {"rule": "isfinite(depth) and depth < 25 km", "rows_out": len(df)}

    # --- project to the competition grid ---
    transformer = Transformer.from_crs("EPSG:4326", "EPSG:32611", always_xy=True)
    lon = pd.to_numeric(df["longitude"], errors="coerce").to_numpy(dtype=np.float64)
    lat = pd.to_numeric(df["latitude"], errors="coerce").to_numpy(dtype=np.float64)
    x, y = transformer.transform(lon, lat)
    x = np.asarray(x, dtype=np.float64)
    y = np.asarray(y, dtype=np.float64)
    inverse = ~transform
    col_f, row_f = inverse * (x, y)
    row = np.floor(row_f).astype(np.int64)
    col = np.floor(col_f).astype(np.int64)
    ok = (
        np.isfinite(lon)
        & np.isfinite(lat)
        & (row >= 0)
        & (row < height)
        & (col >= 0)
        & (col < width)
    )
    # H56 precedent: keep events inside the grid *rectangle*.  Events outside the
    # finite study footprint may still define corridors that cross into it; the
    # belief is masked to the off-catalogue domain before emission regardless.
    in_valid = ok & valid[np.clip(row, 0, height - 1), np.clip(col, 0, width - 1)]
    df = df[ok].reset_index(drop=True)
    x, y = x[ok], y[ok]
    row, col = row[ok], col[ok]
    footprint_report = {
        "rule": "inside the grid rectangle (H56 precedent); both counts recorded",
        "events_in_bounds": int(ok.sum()),
        "events_in_valid_footprint": int(in_valid.sum()),
    }

    sigma_km = h56.epicentral_sigma_km(df)
    mag = pd.to_numeric(df["mag"], errors="coerce").to_numpy(dtype=np.float64)
    time_days, year = _parse_time_days(df["time"])

    xy = np.column_stack((x, y))
    report: dict[str, Any] = {
        "catalog": cat_report,
        "tectonic_screen": tectonic_report,
        "depth_screen": depth_report,
        "footprint": footprint_report,
    }

    # --- site screens: explicit anthropogenic events (3 km), hot features (2 km) ---
    keep = np.ones(len(df), dtype=bool)
    centres = _anthropogenic_centres(comcat_path)
    if centres.size:
        distance, _ = cKDTree(centres).query(xy, k=1)
        keep &= distance > ANTHROPOGENIC_BUFFER_M
    report["anthropogenic_site_screen"] = {
        "rule": "3 km buffer around explicit ComCat blast/mine/quarry event centres",
        "centres": int(centres.shape[0]),
        "events_removed": int(np.count_nonzero(~keep)),
    }
    if hot_points_csv is not None and Path(hot_points_csv).exists():
        hot = _hot_centres(Path(hot_points_csv))
        if hot.size:
            distance, _ = cKDTree(hot).query(xy, k=1)
            keep &= distance > HOT_FEATURE_BUFFER_M
        report["hot_feature_screen"] = {
            "rule": "2 km buffer around GDR-1391 Hot well/spring centres",
            "centres": int(hot.shape[0]),
            "events_removed": int(np.count_nonzero(~keep)),
        }
    else:
        report["hot_feature_screen"] = {
            "status": "LIMITATION — GDR-1391 hot-feature CSV is not present in this "
            "environment; the injection/geothermal site screen is incomplete. The ComCat "
            "type filter and the explicit anthropogenic-event buffer are the remaining "
            "induced-seismicity controls.",
            "events_removed": 0,
        }
    df = df[keep].reset_index(drop=True)
    x, y = x[keep], y[keep]
    row, col = row[keep], col[keep]
    sigma_km, mag = sigma_km[keep], mag[keep]
    time_days, year = time_days[keep], year[keep]
    xy = xy[keep]
    report["after_site_screens"] = len(df)

    # --- optional deterministic sequence thinning (sensitivity only) ---
    if sequence_thin:
        ix = np.floor(x / 250.0).astype(np.int64)
        iy = np.floor(y / 250.0).astype(np.int64)
        it = np.floor(time_days / 90.0).astype(np.int64)
        order = np.lexsort((np.arange(len(df)), -mag, it, iy, ix))
        first = np.ones(order.size, dtype=bool)
        if order.size > 1:
            a, b = order[1:], order[:-1]
            first[1:] = (ix[a] != ix[b]) | (iy[a] != iy[b]) | (it[a] != it[b])
        keep = np.sort(order[first])
        df = df.iloc[keep].reset_index(drop=True)
        x, y = x[keep], y[keep]
        row, col = row[keep], col[keep]
        sigma_km, mag = sigma_km[keep], mag[keep]
        time_days, year = time_days[keep], year[keep]
        xy = xy[keep]
        report["sequence_thinning"] = {
            "rule": "largest magnitude per 250 m cell per 90-day window",
            "events_out": int(keep.size),
        }

    # --- decluster: 2-D triangle-area background test (unverified adaptation) ---
    keep_mask, tri_diag = h56.triangle_area_keep(
        xy, quantile=TRIANGLE_QUANTILE, seed=TRIANGLE_SEED
    )
    report["decluster"] = tri_diag
    df = df[keep_mask].reset_index(drop=True)
    x, y = x[keep_mask], y[keep_mask]
    row, col = row[keep_mask], col[keep_mask]
    sigma_km, mag = sigma_km[keep_mask], mag[keep_mask]
    time_days, year = time_days[keep_mask], year[keep_mask]
    report["events_after_decluster"] = int(keep_mask.sum())

    frame = EventFrame(
        x_m=x,
        y_m=y,
        sigma_km=sigma_km,
        row=row.astype(np.int32),
        col=col.astype(np.int32),
        mag=mag.astype(np.float32),
        time_days=time_days,
        year=year,
        metadata=report,
    )
    return frame, report


def _anthropogenic_centres(comcat_path: str | Path) -> np.ndarray:
    """Projected centres of explicit anthropogenic ComCat events (site screen)."""
    transformer = Transformer.from_crs("EPSG:4326", "EPSG:32611", always_xy=True)
    points: set[tuple[float, float]] = set()
    with gzip.open(comcat_path, "rt", encoding="utf-8", newline="") as stream:
        for row in pd.read_csv(stream, chunksize=50_000):
            types = row["type"].astype(str).str.strip().str.lower()
            sel = row[types.isin(ANTHROPOGENIC_TYPES)]
            if sel.empty:
                continue
            lon = pd.to_numeric(sel["longitude"], errors="coerce").to_numpy(dtype=np.float64)
            lat = pd.to_numeric(sel["latitude"], errors="coerce").to_numpy(dtype=np.float64)
            good = np.isfinite(lon) & np.isfinite(lat)
            if not np.any(good):
                continue
            x, y = transformer.transform(lon[good], lat[good])
            for xi, yi in zip(x, y):
                points.add((round(float(xi), 3), round(float(yi), 3)))
    if not points:
        return np.zeros((0, 2), dtype=np.float64)
    return np.asarray(sorted(points), dtype=np.float64)


def _hot_centres(path: Path) -> np.ndarray:
    """UTM centres of GDR-1391 'Hot' features (thermalclass == Hot)."""
    points: set[tuple[float, float]] = set()
    with path.open("rt", encoding="utf-8", newline="") as stream:
        for row in pd.read_csv(stream, chunksize=50_000):
            if "thermalclass" not in row.columns:
                return np.zeros((0, 2), dtype=np.float64)
            sel = row[(row["thermalclass"].astype(str).str.strip() == "Hot")]
            if sel.empty:
                continue
            x = pd.to_numeric(sel.get("utm_x"), errors="coerce").to_numpy(dtype=np.float64)
            y = pd.to_numeric(sel.get("utm_y"), errors="coerce").to_numpy(dtype=np.float64)
            good = np.isfinite(x) & np.isfinite(y)
            for xi, yi in zip(x[good], y[good]):
                points.add((round(float(xi), 3), round(float(yi), 3)))
    if not points:
        return np.zeros((0, 2), dtype=np.float64)
    return np.asarray(sorted(points), dtype=np.float64)


def corridor_belief(
    frame: EventFrame,
    shape: tuple[int, int],
    transform,
    *,
    lineation_k: int = LINEATION_K,
    min_events: int = LINEATION_MIN_EVENTS,
    min_elongation: float = LINEATION_MIN_ELONGATION,
    min_sigma1_m: float = LINEATION_MIN_SIGMA1_M,
) -> tuple[np.ndarray, Any, dict[str, Any]]:
    """Declustered epicentres -> linear-neighbourhood corridors -> belief field.

    Returns the belief normalised to [0, 1], the fitted lineations, and a report.
    """
    xy = np.column_stack((frame.x_m, frame.y_m))
    lin = h56.neighbourhood_lineations(
        xy,
        frame.sigma_km * 1000.0,
        k=lineation_k,
        min_events=min_events,
        min_elongation=min_elongation,
        min_sigma1_m=min_sigma1_m,
    )
    density = h56.corridor_density(lin, shape, transform)
    maximum = float(density.max()) if density.size else 0.0
    belief = density.astype(np.float32)
    if maximum > 0:
        belief = belief / maximum
    report = {
        "lineations": len(lin),
        "lineation_summary": lin.as_dict(),
        "corridor_max_raw": maximum,
        "corridor_cells_gt_0.05": float((belief > 0.05).mean()),
        "sigma_km_median": float(np.median(frame.sigma_km)),
        "width_note": (
            "corridor half-width is the catalogue horizontalError (scalar, not a covariance); "
            "at 100 m pixels the median width is several pixels — a corridor prior, not a trace"
        ),
    }
    return belief, lin, report


def density_control_field(
    frame: EventFrame,
    shape: tuple[int, int],
    valid: np.ndarray,
    sigma_m: float,
    pixel_m: float = 100.0,
) -> np.ndarray:
    """Gaussian count-density control from exactly the declustered events.

    This is the falsification control the owner asked for: if corridors do not
    beat *smoothed earthquake density* built from the same events at matched
    mass, the seismicity-geometry hypothesis is falsified for this emitter.
    """
    counts = np.zeros(shape, dtype=np.float32)
    np.add.at(counts, (frame.row, frame.col), 1.0)
    field = ndimage.gaussian_filter(counts, sigma=sigma_m / pixel_m, mode="constant", cval=0.0)
    field[~np.asarray(valid, dtype=bool)] = 0.0
    maximum = float(field.max(initial=0.0))
    if maximum > 0:
        field /= maximum
    return field.astype(np.float32, copy=False)


def modelled_hidden_dti(credit_per_dot_sgmc: float, n: int, transfer: float = TRANSFER) -> dict[str, Any]:
    """Transfer-calibrated model of the hidden-frame DTI (a model, not a score).

    Same formula and frozen constants as the H56 build (G_hidden = 12,226,
    transfer 4.2, band [3.97, 4.59], physical cap T <= G_hidden).
    """
    density_ratio = G_HIDDEN / SGMC_OFF_TRUTH_PX
    c_hidden = credit_per_dot_sgmc * density_ratio * transfer
    t_modelled = c_hidden * n
    saturated = t_modelled > G_HIDDEN
    t_eff = min(t_modelled, float(G_HIDDEN))
    dti = t_eff / (0.2 * n + 0.8 * G_HIDDEN)
    return {
        "credit_per_dot_modelled": float(c_hidden),
        "T_modelled": float(t_modelled),
        "T_saturated": bool(saturated),
        "dti_modelled": float(dti),
    }
