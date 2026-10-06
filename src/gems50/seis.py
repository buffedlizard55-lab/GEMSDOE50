"""Seismicity-lineament corridors from epicentre point patterns.

Method and provenance
---------------------
* Ouillon, G., Ducorbier, C. & Sornette, D. (2008), "Automatic reconstruction of
  fault planes from earthquakes", J. Geophys. Res. 113, B11307,
  doi:10.1029/2007JB005032.  Clusters earthquakes, then uses *each cluster's full
  spatial inertia tensor* to test planarity/linearity and recover orientation.
* Ouillon, G. & Sornette, D. (2011), "Faulting pattern and stress transfer in the
  Chi-Chi earthquake", J. Geophys. Res. 116, B06310, doi:10.1029/2010JB007770.
  Separates clustered events from uncorrelated background by comparing
  nearest-neighbour volumes of tetrahedra with randomised catalogues.
* Ouillon, G. & Sornette, D. (2013), arXiv:1304.6912 — the same reconstruction
  with catalogue location uncertainty carried through.

Channel-3 substitution, stated honestly
--------------------------------------
The published background/correlated test uses the distribution of *tetrahedron
volumes* formed by an event and its three nearest neighbours in 3-D, compared with
randomised catalogues that keep location uncertainty.  The competition target is a
2-D raster, so this module works on epicentres and substitutes the *triangle area*
of an event with its two nearest neighbours (the dimensional analogue) plus the
nearest-neighbour distance distribution.  **That 2-D adaptation is ours and is
unverified.**  It is falsified in `gems50/validate.py`: corridors must predict
withheld catalogue segments better than a smoothed earthquake density.
"""

from __future__ import annotations

import csv
import gzip
import math
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np

from . import grid

#: ComCat event types that are not tectonic earthquakes.  Removal is explicit
#: (the brief: remove known injection and mining sites), never silent.
ANTHROPOGENIC = {
    "explosion", "quarry blast", "mining explosion", "nuclear explosion",
    "anthropogenic event", "other event", "chemical explosion", "sonic boom",
    "acoustic noise", "rock burst", "controlled explosion", "blast", "ice quake",
}

KM_PER_DEG_LAT = 110.574


@dataclass
class Catalog:
    """A cleaned epicentre catalogue."""

    lon: np.ndarray
    lat: np.ndarray
    depth_km: np.ndarray
    mag: np.ndarray
    hor_err_km: np.ndarray
    etype: np.ndarray
    time: np.ndarray
    utm_x: np.ndarray = None
    utm_y: np.ndarray = None
    row: np.ndarray = None
    col: np.ndarray = None

    def __len__(self) -> int:
        return int(self.lon.size)

    def subset(self, keep) -> "Catalog":
        keep = np.asarray(keep, dtype=bool)
        def s(v):
            return None if v is None else np.asarray(v)[keep]
        return Catalog(s(self.lon), s(self.lat), s(self.depth_km), s(self.mag),
                       s(self.hor_err_km), s(self.etype), s(self.time),
                       s(self.utm_x), s(self.utm_y), s(self.row), s(self.col))

    @property
    def xy_km(self) -> np.ndarray:
        """Local planar coordinates in km (east, north) about the region centroid."""
        x = self.lon * 111.320 * math.cos(math.radians(float(np.mean(self.lat))))
        y = self.lat * KM_PER_DEG_LAT
        x = x - x.mean()
        y = y - y.mean()
        return np.column_stack([x, y]).astype(np.float64)


def read_comcat(path: str | Path, depth_max_km: float = 30.0,
                mag_min: float | None = 1.0, drop_anthropogenic: bool = True) -> Catalog:
    """Read the ComCat CSV written by scripts/fetch_earthquake_catalog.py."""
    lon, lat, dep, mag, herr, etyp, tim = [], [], [], [], [], [], []
    opener = gzip.open if str(path).endswith(".gz") else open
    with opener(path, "rt", newline="") as fh:
        for row in csv.DictReader(fh):
            try:
                m = float(row["mag"])
                lo = float(row["longitude"])
                la = float(row["latitude"])
            except (TypeError, ValueError, KeyError):
                continue
            etype = row.get("type", "earthquake") or "earthquake"
            if etype in ANTHROPOGENIC and drop_anthropogenic:
                continue
            try:
                d = float(row["depth"])
            except (TypeError, ValueError):
                d = float("nan")
            try:
                he = float(row["horizontalError"])
            except (TypeError, ValueError):
                he = float("nan")
            lon.append(lo); lat.append(la); dep.append(d); mag.append(m)
            herr.append(he); etyp.append(etype); tim.append(row.get("time", ""))
    cat = Catalog(np.array(lon), np.array(lat), np.array(dep), np.array(mag),
                  np.array(herr), np.array(etyp, dtype=object),
                  np.array(tim, dtype=object))
    keep = np.ones(len(cat), dtype=bool)
    if mag_min is not None:
        keep &= cat.mag >= mag_min
    keep &= np.isfinite(cat.depth_km) & (cat.depth_km <= depth_max_km)
    cat = cat.subset(keep)
    return to_pixels(cat)


