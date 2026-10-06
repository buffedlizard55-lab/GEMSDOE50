"""Separating clustered events from uncorrelated background.

Two independent tests are implemented, because the brief's method rests on one of them:

1. :func:`triangle_area_filter` -- a **2-D adaptation** of the Ouillon & Sornette (2011)
   tetrahedron test.  In 3-D that test compares the volume of the tetrahedron formed by
   an event and its three nearest neighbours against the same statistic measured on a
   *randomized* catalogue, and removes events that look like a Poisson background
   (Ouillon, G. and Sornette, D., 2011, "Segmentation of fault networks determined from
   spatial clustering of earthquakes", JGR 116, B02306, doi:10.1029/2010JB007752; the
   abstract states the tetrahedra-randomization step verbatim).  The triangle area in 2-D
   is the natural analogue, but **the adaptation itself is this project's own and is
   unverified against published results** -- it is measured here, not assumed.

2. :func:`nearest_neighbour_filter` -- the rescaled nearest-neighbour distance test, which
   is fully published in 2-D+time: Baiesi, M. and Paczuski, M. (2004), Phys. Rev. E 69,
   066106, doi:10.1103/PhysRevE.69.066106, and Zaliapin, I. and Ben-Zion, Y. (2013),
   JGR 118, 2847-2861, doi:10.1002/jgrb.50159 ("Earthquake clusters in southern
   California I").  It is used here as an independent control on test 1.

Both return a boolean array marking the events *kept* as clustered.
"""

from __future__ import annotations

import numpy as np
from scipy.spatial import cKDTree


def _triangle_areas(xy: np.ndarray, neighbours: np.ndarray) -> np.ndarray:
    """Area of the triangle (event, nn1, nn2) for every event."""
    p = xy
    a = xy[neighbours[:, 0]]
    b = xy[neighbours[:, 1]]
    return 0.5 * np.abs(
        (a[:, 0] - p[:, 0]) * (b[:, 1] - p[:, 1]) - (b[:, 0] - p[:, 0]) * (a[:, 1] - p[:, 1])
    )


def triangle_area_filter(
    xy: np.ndarray,
    n_random: int | None = None,
    quantile: float = 0.95,
    seed: int = 20261006,
    max_area_km2: float | None = None,
) -> tuple[np.ndarray, dict]:
    """Keep events whose local triangle area is below the randomized-catalogue reference.

    The randomized reference is a homogeneous Poisson catalogue with the same number of
    events, drawn uniformly over the axis-aligned bounding box of the data (the standard
    "randomized catalogue" surrogate).  The ``quantile`` of that reference area
    distribution is the clustering threshold: a real clustered event sits much closer to
    its two nearest neighbours than a Poisson event of the same density would.

    Returns ``(keep_mask, diagnostics)``.
    """
    xy = np.asarray(xy, dtype=np.float64)
    n = len(xy)
    if n < 4:
        return np.ones(n, dtype=bool), {"note": "too few events"}

    tree = cKDTree(xy)
    _, idx = tree.query(xy, k=3)
    areas = _triangle_areas(xy, idx[:, 1:])
    areas_km2 = areas / 1e6  # metre^2 -> km^2

    lo, hi = xy.min(axis=0), xy.max(axis=0)
    rng = np.random.default_rng(seed)
    m = int(n_random or n)
    rand = rng.uniform(lo, hi, size=(m, 2))
    rtree = cKDTree(rand)
    _, ridx = rtree.query(rand, k=3)
    ref = _triangle_areas(rand, ridx[:, 1:]) / 1e6
    threshold = float(np.quantile(ref, quantile))
    if max_area_km2 is not None:
        threshold = min(threshold, float(max_area_km2))
    keep = areas_km2 <= threshold
    diag = {
        "test": "2-D triangle-area adaptation of the Ouillon & Sornette (2011) tetrahedron test",
        "status": "ADAPTATION -- not published in this form; see module docstring",
        "n_events": int(n),
        "n_random": int(m),
        "reference_quantile": float(quantile),
        "area_threshold_km2": threshold,
        "reference_median_km2": float(np.median(ref)),
        "catalogue_median_km2": float(np.median(areas_km2)),
        "fraction_kept_clustered": float(keep.mean()),
    }
    return keep, diag


def nearest_neighbour_filter(
    xy: np.ndarray,
    time_years: np.ndarray,
    mag: np.ndarray,
    b_value: float = 1.0,
    d_f: float = 1.6,
    log_eta_threshold: float = -5.0,
) -> tuple[np.ndarray, dict]:
    """Baiesi-Paczuski / Zaliapin-Ben-Zion rescaled nearest-neighbour distance test.

    ``eta = t * r**d_f * 10**(-b*m)`` with ``t`` in years, ``r`` in km and ``m`` the
    parent magnitude; a pair is a *triggered* link when ``log10(eta) < threshold``.  Every
    event that has at least one such link to an earlier event is kept as clustered; the
    remainder is the uncorrelated background.

    Defaults follow Zaliapin & Ben-Zion (2013) for southern California
    (``b = 1``, ``d_f = 1.6``, ``log10(eta) = -5``); they are *not* re-tuned on the GEMS
    labels anywhere in this project.
    """
    xy = np.asarray(xy, dtype=np.float64)
    t = np.asarray(time_years, dtype=np.float64)
    m = np.asarray(mag, dtype=np.float64)
    n = len(xy)
    keep = np.zeros(n, dtype=bool)
    if n < 2:
        return keep, {"note": "too few events"}

    tree = cKDTree(xy)
    # 10 nearest neighbours in space is ample for the nearest *earlier* event
    _, idx = tree.query(xy, k=min(11, n))
    if idx.ndim == 1:
        idx = idx[:, None]
    for i in range(n):
        cand = idx[i][idx[i] != i]
        earlier = cand[t[cand] < t[i]]
        if earlier.size == 0:
            continue
        r_km = np.linalg.norm(xy[earlier] - xy[i], axis=1) / 1000.0
        r_km = np.maximum(r_km, 1e-3)
        dt = np.maximum(t[i] - t[earlier], 1e-6)
        eta = dt * r_km**d_f * 10.0 ** (-b_value * m[earlier])
        if np.min(np.log10(eta)) < log_eta_threshold:
            keep[i] = True
    diag = {
        "test": "rescaled nearest-neighbour distance (Baiesi & Paczuski 2004; Zaliapin & Ben-Zion 2013)",
        "b_value": b_value,
        "d_f": d_f,
        "log_eta_threshold": log_eta_threshold,
        "n_events": int(n),
        "fraction_kept_clustered": float(keep.mean()),
    }
    return keep, diag
