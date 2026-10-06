"""2-D anisotropic lineation extraction (the OADC idea, adapted from 3-D to epicentres).

Method, and exactly which part of it is published where
-------------------------------------------------------
* Ouillon, G., Ducorbier, C. and Sornette, D. (2008), "Automatic reconstruction of fault
  networks from seismicity catalogs: Three-dimensional optimal anisotropic dynamic
  clustering", JGR 113, B01306, doi:10.1029/2007JB005032.  Published content used here:
  a cluster is fitted by its **full covariance tensor**, the fitting criterion is the
  *smallest* eigenvalue (clusters that are as thin as possible in one direction), and the
  cluster count/stopping criterion is set by the **location uncertainty Δ** (their
  eq. 27 ff.: clusters should satisfy lambda_3 < Delta*Delta).  In 3-D they minimise
  sum(lambda_3^2) over partitions.
* Ouillon, G. and Sornette, D. (2011), JGR 116, B02306, doi:10.1029/2010JB007752.
  Published content used here: separation of clustered events from an uncorrelated
  background **before** clustering (:mod:`gems50.decluster`), and the statement that
  faults should be reconstructed as anisotropic kernels rather than perfect planes.
* Wang, Y., Ouillon, G., Woessner, J., Sornette, D. and Husen, S. (2013),
  "Automatic reconstruction of fault networks from seismicity catalogs including location
  uncertainty", JGR Solid Earth 118, 5956-5975, doi:10.1002/2013JB010164
  (preprint arXiv:1304.6912).  Published content used here: each event carries its **own**
  location uncertainty and the clustering must respect that heterogeneity.  That is
  implemented here as uncertainty weighting and as a per-neighbourhood Δ.

What is *this project's own* adaptation (flagged, unverified against published results):

* the 2-D reduction itself (the sources are 3-D and use hypocentral depth);
* the triangle-area analogue of the tetrahedron test (:mod:`gems50.decluster`);
* using an oriented matched filter over the segment support to turn many short local
  axes into continuous corridors, and the "credit field" it produces.

The adaptation is not assumed correct: :mod:`gems50.validate` measures it against
withheld catalogue segments and against an independent fault inventory, and the shipped
site reports the measured numbers rather than the method's plausibility.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from scipy import ndimage
from scipy.spatial import cKDTree


@dataclass
class Segments:
    """Local principal axes, one row per accepted neighbourhood."""

    x: np.ndarray  # centroid easting (m)
    y: np.ndarray  # centroid northing (m)
    ux: np.ndarray  # unit vector along the principal axis
    uy: np.ndarray
    sigma1_m: np.ndarray  # major-axis standard deviation (m)
    sigma2_m: np.ndarray  # minor-axis standard deviation (m)
    delta_m: np.ndarray  # local location uncertainty 1-sigma (m)
    n_events: np.ndarray
    weight: np.ndarray  # linearity weight in (0, 1]

    def __len__(self) -> int:
        return len(self.x)

    @property
    def strike_deg(self) -> np.ndarray:
        """Azimuth of the principal axis, degrees clockwise from north (for reporting)."""
        return (np.degrees(np.arctan2(self.ux, self.uy))) % 180.0


def neighbourhood_axes(
    xy: np.ndarray,
    h_err_m: np.ndarray,
    k: int = 12,
    r_max_m: float = 8000.0,
    min_events: int = 8,
    linearity_min: float = 0.5,
    sigma2_over_delta_max: float = 1.0,
    sigma1_over_delta_min: float = 2.0,
    min_sigma1_m: float = 800.0,
    uncertainty_weighted: bool = True,
) -> Segments:
    """Principal-axis fit of every event's k-nearest neighbourhood, with OADC criteria.

    Parameters
    ----------
    xy : (n, 2) projected metres.
    h_err_m : (n,) epicentral 1-sigma uncertainty, metres.
    k, r_max_m : neighbourhood definition.
    min_events : a neighbourhood must contain at least this many events.
    linearity_min : ``1 - sigma2/sigma1`` must reach this (higher = more line-like).
    sigma2_over_delta_max : the OADC criterion in 2-D -- the minor-axis scatter must not
        exceed the location uncertainty (in 3-D the published rule is lambda_3 < Delta^2).
    sigma1_over_delta_min : the major axis must be resolved by the data, i.e. longer than
        the location uncertainty.
    min_sigma1_m : absolute floor so that a tight cluster in a well-located region is not
        promoted to a line on the strength of uncertainty alone.
    uncertainty_weighted : weight each neighbour by ``1 / h_err^2`` (Wang et al. 2013).
    """
    xy = np.asarray(xy, dtype=np.float64)
    h = np.asarray(h_err_m, dtype=np.float64)
    n = len(xy)
    if n < min_events:
        return _empty()

    tree = cKDTree(xy)
    kq = min(k, n)
    dist, idx = tree.query(xy, k=kq, distance_upper_bound=r_max_m)
    dist = np.where(np.isfinite(dist), dist, np.inf)

    out = {key: [] for key in ("x", "y", "ux", "uy", "s1", "s2", "delta", "n", "w")}
    for i in range(n):
        nb = idx[i][np.isfinite(dist[i]) & (idx[i] != i)]
        if nb.size < min_events - 1:
            continue
        pts = xy[nb] - xy[i]
        w = 1.0 / np.maximum(h[nb], 50.0) ** 2 if uncertainty_weighted else np.ones(nb.size)
        w = w / w.sum()
        mu = (w[:, None] * pts).sum(axis=0)
        d = pts - mu
        cov = (w[:, None] * d).T @ d
        vals, vecs = np.linalg.eigh(cov)  # ascending
        lam1, lam2 = float(vals[1]), float(vals[0])
        if lam1 <= 0:
            continue
        s1, s2 = float(np.sqrt(lam1)), float(np.sqrt(max(lam2, 0.0)))
        delta = float(np.median(h[nb]))
        linearity = 1.0 - (s2 / s1 if s1 > 0 else 1.0)
        if linearity < linearity_min:
            continue
        if s2 > sigma2_over_delta_max * delta:
            continue
        if s1 < max(sigma1_over_delta_min * delta, min_sigma1_m):
            continue
        v = vecs[:, 1]
        out["x"].append(xy[i, 0] + mu[0])
        out["y"].append(xy[i, 1] + mu[1])
        out["ux"].append(float(v[0]))
        out["uy"].append(float(v[1]))
        out["s1"].append(s1)
        out["s2"].append(s2)
        out["delta"].append(delta)
        out["n"].append(int(nb.size + 1))
        out["w"].append(float(linearity))
    if not out["x"]:
        return _empty()
    return Segments(
        x=np.array(out["x"]),
        y=np.array(out["y"]),
        ux=np.array(out["ux"]),
        uy=np.array(out["uy"]),
        sigma1_m=np.array(out["s1"]),
        sigma2_m=np.array(out["s2"]),
        delta_m=np.array(out["delta"]),
        n_events=np.array(out["n"]),
        weight=np.array(out["w"]),
    )


def _empty() -> Segments:
    z = np.zeros(0)
    return Segments(z, z.copy(), z.copy(), z.copy(), z.copy(), z.copy(), z.copy(),
                    z.astype(int), z.copy())


def segment_points(seg: Segments, sample_m: float = 100.0) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Sample every segment's centreline at ``sample_m`` spacing (for rasterisation).

    Returns ``(x, y, weight)`` arrays, one entry per sample.
    """
    if len(seg) == 0:
        return np.zeros(0), np.zeros(0), np.zeros(0)
    half = np.minimum(2.0 * seg.sigma1_m, 8.0 * seg.delta_m + 1000.0)
    xs, ys, ws = [], [], []
    for i in range(len(seg)):
        m = max(int(2 * half[i] / sample_m) + 1, 2)
        t = np.linspace(-1.0, 1.0, m)
        xs.append(seg.x[i] + t * half[i] * seg.ux[i])
        ys.append(seg.y[i] + t * half[i] * seg.uy[i])
        ws.append(np.full(m, seg.weight[i]))
    return np.concatenate(xs), np.concatenate(ys), np.concatenate(ws)


