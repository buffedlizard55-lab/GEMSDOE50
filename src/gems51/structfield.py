"""Structural lineament evidence from the official feature stack and the owner-mirrored
derived rasters, plus the orientation-concordance fusion.

What is measured here
---------------------
For every layer the module computes a **structure-tensor lineament field**:

* smooth the layer at several scales,
* take its gradient, smooth the gradient's outer products (the structure tensor),
* *coherence* = sqrt((Jxx-Jyy)^2 + 4Jxy^2) / (Jxx+Jyy): 1 where the gradient direction is
  single-valued (a lineament edge), 0 where it is isotropic (noise, or a texture),
* *strength* = smoothed gradient magnitude * coherence,
* robust-normalise by the 98th percentile inside the valid footprint.

The direction of the gradient is perpendicular to a lineament, so the lineament azimuth is
the gradient azimuth + 90 deg; that azimuth is what the concordance step compares between
independent families.

Families (independent physical measurements, kept separate on purpose):

``topographic_scarp``
                the scarp-focused subset measured best on both independent instruments in
                amendment A2: the LiDAR scarp descriptors (step_max, lapneg_max, relief)
                plus the 10 m topographic openness/curvature/relief proxies (bands 2, 5, 6, 8).
``topographic``  3DEP-derived scarp descriptors (step_max, lapneg_max, coh100, relief),
                 detrended elevation and its slope, 10 m topographic openness/LRM
                 proxies (slope percentiles, profile curvature, local relief, hillshade
                 lineament, aspect coherence, mean elevation).
``magnetic``     magnetic anomaly, reduced-to-pole, total intensity and its horizontal and
                 vertical gradients, tilt angle / total curvature, TMI upward-continued 150 m.
``gravity``      isostatic gravity anomaly and its horizontal, vertical and slope derivatives.
``radiometric``  airborne K, Th, U, total count and the Th/K, U/K, U/Th ratios.
``seismic``      the event-geometry corridors of :mod:`gems51.seisfield` (this project's own
                 earthquake-lineation construction).

Concordance
-----------
A cell is *corroborated* when at least ``min_families`` families are simultaneously above
their own high-percentile lineament threshold **and** their lineament azimuths agree within
``angle_tol_deg``.  :func:`fuse` implements the bounded corroboration multiplier for
comparison, but the measurement stage of 2026-10-06 found it *harmful* on both independent
instruments (SGMC-off credit per dot 0.1784 with the multiplier against 0.1817 without it, and
Monte Cristo coverage 13.8 against 32.0 weighted pixels for the same mass), because it
concentrates mass on the largest structures and drops the small ones.  The shipped build
therefore uses a plain weighted sum of two max-normalised families
(``scripts/build_h51.py``); :func:`concordance` is kept as a diagnostic only.
"""
from __future__ import annotations

import numpy as np
import rasterio
from scipy import ndimage

from . import grid as g
from .notes import MEASURED, OWN

EPS = 1e-9


def _normalise(field: np.ndarray, valid: np.ndarray, percentile: float = 98.0) -> np.ndarray:
    values = field[valid & np.isfinite(field)]
    if values.size == 0:
        return np.zeros_like(field, dtype=np.float32)
    hi = float(np.percentile(values, percentile))
    hi = hi if hi > 0 else float(values.max())
    if hi <= 0:
        return np.zeros_like(field, dtype=np.float32)
    return np.clip(field / hi, 0.0, 1.0).astype(np.float32)


def structure_tensor(layer: np.ndarray, sigma: float, coherence_sigma: float) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    smooth = ndimage.gaussian_filter(np.nan_to_num(layer, nan=0.0), sigma)
    gy, gx = np.gradient(smooth)
    jxx = ndimage.gaussian_filter(gx * gx, coherence_sigma)
    jyy = ndimage.gaussian_filter(gy * gy, coherence_sigma)
    jxy = ndimage.gaussian_filter(gx * gy, coherence_sigma)
    trace = jxx + jyy
    coherence = np.sqrt((jxx - jyy) ** 2 + 4.0 * jxy ** 2) / (trace + EPS)
    magnitude = np.sqrt(trace)
    # azimuth of the lineament = azimuth of the gradient + 90 deg
    angle = np.arctan2(gy, gx) + np.pi / 2.0
    return magnitude * coherence, coherence, angle


