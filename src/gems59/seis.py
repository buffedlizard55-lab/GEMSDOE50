"""Seismicity point-geometry corridor field (owner-specified H55 lineage).

Method, exactly as specified by the project owner on 2026-10-06/07 and re-used here:

1.  Take epicentres from a public catalogue (here: the CC BY 4.0 Trugman
    relocated Nevada catalogue, DOI 10.5281/zenodo.11167510).
2.  Space-time thin the catalogue (largest event per 250 m x 90 d cell) and screen
    events outside the study footprint.
3.  For each retained event's neighbourhood of k nearest events, compute the full
    2-D covariance of the epicentres, eigen-decompose it, and keep linear,
    well-sampled neighbourhoods.
4.  Emit a corridor along the principal axis whose half-width equals the assumed
    catalogue location error (300 m = 3 px at 100 m).

Labelling discipline (the project charter requires this to be stated):
  * ``project`` is a 2-D adaptation of the Ouillon-Sornette clustering idea.  It is
    NOT the published 3-D tetrahedron test of Ouillon & Sornette (2011) and it is
    NOT ACLUD.  The step is an **unverified project adaptation**.
  * The catalogue carries no event-specific covariance; the 300 m half-width is an
    assumption, not a measured location error.
"""

from __future__ import annotations

import gzip
from dataclasses import dataclass
from pathlib import Path

import numpy as np

DEFAULT_K = 8
DEFAULT_LINEARITY = 0.85
DEFAULT_MIN_EVENTS = 6
DEFAULT_HALF_WIDTH_PX = 3.0


@dataclass(frozen=True)
class Catalog:
    x: np.ndarray  # projected easting (m)
    y: np.ndarray  # projected northing (m)
    z: np.ndarray  # depth (km)
    mag: np.ndarray
    t: np.ndarray  # days since epoch


def _to_days(otime: np.ndarray) -> np.ndarray:
    import datetime as _dt

    out = np.empty(len(otime), dtype=np.float64)
    for i, s in enumerate(otime):
        try:
            out[i] = _dt.datetime.fromisoformat(s.replace("Z", "+00:00")).timestamp() / 86400.0
        except ValueError:
            out[i] = np.nan
    return out


def load_trugman(path: Path | str, transformer) -> Catalog:
    """Load the hash-pinned relocated catalogue and project it to the grid CRS."""
    # Layout: evid "YYYY-MM-DD HH:MM:SS.sss" lat lon dep mag reloc
    # The origin time is quoted and contains a space, so the line is split on the
    # quote character rather than on whitespace.
    evid: list[str] = []
    otime: list[str] = []
    nums: list[tuple[float, float, float, float, float]] = []
    with gzip.open(path, "rt") as fh:
        header = fh.readline().split()
        for ln in fh:
            ln = ln.strip()
            if not ln:
                continue
            left, mid, right = ln.split('"')
            evid.append(left.strip())
            otime.append(mid)
            v = right.split()
            nums.append((float(v[0]), float(v[1]), float(v[2]), float(v[3]), float(v[4])))
    if header != ["evid", "otime", "lat", "lon", "dep", "mag", "reloc"]:
        raise ValueError(f"unexpected catalogue header: {header}")
    arr = np.array(nums, dtype=np.float64)
    lat = arr[:, 0]
    lon = arr[:, 1]
    dep = arr[:, 2]
    mag = arr[:, 3]
    otime = np.array(otime, dtype=object)
    x, y = transformer.transform(lon, lat)
    return Catalog(
        x=np.asarray(x), y=np.asarray(y), z=dep, mag=mag, t=_to_days(otime)
    )


def space_time_thin(cat: Catalog, *, cell_m: float = 250.0, window_d: float = 90.0) -> Catalog:
    """Deterministic largest-event-per-cell thinning (documented, not ETAS)."""
    key_c = (np.floor(cat.x / cell_m).astype(np.int64) << 32) ^ np.floor(cat.y / cell_m).astype(
        np.int64
    )
    key_t = np.floor(cat.t / window_d).astype(np.int64)
    order = np.lexsort((-cat.mag, key_c, key_t))
    kc, kt = key_c[order], key_t[order]
    keep = np.ones(len(order), dtype=bool)
    keep[1:] = (kc[1:] != kc[:-1]) | (kt[1:] != kt[:-1])
    sel = order[keep]
    return Catalog(cat.x[sel], cat.y[sel], cat.z[sel], cat.mag[sel], cat.t[sel])