def rasterise_support(
    seg: Segments,
    shape: tuple[int, int],
    transform: tuple,
    sample_m: float = 100.0,
) -> np.ndarray:
    """Paint segment centrelines into a weighted support field (float32, same grid)."""
    a, _, c, _, e, f = transform
    x, y, w = segment_points(seg, sample_m=sample_m)
    out = np.zeros(shape, dtype=np.float32)
    if x.size == 0:
        return out
    col = np.floor((x - c) / a).astype(np.int64)
    row = np.floor((y - f) / e).astype(np.int64)
    ok = (col >= 0) & (col < shape[1]) & (row >= 0) & (row < shape[0])
    np.add.at(out, (row[ok], col[ok]), w[ok].astype(np.float32))
    return out


def oriented_matched_filter(
    support: np.ndarray,
    n_orient: int = 12,
    length_px: int = 21,
    width_px: int = 3,
) -> tuple[np.ndarray, np.ndarray]:
    """Oriented box-filter response: max over orientations, plus the argmax orientation.

    This is the step that converts many short, noisy local axes into continuous
    corridors: a corridor pixel is one where the support is high *and* aligned over a
    length of ``length_px``.  It is the lineament analogue of a Hough/matched-filter
    detector (this project's own adaptation -- see the module docstring).
    """
    support = np.asarray(support, dtype=np.float32)
    best = np.zeros_like(support)
    best_theta = np.zeros(support.shape, dtype=np.int16)
    half_l = (length_px - 1) // 2
    for j in range(n_orient):
        theta = np.pi * j / n_orient
        # separable box along the orientation: sample the line at 1 px steps
        ts = np.arange(-half_l, half_l + 1, dtype=np.float64)
        xs = np.round(ts * np.cos(theta)).astype(int)
        ys = np.round(ts * np.sin(theta)).astype(int)
        acc = np.zeros_like(support)
        for dx, dy in zip(xs, ys):
            acc += np.roll(np.roll(support, -dy, axis=0), -dx, axis=1)
        if width_px > 1:
            acc = ndimage.uniform_filter(acc, size=(width_px, width_px), mode="nearest")
        acc /= float(len(ts))
        upd = acc > best
        best[upd] = acc[upd]
        best_theta[upd] = j
    return best, best_theta


