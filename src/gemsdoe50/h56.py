"""Archived H56 research methods: earthquake lineations with geophysical corroboration.

H56 is **NO-GO / NO SLOT**; the historical raster remains archive-only. This module retains
its analysis helpers, and its corrected ``emit_blue_noise`` implementation is prospective:
existing H56/H58 TIFF bytes were not regenerated.

For binary unit dots the exact published metric uses directional credit separately. Let ``T``
be truth-side ``TP_w``, ``M`` the sum over predicted cells of their best truth-kernel credit,
``N`` the predicted-cell count, and ``G`` the truth-cell count. Then

    DTI = T / (0.2*N + 0.8*G + 0.2*(T-M) + epsilon)

The shorter ``T / (0.2*N + 0.8*G)`` form requires ``T == M``; prediction spacing alone does not
establish this. Use the full TP/FP/FN calculation for local scores. Historical hidden-score
transfer numbers in the research notes are conditional models, not organizer scores or forecasts.

The historical belief-field design combined two evidence classes:

``seismic``
    Declustered earthquake epicentres -> local 2-D covariance of neighboring points -> linear,
    well-sampled neighborhoods -> corridors along the principal axis with half-width tied to
    catalogue location uncertainty. This is a project-specific 2-D adaptation of anisotropic
    clustering work and remains scientifically unverified; see
    ``docs/research/h56-diagnosis.md``.

``ridge``
    GeoDAWN airborne magnetic/radiometric fields and USGS 3DEP LiDAR scarp descriptors, reduced
    to a multi-scale gradient-ridge density. This is historical method documentation, not a
    current authorized candidate.

``emit_blue_noise`` now performs deterministic density-weighted random-sequential selection
with an explicit hard Euclidean minimum distance. Its 3 px parameter is a spacing design rule,
not a proven metric optimum, disjoint-support guarantee, or maximum-coverage optimizer.
Nothing here authorizes rebuilding or submitting H56; source rights, scientific, format, and
uniqueness gates remain independent requirements.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import numpy as np
from scipy import ndimage as ndi
from scipy.ndimage import distance_transform_edt
from scipy.spatial import cKDTree

#: The competition grid (EPSG:32611, 100 m).
PIXEL_M = 100.0
R_PX = 3.0          # 300 m support of the official kernel
ALPHA = 0.2
BETA = 0.8


# --------------------------------------------------------------------------------------
# 1. Catalog conditioning
# --------------------------------------------------------------------------------------
#: ComCat ``type`` values that are not tectonic earthquakes.  Dropped, and counted.
NON_TECTONIC = frozenset({
    "quarry blast", "explosion", "mining explosion", "chemical explosion",
    "nuclear explosion", "mine collapse", "quarry", "acoustic noise", "sonic boom",
    "rockslide", "other event", "not reported", "anthropogenic event",
})


def select_tectonic(df, min_mag: float = 0.0, max_h_err_km: float | None = 10.0):
    """Keep ComCat rows that are tectonic earthquakes with usable locations.

    Returns ``(frame, report)``.  The report is written into the evidence JSON so the
    rejected counts are auditable rather than silent.
    """
    import pandas as pd  # local import: pandas is only needed on this path

    df = df.copy()
    n0 = len(df)
    type_counts = df["type"].value_counts().to_dict() if "type" in df else {}
    if "type" in df:
        df = df[~df["type"].isin(NON_TECTONIC)]
    n1 = len(df)
    if min_mag > 0:
        df = df[df["mag"] >= min_mag]
    n2 = len(df)
    dropped_err = 0
    if max_h_err_km is not None and "horizontalError" in df:
        h = pd.to_numeric(df["horizontalError"], errors="coerce")
        bad = h.notna() & (h > max_h_err_km)
        dropped_err = int(bad.sum())
        df = df[~bad]
    df = df.reset_index(drop=True)
    report = {
        "rows_in": int(n0), "after_non_tectonic": int(n1),
        "after_min_mag": int(n2), "dropped_horizontal_error_gt_km": dropped_err,
        "rows_out": len(df), "min_mag": float(min_mag),
        "max_h_err_km": (None if max_h_err_km is None else float(max_h_err_km)),
        "input_type_counts": {str(k): int(v) for k, v in list(type_counts.items())[:20]},
    }
    return df, report


def epicentral_sigma_km(df, *, fallback_km: float = 2.0, floor_km: float = 0.2,
                        era_break_year: int = 2000,
                        pre_era_fallback_km: float = 2.0) -> np.ndarray:
    """Per-event epicentral 1-sigma in km, measured where the catalogue publishes it.

    ComCat's ``horizontalError`` is the authoritative field when present.  Where it is
    absent this uses a documented, era-dependent constant, and *counts* how often that
    happens so the choice is auditable.  This is an imputation, not a measurement, and it
    is flagged as such.  No per-event covariance is available, so this is **not** an
    ACLUD reproduction (Wang et al. 2013).
    """
    import pandas as pd

    n = len(df)
    h = np.full(n, np.nan, dtype=np.float64)
    if "horizontalError" in df:
        h = pd.to_numeric(df["horizontalError"], errors="coerce").to_numpy(dtype=np.float64)
    if "time" in df:
        years = pd.to_datetime(df["time"], format="ISO8601", utc=True).dt.year.to_numpy()
    else:
        years = np.full(n, era_break_year, dtype=int)
    missing = ~np.isfinite(h) | (h <= 0)
    h = np.where(missing, np.where(years < era_break_year, pre_era_fallback_km, fallback_km), h)
    h = np.maximum(h, floor_km)
    return h


def triangle_area_keep(xy_m: np.ndarray, *, n_random: int | None = None, quantile: float = 0.95,
                       seed: int = 20261007) -> tuple[np.ndarray, dict]:
    """Cluster/background separation by the 2-D triangle-area analogue of the tetrahedron test.

    Ouillon & Sornette (2011, JGR 116, B02306, doi:10.1029/2010JB007752) separate clustered
    events from an uncorrelated Poisson background by comparing the volume of the tetrahedron
    formed by an event and its three nearest neighbours against the same statistic measured on
    a **randomized catalogue**.  The 2-D reduction used here replaces the tetrahedron volume by
    the triangle area of (event, nn1, nn2); the reduction is this project's own and is
    **unverified against published results** -- it is measured, not assumed
    (``docs/research/h56-diagnosis.md``).

    Returns ``(keep, diagnostics)`` with keep = True for events classified as *clustered*.
    """
    xy = np.asarray(xy_m, dtype=np.float64)
    n = len(xy)
    if n < 4:
        return np.ones(n, dtype=bool), {"note": "too few events", "n_events": int(n)}
    tree = cKDTree(xy)
    _, idx = tree.query(xy, k=3)
    a = xy[idx[:, 1]]
    b = xy[idx[:, 2]]
    p = xy
    areas = 0.5 * np.abs((a[:, 0] - p[:, 0]) * (b[:, 1] - p[:, 1])
                         - (b[:, 0] - p[:, 0]) * (a[:, 1] - p[:, 1]))
    lo, hi = xy.min(axis=0), xy.max(axis=0)
    rng = np.random.default_rng(seed)
    m = int(n_random or n)
    rand = rng.uniform(lo, hi, size=(m, 2))
    rtree = cKDTree(rand)
    _, ridx = rtree.query(rand, k=3)
    ra = rand[ridx[:, 1]]
    rb = rand[ridx[:, 2]]
    rref = 0.5 * np.abs((ra[:, 0] - rand[:, 0]) * (rb[:, 1] - rand[:, 1])
                        - (rb[:, 0] - rand[:, 0]) * (ra[:, 1] - rand[:, 1]))
    thr = float(np.quantile(rref, quantile))
    keep = areas <= thr
    diag = {
        "test": "2-D triangle-area adaptation of the Ouillon & Sornette (2011) tetrahedron test",
        "status": "ADAPTATION -- not published in this 2-D form",
        "n_events": int(n), "n_random": int(m), "reference_quantile": float(quantile),
        "area_threshold_m2": thr,
        "reference_median_m2": float(np.median(rref)),
        "catalogue_median_m2": float(np.median(areas)),
        "fraction_kept_clustered": float(keep.mean()),
    }
    return keep, diag


def gardner_knopoff_keep(spatial_km: np.ndarray, time_days: np.ndarray,
                         mag: np.ndarray) -> tuple[np.ndarray, dict]:
    """Standard magnitude-dependent space-time aftershock removal.

    Gardner, J. K. & Knopoff, L. (1974), "Is the sequence of earthquakes in Southern
    California, with aftershocks removed, Poissonian?", BSSA 64(5), 1363-1367.  The metric
    form of the windows used here is the one published for the western United States:

        log10 R(M) = 0.1238 * M + 0.983      (R in km)
        log10 T(M) = 0.032   * M + 2.738     (T in days)

    An event is removed when it falls inside the window of a **larger** event earlier in
    time.  This is fully published in 2-D + time and is independent of the triangle-area
    adaptation above, so the two together give a cross-check rather than a single
    unvalidated filter.

    Returns ``(keep, diagnostics)``, keep = True for events that survive (background + the
    largest event of each sequence).
    """
    spatial_km = np.asarray(spatial_km, dtype=np.float64)
    time_days = np.asarray(time_days, dtype=np.float64)
    mag = np.asarray(mag, dtype=np.float64)
    n = len(mag)
    if n == 0:
        return np.zeros(0, dtype=bool), {"note": "no events"}
    order = np.argsort(-mag, kind="stable")          # largest first
    keep = np.ones(n, dtype=bool)
    tree = cKDTree(spatial_km)
    removed = 0
    for i in order:
        if not keep[i]:
            continue
        r_km = 10.0 ** (0.1238 * mag[i] + 0.983)
        t_d = 10.0 ** (0.032 * mag[i] + 2.738)
        for j in tree.query_ball_point(spatial_km[i], r_km):
            if j == i or not keep[j]:
                continue
            if (abs(time_days[j] - time_days[i]) <= t_d and mag[j] <= mag[i]
                    and (mag[j] < mag[i] or time_days[j] > time_days[i])):
                keep[j] = False
                removed += 1
    diag = {"test": "Gardner & Knopoff (1974) space-time window declustering",
            "status": "FULLY PUBLISHED (2-D + time)", "n_events": int(n),
            "removed": int(removed), "kept": int(keep.sum()),
            "fraction_kept": float(keep.mean()),
            "window_R_km_at_M3": float(10.0 ** (0.1238 * 3 + 0.983)),
            "window_T_days_at_M3": float(10.0 ** (0.032 * 3 + 2.738))}
    return keep, diag


# --------------------------------------------------------------------------------------
# 2. Local lineation from the point pattern (2-D covariance / inertia tensor)
# --------------------------------------------------------------------------------------
@dataclass
class Lineations:
    x: np.ndarray
    y: np.ndarray
    ux: np.ndarray
    uy: np.ndarray
    sigma1_m: np.ndarray
    sigma2_m: np.ndarray
    sigma_loc_m: np.ndarray
    n_events: np.ndarray
    weight: np.ndarray

    def __len__(self) -> int:
        return int(self.x.size)

    def as_dict(self) -> dict[str, Any]:
        return {
            "n_neighbourhoods": len(self),
            "sigma1_m_median": float(np.median(self.sigma1_m)) if len(self) else None,
            "sigma2_m_median": float(np.median(self.sigma2_m)) if len(self) else None,
            "sigma_loc_m_median": float(np.median(self.sigma_loc_m)) if len(self) else None,
            "n_events_median": float(np.median(self.n_events)) if len(self) else None,
        }


def _empty_lineations() -> Lineations:
    z = np.zeros(0)
    return Lineations(z, z.copy(), z.copy(), z.copy(), z.copy(), z.copy(), z.copy(), z.copy(), z.copy())


def neighbourhood_lineations(
    xy_m: np.ndarray,
    sigma_loc_m: np.ndarray,
    *,
    k: int = 14,
    r_max_m: float = 12_000.0,
    min_events: int = 8,
    min_elongation: float = 4.0,
    sigma2_over_loc_max: float = 1.0,
    min_sigma1_m: float = 1_500.0,
) -> Lineations:
    """Principal-axis (2-D inertia tensor) fit of every event's k-nearest neighbourhood.

    Acceptance criteria, all of them stated in the docstring so a reviewer can move them:

    * ``n_events >= min_events``                 -- the neighbourhood must be well sampled
    * ``elongation = sigma1 / sigma2 >= min_elongation``  -- it must be *linear*
    * ``sigma2 <= sigma2_over_loc_max * sigma_loc``       -- the 2-D reduction of the
      published 3-D rule ``lambda_3 < Delta^2`` (Ouillon et al. 2008); a neighbourhood no
      thinner than its own location error says nothing about a plane
    * ``sigma1 >= min_sigma1_m``                 -- the long axis must be resolved

    Each event is weighted by ``1 / sigma_loc^2`` (the Wang et al. 2013 weighting, applied
    to the epicentral uncertainty this catalogue actually publishes).
    """
    xy = np.asarray(xy_m, dtype=np.float64)
    sig = np.maximum(np.asarray(sigma_loc_m, dtype=np.float64), 1.0)
    n = len(xy)
    if n < min_events:
        return _empty_lineations()
    tree = cKDTree(xy)
    kq = min(k, n)
    dist, idx = tree.query(xy, k=kq, distance_upper_bound=r_max_m)
    dist = np.asarray(dist, dtype=np.float64)

    out = {name: [] for name in ("x", "y", "ux", "uy", "s1", "s2", "sl", "ne", "w")}
    for i in range(n):
        ok = np.isfinite(dist[i])
        nb = idx[i][ok]
        nb = nb[nb != i]
        if nb.size < min_events - 1:
            continue
        pts = xy[nb] - xy[i]
        sl = np.maximum(sig[nb], 100.0)
        w = 1.0 / sl ** 2
        w = w / w.sum()
        mu = (w[:, None] * pts).sum(axis=0)
        d = pts - mu
        cov = (w[:, None] * d).T @ d
        vals, vecs = np.linalg.eigh(cov)
        lam2, lam1 = float(max(vals[0], 0.0)), float(max(vals[1], 0.0))
        s1, s2 = float(np.sqrt(lam1)), float(np.sqrt(lam2))
        if nb.size + 1 < min_events or s2 <= 0:
            continue
        elong = s1 / max(s2, 1e-9)
        s_loc = float(np.sqrt(np.mean(sl ** 2)))
        if elong < min_elongation:
            continue
        if s2 > sigma2_over_loc_max * s_loc:
            continue
        if s1 < min_sigma1_m:
            continue
        v = vecs[:, 1]
        out["x"].append(float(xy[i, 0] + mu[0]))
        out["y"].append(float(xy[i, 1] + mu[1]))
        out["ux"].append(float(v[0]))
        out["uy"].append(float(v[1]))
        out["s1"].append(s1)
        out["s2"].append(s2)
        out["sl"].append(s_loc)
        out["ne"].append(float(nb.size + 1))
        out["w"].append(float(min(elong / 10.0, 1.0)))
    if not out["x"]:
        return _empty_lineations()
    return Lineations(
        x=np.asarray(out["x"]), y=np.asarray(out["y"]),
        ux=np.asarray(out["ux"]), uy=np.asarray(out["uy"]),
        sigma1_m=np.asarray(out["s1"]), sigma2_m=np.asarray(out["s2"]),
        sigma_loc_m=np.asarray(out["sl"]), n_events=np.asarray(out["ne"]),
        weight=np.asarray(out["w"]),
    )


def corridor_density(lin: Lineations, shape, transform, *, sigma_perp_scale: float = 1.0,
                     min_half_width_px: float = 1.0, max_half_width_px: float = 6.0,
                     along_cap_px: float = 6.0, length_scale_px: float = 2.0) -> np.ndarray:
    """Render the accepted neighbourhoods as an oriented *density*, one ellipse each.

    The corridor half-width is the catalogue's own epicentral uncertainty
    (``sigma_loc_m``), scaled by ``sigma_perp_scale`` and clipped -- this is a **corridor
    prior**, not a trace, because a location error of 2 km is 20 pixels at 100 m.  Each
    neighbourhood contributes along its principal axis with half-length
    ``min(sigma1, along_cap_px)`` so that one long, well-determined cluster cannot flood the
    grid.
    """
    h, w = shape
    acc = np.zeros((h, w), dtype=np.float64)
    if len(lin) == 0:
        return acc
    a = float(transform.a)
    e = float(transform.e)
    # work in pixel space
    px = (lin.x - transform.c) / a
    py = (lin.y - transform.f) / e
    for i in range(len(lin)):
        s1px = min(float(lin.sigma1_m[i]) / abs(a), along_cap_px) * length_scale_px
        s2px = np.clip(float(lin.sigma_loc_m[i]) / abs(a) * sigma_perp_scale,
                       min_half_width_px, max_half_width_px)
        ux, uy = float(lin.ux[i]), float(lin.uy[i])
        # local frame: rows increase downward while e < 0
        u_col, u_row = ux, -uy
        n = int(np.ceil(3.5 * max(s1px, s2px)))
        rr = np.arange(-n, n + 1)
        cc = np.arange(-n, n + 1)
        CC, RR = np.meshgrid(cc, rr)
        # rotate into the axis frame: along = C*u_col + R*u_row
        along = CC * u_col + RR * u_row
        perp = -CC * u_row + RR * u_col
        g = np.exp(-0.5 * ((along / max(s1px, 1e-6)) ** 2 + (perp / max(s2px, 1e-6)) ** 2))
        g /= max(g.max(), 1e-12)
        r0 = round(py[i])
        c0 = round(px[i])
        r1, r2 = r0 - n, r0 + n + 1
        c1, c2 = c0 - n, c0 + n + 1
        sr1, sr2 = max(r1, 0), min(r2, h)
        sc1, sc2 = max(c1, 0), min(c2, w)
        if sr1 >= sr2 or sc1 >= sc2:
            continue
        sub = g[sr1 - r1: sr2 - r1, sc1 - c1: sc2 - c1]
        acc[sr1:sr2, sc1:sc2] = np.maximum(acc[sr1:sr2, sc1:sc2],
                                           sub * float(lin.weight[i]))
    return acc


# --------------------------------------------------------------------------------------
# 3. Geophysical ridge *density*
# --------------------------------------------------------------------------------------
def fill_nan(a: np.ndarray) -> np.ndarray:
    """Nearest-neighbour fill; used only to keep gradients finite at survey edges."""
    a = np.asarray(a, dtype=np.float64)
    m = np.isfinite(a)
    if m.all():
        return a
    idx = distance_transform_edt(~m, return_distances=False, return_indices=True)
    filled = a[tuple(idx)]
    return np.where(m, a, filled)


def ridge_response(field: np.ndarray, sigma: float) -> np.ndarray:
    """Multi-scale gradient ridge response ``|grad G_sigma f|`` smoothed at the same scale.

    A fault that juxtaposes rocks of different magnetisation (or a scarp that offsets the
    surface) produces a *linear gradient*, not a blob, so the gradient magnitude is the
    physical signature; the second smoothing removes pixel-scale noise and gives the ridge a
    finite footprint of the same width as the metric's own support.
    """
    f = ndi.gaussian_filter(fill_nan(field), sigma)
    gy, gx = np.gradient(f)
    g = np.hypot(gx, gy)
    return ndi.gaussian_filter(g, sigma)


def ridge_density(channels: dict[str, np.ndarray], *, sigmas=(1.5, 3.0),
                  density_sigma_px: float = 8.0) -> tuple[np.ndarray, dict]:
    """Rank-normalised multi-scale ridge density from a dict of scalar channel rasters.

    Each channel is transformed to within-channel rank (a monotone transform that makes
    physically different units, nT/m and counts/s, comparable without inventing a scale),
    its ridge response is computed at each ``sigma``, and the responses are averaged and
    then **smoothed at ``density_sigma_px``**.  The smoothing is the point: the emitter must
    see "this district carries a lot of lineament", not "this one pixel is the strongest
    ridge in the state", because concentration is the failure mode being fixed.
    """
    ranks = []
    per_channel = {}
    for name, ch in channels.items():
        a = np.asarray(ch, dtype=np.float64)
        finite = np.isfinite(a)
        if finite.sum() < 100:
            continue
        order = np.argsort(np.argsort(a[finite], kind="stable"), kind="stable")
        r = np.full(a.shape, np.nan)
        r[finite] = order / max(finite.sum() - 1, 1)
        resp = np.zeros(a.shape, dtype=np.float64)
        for s in sigmas:
            resp += ridge_response(r, s) / len(sigmas)
        per_channel[name] = float(np.nanmean(resp))
        ranks.append(resp)
    if not ranks:
        raise ValueError("ridge_density needs at least one usable channel")
    total = np.mean(ranks, axis=0)
    dens = ndi.gaussian_filter(fill_nan(total), density_sigma_px)
    dens = np.where(np.isfinite(total), dens, 0.0)
    return dens, {"channels": list(channels), "sigmas": list(sigmas),
                  "density_sigma_px": float(density_sigma_px),
                  "per_channel_mean": per_channel}


def unit_range(a: np.ndarray, mask: np.ndarray | None = None) -> np.ndarray:
    """Scale to [0, 1] using the 1st/99th percentile of the masked region."""
    a = np.asarray(a, dtype=np.float64)
    sel = np.isfinite(a) if mask is None else (mask & np.isfinite(a))
    if sel.sum() < 10:
        return np.zeros_like(a)
    lo, hi = np.percentile(a[sel], [1.0, 99.0])
    if hi <= lo:
        return np.zeros_like(a)
    return np.clip((a - lo) / (hi - lo), 0.0, 1.0)


# --------------------------------------------------------------------------------------
# 4. Coverage-optimal emission (the metric's own marginal rule as a greedy submodular step)
# --------------------------------------------------------------------------------------
def kernel_offsets(offsets: int = 3):
    rr, cc = np.mgrid[-offsets: offsets + 1, -offsets: offsets + 1]
    d = np.sqrt(rr.astype(np.float64) ** 2 + cc.astype(np.float64) ** 2)
    keep = d <= offsets
    return cc[keep], rr[keep], np.maximum(1.0 - d[keep] / offsets, 0.0)


@dataclass
class Emission:
    rows: np.ndarray
    cols: np.ndarray
    belief_credit: float
    marginal_credits: list[float] = field(default_factory=list)

    def as_dict(self) -> dict[str, Any]:
        return {
            "n_dots": int(self.rows.size),
            "belief_credit": float(self.belief_credit),
            "marginal_credit_min": float(min(self.marginal_credits)) if self.marginal_credits else None,
            "marginal_credit_mean": (float(np.mean(self.marginal_credits))
                                     if self.marginal_credits else None),
        }


def emit_coverage(belief: np.ndarray, domain: np.ndarray, *, n_max: int,
                  g_hat: float, s_init: float = 0.25,
                  min_belief_frac: float = 1e-6) -> Emission:
    """Legacy greedy belief-coverage heuristic; not the official metric optimizer.

    ``belief`` is treated as a non-negative credit density and the procedure maximizes
    ``sum_y b(y) max_dot k(d(y, dot))`` greedily. Its acceptance gate uses a simplified
    denominator model, `T/(0.2 N + 0.8 G_hat)`, which assumes equality of truth-side and
    prediction-side matched credit. That equality is not guaranteed by a calibrated belief or
    by minimum-distance spacing. Retain this helper only for historical comparisons; evaluate
    candidates with the full published TP/FP/FN equations (as ``score_dots`` does).

    Complexity is O(#candidates x 49); candidates are visited in descending belief order.
    """
    belief = np.asarray(belief, dtype=np.float64)
    h, w = belief.shape
    pad = 3
    bp = np.pad(belief, pad)
    m = np.zeros_like(bp)
    cand = np.flatnonzero(np.asarray(domain, dtype=bool).ravel() & (belief.ravel() > min_belief_frac))
    if cand.size == 0:
        return Emission(np.zeros(0, dtype=int), np.zeros(0, dtype=int), 0.0)
    order = cand[np.argsort(-belief.ravel()[cand], kind="stable")]
    rows = (order // w).astype(np.int64)
    cols = (order % w).astype(np.int64)

    dc_, dr_, dw_ = kernel_offsets(pad)
    b_views = [bp[pad + dr: pad + dr + h, pad + dc: pad + dc + w] for dc, dr in zip(dc_, dr_)]
    m_views = [m[pad + dr: pad + dr + h, pad + dc: pad + dc + w] for dc, dr in zip(dc_, dr_)]

    out_r: list[int] = []
    out_c: list[int] = []
    credits: list[float] = []
    t_credit = 0.0
    n = 0
    for i in range(rows.size):
        r = int(rows[i])
        c = int(cols[i])
        dt = 0.0
        dc = 0.0
        for o in range(dw_.size):
            ko = dw_[o]
            mo = m_views[o][r, c]
            if ko > mo:
                bv = b_views[o][r, c]
                if bv > 0.0:
                    dt += bv * (ko - mo)
                dc = max(dc, ko)
        if dt <= 0.0:
            continue
        s = t_credit / (ALPHA * (2 * n + 1) + (1.0 - ALPHA) * g_hat) if n else s_init
        if dt <= ALPHA * s * (dt + 1.0 - dc):
            continue
        for o in range(dw_.size):
            ko = dw_[o]
            m_views[o][r, c] = max(m_views[o][r, c], ko)
        t_credit += dt
        n += 1
        out_r.append(r)
        out_c.append(c)
        credits.append(dt)
        if n >= n_max:
            break
    return Emission(np.asarray(out_r, dtype=np.int64), np.asarray(out_c, dtype=np.int64),
                    t_credit, credits)


def emit_poisson_disk(score: np.ndarray, domain: np.ndarray, n_target: int,
                      min_sep_px: float, seed: int = 0) -> Emission:
    """Rank-ordered emission with a hard minimum separation.

    Kept as an explicit **control**: it is the corpus's own emission geometry (top-ranked
    pixels thinned by a Poisson-disk radius), so a candidate can be compared against the
    prior art's geometry at matched mass.
    """
    score = np.asarray(score, dtype=np.float64)
    w = score.shape[1]
    dom = np.asarray(domain, dtype=bool)
    cand = np.flatnonzero(dom.ravel() & np.isfinite(score.ravel()) & (score.ravel() > 0))
    if cand.size == 0:
        return Emission(np.zeros(0, dtype=int), np.zeros(0, dtype=int), 0.0)
    rng = np.random.default_rng(seed)
    order = cand[np.argsort(-score.ravel()[cand], kind="stable")]
    sep2 = float(min_sep_px) ** 2
    cell = max(float(min_sep_px), 1.0)
    grid: dict[tuple[int, int], list[tuple[int, int]]] = {}
    kept: list[tuple[int, int]] = []
    for idx in order:
        r = int(idx // w)
        c = int(idx % w)
        r0, c0 = int(r // cell), int(c // cell)
        clash = False
        for dr in (-1, 0, 1):
            for dcc in (-1, 0, 1):
                for (pr, pc) in grid.get((r0 + dr, c0 + dcc), ()):
                    if (pr - r) ** 2 + (pc - c) ** 2 < sep2:
                        clash = True
                        break
                if clash:
                    break
            if clash:
                break
        if clash:
            continue
        grid.setdefault((r0, c0), []).append((r, c))
        kept.append((r, c))
        if len(kept) >= n_target:
            break
    del rng
    if not kept:
        return Emission(np.zeros(0, dtype=int), np.zeros(0, dtype=int), 0.0)
    arr = np.asarray(kept, dtype=np.int64)
    return Emission(arr[:, 0], arr[:, 1], float(score[arr[:, 0], arr[:, 1]].sum()))


def emit_blue_noise(density: np.ndarray, domain: np.ndarray, *, n_target: int,
                    min_sep_px: float = 3.0, seed: int = 0) -> Emission:
    """Emit density-weighted pixels with a hard Euclidean Poisson-disk separation.

    Each finite, positive-density eligible pixel receives an exponential-race priority
    ``-log(U) / density``. Candidates are visited in increasing-priority order and accepted
    only when their pixel-centre distance from every accepted point is at least
    ``min_sep_px``. A spatial hash limits each exact Euclidean check to nearby buckets.
    This is weighted random sequential inhibition: high-density cells have a higher chance
    of early selection, while the hard-distance rule reduces immediate crowding at the scale
    of the metric kernel. It does not make full kernel footprints disjoint.

    The result is deterministic for a fixed seed and never relaxes spacing to hit the target.
    It may return fewer than ``n_target`` when the positive-density domain cannot supply
    that many separated pixels. This is a Poisson-disk emitter, not a claim of a particular
    spectral blue-noise distribution.
    """
    density = np.asarray(density, dtype=np.float64)
    domain = np.asarray(domain, dtype=bool)
    if density.ndim != 2 or domain.shape != density.shape:
        raise ValueError("density and domain must be same-shaped 2-D arrays")
    if not np.isfinite(min_sep_px) or min_sep_px <= 0:
        raise ValueError("min_sep_px must be finite and positive")
    if int(n_target) != n_target or n_target < 0:
        raise ValueError("n_target must be a non-negative integer")
    n_target = int(n_target)
    if n_target == 0:
        return Emission(np.zeros(0, dtype=np.int64), np.zeros(0, dtype=np.int64), 0.0)

    candidate_idx = np.flatnonzero(
        (domain & np.isfinite(density) & (density > 0.0)).ravel()
    )
    if candidate_idx.size == 0:
        return Emission(np.zeros(0, dtype=np.int64), np.zeros(0, dtype=np.int64), 0.0)

    # Exponential-race priorities implement weighted sampling without replacement.
    # Work in log space so very small but positive density values do not overflow. Fill the
    # priority array in place and gather weights in chunks to avoid several full-grid copies.
    rng = np.random.default_rng(seed)
    priorities = rng.random(candidate_idx.size)
    chunk_size = 1_000_000
    for start in range(0, candidate_idx.size, chunk_size):
        end = min(start + chunk_size, candidate_idx.size)
        priority_chunk = priorities[start:end]
        np.maximum(priority_chunk, np.finfo(np.float64).tiny, out=priority_chunk)
        np.log(priority_chunk, out=priority_chunk)
        np.negative(priority_chunk, out=priority_chunk)
        np.log(priority_chunk, out=priority_chunk)
        log_weights = density.ravel()[candidate_idx[start:end]]
        np.log(log_weights, out=log_weights)
        priority_chunk -= log_weights

    width = density.shape[1]
    cell_size = float(min_sep_px)
    min_distance_sq = cell_size * cell_size
    neighbor_offsets = (-1, 0, 1)  # cell size equals radius, so any clash is in these buckets
    kept: list[tuple[int, int]] = []
    buckets: dict[tuple[int, int], list[tuple[int, int]]] = {}

    # Start with a modest prefix. If density concentration or boundary effects leave the
    # target short, expand the exact priority prefix and restart; candidates are never lost.
    pool_size = min(candidate_idx.size, max(1_024, 4 * n_target))
    while True:
        if pool_size == candidate_idx.size:
            pool = np.arange(candidate_idx.size, dtype=np.int64)
        else:
            pool = np.argpartition(priorities, pool_size - 1)[:pool_size]
        order = pool[np.lexsort((pool, priorities[pool]))]
        kept = []
        buckets = {}
        for candidate_position in order:
            flat = int(candidate_idx[candidate_position])
            row, col = divmod(flat, width)
            bucket = (int(np.floor(row / cell_size)), int(np.floor(col / cell_size)))
            clash = False
            for dr in neighbor_offsets:
                for dc in neighbor_offsets:
                    for other_row, other_col in buckets.get((bucket[0] + dr, bucket[1] + dc), ()):
                        if (row - other_row) ** 2 + (col - other_col) ** 2 < min_distance_sq:
                            clash = True
                            break
                    if clash:
                        break
                if clash:
                    break
            if clash:
                continue
            buckets.setdefault(bucket, []).append((row, col))
            kept.append((row, col))
            if len(kept) >= n_target:
                break

        if len(kept) >= n_target or pool_size == candidate_idx.size:
            break
        pool_size = min(candidate_idx.size, max(pool_size * 2, 4 * n_target))

    if not kept:
        return Emission(np.zeros(0, dtype=np.int64), np.zeros(0, dtype=np.int64), 0.0)
    points = np.asarray(kept, dtype=np.int64)
    rows, cols = points[:, 0], points[:, 1]
    return Emission(rows, cols, float(density[rows, cols].sum()))


def snap_to_ridge(rows: np.ndarray, cols: np.ndarray, ridge: np.ndarray,
                  max_snap_px: float = 3.0) -> tuple[np.ndarray, np.ndarray, dict]:
    """Move each dot to the strongest ridge pixel within ``max_snap_px``.

    Placement step required by the design: a corridor is a *prior* over a several-pixel
    swath, so the final dot is put on the strongest independent geophysical ridge inside
    that swath.  If no ridge exceeds zero within the radius, the dot is left where it is and
    the miss is counted.

    The input arrays are **not** modified; the returned positions are a fresh array.  (An
    earlier revision mutated the caller's array through ``np.asarray`` and silently turned a
    rejected snap into a 16 % pixel collision rate downstream -- see
    ``tests/test_h56.py::test_snap_to_ridge_does_not_mutate_its_inputs``.)
    """
    r = np.array(rows, dtype=np.int64, copy=True)   # copy: this function rewrites positions
    c = np.array(cols, dtype=np.int64, copy=True)
    h, w = ridge.shape
    n = int(np.floor(max_snap_px))
    snapped = 0
    for i in range(r.size):
        r0, c0 = int(r[i]), int(c[i])
        r1, r2 = max(r0 - n, 0), min(r0 + n + 1, h)
        c1, c2 = max(c0 - n, 0), min(c0 + n + 1, w)
        if r1 >= r2 or c1 >= c2:
            continue
        win = ridge[r1:r2, c1:c2]
        k = int(np.argmax(win))
        if win.flat[k] <= 0:
            continue
        dr, dc = divmod(k, win.shape[1])
        nr, nc = r1 + dr, c1 + dc
        if (nr - r0) ** 2 + (nc - c0) ** 2 <= max_snap_px ** 2:
            r[i] = nr
            c[i] = nc
            snapped += 1
    info = {"n": int(r.size), "snapped": int(snapped),
            "snap_fraction": float(snapped / max(r.size, 1)),
            "max_snap_px": float(max_snap_px)}
    return r, c, info


def dedupe(rows: np.ndarray, cols: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Remove duplicate pixels (two dots on one pixel pay 0.2 N for one dot's credit)."""
    if rows.size == 0:
        return rows, cols
    lin = rows.astype(np.int64) * 1_000_000 + cols.astype(np.int64)
    _, keep = np.unique(lin, return_index=True)
    keep = np.sort(keep)
    return rows[keep], cols[keep]