def lineation_corridors(
    cat: Catalog,
    *,
    k: int = DEFAULT_K,
    linearity: float = DEFAULT_LINEARITY,
    min_events: int = DEFAULT_MIN_EVENTS,
    radius_m: float = 8000.0,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """Local 2-D covariance eigen-fit of each event's k-nearest neighbourhood.

    Returns ``(x, y, angle_rad, half_length_m)`` for accepted neighbourhoods.
    Acceptance requires at least ``min_events`` neighbours inside ``radius_m``,
    a linearity ``1 - l2/l1 >= linearity``, and a principal half-length of at
    least one 100 m grid pixel.
    """
    from scipy.spatial import cKDTree

    pts = np.column_stack([cat.x, cat.y])
    tree = cKDTree(pts)
    dist, idx = tree.query(pts, k=k + 1, distance_upper_bound=radius_m)
    dist, idx = dist[:, 1:], idx[:, 1:]
    valid = np.isfinite(dist)

    xs = np.where(valid, cat.x[np.where(valid, idx, 0)], 0.0)
    ys = np.where(valid, cat.y[np.where(valid, idx, 0)], 0.0)
    w = valid.astype(np.float64)
    n = w.sum(axis=1)
    mx = (xs * w).sum(axis=1) / np.maximum(n, 1)
    my = (ys * w).sum(axis=1) / np.maximum(n, 1)
    dx = (xs - mx[:, None]) * w
    dy = (ys - my[:, None]) * w
    sxx = (dx * dx).sum(axis=1) / np.maximum(n - 1, 1)
    syy = (dy * dy).sum(axis=1) / np.maximum(n - 1, 1)
    sxy = (dx * dy).sum(axis=1) / np.maximum(n - 1, 1)

    tr = sxx + syy
    det = sxx * syy - sxy * sxy
    disc = np.sqrt(np.maximum(tr * tr / 4.0 - det, 0.0))
    l1 = tr / 2.0 + disc
    l2 = tr / 2.0 - disc
    lin = np.where(l1 > 0, 1.0 - np.maximum(l2, 0.0) / np.maximum(l1, 1e-12), 0.0)
    angle = 0.5 * np.arctan2(2.0 * sxy, (sxx - syy) + 1e-30)
    half_len = 2.0 * np.sqrt(np.maximum(l1, 0.0))  # 2 sigma along the principal axis

    ok = (n >= min_events) & (lin >= linearity) & (half_len >= 100.0)
    return cat.x[ok], cat.y[ok], angle[ok], half_len[ok]


def corridor_raster(
    x: np.ndarray,
    y: np.ndarray,
    angle: np.ndarray,
    half_len: np.ndarray,
    *,
    shape: tuple[int, int],
    transform,
    half_width_px: float = DEFAULT_HALF_WIDTH_PX,
    samples: int = 24,
) -> tuple[np.ndarray, np.ndarray]:
    """Rasterise corridors and return ``(binary_axis_mask, corridor_field)``.

    ``corridor_field`` is ``max(0, 1 - d/half_width_px)`` where ``d`` is the
    Euclidean distance (in pixels) to the nearest axis pixel.
    """
    from scipy import ndimage

    h, w = shape
    mask = np.zeros((h, w), dtype=bool)
    if len(x) == 0:
        return mask, np.zeros((h, w), dtype=np.float32)

    # Project the principal axis into pixel space.  The grid is north-up with a
    # 100 m square pixel whose y axis points down, so
    #   col = (X - left)/100,   row = (top - Y)/100.
    left, top = transform.c, transform.f
    col = (x - left) / 100.0
    row = (top - y) / 100.0
    ang = np.asarray(angle, dtype=np.float64)
    hl_px = np.asarray(half_len, dtype=np.float64) / 100.0
    t = np.linspace(-1.0, 1.0, samples)[None, :]
    cc = col[:, None] + np.cos(ang)[:, None] * hl_px[:, None] * t
    rr = row[:, None] - np.sin(ang)[:, None] * hl_px[:, None] * t
    ci = np.rint(cc).astype(np.int64).ravel()
    ri = np.rint(rr).astype(np.int64).ravel()
    ok = (ri >= 0) & (ri < h) & (ci >= 0) & (ci < w)
    mask[ri[ok], ci[ok]] = True

    d = ndimage.distance_transform_edt(~mask)
    field = np.maximum(1.0 - d / float(half_width_px), 0.0).astype(np.float32)
    return mask, field