def theta_degrees(theta_index: np.ndarray, n_orient: int = 12) -> np.ndarray:
    """Map the argmax orientation index to an azimuth in degrees from north."""
    return (90.0 - 180.0 * np.asarray(theta_index) / n_orient) % 180.0


# ---------------------------------------------------------------------------------------
# Cluster-scale lineations: the OADC splitting logic applied to 2-D epicentres
# ---------------------------------------------------------------------------------------

@dataclass
class ClusterLineations:
    """One principal-axis corridor per linear cluster (or sub-cluster)."""

    x: np.ndarray
    y: np.ndarray
    ux: np.ndarray
    uy: np.ndarray
    half_length_m: np.ndarray
    half_width_m: np.ndarray
    n_events: np.ndarray
    ratio: np.ndarray  # lambda1 / lambda2
    p_value: np.ndarray  # Monte-Carlo p of the elongation under isotropy
    t0: np.ndarray  # first event year in the cluster
    t1: np.ndarray  # last event year in the cluster

    def __len__(self) -> int:
        return len(self.x)

    @property
    def strike_deg(self) -> np.ndarray:
        return (np.degrees(np.arctan2(self.ux, self.uy))) % 180.0


def _ratio_null(n: int, draws: int = 400, seed: int = 20261006) -> np.ndarray:
    """Monte-Carlo null distribution of lambda1/lambda2 for n isotropic 2-D points."""
    rng = np.random.default_rng(seed + n)
    pts = rng.normal(size=(draws, n, 2))
    pts -= pts.mean(axis=1, keepdims=True)
    cov = np.einsum("dni,dnj->dij", pts, pts) / (n - 1)
    vals = np.linalg.eigvalsh(cov)
    return vals[:, 1] / np.maximum(vals[:, 0], 1e-12)