# --------------------------------------------------------------------------------------
# 5. Scoring helpers used by the build script (never an organizer score)
# --------------------------------------------------------------------------------------
def credit_field(truth: np.ndarray, offsets: int = 3) -> np.ndarray:
    """``max_g k(d(x,g))`` for every pixel x, computed exactly from a distance transform."""
    d = distance_transform_edt(~np.asarray(truth, dtype=bool))
    return np.maximum(1.0 - d / offsets, 0.0)


def score_dots(truth: np.ndarray, rows: np.ndarray, cols: np.ndarray) -> dict:
    """Exact DTI components of a binary dot set, using the published equations."""
    truth = np.asarray(truth, dtype=bool)
    t_idx = np.argwhere(truth)
    g = float(t_idx.shape[0])
    p_idx = np.column_stack([rows, cols]).astype(np.float64)
    n = int(p_idx.shape[0])
    if n == 0:
        return {"dti": 0.0, "tp": 0.0, "fp": 0.0, "fn": g, "n": 0, "g": g,
                "credit_per_dot": 0.0, "coverage": 0.0}
    tree = cKDTree(p_idx)
    cred = np.zeros(t_idx.shape[0], dtype=np.float64)
    for j, nb in enumerate(tree.query_ball_point(t_idx.astype(np.float64), r=R_PX + 1e-9)):
        if nb:
            d = np.hypot(*(p_idx[nb] - t_idx[j]).T)
            cred[j] = float(np.max(np.maximum(1.0 - d / R_PX, 0.0)))
    tp = float(cred.sum())
    fn = float((1.0 - cred).sum())
    if t_idx.size:
        dt = distance_transform_edt(~truth)
        support = np.maximum(1.0 - dt / R_PX, 0.0)
        fp = float(np.sum(1.0 - support[rows, cols]))
    else:
        fp = float(n)
    dti = tp / (tp + ALPHA * fp + BETA * fn + 1e-9)
    return {"dti": float(dti), "tp": tp, "fp": fp, "fn": fn, "n": n, "g": g,
            "credit_per_dot": float(tp / n), "coverage": float(tp / g) if g else 0.0}


def required_credit(score: float, n_dots: int, g_hat: float) -> float:
    """Legacy model-only credit target under the conditional ``T=M`` simplification.

    The exact metric depends on both directional credits; this helper is retained for
    historical comparison and must not be used as an official-score inversion.
    """
    return float(score * (ALPHA * n_dots + (1.0 - ALPHA) * g_hat))
