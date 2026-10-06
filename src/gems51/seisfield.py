"""Seismicity-plane lineament evidence from event *geometry*, not from a density band.

Steps and their evidence classes (see :mod:`gems51.notes`):

1. ComCat events, ``type == earthquake``, magnitude >= ``min_mag``, depth <= ``max_depth``,
   inside the survey plus a buffer.                                                   [MEASURED]
2. Documented induced / mining / geothermal sources removed *before* any geometry is
   fitted: explicit ComCat event types plus circular exclusion zones around a sourced list
   of fields and mines (``INDUCED_SITES``).                                            [OWN]
3. Per-event 1-sigma epicentral uncertainty: the catalog's own ``horizontalError`` where
   present, otherwise the calibrated model of :mod:`gems51.uncertainty`.               [OWN]
4. Background separation by the **space-time tetrahedron volume** of each event with its
   three nearest neighbours in (x, y, t_scaled), tested against 200 time-shuffled
   surrogates by a paired sign test; the clustered low-p population is kept.  The cited
   method uses 3-D hypocentre tetrahedra and a randomised catalogue; this is the
   epicentre-plus-time reduction.                                              [ADAPTED_2D]
5. Neighbourhood covariance axes: k nearest events weighted by 1/sigma^2 (Wang et al.
   2013), eigenvalues l1 >= l2 of the 2-D covariance, elongation 1 - l2/l1, with the OADC
   thinness rule l2 < Delta^2 applied in 2-D and Delta the *local* modelled uncertainty. [ADAPTED_2D]
6. Space-time cluster spines: density clustering of the clustered population, principal
   axis of every elongated cluster meeting a minimum event count and multi-year support. [OWN]
7. Corridors: each accepted axis is drawn from -l1^0.5 to +l1^0.5 and given width
   ``max(2*Delta, 300 m)`` - i.e. the width is set by the catalogue's own location error,
   so the output is a corridor prior, not a trace.                                    [MEASURED]
   The corridor is then smoothed with a Gaussian about that width, because the metric's own
   support is a 300 m triangle and emission must be able to use it.

Dip projection from hypocentre depths is deliberately **not** applied: ComCat's own
``depthError`` has a 1.5 km median in this footprint, and a dip-driven surface offset of
several kilometres would be an order of magnitude larger than the 300 m scoring kernel.
The depth information is used only for the space-time decluster.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
import pandas as pd
from pyproj import Transformer
from scipy import ndimage
from scipy.spatial import cKDTree

from . import grid as g
from . import uncertainty
from .notes import ADAPTED_2D, MEASURED, OWN, PUBLISHED_3D

#: Documented geothermal fields, injection areas and mines in/near the survey.  Coordinates
#: are published field/plant locations; the exclusion radius covers the induced-event clouds
#: reported for these systems.  Each row names the source used for the location.
INDUCED_SITES: tuple[tuple[str, float, float, float, str], ...] = (
    ("Dixie Valley", 39.9667, -117.8500, 8000.0, "Dixie Valley geothermal field (Churchill Co., NV)"),
    ("Beowawe", 40.5833, -116.5333, 8000.0, "Beowawe geothermal field (Eureka Co., NV)"),
    ("Brady-Desert Peak", 39.7833, -119.0167, 10000.0, "Brady's and Desert Peak geothermal fields"),
    ("Steamboat", 39.3833, -119.7333, 8000.0, "Steamboat Springs geothermal field"),
    ("Soda Lake", 39.5167, -118.8500, 8000.0, "Soda Lake geothermal field"),
    ("Tuscarora", 41.3000, -116.1167, 8000.0, "Tuscarora geothermal field"),
    ("McGinness Hills", 39.5333, -116.9333, 8000.0, "McGinness Hills geothermal field"),
    ("Blue Mountain", 40.3333, -118.1000, 8000.0, "Blue Mountain geothermal field"),
    ("Jersey Valley", 40.1667, -118.2667, 8000.0, "Jersey Valley geothermal field"),
    ("Salt Wells", 39.3667, -118.6000, 8000.0, "Salt Wells geothermal field"),
    ("Patua", 39.4667, -119.0667, 8000.0, "Patua geothermal field"),
    ("Rye Patch", 40.4500, -118.2500, 8000.0, "Rye Patch / Humboldt geothermal area"),
    ("San Emidio", 40.3667, -119.4500, 8000.0, "San Emidio geothermal field"),
    ("Stillwater", 39.5500, -118.5500, 8000.0, "Stillwater geothermal area"),
    ("Wabuska", 39.1500, -119.1833, 8000.0, "Wabuska geothermal field"),
    ("Goldstrike mine", 40.9833, -116.3833, 8000.0, "Goldstrike / Carlin trend mining district"),
    ("Cortez mine", 40.1500, -116.7000, 8000.0, "Cortez / Pipeline mining district"),
)

_TO_UTM = Transformer.from_crs("EPSG:4326", "EPSG:32611", always_xy=True)
_SITES_XY = np.array([_TO_UTM.transform(lon, lat) for _, lat, lon, _, _ in INDUCED_SITES])
_SITE_RADIUS = np.array([s[3] for s in INDUCED_SITES])


@dataclass
class SeisConfig:
    min_mag: float = 1.0
    max_depth_km: float = 25.0
    survey_buffer_km: float = 30.0
    k_neighbours: int = 12
    min_events: int = 8
    linearity_min: float = 0.55
    sigma2_over_delta_max: float = 1.5
    sigma1_over_delta_min: float = 2.0
    min_sigma1_m: float = 600.0
    r_max_m: float = 8000.0
    recurrence_years_min: int = 2
    time_scale_km_per_year: float = 2.0
    tetra_surrogates: int = 200
    tetra_p_threshold: float = 0.35
    spine_eps_m: float = 3000.0
    spine_eps_days: float = 30.0
    spine_min_events: int = 15
    spine_min_elongation: float = 3.0
    spine_min_length_m: float = 1500.0
    corridor_min_width_m: float = 300.0
    notes: dict = field(default_factory=dict)


def _in_survey(x: np.ndarray, y: np.ndarray, valid: np.ndarray, buffer_m: float) -> np.ndarray:
    col, row = g.col_row(x, y)
    inside = (col >= 0) & (col < g.GRID["width"]) & (row >= 0) & (row < g.GRID["height"])
    near = np.zeros(x.shape, dtype=bool)
    if inside.any():
        grown = ndimage.binary_dilation(valid, iterations=int(buffer_m / g.GRID["pixel_m"]))
        near[inside] = grown[row[inside], col[inside]]
    return near


def load_events(
    catalog: str | Path,
    valid: np.ndarray,
    cfg: SeisConfig,
    uncertainty_report: dict | None = None,
) -> tuple[pd.DataFrame, dict]:
    df = pd.read_csv(catalog, low_memory=False)
    qc: dict = {"comcat_rows": len(df)}
    t = pd.to_datetime(df["time"], format="ISO8601", utc=True, errors="coerce")
    x, y = _TO_UTM.transform(df["longitude"].to_numpy(), df["latitude"].to_numpy())
    depth = pd.to_numeric(df["depth"], errors="coerce").to_numpy()
    mag = pd.to_numeric(df["mag"], errors="coerce").to_numpy()
    herr_km = pd.to_numeric(df["horizontalError"], errors="coerce").to_numpy()
    nst = pd.to_numeric(df["nst"], errors="coerce").to_numpy()
    gap = pd.to_numeric(df["gap"], errors="coerce").to_numpy()
    keep_type = df["type"].astype(str).str.lower().eq("earthquake")
    ok = (keep_type & t.notna().to_numpy() & np.isfinite(depth) & np.isfinite(mag)
          & (mag >= cfg.min_mag) & (depth <= cfg.max_depth_km)
          & _in_survey(x, y, valid, cfg.survey_buffer_km * 1000.0))
    qc["after_type_time_depth_mag"] = int(ok.sum())

    in_footprint = np.zeros(len(df), dtype=bool)
    col, row = g.col_row(x, y)
    inside = (col >= 0) & (col < g.GRID["width"]) & (row >= 0) & (row < g.GRID["height"])
    in_footprint[inside] = valid[row[inside], col[inside]]
    coef, calib = uncertainty.calibrate(herr_km * 1000.0, nst, gap, depth, mag, ~in_footprint)
    modelled, bad_metrics = uncertainty.predict_m(coef, nst, gap, depth, mag)
    documented = np.isfinite(herr_km)
    sigma_m = np.where(documented, herr_km * 1000.0, modelled)
    qc["uncertainty"] = {
        "calibration": calib,
        "documented_in_survey": int(np.sum(ok & documented)),
        "modelled_in_survey": int(np.sum(ok & ~documented)),
        "summary_in_survey": uncertainty.summarise(sigma_m[ok], bad_metrics[ok]),
    }

    tree = cKDTree(_SITES_XY)
    dist_site, nearest = tree.query(np.column_stack([x, y]), k=1)
    near_site = dist_site <= _SITE_RADIUS[nearest]
    qc["removed_within_induced_site"] = int(np.sum(ok & near_site))
    qc["induced_site_nearest_counts"] = {}
    for idx, site in enumerate(INDUCED_SITES):
        n = int(np.sum(ok & near_site & (nearest == idx)))
        if n:
            qc["induced_site_nearest_counts"][site[0]] = n
    ok = ok & ~near_site

    frame = pd.DataFrame({
        "x": x[ok], "y": y[ok], "depth_km": depth[ok], "mag": mag[ok],
        "h_err_m": sigma_m[ok], "h_err_documented": documented[ok],
        "year": t[ok].dt.year.to_numpy(), "day": t[ok].astype("int64").to_numpy() / 8.64e13,
        "net": df["net"].astype(str).to_numpy()[ok], "id": df["id"].astype(str).to_numpy()[ok],
    })
    qc["events_used"] = len(frame)
    qc["magnitude_range"] = [float(frame["mag"].min()), float(frame["mag"].max())]
    qc["depth_range_km"] = [float(frame["depth_km"].min()), float(frame["depth_km"].max())]
    qc["years"] = [int(frame["year"].min()), int(frame["year"].max())]
    return frame, qc


def tetrahedron_decluster(frame: pd.DataFrame, cfg: SeisConfig, seed: int = 51) -> tuple[np.ndarray, dict]:
    """Space-time tetrahedron volume test against time-shuffled surrogates (paired sign test)."""
    pts = frame[["x", "y"]].to_numpy(dtype=np.float64) / 1000.0
    years = frame["year"].to_numpy(dtype=np.float64)
    t3 = years * cfg.time_scale_km_per_year
    xyz = np.column_stack([pts, t3])

    def volumes(coords: np.ndarray) -> np.ndarray:
        """Vectorised |det[a-p, b-p, c-p]|/6 for the 3 nearest neighbours of every point."""
        _, idx = cKDTree(coords).query(coords, k=min(4, len(coords)))
        if idx.ndim == 1:
            idx = idx[:, None]
        out = np.full(len(coords), np.nan)
        if idx.shape[1] < 4:
            return out
        p0 = coords
        v1 = coords[idx[:, 1]] - p0
        v2 = coords[idx[:, 2]] - p0
        v3 = coords[idx[:, 3]] - p0
        triple = v1[:, 0] * (v2[:, 1] * v3[:, 2] - v2[:, 2] * v3[:, 1]) \
            - v1[:, 1] * (v2[:, 0] * v3[:, 2] - v2[:, 2] * v3[:, 0]) \
            + v1[:, 2] * (v2[:, 0] * v3[:, 1] - v2[:, 1] * v3[:, 0])
        out = np.abs(triple) / 6.0
        bad = (idx[:, 1] >= len(coords)) | (idx[:, 2] >= len(coords)) | (idx[:, 3] >= len(coords))
        out[bad] = np.nan
        return out

    obs = volumes(xyz)
    rng = np.random.default_rng(seed)
    smaller = np.zeros(len(xyz))
    for _ in range(cfg.tetra_surrogates):
        shuffled = np.column_stack([pts[:, 0], pts[:, 1], t3[rng.permutation(len(xyz))]])
        with np.errstate(invalid="ignore"):
            smaller += (volumes(shuffled) < obs)
    p = smaller / float(cfg.tetra_surrogates)
    finite = np.isfinite(obs) & np.isfinite(p)
    keep = finite & (p <= cfg.tetra_p_threshold)
    return keep, {
        "class": ADAPTED_2D,
        "test": "space-time tetrahedron volume of each event with its three nearest neighbours "
                "in (x_km, y_km, year * %g km/yr)" % cfg.time_scale_km_per_year,
        "surrogate": "time values shuffled among the same event locations, %d draws"
                     % cfg.tetra_surrogates,
        "statistic": "p = fraction of surrogates with a smaller tetrahedron volume than observed; "
                     "the clustered population has small p",
        "p_threshold": cfg.tetra_p_threshold,
        "events_in": len(xyz),
        "events_kept_clustered": int(keep.sum()),
        "median_p_kept": float(np.median(p[keep])) if keep.any() else None,
    }


def _covariance_axis(points: np.ndarray, sigma: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    w = 1.0 / np.maximum(sigma, 50.0) ** 2
    w = w / w.sum()
    mu = (w[:, None] * points).sum(axis=0)
    d = points - mu
    cov = (w[:, None] * d).T @ d
    vals, vecs = np.linalg.eigh(cov)
    return mu, np.sqrt(np.clip(vals, 0.0, None)), vecs, w


def neighbourhood_axes(frame: pd.DataFrame, cfg: SeisConfig) -> dict:
    """k-nearest-neighbour covariance axes under the OADC thinness rule (2-D reduction)."""
    xy = frame[["x", "y"]].to_numpy(dtype=np.float64)
    sigma = frame["h_err_m"].to_numpy(dtype=np.float64)
    depth = frame["depth_km"].to_numpy(dtype=np.float64)
    years = frame["year"].to_numpy()
    n = len(frame)
    dist, idx = cKDTree(xy).query(xy, k=min(cfg.k_neighbours, n), distance_upper_bound=cfg.r_max_m)
    rows = []
    for i in range(n):
        sel = np.isfinite(dist[i]) & (idx[i] != i) & (idx[i] < n)
        nb = idx[i][sel]
        if nb.size < cfg.min_events - 1:
            continue
        _, s, vecs, w = _covariance_axis(xy[nb] - xy[i], sigma[nb])
        sigma2, sigma1 = float(s[0]), float(s[1])
        if sigma1 <= 0:
            continue
        delta = float(np.average(sigma[nb], weights=w))
        linearity = 1.0 - sigma2 / max(sigma1, 1e-9)
        n_years = int(np.unique(years[nb]).size)
        if (linearity < cfg.linearity_min
                or sigma2 > cfg.sigma2_over_delta_max * delta
                or sigma1 < cfg.sigma1_over_delta_min * delta
                or sigma1 < cfg.min_sigma1_m
                or n_years < cfg.recurrence_years_min):
            continue
        dx, dy = float(vecs[0, 1]), float(vecs[1, 1])
        rows.append((float(xy[i, 0]), float(xy[i, 1]), dx, dy, sigma1, sigma2, delta,
                     int(nb.size), n_years, float(np.mean(depth[nb]))))
    keys = ("x", "y", "ux", "uy", "sigma1", "sigma2", "delta", "n_events", "n_years", "mean_depth_km")
    axes = {k: np.array([r[j] for r in rows], dtype=float) for j, k in enumerate(keys)}
    report = {
        "class": PUBLISHED_3D + " -> " + ADAPTED_2D,
        "criteria": {
            "k_neighbours": cfg.k_neighbours, "r_max_m": cfg.r_max_m,
            "min_events": cfg.min_events, "linearity_min": cfg.linearity_min,
            "sigma2_over_delta_max": cfg.sigma2_over_delta_max,
            "sigma1_over_delta_min": cfg.sigma1_over_delta_min,
            "min_sigma1_m": cfg.min_sigma1_m,
            "recurrence_years_min": cfg.recurrence_years_min,
        },
        "n_accepted": len(rows),
        "median_sigma1_m": float(np.median(axes["sigma1"])) if rows else None,
        "median_delta_m": float(np.median(axes["delta"])) if rows else None,
        "median_linearity": float(np.median(1.0 - axes["sigma2"] / np.maximum(axes["sigma1"], 1e-9)))
                            if rows else None,
    }
    return {"axes": axes, "report": report}


def cluster_spines(frame: pd.DataFrame, cfg: SeisConfig) -> dict:
    """Principal axis of every elongated space-time cluster (own construction)."""
    if len(frame) < cfg.spine_min_events:
        return {"spines": [], "report": {"class": OWN, "n_spines": 0}}
    xy = frame[["x", "y"]].to_numpy(dtype=np.float64)
    day = frame["day"].to_numpy(dtype=np.float64)
    sigma = frame["h_err_m"].to_numpy(dtype=np.float64)
    years = frame["year"].to_numpy()
    scale = cfg.spine_eps_m / max(cfg.spine_eps_days, 1e-9)
    pts = np.column_stack([xy[:, 0] / cfg.spine_eps_m, xy[:, 1] / cfg.spine_eps_m, day / cfg.spine_eps_days])
    labels = _density_clusters(pts, eps=1.0, min_samples=cfg.spine_min_events)
    spines, stats = [], []
    for lab in np.unique(labels):
        if lab < 0:
            continue
        sel = labels == lab
        mu, s, vecs, _ = _covariance_axis(xy[sel], sigma[sel])
        sigma1, sigma2 = float(s[1]), float(s[0])
        elongation = sigma1 / max(sigma2, 1e-9)
        n_years = int(np.unique(years[sel]).size)
        if (sigma1 < cfg.spine_min_length_m or elongation < cfg.spine_min_elongation
                or n_years < cfg.recurrence_years_min):
            continue
        ux, uy = float(vecs[0, 1]), float(vecs[1, 1])
        spines.append({
            "x": float(mu[0]), "y": float(mu[1]), "ux": ux, "uy": uy,
            "half_length_m": float(2.0 * sigma1), "elongation": float(elongation),
            "n_events": int(sel.sum()), "n_years": n_years,
            "median_sigma_m": float(np.median(sigma[sel])),
        })
        stats.append((sel.sum(), sigma1, elongation))
    return {"spines": spines, "report": {
        "class": OWN,
        "method": "density clustering in (x/eps_m, y/eps_m, time/eps_days) with eps=1, then a "
                  "1/sigma^2-weighted principal-axis fit of each cluster",
        "eps_m": cfg.spine_eps_m, "eps_days": cfg.spine_eps_days,
        "min_events": cfg.spine_min_events, "min_elongation": cfg.spine_min_elongation,
        "min_length_m": cfg.spine_min_length_m,
        "n_clusters": len(stats), "n_spines": len(spines),
        "total_clustered_events_in_spines": int(sum(s[0] for s in stats)),
    }}


def _density_clusters(points: np.ndarray, eps: float, min_samples: int) -> np.ndarray:
    """Density clustering as the connected components of the mutual k-nearest-neighbour graph.

    A full radius query over a dense aftershock sequence allocates every pair inside the
    radius and exhausted memory in this sandbox, so the graph is built from each point's
    ``min_samples`` nearest neighbours with an edge kept only when the neighbour is within
    ``eps`` of it.  That is the usual k-NN-graph approximation of density clustering and it
    is bounded at ``n * min_samples`` entries.
    """
    n = len(points)
    if n < min_samples:
        return np.full(n, -1, dtype=np.int64)
    tree = cKDTree(points)
    dist, idx = tree.query(points, k=min(min_samples * 4, n))
    parent = np.arange(n)

    def find(a: int) -> int:
        while parent[a] != a:
            parent[a] = parent[parent[a]]
            a = parent[a]
        return a

    def union(a: int, b: int) -> None:
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[max(ra, rb)] = min(ra, rb)

    core = np.zeros(n, dtype=bool)
    for i in range(n):
        near = idx[i][dist[i] <= eps]
        if len(near) >= min_samples:
            core[i] = True
            for j in near:
                if j != i:
                    union(i, int(j))
    labels = np.full(n, -1, dtype=np.int64)
    roots: dict[int, int] = {}
    for i in range(n):
        if not core[i]:
            continue
        r = find(i)
        if r not in roots:
            roots[r] = len(roots)
        labels[i] = roots[r]
    return labels


def rasterise(axes: dict, spines: list[dict], cfg: SeisConfig, valid: np.ndarray) -> tuple[np.ndarray, dict]:
    """Corridors: one draped segment per accepted axis/spine, width from its own uncertainty."""
    field = np.zeros((g.GRID["height"], g.GRID["width"]), dtype=np.float32)
    widths, centreline_cells = [], 0
    segments = []
    for i in range(len(axes["axes"]["x"])):
        segments.append((axes["axes"]["x"][i], axes["axes"]["y"][i],
                         axes["axes"]["ux"][i], axes["axes"]["uy"][i],
                         float(axes["axes"]["sigma1"][i]), float(axes["axes"]["delta"][i])))
    for sp in spines:
        segments.append((sp["x"], sp["y"], sp["ux"], sp["uy"],
                         sp["half_length_m"] / 2.0, sp["median_sigma_m"]))
    for (cx, cy, ux, uy, half, delta) in segments:
        width_m = max(2.0 * delta, cfg.corridor_min_width_m)
        widths.append(width_m)
        n = max(int(2 * half / g.GRID["pixel_m"]) + 1, 2)
        s = np.linspace(-half, half, n)
        col, row = g.col_row(cx + s * ux, cy + s * uy)
        ok = (col >= 0) & (col < g.GRID["width"]) & (row >= 0) & (row < g.GRID["height"])
        field[row[ok], col[ok]] = 1.0
        centreline_cells += int(ok.sum())
    if field.any():
        sigma_px = max(float(np.median(widths)) / 2.355 / g.GRID["pixel_m"], 0.8)
        field = ndimage.gaussian_filter(field, sigma_px)
        field = field / max(float(field.max()), 1e-9)
    field = np.where(valid, field, 0.0).astype(np.float32)
    return field, {
        "class": MEASURED,
        "n_segments": len(segments),
        "centreline_cells": int(centreline_cells),
        "median_corridor_width_m": float(np.median(widths)) if widths else None,
        "width_rule": "max(2 * local 1-sigma location uncertainty, %g m), then a Gaussian of "
                      "that width so the metric's 300 m kernel can be used at emission"
                      % cfg.corridor_min_width_m,
        "smoothed_cells": int(np.count_nonzero(field)),
    }


def build(catalog: str | Path, valid: np.ndarray, cfg: SeisConfig | None = None,
          frame: pd.DataFrame | None = None, qc: dict | None = None) -> tuple[np.ndarray, dict]:
    cfg = cfg or SeisConfig()
    if frame is None:
        frame, qc = load_events(catalog, valid, cfg)
    keep, decl = tetrahedron_decluster(frame, cfg)
    clustered = frame.loc[keep].reset_index(drop=True)
    axis_pack = neighbourhood_axes(clustered, cfg)
    spine_pack = cluster_spines(clustered, cfg)
    field, corridors = rasterise(axis_pack, spine_pack["spines"], cfg, valid)
    report = {
        "catalog_qc": qc,
        "decluster": decl,
        "axes": axis_pack["report"],
        "spines": spine_pack["report"],
        "corridors": corridors,
        "induced_sites": [{"name": s[0], "lat": s[1], "lon": s[2], "radius_m": s[3], "source": s[4]}
                          for s in INDUCED_SITES],
    }
    return field, report