def _split_cov(pts: np.ndarray, rng: np.random.Generator, tries: int = 8) -> tuple[np.ndarray, np.ndarray]:
    """Best 2-means split by the OADC criterion: minimise the sum of minor-axis variance.

    In 3-D Ouillon et al. (2008) minimise sum(lambda_3^2) over partitions; in this 2-D
    reduction the analogous quantity is sum(lambda_2) (the minor-axis variance).
    """
    best = None
    best_cost = np.inf
    n = len(pts)
    for _ in range(tries):
        # k-means++ style seeding
        i0 = rng.integers(n)
        d2 = ((pts - pts[i0]) ** 2).sum(axis=1)
        i1 = int(np.argmax(d2)) if d2.max() > 0 else (i0 + 1) % n
        cent = np.stack([pts[i0], pts[i1]])
        for _ in range(25):
            dist = ((pts[:, None, :] - cent[None, :, :]) ** 2).sum(axis=2)
            assign = np.argmin(dist, axis=1)
            if len(np.unique(assign)) < 2:
                break
            new = np.stack([pts[assign == k].mean(axis=0) for k in (0, 1)])
            if np.allclose(new, cent):
                cent = new
                break
            cent = new
        cost = 0.0
        ok = True
        for k in (0, 1):
            sub = pts[assign == k]
            if len(sub) < 4:
                ok = False
                break
            cov = np.cov(sub.T)
            cost += float(np.linalg.eigvalsh(cov)[0])
        if ok and cost < best_cost:
            best_cost = cost
            best = assign.copy()
    if best is None:
        best = np.arange(n) % 2
    return best, np.array([best_cost])


def split_cluster(pts: np.ndarray, delta_m: float, min_events: int = 12,
                  max_depth: int = 12, seed: int = 20261006) -> list[np.ndarray]:
    """Recursively split a cluster until every part is thin at scale ``delta_m``.

    Stopping rule (the published OADC idea, reduced to 2-D): a part stops splitting when
    its minor-axis standard deviation is below ``delta_m`` (the resolution scale) or it
    has fewer than ``min_events`` events.  ``delta_m`` plays exactly the role the source
    paper assigns to it: "Delta can take any arbitrary value assigned by the user and, in
    such a case, it must be interpreted as the spatial resolution at which the user needs
    to approximate the anisotropic fault structure defined by the catalog of events"
    (Ouillon, Ducorbier & Sornette 2008, section 5).
    """
    rng = np.random.default_rng(seed)
    out: list[np.ndarray] = []
    stack = [np.asarray(pts, dtype=np.float64)]
    while stack:
        p = stack.pop()
        if len(p) < min_events:
            continue
        cov = np.cov(p.T) if len(p) > 2 else np.eye(2)
        lam = np.linalg.eigvalsh(cov)
        if np.sqrt(max(lam[0], 0.0)) <= delta_m or max_depth <= 0:
            out.append(p)
            continue
        assign, _ = _split_cov(p, rng)
        a, b = p[assign == 0], p[assign == 1]
        if len(a) < 4 or len(b) < 4:
            out.append(p)
            continue
        stack.append(a)
        stack.append(b)
        max_depth -= 1
    return out


