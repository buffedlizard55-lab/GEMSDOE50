"""H59-S — up-dip seismic lineation corridors, snapped to an independent ridge.

Preregistration: ``docs/research/h59-hypotheses-preregistered.md`` (frozen before
this module existed). Every constant below is copied from section 3 of that file.

What is new relative to H55 / H58-S1 (both of which lost to density controls)
-------------------------------------------------------------------------------
1. **Published declustering.** Zaliapin & Ben-Zion (2013, JGR 118, 2847-2864,
   doi:10.1002/jgrb.50179) nearest-neighbour proximity
   ``eta_ij = t_ij * r_ij**df * 10**(-b * m_i)`` with a two-component Gaussian
   mixture threshold on ``log10 eta``.
2. **A stricter spatial background screen.** The 2-D triangle test (my
   *unverified* adaptation of the Ouillon & Sornette 2011 tetrahedron test,
   doi:10.1029/2010JB007752) now calls an event clustered only if its local
   triangle area is below the 5th percentile of a coordinate-permuted
   reference. H58-S1's "below the 95th percentile of a uniform box" kept 96.5 %
   of events and therefore screened almost nothing.
3. **Location-error deconvolution.** Neighbourhood covariance eigenvalues are
   reduced by the inverse-variance-weighted mean squared horizontal error, the
   2-D analogue of the Ouillon, Ducorbier & Sornette (2008) planarity rule
   ``lambda_3 < Delta**2`` (doi:10.1029/2007JB005032). ComCat's
   ``horizontalError`` is a scalar (largest horizontal projection of the error
   ellipsoid), so this is *not* the ACLUD per-event covariance treatment of
   Wang et al. (2013, arXiv:1304.6912, doi:10.1002/2013JB010164).
4. **Up-dip projection.** A hypocentral lineation at median depth ``z`` on a
   fault dipping ``delta`` reaches the surface ``z / tan(delta)`` up-dip; the
   dip direction is unknown from epicentres alone, so both sides are corridors
   and the ridge decides. Corridor width propagates depth error and a +-10 deg
   dip uncertainty.
5. **Explicit cross-axis ridge snap.** Every 300 m along a corridor axis the
   dot moves to the arg-max of the ridge field *across the whole corridor*
   (H58-S1 only nudged dots by <= 3 px, which changed nothing).

All functions are pure (no file I/O except :func:`load_events`) so they can be
unit-tested on synthetic catalogues.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import rasterio
from pyproj import Transformer
from scipy import ndimage
from scipy.spatial import cKDTree

from . import h58

# --- frozen constants (preregistration section 3) ---------------------------
MIN_MAG = 1.5
MIN_DEPTH_KM = 0.5
MAX_DEPTH_KM = 20.0
MAX_HERR_KM = 5.0
HERR_IMPUTE_KM = 2.0
DERR_IMPUTE_KM = 3.0
HERR_FLOOR_KM = 0.1
ANTHROPOGENIC_BUFFER_M = 3_000.0

ZBZ_DF = 1.6
ZBZ_B = 1.0
ZBZ_K = 64
ZBZ_BIG_PARENT_MAG = 5.0
ZBZ_R_FLOOR_KM = 0.1
ZBZ_DT_FLOOR_YR = 1.0 / (365.25 * 86_400.0)  # one second

TRIANGLE_QUANTILE = 0.05
TRIANGLE_SEED = 20_261_059

LIN_K = 12
LIN_MIN_EVENTS = 8
LIN_RADIUS_KM = 5.0
LIN_THICKNESS_FACTOR = 2.25  # lambda2 <= (1.5 sigma)^2
LIN_MIN_HALF_KM = 1.0
LIN_MIN_ELONGATION = 3.0
MERGE_DIST_KM = 1.0
MERGE_AZ_DEG = 15.0
HALF_LENGTH_CAP_KM = 10.0

DIP_DEG = 60.0
DIP_SIGMA_RAD = float(np.deg2rad(10.0))
W_E_KM = (0.2, 1.0)
W_U_KM = (0.2, 2.0)
AXIS_STEP_M = 300.0
CROSS_STEP_M = 100.0
MAX_DOTS = 40_000
SPACING_PX = 3

KIND_NAMES = ("epicentral", "updip_left", "updip_right")


# --- event loading -----------------------------------------------------------
@dataclass
class Events:
    """Screened, projected events (metres on EPSG:32611, years, km)."""

    x: np.ndarray
    y: np.ndarray
    depth_km: np.ndarray
    mag: np.ndarray
    t_years: np.ndarray
    herr_km: np.ndarray
    derr_km: np.ndarray
    herr_imputed: np.ndarray

    def __len__(self) -> int:
        return int(self.x.size)

    def subset(self, keep: np.ndarray) -> Events:
        return Events(*(getattr(self, f)[keep] for f in self.__dataclass_fields__))


def load_events(comcat_path: str | Path, template_path: str | Path) -> tuple[Events, dict[str, Any]]:
    """Read the hash-pinned ComCat extract and apply the frozen H59 screens."""
    df, cat_report = h58.load_comcat(comcat_path)
    report: dict[str, Any] = {"catalog": cat_report, "rows_in": len(df)}
    df = df[df["type"].astype(str) == "earthquake"]
    report["after_type_earthquake"] = len(df)
    mag = pd.to_numeric(df["mag"], errors="coerce")
    df = df[mag >= MIN_MAG]
    report["after_min_mag"] = len(df)
    depth = pd.to_numeric(df["depth"], errors="coerce")
    df = df[(depth > MIN_DEPTH_KM) & (depth <= MAX_DEPTH_KM)]
    report["after_depth_window"] = len(df)
    herr = pd.to_numeric(df["horizontalError"], errors="coerce")
    df = df[~(herr > MAX_HERR_KM)]
    report["after_horizontal_error"] = len(df)
    df = df.reset_index(drop=True)

    with rasterio.open(template_path) as ds:
        transform = ds.transform
        height, width = ds.shape
    tr = Transformer.from_crs("EPSG:4326", "EPSG:32611", always_xy=True)
    lon = pd.to_numeric(df["longitude"], errors="coerce").to_numpy(np.float64)
    lat = pd.to_numeric(df["latitude"], errors="coerce").to_numpy(np.float64)
    x, y = (np.asarray(v, dtype=np.float64) for v in tr.transform(lon, lat))
    col_f, row_f = ~transform * (x, y)
    inside = (
        np.isfinite(x) & np.isfinite(y)
        & (row_f >= 0) & (row_f < height) & (col_f >= 0) & (col_f < width)
    )
    df = df[inside].reset_index(drop=True)
    x, y = x[inside], y[inside]
    report["inside_grid_rectangle"] = len(df)

    keep = np.ones(len(df), dtype=bool)
    centres = h58._anthropogenic_centres(comcat_path)
    if centres.size:
        dist, _ = cKDTree(centres).query(np.column_stack([x, y]), k=1)
        keep &= dist > ANTHROPOGENIC_BUFFER_M
    report["anthropogenic_screen"] = {
        "rule": "3 km around explicit ComCat explosion/blast/mine/induced event centres",
        "centres": int(centres.shape[0]),
        "removed": int((~keep).sum()),
        "limitation": "no official injection-well / geothermal-plant inventory offline",
    }
    df = df[keep].reset_index(drop=True)
    x, y = x[keep], y[keep]

    herr_raw = pd.to_numeric(df["horizontalError"], errors="coerce").to_numpy(np.float64)
    imputed = ~np.isfinite(herr_raw) | (herr_raw <= 0)
    herr_km = np.maximum(np.where(imputed, HERR_IMPUTE_KM, herr_raw), HERR_FLOOR_KM)
    derr_raw = pd.to_numeric(df.get("depthError"), errors="coerce").to_numpy(np.float64)
    derr_km = np.where(np.isfinite(derr_raw) & (derr_raw > 0), derr_raw, DERR_IMPUTE_KM)
    days, _year = h58._parse_time_days(df["time"])
    events = Events(
        x=x,
        y=y,
        depth_km=pd.to_numeric(df["depth"], errors="coerce").to_numpy(np.float64),
        mag=pd.to_numeric(df["mag"], errors="coerce").to_numpy(np.float64),
        t_years=days / 365.25,
        herr_km=herr_km,
        derr_km=derr_km,
        herr_imputed=imputed,
    )
    report["events_out"] = len(events)
    report["horizontal_error_imputed_fraction"] = float(imputed.mean()) if len(events) else 0.0
    return events, report


# --- Zaliapin & Ben-Zion (2013) nearest-neighbour declustering ----------------
def _gmm_threshold(values: np.ndarray, iters: int = 500) -> dict[str, Any]:
    """Two-component 1-D Gaussian mixture; threshold at the weighted-density crossing."""
    v = np.asarray(values, dtype=np.float64)
    mu = np.quantile(v, [0.25, 0.75])
    sd = np.full(2, max(v.std() / 2.0, 1e-3))
    w = np.array([0.5, 0.5])
    for _ in range(iters):
        dens = w / (sd * np.sqrt(2 * np.pi)) * np.exp(-0.5 * ((v[:, None] - mu) / sd) ** 2)
        tot = dens.sum(axis=1, keepdims=True)
        tot[tot == 0] = 1e-300
        resp = dens / tot
        nk = resp.sum(axis=0)
        new_mu = (resp * v[:, None]).sum(axis=0) / nk
        new_sd = np.sqrt((resp * (v[:, None] - new_mu) ** 2).sum(axis=0) / nk)
        new_sd = np.maximum(new_sd, 1e-3)
        w = nk / v.size
        converged = np.allclose(new_mu, mu, atol=1e-7) and np.allclose(new_sd, sd, atol=1e-7)
        mu, sd = new_mu, new_sd
        if converged:
            break
    order = np.argsort(mu)
    mu, sd, w = mu[order], sd[order], w[order]
    # solve w1 N(x; mu1, sd1) = w2 N(x; mu2, sd2)
    a = 1.0 / (2 * sd[1] ** 2) - 1.0 / (2 * sd[0] ** 2)
    b = mu[0] / sd[0] ** 2 - mu[1] / sd[1] ** 2
    c = (
        mu[1] ** 2 / (2 * sd[1] ** 2)
        - mu[0] ** 2 / (2 * sd[0] ** 2)
        + np.log((w[0] * sd[1]) / (w[1] * sd[0]))
    )
    if abs(a) < 1e-12:
        roots = np.array([-c / b]) if abs(b) > 1e-12 else np.array([])
    else:
        disc = b * b - 4 * a * c
        roots = np.array([]) if disc < 0 else (-b + np.array([1.0, -1.0]) * np.sqrt(disc)) / (2 * a)
    between = [r for r in np.atleast_1d(roots) if mu[0] <= r <= mu[1]]
    threshold = float(between[0]) if between else float(0.5 * (mu[0] + mu[1]))
    return {
        "means": mu.tolist(),
        "sds": sd.tolist(),
        "weights": w.tolist(),
        "threshold": threshold,
        "threshold_rule": "density crossing" if between else "midpoint fallback",
    }


def zbz_nearest_neighbour(
    x_km: np.ndarray,
    y_km: np.ndarray,
    t_years: np.ndarray,
    mag: np.ndarray,
    *,
    k: int = ZBZ_K,
    df: float = ZBZ_DF,
    b: float = ZBZ_B,
    big_parent_mag: float = ZBZ_BIG_PARENT_MAG,
) -> tuple[np.ndarray, np.ndarray]:
    """Return (eta, parent index) for every event; eta = inf when no earlier candidate."""
    n = x_km.size
    eta = np.full(n, np.inf)
    parent = np.full(n, -1, dtype=np.int64)
    if n < 2:
        return eta, parent
    xy = np.column_stack([x_km, y_km])
    kq = min(k + 1, n)
    dist, idx = cKDTree(xy).query(xy, k=kq)
    dist = np.atleast_2d(dist)
    idx = np.atleast_2d(idx)
    dt = t_years[:, None] - t_years[idx]
    earlier = (dt > 0) | ((dt == 0) & (idx < np.arange(n)[:, None]))
    earlier &= idx != np.arange(n)[:, None]
    r = np.maximum(dist, ZBZ_R_FLOOR_KM)
    e = np.maximum(dt, ZBZ_DT_FLOOR_YR) * r**df * 10.0 ** (-b * mag[idx])
    e = np.where(earlier, e, np.inf)
    j = np.argmin(e, axis=1)
    eta = e[np.arange(n), j]
    parent = np.where(np.isfinite(eta), idx[np.arange(n), j], -1)

    big = np.flatnonzero(mag >= big_parent_mag)
    if big.size:
        dx = x_km[:, None] - x_km[big][None, :]
        dy = y_km[:, None] - y_km[big][None, :]
        rb = np.maximum(np.hypot(dx, dy), ZBZ_R_FLOOR_KM)
        dtb = t_years[:, None] - t_years[big][None, :]
        ok = (dtb > 0) & (big[None, :] != np.arange(n)[:, None])
        eb = np.where(ok, np.maximum(dtb, ZBZ_DT_FLOOR_YR) * rb**df * 10.0 ** (-b * mag[big][None, :]), np.inf)
        jb = np.argmin(eb, axis=1)
        ebest = eb[np.arange(n), jb]
        better = ebest < eta
        eta = np.where(better, ebest, eta)
        parent = np.where(better, big[jb], parent)
    return eta, parent


def zbz_decluster(events: Events) -> tuple[np.ndarray, dict[str, Any]]:
    """Background (declustered) mask: events with no strong nearest-neighbour parent."""
    eta, _parent = zbz_nearest_neighbour(
        events.x / 1000.0, events.y / 1000.0, events.t_years, events.mag
    )
    finite = np.isfinite(eta) & (eta > 0)
    log_eta = np.log10(eta[finite])
    gmm = _gmm_threshold(log_eta)
    keep = ~finite | (np.log10(np.where(finite, eta, 1.0)) >= gmm["threshold"])
    report = {
        "method": "Zaliapin & Ben-Zion (2013) nearest-neighbour proximity, doi:10.1002/jgrb.50179",
        "df": ZBZ_DF,
        "b": ZBZ_B,
        "candidate_parents": f"{ZBZ_K} nearest epicentres + all events with M >= {ZBZ_BIG_PARENT_MAG}",
        "units": "time in years, distance in km",
        "gmm_log10_eta": gmm,
        "events_in": len(events),
        "no_earlier_candidate": int((~finite).sum()),
        "clustered_removed": int((~keep).sum()),
        "background_kept": int(keep.sum()),
        "background_fraction": float(keep.mean()) if keep.size else 0.0,
    }
    return keep, report


# --- 2-D triangle screen (unverified adaptation) ------------------------------
def _triangle_areas(xy: np.ndarray) -> np.ndarray:
    if xy.shape[0] < 3:
        return np.full(xy.shape[0], np.inf)
    _, idx = cKDTree(xy).query(xy, k=3)
    p0, p1, p2 = xy[idx[:, 0]], xy[idx[:, 1]], xy[idx[:, 2]]
    cross = (p1[:, 0] - p0[:, 0]) * (p2[:, 1] - p0[:, 1]) - (p1[:, 1] - p0[:, 1]) * (p2[:, 0] - p0[:, 0])
    return 0.5 * np.abs(cross)


def triangle_keep(xy_m: np.ndarray, *, quantile: float = TRIANGLE_QUANTILE, seed: int = TRIANGLE_SEED) -> tuple[np.ndarray, dict[str, Any]]:
    """Clustered = local triangle area below the ``quantile`` of a coordinate-permuted reference."""
    xy = np.asarray(xy_m, dtype=np.float64)
    areas = _triangle_areas(xy)
    rng = np.random.default_rng(seed)
    ref = np.column_stack([rng.permutation(xy[:, 0]), rng.permutation(xy[:, 1])])
    ref_areas = _triangle_areas(ref)
    thr = float(np.quantile(ref_areas, quantile)) if ref_areas.size else np.inf
    keep = areas <= thr
    return keep, {
        "status": "UNVERIFIED 2-D adaptation of the Ouillon & Sornette (2011) tetrahedron test",
        "reference": "x and y independently permuted (same seed every run)",
        "seed": seed,
        "quantile": quantile,
        "threshold_m2": thr,
        "events_in": int(xy.shape[0]),
        "kept": int(keep.sum()),
        "kept_fraction": float(keep.mean()) if keep.size else 0.0,
        "median_area_m2_real": float(np.median(areas)) if areas.size else None,
        "median_area_m2_reference": float(np.median(ref_areas)) if ref_areas.size else None,
    }


# --- lineations ----------------------------------------------------------------
@dataclass
class Lineations:
    """One row per accepted, merged neighbourhood (metres, km for depth)."""

    cx: np.ndarray
    cy: np.ndarray
    ux: np.ndarray
    uy: np.ndarray
    half_len_m: np.ndarray
    sigma_loc_km: np.ndarray
    z_km: np.ndarray
    sz_km: np.ndarray
    n_events: np.ndarray
    elongation: np.ndarray

    def __len__(self) -> int:
        return int(self.cx.size)


def neighbourhood_lineations(events: Events) -> tuple[Lineations, dict[str, Any]]:
    """Location-error-deconvolved 2-D covariance lineations, then azimuth-aware merging."""
    n = len(events)
    empty = Lineations(*(np.zeros(0) for _ in range(10)))
    if n < LIN_MIN_EVENTS:
        return empty, {"events": n, "accepted": 0, "merged": 0}
    xy_km = np.column_stack([events.x, events.y]) / 1000.0
    k = min(LIN_K, n)
    dist, idx = cKDTree(xy_km).query(xy_km, k=k)
    inside = dist <= LIN_RADIUS_KM
    n_in = inside.sum(axis=1)
    sig2 = events.herr_km[idx] ** 2
    w = np.where(inside, 1.0 / sig2, 0.0)
    sw = w.sum(axis=1)
    px, py = xy_km[idx, 0], xy_km[idx, 1]
    mx = (w * px).sum(axis=1) / sw
    my = (w * py).sum(axis=1) / sw
    dx, dy = px - mx[:, None], py - my[:, None]
    cxx = (w * dx * dx).sum(axis=1) / sw
    cyy = (w * dy * dy).sum(axis=1) / sw
    cxy = (w * dx * dy).sum(axis=1) / sw
    sigbar2 = n_in / sw  # inverse-variance-weighted mean squared error
    tr = cxx + cyy
    disc = np.sqrt(0.25 * (cxx - cyy) ** 2 + cxy**2)
    lam1 = 0.5 * tr + disc
    lam2 = np.maximum(0.5 * tr - disc, 1e-12)
    theta = 0.5 * np.arctan2(2 * cxy, cxx - cyy)
    lam1_dec = lam1 - sigbar2
    elong = np.sqrt(lam1 / lam2)
    ok = (
        (n_in >= LIN_MIN_EVENTS)
        & (lam2 <= LIN_THICKNESS_FACTOR * sigbar2)
        & (lam1_dec >= LIN_MIN_HALF_KM**2)
        & (elong >= LIN_MIN_ELONGATION)
    )
    depth_nb = np.where(inside, events.depth_km[idx], np.nan)
    z_med = np.nanmedian(depth_nb, axis=1)
    sz = np.sqrt(np.nanmean(np.where(inside, events.derr_km[idx] ** 2, np.nan), axis=1))

    cand = np.flatnonzero(ok)
    order = cand[np.argsort(-elong[cand], kind="stable")]
    acc: list[int] = []
    cell: dict[tuple[int, int], list[int]] = {}
    for i in order:
        gx, gy = int(np.floor(mx[i] / MERGE_DIST_KM)), int(np.floor(my[i] / MERGE_DIST_KM))
        dup = False
        for ox in (-1, 0, 1):
            for oy in (-1, 0, 1):
                for j in cell.get((gx + ox, gy + oy), ()):
                    if np.hypot(mx[i] - mx[j], my[i] - my[j]) <= MERGE_DIST_KM:
                        daz = abs(np.degrees(theta[i] - theta[j])) % 180.0
                        if min(daz, 180.0 - daz) < MERGE_AZ_DEG:
                            dup = True
                            break
                if dup:
                    break
            if dup:
                break
        if not dup:
            acc.append(int(i))
            cell.setdefault((gx, gy), []).append(int(i))
    a = np.asarray(acc, dtype=np.int64)
    lins = Lineations(
        cx=mx[a] * 1000.0,
        cy=my[a] * 1000.0,
        ux=np.cos(theta[a]),
        uy=np.sin(theta[a]),
        half_len_m=np.minimum(2.0 * np.sqrt(np.maximum(lam1_dec[a], 0.0)), HALF_LENGTH_CAP_KM) * 1000.0,
        sigma_loc_km=np.sqrt(sigbar2[a]),
        z_km=z_med[a],
        sz_km=sz[a],
        n_events=n_in[a],
        elongation=elong[a],
    )
    report = {
        "events": n,
        "k": LIN_K,
        "radius_km": LIN_RADIUS_KM,
        "min_events": LIN_MIN_EVENTS,
        "rules": "lambda2 <= 2.25 sigbar^2; sqrt(lambda1 - sigbar^2) >= 1 km; sqrt(lambda1/lambda2) >= 3",
        "neighbourhoods_with_min_events": int((n_in >= LIN_MIN_EVENTS).sum()),
        "fail_thickness": int(((n_in >= LIN_MIN_EVENTS) & (lam2 > LIN_THICKNESS_FACTOR * sigbar2)).sum()),
        "fail_length": int(((n_in >= LIN_MIN_EVENTS) & (lam1_dec < LIN_MIN_HALF_KM**2)).sum()),
        "fail_elongation": int(((n_in >= LIN_MIN_EVENTS) & (elong < LIN_MIN_ELONGATION)).sum()),
        "accepted_neighbourhoods": int(ok.sum()),
        "merged_lineations": len(lins),
        "median_sigma_loc_km": float(np.median(lins.sigma_loc_km)) if len(lins) else None,
        "median_depth_km": float(np.nanmedian(lins.z_km)) if len(lins) else None,
        "median_half_length_km": float(np.median(lins.half_len_m) / 1000.0) if len(lins) else None,
    }
    return lins, report


# --- corridors ------------------------------------------------------------------
def corridor_geometry(lins: Lineations) -> list[dict[str, Any]]:
    """Epicentral + two up-dip corridors per lineation (centre, unit axis, half-length, half-width)."""
    out: list[dict[str, Any]] = []
    tan_d = np.tan(np.deg2rad(DIP_DEG))
    sin2_d = np.sin(np.deg2rad(DIP_DEG)) ** 2
    for i in range(len(lins)):
        ux, uy = float(lins.ux[i]), float(lins.uy[i])
        nx, ny = -uy, ux
        sig = float(lins.sigma_loc_km[i])
        z = float(lins.z_km[i]) if np.isfinite(lins.z_km[i]) else 5.0
        sz = float(lins.sz_km[i]) if np.isfinite(lins.sz_km[i]) else DERR_IMPUTE_KM
        w_e = float(np.clip(sig, *W_E_KM)) * 1000.0
        w_u = float(
            np.clip(np.sqrt(sig**2 + (sz / tan_d) ** 2 + (z * DIP_SIGMA_RAD / sin2_d) ** 2), *W_U_KM)
        ) * 1000.0
        delta = z / tan_d * 1000.0
        base = {"lineation": i, "ux": ux, "uy": uy, "half_len_m": float(lins.half_len_m[i])}
        out.append({**base, "kind": 0, "cx": float(lins.cx[i]), "cy": float(lins.cy[i]), "half_w_m": w_e, "offset_m": 0.0})
        for kind, sgn in ((1, 1.0), (2, -1.0)):
            out.append(
                {
                    **base,
                    "kind": kind,
                    "cx": float(lins.cx[i] + sgn * delta * nx),
                    "cy": float(lins.cy[i] + sgn * delta * ny),
                    "half_w_m": w_u,
                    "offset_m": sgn * delta,
                }
            )
    return out


def snap_corridor_dots(
    corridors: list[dict[str, Any]],
    ridge: np.ndarray,
    eligible: np.ndarray,
    transform,
) -> dict[str, np.ndarray]:
    """Every 300 m along each axis, the arg-max of ``ridge`` across the corridor (eligible cells)."""
    h, w = ridge.shape
    inv = ~transform
    rows, cols, vals, kinds, lin = [], [], [], [], []
    field = np.where(eligible & np.isfinite(ridge), ridge, -np.inf).astype(np.float32)
    for cor in corridors:
        L, W = cor["half_len_m"], cor["half_w_m"]
        t = np.arange(-L, L + 1e-6, AXIS_STEP_M)
        s = np.arange(-W, W + 1e-6, CROSS_STEP_M)
        if t.size == 0 or s.size == 0:
            continue
        ux, uy = cor["ux"], cor["uy"]
        nx, ny = -uy, ux
        X = cor["cx"] + t[:, None] * ux + s[None, :] * nx
        Y = cor["cy"] + t[:, None] * uy + s[None, :] * ny
        cf, rf = inv * (X, Y)
        r = np.floor(rf).astype(np.int64)
        c = np.floor(cf).astype(np.int64)
        inb = (r >= 0) & (r < h) & (c >= 0) & (c < w)
        v = np.full(r.shape, -np.inf, dtype=np.float32)
        v[inb] = field[r[inb], c[inb]]
        j = np.argmax(v, axis=1)
        best = v[np.arange(t.size), j]
        good = np.isfinite(best)
        if not good.any():
            continue
        rows.append(r[np.arange(t.size), j][good])
        cols.append(c[np.arange(t.size), j][good])
        vals.append(best[good])
        kinds.append(np.full(int(good.sum()), cor["kind"], dtype=np.int8))
        lin.append(np.full(int(good.sum()), cor["lineation"], dtype=np.int32))
    if not rows:
        z = np.zeros(0, dtype=np.int64)
        return {"rows": z, "cols": z, "vals": np.zeros(0, np.float32), "kind": z.astype(np.int8), "lineation": z.astype(np.int32)}
    return {
        "rows": np.concatenate(rows),
        "cols": np.concatenate(cols),
        "vals": np.concatenate(vals),
        "kind": np.concatenate(kinds),
        "lineation": np.concatenate(lin),
    }


def greedy_spaced(
    rows: np.ndarray,
    cols: np.ndarray,
    vals: np.ndarray,
    shape: tuple[int, int],
    *,
    max_dots: int = MAX_DOTS,
    spacing: int = SPACING_PX,
    blocked: np.ndarray | None = None,
) -> np.ndarray:
    """Indices of accepted candidates: descending value, Chebyshev spacing >= ``spacing``."""
    order = np.lexsort((cols, rows, -vals.astype(np.float64)))
    occ = np.zeros(shape, dtype=bool) if blocked is None else blocked.copy()
    r0 = spacing - 1
    acc: list[int] = []
    for k in order:
        if len(acc) >= max_dots:
            break
        r, c = int(rows[k]), int(cols[k])
        if occ[r, c]:
            continue
        acc.append(int(k))
        occ[max(0, r - r0) : r + r0 + 1, max(0, c - r0) : c + r0 + 1] = True
    return np.asarray(acc, dtype=np.int64)


def corridor_union(corridors: list[dict[str, Any]], shape: tuple[int, int], transform) -> np.ndarray:
    """Boolean raster of every corridor rectangle (pixel centres inside |t|<=L, |s|<=W)."""
    h, w = shape
    out = np.zeros(shape, dtype=bool)
    px = abs(float(transform.a))
    x0, y0 = float(transform.c), float(transform.f)
    for cor in corridors:
        L, W = cor["half_len_m"], cor["half_w_m"]
        ux, uy = cor["ux"], cor["uy"]
        nx, ny = -uy, ux
        corners = [
            (cor["cx"] + a * L * ux + b * W * nx, cor["cy"] + a * L * uy + b * W * ny)
            for a in (-1, 1)
            for b in (-1, 1)
        ]
        xs = [p[0] for p in corners]
        ys = [p[1] for p in corners]
        c0 = max(int(np.floor((min(xs) - x0) / px)), 0)
        c1 = min(int(np.ceil((max(xs) - x0) / px)), w - 1)
        r0 = max(int(np.floor((y0 - max(ys)) / px)), 0)
        r1 = min(int(np.ceil((y0 - min(ys)) / px)), h - 1)
        if c1 < c0 or r1 < r0:
            continue
        cc, rr = np.meshgrid(np.arange(c0, c1 + 1), np.arange(r0, r1 + 1))
        X = x0 + (cc + 0.5) * px - cor["cx"]
        Y = y0 - (rr + 0.5) * px - cor["cy"]
        t = X * ux + Y * uy
        s = X * nx + Y * ny
        m = (np.abs(t) <= L) & (np.abs(s) <= W)
        out[rr[m], cc[m]] = True
    return out


def density_field(events: Events, shape: tuple[int, int], transform, sigma_m: float) -> np.ndarray:
    """Gaussian-smoothed epicentre density on the grid (the falsification control)."""
    h, w = shape
    inv = ~transform
    cf, rf = inv * (events.x, events.y)
    r = np.floor(rf).astype(np.int64)
    c = np.floor(cf).astype(np.int64)
    ok = (r >= 0) & (r < h) & (c >= 0) & (c < w)
    counts = np.zeros(shape, dtype=np.float32)
    np.add.at(counts, (r[ok], c[ok]), 1.0)
    return ndimage.gaussian_filter(counts, sigma_m / abs(float(transform.a))).astype(np.float32)


def top_area_support(field: np.ndarray, eligible: np.ndarray, area: int) -> np.ndarray:
    """The ``area`` highest-``field`` eligible cells (ties broken by flat index)."""
    flat = np.flatnonzero(eligible.ravel())
    if area >= flat.size:
        return eligible.copy()
    v = field.ravel()[flat]
    pick = flat[np.argsort(-v, kind="stable")[:area]]
    out = np.zeros(field.size, dtype=bool)
    out[pick] = True
    return out.reshape(field.shape)


def kernel_credit_field(truth: np.ndarray, radius_px: float = 3.0) -> np.ndarray:
    """K(x) = clip(1 - d(x, truth)/R, 0, 1): the credit a lone dot at x would earn."""
    d = ndimage.distance_transform_edt(~truth)
    return np.clip(1.0 - d / radius_px, 0.0, 1.0).astype(np.float32)


def stratified_corridor_enrichment(
    k_field: np.ndarray,
    belief: np.ndarray,
    corridor: np.ndarray,
    domain: np.ndarray,
    n_strata: int = 10,
) -> dict[str, Any]:
    """Mean K inside vs outside the corridors within H57-belief deciles (incremental value)."""
    cells = domain & np.isfinite(belief)
    b = belief[cells]
    edges = np.quantile(b, np.linspace(0, 1, n_strata + 1))
    stratum = np.clip(np.searchsorted(edges, b, side="right") - 1, 0, n_strata - 1)
    k = k_field[cells]
    cin = corridor[cells]
    rows = []
    ratios = []
    for s in range(n_strata):
        m = stratum == s
        i, o = m & cin, m & ~cin
        ki = float(k[i].mean()) if i.any() else None
        ko = float(k[o].mean()) if o.any() else None
        ratio = (ki / ko) if (ki is not None and ko) else None
        if ratio is not None:
            ratios.append(ratio)
        rows.append({"stratum": s, "cells_in": int(i.sum()), "cells_out": int(o.sum()), "meanK_in": ki, "meanK_out": ko, "ratio": ratio})
    top = rows[-3:]
    return {
        "strata": rows,
        "median_ratio": float(np.median(ratios)) if ratios else None,
        "strata_with_ratio_gt_1": int(sum(r > 1 for r in ratios)),
        "top3_strata_ratio": [r["ratio"] for r in top],
    }