def to_pixels(cat: Catalog, transform=None) -> Catalog:
    """Attach official-grid (row, col) coordinates to the catalogue (EPSG:32611)."""
    from pyproj import Transformer

    tr = Transformer.from_crs("EPSG:4326", grid.CRS, always_xy=True)
    x, y = tr.transform(cat.lon, cat.lat)
    cat.utm_x = np.asarray(x)
    cat.utm_y = np.asarray(y)
    t = transform or grid.TRANSFORM
    a, _b, c, _d, e, f = t
    cat.col = (cat.utm_x - c) / a
    cat.row = (cat.utm_y - f) / e
    return cat


def inside_footprint(cat: Catalog, shape=grid.SHAPE) -> np.ndarray:
    r = np.round(cat.row).astype(int)
    c = np.round(cat.col).astype(int)
    return (r >= 0) & (r < shape[0]) & (c >= 0) & (c < shape[1])


def nn_distances(cat: Catalog, k: int = 1) -> np.ndarray:
    """Distance (km) from each event to its k-th nearest neighbour."""
    from scipy.spatial import cKDTree

    xy = cat.xy_km
    d, _ = cKDTree(xy).query(xy, k=k + 1)
    return d[:, k]


def triangle_areas(cat: Catalog) -> np.ndarray:
    """Area (km^2) of the triangle: event + its two nearest neighbours.

    The 2-D analogue of the 3-D tetrahedron-volume statistic.  **Ours, unverified.**
    """
    from scipy.spatial import cKDTree

    xy = cat.xy_km
    n = xy.shape[0]
    out = np.full(n, np.nan)
    if n < 3:
        return out
    d, idx = cKDTree(xy).query(xy, k=3)
    p0 = xy[idx[:, 0]]
    p1 = xy[idx[:, 1]]
    p2 = xy[idx[:, 2]]
    out = 0.5 * np.abs((p1[:, 0] - p0[:, 0]) * (p2[:, 1] - p0[:, 1])
                       - (p2[:, 0] - p0[:, 0]) * (p1[:, 1] - p0[:, 1]))
    return out


def randomized_nn_distances(cat: Catalog, area_km2: float, n_rand: int = 20,
                            k: int = 1, seed: int = 7) -> np.ndarray:
    """Null model: Poisson epicentres, same count, in the same rectangle."""
    from scipy.spatial import cKDTree

    rng = np.random.default_rng(seed)
    xy = cat.xy_km
    (xmin, ymin), (xmax, ymax) = xy.min(axis=0), xy.max(axis=0)
    n = xy.shape[0]
    out = []
    for _ in range(n_rand):
        pts = np.column_stack([rng.uniform(xmin, xmax, n), rng.uniform(ymin, ymax, n)])
        d, _ = cKDTree(pts).query(pts, k=k + 1)
        out.append(d[:, k])
    return np.concatenate(out)


def correlation_scale(cat: Catalog, k: int = 1, margin: float = 0.05,
                      n_rand: int = 20, seed: int = 7) -> dict:
    """Crossover between the clustered population and the Poisson background.

    The observed k-th nearest-neighbour CDF is compared with the Poisson null of the
    same event count in the same rectangle; `r_c` is the largest distance at which
    the observed CDF still exceeds the null by `margin`.  Events with
    NN distance <= r_c are called "clustered" (Ouillon & Sornette 2011, 2-D analogue).
    """
    d_obs = nn_distances(cat, k=k)
    xy = cat.xy_km
    area = float(np.ptp(xy[:, 0]) * np.ptp(xy[:, 1]))
    d_null = randomized_nn_distances(cat, area, n_rand=n_rand, k=k, seed=seed)
    hi = float(np.quantile(d_obs, 0.995))
    grid_ = np.linspace(0.0, hi, 400)
    c_obs = np.searchsorted(np.sort(d_obs), grid_, side="right") / d_obs.size
    c_null = np.searchsorted(np.sort(d_null), grid_, side="right") / d_null.size
    excess = c_obs - c_null
    above = np.flatnonzero(excess > margin)
    r_c = float(grid_[above[-1]]) if above.size else float(np.quantile(d_obs, 0.5))
    return dict(r_c_km=r_c, clustered_fraction=float((d_obs <= r_c).mean()),
                n=int(len(cat)), nn_median_km=float(np.median(d_obs)),
                nn_median_random_km=float(np.median(d_null)), area_km2=area,
                d_obs=d_obs, d_null=d_null, grid=grid_, excess=excess)


def dbscan_labels(cat: Catalog, eps_km: float, min_samples: int = 6) -> np.ndarray:
    """Density-connected clustering of epicentres (2-D, Euclidean)."""
    from sklearn.cluster import DBSCAN

    return DBSCAN(eps=eps_km, min_samples=min_samples).fit_predict(cat.xy_km)