def cluster_lineations(
    xy: np.ndarray,
    t_years: np.ndarray,
    h_err_m: np.ndarray,
    eps_m: float = 4000.0,
    min_samples: int = 15,
    delta_m: float = 1000.0,
    min_events: int = 12,
    ratio_min: float = 3.0,
    p_max: float = 0.01,
    max_depth: int = 12,
    time_scale_m_per_year: float = 3000.0,
    seed: int = 20261006,
) -> ClusterLineations:
    """Clusters -> OADC splitting -> principal-axis corridors, with an elongation test.

    Clustering is DBSCAN in a space-time metric ((x, y, t * time_scale)), which is what
    separates independent sequences; the splitting follows the published OADC criterion;
    the elongation significance is a Monte-Carlo test of lambda1/lambda2 under isotropy.
    """
    from sklearn.cluster import DBSCAN

    xy = np.asarray(xy, dtype=np.float64)
    t = np.asarray(t_years, dtype=np.float64)
    h = np.asarray(h_err_m, dtype=np.float64)
    if len(xy) == 0:
        return _empty_clusters()
    feats = np.column_stack([xy[:, 0], xy[:, 1], t * time_scale_m_per_year])
    labels = DBSCAN(eps=eps_m, min_samples=min_samples).fit_predict(feats)

    rows = []
    for lab in np.unique(labels):
        if lab < 0:
            continue
        m = labels == lab
        pts, tl, hl = xy[m], t[m], h[m]
        if len(pts) < min_events:
            continue
        delta = float(np.median(hl))
        for part in split_cluster(pts, delta, min_events=min_events, max_depth=max_depth,
                                  seed=seed):
            if len(part) < min_events:
                continue
            mu = part.mean(axis=0)
            d = part - mu
            cov = np.cov(d.T)
            vals, vecs = np.linalg.eigh(cov)
            lam1, lam2 = float(vals[1]), float(max(vals[0], 1e-9))
            ratio = lam1 / lam2
            if ratio < ratio_min:
                continue
            null = _ratio_null(len(part), seed=seed)
            p_value = float((null >= ratio).mean())
            if p_value > p_max:
                continue
            v = vecs[:, 1]
            along = d @ v
            perp = d @ vecs[:, 0]
            half_len = float(max(np.percentile(along, 95) - np.percentile(along, 5), 0) / 2)
            half_wid = float(max(np.percentile(perp, 95) - np.percentile(perp, 5), 0) / 2)
            if half_len <= 0:
                continue
            idx = np.where(m)[0]
            rows.append((
                float(mu[0]), float(mu[1]), float(v[0]), float(v[1]),
                max(half_len, 0.5 * delta), max(half_wid, delta), int(len(part)),
                ratio, p_value, float(tl.min()), float(tl.max()),
            ))
    if not rows:
        return _empty_clusters()
    a = np.array(rows)
    return ClusterLineations(
        x=a[:, 0], y=a[:, 1], ux=a[:, 2], uy=a[:, 3], half_length_m=a[:, 4],
        half_width_m=a[:, 5], n_events=a[:, 6].astype(int), ratio=a[:, 7],
        p_value=a[:, 8], t0=a[:, 9], t1=a[:, 10])


def _empty_clusters() -> ClusterLineations:
    z = np.zeros(0)
    return ClusterLineations(z, z.copy(), z.copy(), z.copy(), z.copy(), z.copy(),
                             z.astype(int), z.copy(), z.copy(), z.copy(), z.copy())


def rasterise_clusters(cl: ClusterLineations, shape: tuple[int, int], transform: tuple,
                       half_width_m: float | None = None, weight: str = "none",
                       sample_m: float = 100.0) -> np.ndarray:
    """Paint the corridors: centre line plus half-width (default: the corridor's own)."""
    a, _, c0, _, e, f = transform
    out = np.zeros(shape, dtype=np.float32)
    for i in range(len(cl)):
        hw = half_width_m if half_width_m is not None else cl.half_width_m[i]
        n = max(int(2 * cl.half_length_m[i] / sample_m) + 1, 2)
        ts = np.linspace(-cl.half_length_m[i], cl.half_length_m[i], n)
        xs = cl.x[i] + ts * cl.ux[i]
        ys = cl.y[i] + ts * cl.uy[i]
        col = np.floor((xs - c0) / a).astype(np.int64)
        row = np.floor((ys - f) / e).astype(np.int64)
        rad = int(np.ceil(hw / abs(a)))
        dy, dx = np.mgrid[-rad : rad + 1, -rad : rad + 1]
        disk = (dx * dx + dy * dy) <= rad * rad
        offs = np.column_stack([dy[disk], dx[disk]])
        rows = row[:, None] + offs[None, :, 0]
        cols = col[:, None] + offs[None, :, 1]
        ok = (rows >= 0) & (rows < shape[0]) & (cols >= 0) & (cols < shape[1])
        if weight == "z":
            val = np.float32(min(cl.ratio[i] / 10.0, 1.0))
        elif weight == "events":
            val = np.float32(min(cl.n_events[i] / 100.0, 1.0))
        else:
            val = np.float32(1.0)
        v = np.broadcast_to(np.full(n, val, dtype=np.float32)[:, None], rows.shape)
        np.maximum.at(out, (rows[ok], cols[ok]), v[ok])
    return out