def layer_lineament(layer: np.ndarray, valid: np.ndarray, scales: tuple[float, ...] = (2.0, 5.0, 10.0),
                    coherence_sigma: float = 3.0) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Multi-scale lineament strength plus the azimuth and coherence at the winning scale."""
    best = np.zeros_like(layer, dtype=np.float32)
    best_angle = np.zeros_like(layer, dtype=np.float32)
    best_coh = np.zeros_like(layer, dtype=np.float32)
    for sigma in scales:
        strength, coherence, angle = structure_tensor(layer, sigma, coherence_sigma)
        take = strength > best
        best = np.where(take, strength, best)
        best_angle = np.where(take, angle, best_angle)
        best_coh = np.where(take, coherence, best_coh)
    return _normalise(best, valid), best_angle.astype(np.float32), best_coh.astype(np.float32)


def _load_band(path: str, band: int) -> tuple[np.ndarray, np.ndarray, dict]:
    with rasterio.open(path) as ds:
        data = ds.read(band).astype(np.float32)
        tags = dict(ds.tags(band))
        desc = ds.descriptions[band - 1] if ds.descriptions else None
    if "q_lo" in tags and "q_hi" in tags:
        lo, hi = float(tags["q_lo"]), float(tags["q_hi"])
        valid = data > 0
        decoded = np.where(valid, lo + (data - 1.0) / 254.0 * (hi - lo), np.nan)
    else:
        valid = np.isfinite(data) & (data > 0)
        decoded = np.where(valid, data, np.nan)
    lo_p, hi_p = np.nanpercentile(decoded[valid], [1, 99]) if valid.any() else (0.0, 1.0)
    decoded = np.clip(decoded, lo_p, hi_p)
    return decoded.astype(np.float32), valid, {"path": path, "band": band, "description": desc,
                                               "percentiles_1_99": [float(lo_p), float(hi_p)]}


def families(paths: dict, valid: np.ndarray, scales: tuple[float, ...] = (2.0, 5.0, 10.0)) -> dict:
    """Build one lineament field per independent family and return their diagnostics."""
    spec = {
        "topographic": [(paths["features"], 19), (paths["features"], 12),
                        (paths["topo"], 1), (paths["topo"], 2), (paths["topo"], 4),
                        (paths["topo"], 5), (paths["topo"], 6), (paths["topo"], 8),
                        (paths["topo"], 9), (paths["scarp"], 3), (paths["scarp"], 4),
                        (paths["scarp"], 9)],
        "topographic_scarp": [(paths["scarp"], 3), (paths["scarp"], 4), (paths["scarp"], 9),
                              (paths["topo"], 2), (paths["topo"], 5), (paths["topo"], 6),
                              (paths["topo"], 8)],
        "magnetic": [(paths["features"], 1), (paths["features"], 2), (paths["features"], 3),
                     (paths["features"], 6), (paths["features"], 9), (paths["features"], 14),
                     (paths["extensions"], 4)],
        "gravity": [(paths["features"], 5), (paths["features"], 11), (paths["features"], 13),
                    (paths["features"], 18)],
        "radiometric": [(paths["radiometric"], 1), (paths["radiometric"], 2), (paths["radiometric"], 3),
                        (paths["radiometric"], 4), (paths["radiometric"], 5), (paths["radiometric"], 6),
                        (paths["radiometric"], 7), (paths["geodawn_rad"], 1), (paths["geodawn_rad"], 2),
                        (paths["geodawn_rad"], 3), (paths["geodawn_rad"], 4),
                        (paths["extensions"], 1), (paths["extensions"], 2), (paths["extensions"], 3)],
    }
    out: dict = {}
    for name, bands in spec.items():
        strength = np.zeros((g.GRID["height"], g.GRID["width"]), dtype=np.float32)
        angle = np.zeros_like(strength)
        coherence = np.zeros_like(strength)
        layers = []
        for path, band in bands:
            layer, layer_valid, info = _load_band(path, band)
            layer = np.where(layer_valid & valid, layer, np.nan)
            s, a, c = layer_lineament(layer, valid & layer_valid, scales)
            take = s > strength
            strength = np.where(take, s, strength)
            angle = np.where(take, a, angle)
            coherence = np.where(take, c, coherence)
            layers.append({"path": path, "band": band, "description": info["description"],
                           "valid_fraction": float((layer_valid & valid).mean()),
                           "p1_p99": info["percentiles_1_99"]})
        out[name] = {"strength": strength, "angle": angle, "coherence": coherence,
                     "layers": layers, "class": MEASURED}
    return out


def concordance(fams: dict, valid: np.ndarray, *, angle_tol_deg: float = 25.0,
                strength_percentile: float = 75.0, coherence_min: float = 0.25) -> tuple[np.ndarray, np.ndarray, dict]:
    """Count families simultaneously above threshold with agreeing azimuths."""
    names = sorted(fams)
    thresholds = {n: float(np.percentile(fams[n]["strength"][valid], strength_percentile)) for n in names}
    strong = {n: (fams[n]["strength"] >= thresholds[n]) & (fams[n]["coherence"] >= coherence_min) & valid
              for n in names}
    tol = np.radians(angle_tol_deg)
    count = np.zeros(np.asarray(valid).shape, dtype=np.uint8)
    best_angle = np.zeros(count.shape, dtype=np.float32)
    for i, a_name in enumerate(names):
        agree = strong[a_name].copy()
        angle_a = fams[a_name]["angle"]
        for b_name in names:
            if b_name == a_name:
                continue
            diff = np.abs(np.angle(np.exp(1j * 2.0 * (angle_a - fams[b_name]["angle"])))) / 2.0
            agree &= ~strong[b_name] | (diff <= tol)
        supports = agree & strong[a_name]
        count += supports.astype(np.uint8)
        best_angle = np.where(supports & (count <= 1), angle_a, best_angle)
    return count, best_angle, {
        "class": OWN,
        "families": names,
        "angle_tolerance_deg": angle_tol_deg,
        "strength_percentile": strength_percentile,
        "coherence_min": coherence_min,
        "thresholds": thresholds,
        "cells_with_2plus_families": int(np.count_nonzero(count >= 2)),
        "cells_with_3plus_families": int(np.count_nonzero(count >= 3)),
    }


def fuse(fams: dict, count: np.ndarray, *, corroboration_bonus: float = 0.5,
         corroborated_only: bool = False) -> np.ndarray:
    """Belief = strongest family strength x bounded corroboration factor."""
    names = sorted(fams)
    strength = np.maximum.reduce([fams[n]["strength"] for n in names])
    factor = 1.0 + corroboration_bonus * np.clip(count.astype(np.float32) - 1.0, 0.0, 3.0)
    belief = strength * factor
    if corroborated_only:
        belief = np.where(count >= 2, belief, 0.0)
    return np.clip(belief / max(float(belief.max()), EPS), 0.0, 1.0).astype(np.float32)
