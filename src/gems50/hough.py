"""Significance-tested Hough lineaments from epicentres.

Why this module exists
----------------------
The OADC-style local covariance fit in :mod:`gems50.lineation` is a *local* estimator: it
sees only a k-nearest neighbourhood, so on a catalogue whose density varies by orders of
magnitude it either finds nothing (a dense cluster is wider than the location error) or
finds very short axes.  The classical remedy for lineament extraction from a point pattern
is the Hough transform -- one of the transforms named in the source literature (Ouillon et
al. 2008 open with a review of "pattern recognition methods used to detect linear or planar
features in images, such as the Hough and wavelet transforms").

The statistical test is the one the brief asks for and that Ouillon & Sornette (2011, JGR
116, B02306, doi:10.1029/2010JB007752) publish for the 3-D case: linear structure is
compared against **randomized catalogues** that keep the coarse intensity but destroy the
fine-scale geometry.  A candidate line is kept only if it carries enough events *and*
exceeds the surrogate count by ``z_min`` Poisson standard deviations.

Provenance, stated explicitly (this repository's rule):
  * Hough transform: classical (Hough 1962), standard in geophysical lineament detection.
  * Comparison against randomized catalogues: published (Ouillon & Sornette 2011).
  * The 2-D epicentral application, the surrogate construction, the Poisson z and the
    non-maximum suppression: **this project's own choices**, measured in
    :mod:`gems50.validate` -- not taken on faith and not claimed as published results.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np


@dataclass
class Lineaments:
    """Significant Hough lineaments, in pixel coordinates."""

    theta_rad: np.ndarray  # orientation, [0, pi)
    rho_px: np.ndarray  # perpendicular distance from the pixel-space origin
    z: np.ndarray  # Poisson z of the excess over the surrogates
    n_events: np.ndarray  # events in the corridor
    lambda_surrogate: np.ndarray  # surrogate mean in the same corridor
    extent_px: np.ndarray  # 5-95 percentile extent along the line
    t_min_px: np.ndarray  # along-line coordinate span of the supporting events
    t_max_px: np.ndarray
    votes: np.ndarray  # weighted (magnitude) support

    def __len__(self) -> int:
        return len(self.theta_rad)

    def as_dict(self) -> dict:
        return {
            "n": int(len(self)),
            "z_max": float(self.z.max()) if len(self) else None,
            "extent_px_median": float(np.median(self.extent_px)) if len(self) else None,
        }


def _rho(col: np.ndarray, row: np.ndarray, theta: np.ndarray) -> np.ndarray:
    return col * np.cos(theta) + row * np.sin(theta)


def surrogate_catalog(col: np.ndarray, row: np.ndarray, shape: tuple[int, int],
                      n_surrogates: int = 20, cell_px: int = 50,
                      seed: int = 20261006) -> np.ndarray:
    """Randomized catalogues: same coarse intensity, no fine-scale geometry."""
    rng = np.random.default_rng(seed)
    h, w = shape
    gh, gw = h // cell_px + 1, w // cell_px + 1
    gcol = np.clip(col // cell_px, 0, gw - 1).astype(np.int64)
    grow = np.clip(row // cell_px, 0, gh - 1).astype(np.int64)
    counts = np.zeros((gh, gw), dtype=np.float64)
    np.add.at(counts, (grow, gcol), 1.0)
    p = (counts + 0.05).ravel()
    p /= p.sum()
    n = len(col)
    out = np.empty((n_surrogates, n, 2), dtype=np.float64)
    flat = rng.choice(p.size, size=(n_surrogates, n), p=p)
    gy, gx = np.divmod(flat, gw)
    out[..., 0] = gx * cell_px + rng.uniform(0, cell_px, size=(n_surrogates, n))
    out[..., 1] = gy * cell_px + rng.uniform(0, cell_px, size=(n_surrogates, n))
    return out


def hough_accumulator(col: np.ndarray, row: np.ndarray, weights: np.ndarray,
                      n_theta: int = 180, rho_bin_px: float = 1.0,
                      shape: tuple[int, int] | None = None,
                      rho_smooth: int = 1) -> tuple[np.ndarray, np.ndarray, float]:
    """Vote matrix ``V[theta, rho_bin]``; returns ``(V, thetas, rho_max)``."""
    h, w = shape if shape is not None else (int(row.max()) + 2, int(col.max()) + 2)
    rho_max = float(np.hypot(h, w) + 2)
    n_rho = int(np.ceil(2 * rho_max / rho_bin_px)) + 1
    offset = rho_max / rho_bin_px
    thetas = np.linspace(0.0, np.pi, n_theta, endpoint=False)
    V = np.zeros((n_theta, n_rho), dtype=np.float64)
    for i, th in enumerate(thetas):
        r = _rho(col, row, th) / rho_bin_px + offset
        base = np.floor(r).astype(np.int64)
        for s in range(-rho_smooth, rho_smooth + 1):
            idx = base + s
            ok = (idx >= 0) & (idx < n_rho)
            V[i] += np.bincount(idx[ok], weights=weights[ok], minlength=n_rho)
    return V, thetas, rho_max


def detect_lineaments(col: np.ndarray, row: np.ndarray, weights: np.ndarray,
                      shape: tuple[int, int], n_theta: int = 180,
                      rho_bin_px: float = 1.0, rho_smooth: int = 1,
                      n_surrogates: int = 20, z_min: float = 6.0,
                      min_events: int = 8, min_extent_px: float = 40.0,
                      nms_dtheta_deg: float = 5.0, nms_drho_px: float = 4.0,
                      max_lineaments: int = 4000, seed: int = 20261006) -> Lineaments:
    """Hough lineaments that beat randomized catalogues, with non-maximum suppression.

    ``min_events`` is an absolute floor (a line with three events is not evidence of a
    fault), ``min_extent_px`` removes short bursts, and the NMS radii remove the many
    near-duplicate peaks that a single physical lineament produces.
    """
    col = np.asarray(col, dtype=np.float64)
    row = np.asarray(row, dtype=np.float64)
    weights = np.asarray(weights, dtype=np.float64)
    ones = np.ones(len(col))
    wmax = float(weights.max()) if len(weights) else 1.0

    V, thetas, rho_max = hough_accumulator(col, row, ones, n_theta, rho_bin_px, shape,
                                           rho_smooth)
    Vw, _, _ = hough_accumulator(col, row, weights / (wmax or 1.0), n_theta, rho_bin_px,
                                 shape, rho_smooth)
    sur = surrogate_catalog(col, row, shape, n_surrogates=n_surrogates, seed=seed)
    total = np.zeros_like(V)
    for j in range(n_surrogates):
        Vs, _, _ = hough_accumulator(sur[j, :, 0], sur[j, :, 1], ones, n_theta,
                                     rho_bin_px, shape, rho_smooth)
        total += Vs
    lam = total / n_surrogates
    Z = (V - lam) / np.sqrt(lam + 1.0)

    # candidate peaks: local maxima in rho, above both thresholds
    cands = []
    for i in range(n_theta):
        zrow, vrow = Z[i], V[i]
        peak = (zrow[1:-1] > zrow[:-2]) & (zrow[1:-1] >= zrow[2:]) & (zrow[1:-1] > z_min) \
            & (vrow[1:-1] >= min_events)
        idx = np.argwhere(peak).ravel() + 1
        for k in idx:
            cands.append((float(zrow[k]), i, int(k)))
    if not cands:
        return _empty()
    cands.sort(reverse=True)

    keep = []
    for z, i, k in cands:
        th = thetas[i]
        rho = k * rho_bin_px - rho_max
        if any(
            min(abs(np.degrees(th - thetas[j])), 180.0 - abs(np.degrees(th - thetas[j])))
            < nms_dtheta_deg
            and abs(rho - rj) < nms_drho_px
            for j, rj in keep
        ):
            continue
        keep.append((i, rho))
        if len(keep) >= max_lineaments:
            break

    th_out, rho_out, z_out, n_out, lam_out, ext_out, t0_out, t1_out, v_out = (
        [], [], [], [], [], [], [], [], [])
    for i, rho in keep:
        th = thetas[i]
        d = np.abs(_rho(col, row, th) - rho)
        sel = d <= (rho_smooth + 0.5) * rho_bin_px
        if sel.sum() < 3:
            continue
        along = -col[sel] * np.sin(th) + row[sel] * np.cos(th)
        ext = float(np.percentile(along, 95) - np.percentile(along, 5))
        if ext < min_extent_px:
            continue
        k = int(round((rho + rho_max) / rho_bin_px))
        th_out.append(float(th))
        rho_out.append(float(rho))
        z_out.append(float(Z[i, k]))
        n_out.append(int(V[i, k] / (2 * rho_smooth + 1)))
        lam_out.append(float(lam[i, k] / (2 * rho_smooth + 1)))
        ext_out.append(ext)
        t0_out.append(float(along.min()))
        t1_out.append(float(along.max()))
        v_out.append(float(Vw[i, k]))
    if not th_out:
        return _empty()
    return Lineaments(np.array(th_out), np.array(rho_out), np.array(z_out),
                      np.array(n_out), np.array(lam_out), np.array(ext_out),
                      np.array(t0_out), np.array(t1_out), np.array(v_out))


def _empty() -> Lineaments:
    z = np.zeros(0)
    return Lineaments(z, z.copy(), z.copy(), z.copy(), z.copy(), z.copy(), z.copy(),
                      z.copy(), z.copy())


def rasterise_lineaments(lin: Lineaments, shape: tuple[int, int], half_width_px: float,
                         weight_by_z: bool = True, extend_px: float = 0.0) -> np.ndarray:
    """Corridor field: every lineament painted with half-width ``half_width_px``.

    Values are the lineament's z score (or 1.0): a support weight, not a probability.  The
    corridor is only as wide as the catalogue's own epicentral uncertainty, which is the
    honest width this technique supports.
    """
    h, w = shape
    out = np.zeros(shape, dtype=np.float32)
    if len(lin) == 0:
        return out
    r = float(half_width_px)
    rad = int(np.ceil(r))
    dy, dx = np.mgrid[-rad : rad + 1, -rad : rad + 1]
    disk = (dx * dx + dy * dy) <= (r + 0.5) ** 2
    offs = np.column_stack([dy[disk], dx[disk]])
    for i in range(len(lin)):
        th, rho = float(lin.theta_rad[i]), float(lin.rho_px[i])
        c0, s0 = np.cos(th), np.sin(th)
        px, py = rho * c0, rho * s0
        t0 = float(lin.t_min_px[i]) - extend_px
        t1 = float(lin.t_max_px[i]) + extend_px
        n = max(int(abs(t1 - t0)) + 1, 2)
        ts = np.linspace(t0, t1, n)
        cs = px - ts * s0
        rs = py + ts * c0
        val = float(lin.z[i]) if weight_by_z else 1.0
        vals = np.full(n, val, dtype=np.float32)
        rows = np.rint(rs).astype(np.int64)[:, None] + offs[None, :, 0]
        cols = np.rint(cs).astype(np.int64)[:, None] + offs[None, :, 1]
        ok = (rows >= 0) & (rows < h) & (cols >= 0) & (cols < w)
        if not ok.any():
            continue
        v = np.broadcast_to(vals[:, None], rows.shape)
        np.maximum.at(out, (rows[ok], cols[ok]), v[ok])
    return out


def span_prune(col: np.ndarray, row: np.ndarray, lin: Lineaments, window_px: int = 24,
               z_span: float = 4.0, min_events_span: int = 6,
               merge_gap_px: float = 12.0) -> Lineaments:
    """Keep only the along-line spans where the local event count beats the local null.

    A Hough line is an infinite line; the evidence for it is local.  This function walks
    the line in ``window_px`` windows, compares the window's event count with the count
    expected from the *same window displaced perpendicular* to the line (a local, data-
    driven null that needs no extra random draws), and keeps only the contiguous spans
    that exceed ``z_span`` standard deviations of that null.  Adjacent kept spans closer
    than ``merge_gap_px`` are merged.

    This is this project's own refinement.  Its effect is measured in
    :mod:`gems50.validate` -- it exists because a raw Hough line paints tens of kilometres
    of corridor where only a few kilometres carry evidence.
    """
    col = np.asarray(col, dtype=np.float64)
    row = np.asarray(row, dtype=np.float64)
    out = []
    for i in range(len(lin)):
        th, rho = float(lin.theta_rad[i]), float(lin.rho_px[i])
        c0, s0 = np.cos(th), np.sin(th)
        rho_ev = col * c0 + row * s0
        along = -col * s0 + row * c0
        t0, t1 = float(lin.t_min_px[i]), float(lin.t_max_px[i])
        if t1 - t0 < window_px:
            out.append((th, rho, t0, t1, float(lin.z[i]), float(lin.n_events[i])))
            continue
        centres = np.arange(t0, t1 + 1e-9, window_px / 2.0)
        # local null: the same windows displaced perpendicular by +-5 px
        null_counts = []
        obs_counts = []
        for c in centres:
            for dperp in (-5.0, 5.0):
                m = (np.abs(rho_ev - (rho + dperp)) <= 1.5) & (np.abs(along - c) <= window_px / 2)
                null_counts.append(float(m.sum()))
            m = (np.abs(rho_ev - rho) <= 1.5) & (np.abs(along - c) <= window_px / 2)
            obs_counts.append(float(m.sum()))
        null_counts = np.array(null_counts)
        obs_counts = np.array(obs_counts)
        mu = null_counts.mean()
        sd = null_counts.std() + 1e-9
        thr = max(mu + z_span * sd, float(min_events_span))
        keep = obs_counts > thr
        if not keep.any():
            continue
        # contiguous spans
        spans = []
        start = None
        for j, k in enumerate(keep):
            if k and start is None:
                start = j
            if not k and start is not None:
                spans.append((centres[start] - window_px / 2, centres[j - 1] + window_px / 2))
                start = None
        if start is not None:
            spans.append((centres[start] - window_px / 2, centres[-1] + window_px / 2))
        merged = []
        for s in spans:
            if merged and s[0] - merged[-1][1] <= merge_gap_px:
                merged[-1] = (merged[-1][0], s[1])
            else:
                merged.append(s)
        for a, b in merged:
            if b - a < window_px / 2:
                continue
            m = (np.abs(rho_ev - rho) <= 1.5) & (along >= a) & (along <= b)
            out.append((th, rho, a, b, float(lin.z[i]), float(m.sum())))
    if not out:
        return _empty()
    arr = np.array(out)
    return Lineaments(arr[:, 0], arr[:, 1], arr[:, 4], arr[:, 5],
                      np.full(len(arr), np.nan), arr[:, 3] - arr[:, 2],
                      arr[:, 2], arr[:, 3], arr[:, 5])