def merge_clusters(cl: "ClusterLineations", near_m: float = 1500.0,
                   angle_tol_deg: float = 25.0, passes: int = 4) -> "ClusterLineations":
    """Agglomerative chaining of collinear, near-touching corridors.

    Kamer, Ouillon & Sornette (NHESS 20, 3611-3628, 2020) merge overlapping anisotropic
    clusters agglomeratively because a single fault is typically split into several
    sub-clusters by the splitting recursion; a chain of short corridors under-covers the
    trend.  Here two corridors are merged when their nearest endpoints are within
    ``near_m`` and their orientation difference is below ``angle_tol_deg``; the merged
    corridor is re-fit by the inertia tensor of its two endpoint clouds weighted by event
    count.  Unverified adaptation, flagged as such -- it changes coverage, not the
    detector's significance test.
    """
    import numpy as _np

    if len(cl) < 2:
        return cl
    x, y = cl.x.copy(), cl.y.copy()
    ux, uy = cl.ux.copy(), cl.uy.copy()
    hl, hw = cl.half_length_m.copy(), cl.half_width_m.copy()
    n = cl.n_events.copy().astype(float)
    alive = _np.ones(len(x), bool)
    for _ in range(passes):
        merged = False
        order = _np.argsort(-hl)
        for i in order:
            if not alive[i]:
                continue
            for j in range(len(x)):
                if j == i or not alive[j]:
                    continue
                # endpoints of each corridor
                pi = [(x[i] + s * hl[i] * ux[i], y[i] + s * hl[i] * uy[i]) for s in (-1, 1)]
                pj = [(x[j] + s * hl[j] * ux[j], y[j] + s * hl[j] * uy[j]) for s in (-1, 1)]
                d = min(_np.hypot(a[0] - b[0], a[1] - b[1]) for a in pi for b in pj)
                if d > near_m:
                    continue
                cosang = abs(ux[i] * ux[j] + uy[i] * uy[j])
                ang = _np.degrees(_np.arccos(_np.clip(cosang, -1, 1)))
                if ang > angle_tol_deg:
                    continue
                w = n[i] + n[j]
                # endpoint-cloud inertia of the two corridors, weighted by event count
                pts = []
                wts = []
                for k, nn in ((i, n[i]), (j, n[j])):
                    for s in (-1, 1):
                        pts.append((x[k] + s * hl[k] * ux[k], y[k] + s * hl[k] * uy[k]))
                        wts.append(nn / 2.0)
                pts = _np.asarray(pts)
                wts = _np.asarray(wts)
                mu = (pts * wts[:, None]).sum(0) / wts.sum()
                cov = ((pts - mu) * wts[:, None]).T @ (pts - mu) / wts.sum()
                vals, vecs = _np.linalg.eigh(cov)
                v = vecs[:, -1]
                proj = (pts - mu) @ v
                x[i], y[i] = mu
                ux[i], uy[i] = v
                hl[i] = max(proj.max(), -proj.min())
                hw[i] = max(hw[i], hw[j])
                n[i] = w
                alive[j] = False
                merged = True
        if not merged:
            break
    return ClusterLineations(
        x=x[alive], y=y[alive], ux=ux[alive], uy=uy[alive], half_length_m=hl[alive],
        half_width_m=hw[alive], n_events=n[alive].astype(int),
        ratio=cl.ratio[alive], p_value=cl.p_value[alive],
        t0=cl.t0[alive], t1=cl.t1[alive])