@dataclass
class Cluster:
    label: int
    n: int
    centroid_row: float
    centroid_col: float
    centroid_lonlat: tuple
    axis_angle_deg: float        # clockwise from east, degrees, 0..180
    lam1: float                  # principal eigenvalue (km^2)
    lam2: float                  # minor eigenvalue (km^2)
    length_km: float
    width_km: float
    elongation: float
    anisotropy: float
    sigma_km: float
    seg_row: tuple = field(default=None)
    seg_col: tuple = field(default=None)


def cluster_inertia(cat: Catalog, labels: np.ndarray, min_events: int = 8) -> list:
    """Spatial inertia tensor of each cluster, weighted by location uncertainty.

    Ouillon, Ducorbier & Sornette (2008): the full inertia tensor of a cluster decides
    whether it is a plane/line and gives its orientation.  Location uncertainty enters
    as 1/(sigma^2 + 1) weights (arXiv:1304.6912).
    """
    sigma = np.where(np.isfinite(cat.hor_err_km) & (cat.hor_err_km > 0), cat.hor_err_km, 1.5)
    xy = cat.xy_km
    out: list[Cluster] = []
    for lab in sorted(set(labels)):
        if lab < 0:
            continue
        sel = labels == lab
        n = int(sel.sum())
        if n < min_events:
            continue
        pts = xy[sel]
        w = 1.0 / (sigma[sel] ** 2 + 1.0)
        w = w / w.sum()
        mu = (pts * w[:, None]).sum(axis=0)
        c = pts - mu
        cov = (w[:, None] * c).T @ c
        lam, vec = np.linalg.eigh(cov)
        order = np.argsort(-lam)
        lam, vec = lam[order], vec[:, order]
        lam1, lam2 = float(lam[0]), float(max(lam[1], 1e-12))
        v1 = vec[:, 0]                       # (east, north)
        angle = math.degrees(math.atan2(v1[1], v1[0])) % 180.0
        proj = c @ v1
        length_km = float(proj.max() - proj.min())
        # pixel-space segment: +x_col follows east, +y_row follows SOUTH
        half = length_km / 2.0
        c_row = float(np.mean(cat.row[sel]))
        c_col = float(np.mean(cat.col[sel]))
        dr = -v1[1] * half * 10.0
        dc = v1[0] * half * 10.0
        out.append(Cluster(
            label=int(lab), n=n, centroid_row=c_row, centroid_col=c_col,
            centroid_lonlat=(float(np.mean(cat.lon[sel])), float(np.mean(cat.lat[sel]))),
            axis_angle_deg=angle, lam1=lam1, lam2=lam2, length_km=length_km,
            width_km=float(2.0 * math.sqrt(lam2)),
            elongation=float(lam1 / lam2), anisotropy=float((lam1 - lam2) / (lam1 + lam2)),
            sigma_km=float(np.median(sigma[sel])),
            seg_row=(c_row - dr, c_row + dr), seg_col=(c_col - dc, c_col + dc)))
    return out


def corridor_raster(clusters: list, shape=grid.SHAPE, min_events: int = 8,
                    min_length_px: float = 6.0, min_elongation: float = 4.0,
                    half_width_px: float | None = None,
                    weight_by: str = "anisotropy") -> np.ndarray:
    """Oriented corridors along the principal axis of every retained cluster.

    Half-width defaults to the cluster's own catalogue location uncertainty (in
    pixels, floored at 1) — a *corridor prior*, not a trace, as the brief states.
    """
    mask = np.zeros(shape, dtype=np.float32)
    for cl in clusters:
        if cl.n < min_events or cl.length_km * 10.0 < min_length_px:
            continue
        if np.isfinite(cl.elongation) and cl.elongation < min_elongation:
            continue
        half = half_width_px if half_width_px is not None else max(1.0, cl.sigma_km * 10.0)
        r0, r1 = cl.seg_row
        c0, c1 = cl.seg_col
        rr = np.arange(max(0, int(min(r0, r1) - half - 2)), min(shape[0], int(max(r0, r1) + half + 3)))
        cc = np.arange(max(0, int(min(c0, c1) - half - 2)), min(shape[1], int(max(c0, c1) + half + 3)))
        if rr.size == 0 or cc.size == 0:
            continue
        R, C = np.meshgrid(rr, cc, indexing="ij")
        dr, dc = r1 - r0, c1 - c0
        L2 = dr * dr + dc * dc
        if L2 < 1e-9:
            continue
        t = np.clip(((R - r0) * dr + (C - c0) * dc) / L2, 0.0, 1.0)
        dist = np.hypot(R - (r0 + t * dr), C - (c0 + t * dc))
        if weight_by == "anisotropy":
            w = float(np.clip(cl.anisotropy, 0.0, 1.0))
        elif weight_by == "events":
            w = float(min(cl.n, 50)) / 50.0
        else:
            w = 1.0
        band = (dist <= half)
        np.maximum.at(mask, (R[band], C[band]), w)
    return mask
