"""Lineament transforms: ridge/valley response, orientation, and chain voting.

The physical argument (documented in docs/research/hypotheses.md): a fault is a
*line*, so an estimator that only measures how anomalous a pixel is will place mass
in blobs, whereas the metric pays only for being within 300 m of a fault trace.  The
transforms here measure (a) that a line passes through a pixel, (b) which way it
runs, and (c) whether *other* line pixels continue along the same direction.

All transforms are label-free: nothing in this module reads the fault catalogue.
"""

from __future__ import annotations

import numpy as np


def _hessian(band: np.ndarray, sigma: float):
    from scipy.ndimage import gaussian_filter

    g = gaussian_filter(band.astype(np.float32), sigma, order=0)
    gx = gaussian_filter(band.astype(np.float32), sigma, order=(0, 1))
    gy = gaussian_filter(band.astype(np.float32), sigma, order=(1, 0))
    gxx = gaussian_filter(band.astype(np.float32), sigma, order=(0, 2))
    gyy = gaussian_filter(band.astype(np.float32), sigma, order=(2, 0))
    gxy = gaussian_filter(band.astype(np.float32), sigma, order=(1, 1))
    return gx, gy, gxx, gyy, gxy


def line_response(band: np.ndarray, valid: np.ndarray, sigmas=(1.2, 2.5),
                  both_polarities: bool = True, normalized: bool = True) -> tuple:
    """Scale-normalised Hessian line (ridge/valley) response and orientation.

    Uses the second-derivative ratio of Sato et al. (1998) style structure
    enhancement: with |l1| <= |l2| the eigenvalues of the Hessian, the line response
    is  |l2| - |l1|  (large when one direction is flat and the other curved).  Both
    polarities are kept because a magnetic low and a magnetic high are equally good
    contact markers.

    Returns
    -------
    (response, orientation) where orientation is the *line* direction in radians,
    modulo pi, and response >= 0.
    """
    best = np.zeros(band.shape, dtype=np.float32)
    ang = np.zeros(band.shape, dtype=np.float32)
    for s in sigmas:
        _gx, _gy, gxx, gyy, gxy = _hessian(band, s)
        tmp = np.sqrt(np.maximum((gxx - gyy) ** 2 + 4.0 * gxy ** 2, 0.0))
        l1 = 0.5 * (gxx + gyy - tmp)          # smaller magnitude
        l2 = 0.5 * (gxx + gyy + tmp)          # larger magnitude
        a1, a2 = np.abs(l1), np.abs(l2)
        lo = np.minimum(a1, a2)
        hi = np.maximum(a1, a2)
        resp = (hi - lo) * (s ** 2) if normalized else (hi - lo)
        # orientation of the *line* = eigenvector of the smaller eigenvalue
        theta = 0.5 * np.arctan2(2.0 * gxy, (gxx - gyy))
        # eigenvector for the smaller |eigenvalue| is perpendicular to the gradient
        # direction of the larger curvature; rotate the curvature axis by 90 deg.
        line_ang = theta + np.pi / 2.0
        update = resp > best
        best = np.where(update, resp, best)
        ang = np.where(update, line_ang, ang)
    if both_polarities:
        best = np.abs(best)
    best[~valid] = 0.0
    return best, ang


def normalize(x: np.ndarray, valid: np.ndarray, lo_pct: float = 50.0,
              hi_pct: float = 99.5) -> np.ndarray:
    """Robust min-max scaling on the valid domain."""
    v = x[valid]
    if v.size == 0:
        return np.zeros_like(x)
    lo = np.percentile(v, lo_pct)
    hi = np.percentile(v, hi_pct)
    if hi <= lo:
        return np.zeros_like(x)
    return np.clip((x - lo) / (hi - lo), 0.0, 1.0).astype(np.float32)


def orientation_order(responses: list, angles: list, radius: int = 5,
                      eps: float = 1e-6) -> np.ndarray:
    """Second-order orientation order parameter across independent physics.

    R = | sum_p w_p exp(2 i theta_p) | / sum_p w_p ,  w_p = normalised line response
    of physics p.  R = 1 when every physics agrees on the strike (mod pi), R = 0 when
    they are uniformly distributed.  This requires *independent* fields to agree on
    the orientation of a line — the property the brief calls multi-physics consensus.
    """
    from scipy.ndimage import uniform_filter

    num = np.zeros(responses[0].shape, dtype=np.float32)
    den = np.zeros_like(num)
    for r, a in zip(responses, angles):
        w = uniform_filter(r.astype(np.float32), size=2 * radius + 1)
        num += w * np.cos(2.0 * a)
        den += w
    mag = np.hypot(num, np.zeros_like(num))
    R = mag / np.maximum(den, eps)
    return np.clip(R, 0.0, 1.0).astype(np.float32)


def cross_physics_consensus(responses: list, angles: list, radius: int = 5) -> np.ndarray:
    """Agreement-weighted line strength: geometric mean of strength x orientation order."""
    strength = np.ones_like(responses[0], dtype=np.float32)
    for r in responses:
        strength *= np.maximum(r, 0.0)
    strength = np.power(strength, 1.0 / max(1, len(responses)))
    return (strength * orientation_order(responses, angles, radius)).astype(np.float32)


def chain_vote(mask: np.ndarray, length_px: int = 9, n_dirs: int = 16,
               weights: np.ndarray | None = None) -> np.ndarray:
    """Fraction of straight lines through each pixel that stay inside `mask`.

    The vote is what separates a structure from an isolated lineament: a single
    straight valley is a stream; a chain of collinear segments is a fault.
    """
    from numpy import cos, pi, sin

    H, W = mask.shape
    m = mask.astype(np.float32)
    acc = np.zeros((H, W), dtype=np.float32)
    half = max(1, length_px // 2)
    for d in range(n_dirs):
        th = pi * d / n_dirs
        dr, dc = sin(th), cos(th)
        total = np.zeros((H, W), dtype=np.float32)
        cnt = 0
        for k in range(-half, half + 1):
            sh_r = int(round(k * dr))
            sh_c = int(round(k * dc))
            shifted = np.roll(np.roll(m, sh_r, axis=0), sh_c, axis=1)
            total += shifted
            cnt += 1
        acc += (total / max(1, cnt))
    vote = acc / n_dirs
    if weights is not None:
        vote = vote * weights
    return vote.astype(np.float32)


def skeletonize(mask: np.ndarray) -> np.ndarray:
    from skimage.morphology import skeletonize as _sk

    return _sk(mask.astype(bool))


def nms_ridge(response: np.ndarray, size: int = 3) -> np.ndarray:
    """Non-maximum suppression across the gradient of a ridge-like surface."""
    from scipy.ndimage import maximum_filter

    mx = maximum_filter(response, size=size)
    return (response >= mx).astype(np.float32) * response