def chain_segments(cl: "ClusterLineations", near_m: float = 1500.0,
                   angle_tol_deg: float = 40.0) -> list[tuple[float, float, float, float]]:
    """Straight connectors between corridor endpoints that are close and near-collinear.

    The splitting recursion cuts one fault into many short corridors; the union of their
    axes leaves gaps where no sub-cluster was significant.  A connector is a *bet* that the
    gap belongs to the same structure, so it is emitted sparsely (one dot every 3 px) and is
    reported separately from the axes in the evidence receipt.
    """
    import numpy as _np

    segs = []
    for i in range(len(cl)):
        for j in range(i + 1, len(cl)):
            cosang = abs(cl.ux[i] * cl.ux[j] + cl.uy[i] * cl.uy[j])
            ang = _np.degrees(_np.arccos(_np.clip(cosang, -1, 1)))
            if ang > angle_tol_deg:
                continue
            best = None
            for si in (-1, 1):
                for sj in (-1, 1):
                    ax, ay = cl.x[i] + si * cl.half_length_m[i] * cl.ux[i], cl.y[i] + si * cl.half_length_m[i] * cl.uy[i]
                    bx, by = cl.x[j] + sj * cl.half_length_m[j] * cl.ux[j], cl.y[j] + sj * cl.half_length_m[j] * cl.uy[j]
                    d = float(_np.hypot(ax - bx, ay - by))
                    if best is None or d < best[0]:
                        best = (d, ax, ay, bx, by)
            if best is not None and best[0] <= near_m:
                segs.append(best[1:])
    return segs


def dbscan_labels(xy: np.ndarray, t_years: np.ndarray, h_err_m: np.ndarray,
                  eps_m: float = 3000.0, min_samples: int = 15,
                  time_scale_m_per_yr: float = 3000.0) -> np.ndarray:
    """The DBSCAN labelling used by :func:`cluster_lineations`, exposed for spine extraction."""
    from sklearn.cluster import DBSCAN

    xy = np.asarray(xy, dtype=float)
    t = np.asarray(t_years, dtype=float)
    P = np.column_stack([xy[:, 0], xy[:, 1], t * time_scale_m_per_yr])
    return DBSCAN(eps=eps_m, min_samples=min_samples).fit_predict(P)


def cluster_spines(xy: np.ndarray, labels: np.ndarray, min_events: int = 15,
                   n_bins: int = 24, max_gap_bins: int = 1) -> list[np.ndarray]:
    """Thin polyline spine of every cluster: the principal axis, curved to the data.

    A single straight principal axis under-covers a curved rupture (measured: 34 % of the
    2020 Monte Cristo trend).  Binning the cluster along its principal axis and taking the
    perpendicular *median* of each bin gives a backbone that follows the cloud; bins with
    fewer than 3 events are skipped so the spine is interpolated across gaps in the same
    way a geologist would connect mapped scarps.  This is our own construction (not an
    OADC output) and is labelled as such in the evidence receipt.

    Returns a list of (n, 2) arrays in UTM metres.
    """
    out = []
    labels = np.asarray(labels)
    xy = np.asarray(xy, dtype=float)
    for lab in sorted(set(labels.tolist())):
        if lab < 0:
            continue
        P = xy[labels == lab]
        if len(P) < min_events:
            continue
        mu = P.mean(axis=0)
        Q = P - mu
        # principal axis from the inertia tensor (unweighted inside a cluster)
        cov = Q.T @ Q / len(Q)
        vals, vecs = np.linalg.eigh(cov)
        v = vecs[:, -1]                      # major axis
        s = Q @ v                            # along-axis coordinate
        w = Q @ np.array([-v[1], v[0]])      # perpendicular coordinate
        edges = np.linspace(s.min(), s.max(), n_bins + 1)
        pts = []
        for k in range(n_bins):
            m = (s >= edges[k]) & (s <= edges[k + 1])
            if m.sum() < 3:
                continue
            sc, wc = 0.5 * (edges[k] + edges[k + 1]), float(np.median(w[m]))
            pts.append(mu + sc * v + wc * np.array([-v[1], v[0]]))
        if len(pts) < 2:
            continue
        out.append(np.asarray(pts))
    return out
