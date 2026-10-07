"""Label-free belief field on the official competition grid.

Everything here is computed from measurement rasters that contain **no fault labels**:

``lidar_scarp_features_u8.tif``
    12 bands of USGS 3DEP 1 m LiDAR topographic descriptors (slope excess, 10 m-vs-50 m step,
    crest convexity, base concavity, down/up-facing maximum, cross-profile, local relief,
    100 m orientation coherence, strike, validity).  Owner-derived from the public 3DEP 1 m DEM
    tiles the competition itself links; quantisation rule and per-band units are recorded in the
    sidecar JSON shipped next to it.
``geodawn_rad_u8.tif`` / ``geodawn_extensions_u8.tif``
    GeoDAWN airborne radiometrics (K, Th, U, total count) and the ratio/extension products
    (Th/K, U/K, U/Th, TMI upward-continued 150 m).  USGS, DOI 10.5066/P93LGLVQ.
``gdr_wellspring_in_footprint.csv`` / ``gdr_volcanic_vents_in_footprint.csv``
    Geothermal Data Repository submission 1391 + Nevada volcanic vents, in-footprint points with
    temperature and geochemistry (public, free to use with attribution).
``tiger_road_distance_m.tif`` / ``blm_closed_claim_distance_m.tif``
    Metres to the nearest Census road/trail and to the nearest *closed* BLM mineral claim -
    the two human-made linear artifacts that manufacture scarps and lineations.

No function in this module reads ``labels.tif``/``existing_faults.tif`` except through
:func:`catalogue_distance_px`, which is used only to *exclude* cells, and the exclusion is a
scalar distance, so a spatially blocked holdout is not contaminated by the field itself.
"""
from __future__ import annotations

from dataclasses import dataclass, field as dc_field
from pathlib import Path
from typing import Any

import numpy as np
import rasterio
from scipy import ndimage


from .truthmodel import PIXEL_M

REPO = Path(__file__).resolve().parents[2]
INPUTS = Path("/home/user/.arena/inputs")
EXT = REPO / "data" / "external"
MIRROR = Path("/home/user/gemsdata/GEMSDOE24/data/external")
AUDIT = MIRROR / "audit_sources"
GRID = (3730, 3292)

# sidecar quantisation: x = xmax * ((q-1)/254)**2 for "sqrt" bands, xmax * (q-1)/254 for "linear"
SCARP_QUANT = {
    "ex_max": (1.5, "sqrt"), "ex_mean": (0.3, "sqrt"), "step_max": (1.0, "sqrt"),
    "lapneg_max": (0.05, "sqrt"), "lappos_max": (0.05, "sqrt"), "downface_max": (1.0, "sqrt"),
    "upface_max": (1.0, "sqrt"), "cross_max": (1.0, "sqrt"), "relief": (300.0, "sqrt"),
    "coh100": (1.0, "linear"), "strike": (180.0, "linear"), "valid": (1.0, "linear"),
}
SCARP_BANDS = list(SCARP_QUANT)
RADIOMETRIC_BANDS = ["K", "Th", "U", "TC"]
EXTENSION_BANDS = ["ThK", "UK", "UTh", "TMI_up150"]

SCARP_FAMILY = ["step_max", "lapneg_max", "lappos_max", "downface_max", "upface_max",
                "cross_max", "ex_max", "relief", "coh100"]
RADIO_FAMILY = ["K", "Th", "U", "TC", "ThK", "UK", "UTh", "TMI_up150"]


def _decode_scarp(q: np.ndarray, xmax: float, kind: str) -> np.ndarray:
    t = (q.astype(np.float32) - 1.0) / 254.0
    t = np.clip(t, 0.0, 1.0)
    x = t ** 2 if kind == "sqrt" else t
    return np.where(q > 0, xmax * x, np.nan).astype(np.float32)


def _decode_linear_rank(q: np.ndarray) -> np.ndarray:
    """Radiometrics/extensions: uint8 1..255 over the 1st..99th percentile, 0 = nodata."""
    return np.where(q > 0, (q.astype(np.float32) - 1.0) / 254.0, np.nan).astype(np.float32)


def _read_multi(path: Path) -> tuple[np.ndarray, dict]:
    with rasterio.open(path) as ds:
        data = ds.read()
        crs, transform = ds.crs, tuple(float(v) for v in ds.transform)[:6]
    if data.shape[1:] != tuple(GRID):
        raise ValueError(f"{path}: shape {data.shape[1:]} != {GRID}")
    return data, {"path": str(path), "crs": str(crs), "transform": transform,
                  "bands": data.shape[0], "dtype": str(data.dtype)}


@dataclass
class Inputs:
    footprint: np.ndarray
    labels: np.ndarray
    scarp: dict[str, np.ndarray] = dc_field(default_factory=dict)
    radio: dict[str, np.ndarray] = dc_field(default_factory=dict)
    roads_m: np.ndarray | None = None
    claims_m: np.ndarray | None = None
    springs: np.ndarray | None = None          # (n, 3): row, col, temperature C (NaN if unknown)
    vents: np.ndarray | None = None            # (n, 2): row, col
    notes: dict[str, Any] = dc_field(default_factory=dict)


def _first_existing(cands: list[Path]) -> Path | None:
    for c in cands:
        if c.exists():
            return c
    return None


def load_inputs() -> Inputs:
    import csv

    with rasterio.open(REPO / "data/grid/sample_submission.tif") as ds:
        ss = ds.read(1)
    footprint = np.isfinite(ss)
    with rasterio.open(REPO / "data/grid/labels.tif") as ds:
        lab = ds.read(1)
    labels = (lab == 1) & footprint

    inp = Inputs(footprint=footprint, labels=labels)

    scarp_path = _first_existing([INPUTS / "lidar_scarp_features_u8.tif",
                                  MIRROR / "lidar_scarp_features_u8.tif"])
    if scarp_path is None:
        raise FileNotFoundError("lidar_scarp_features_u8.tif missing from both input locations")
    raw, info = _read_multi(scarp_path)
    inp.notes["scarp"] = info
    for i, name in enumerate(SCARP_BANDS):
        xmax, kind = SCARP_QUANT[name]
        inp.scarp[name] = _decode_scarp(raw[i], xmax, kind)
    valid = raw[SCARP_BANDS.index("valid")] > 0
    inp.scarp["valid"] = valid.astype(np.float32)

    rad_path = _first_existing([INPUTS / "geodawn_rad_u8.tif", MIRROR / "geodawn_rad_u8.tif"])
    ext_path = _first_existing([INPUTS / "geodawn_extensions_u8.tif",
                                MIRROR / "geodawn_extensions_u8.tif"])
    if rad_path is not None:
        raw, info = _read_multi(rad_path)
        inp.notes["geodawn_rad"] = info
        for i, name in enumerate(RADIOMETRIC_BANDS):
            inp.radio[name] = _decode_linear_rank(raw[i])
    if ext_path is not None:
        raw, info = _read_multi(ext_path)
        inp.notes["geodawn_extensions"] = info
        for i, name in enumerate(EXTENSION_BANDS):
            inp.radio[name] = _decode_linear_rank(raw[i])

    road_path = AUDIT / "tiger_road_distance_m.tif"
    if road_path.exists():
        with rasterio.open(road_path) as ds:
            inp.roads_m = ds.read(1)
        inp.notes["roads"] = {"path": str(road_path), "units": "metres", "nodata": "NaN"}
    claim_path = AUDIT / "blm_closed_claim_distance_m.tif"
    if claim_path.exists():
        with rasterio.open(claim_path) as ds:
            inp.claims_m = ds.read(1)
        inp.notes["claims"] = {"path": str(claim_path), "units": "metres", "nodata": "NaN"}

    ws = _first_existing([MIRROR / "gdr_wellspring_in_footprint.csv",
                          EXT / "gdr_wellspring_in_footprint.csv"])
    if ws is not None:
        rows = []
        with open(ws, newline="") as fh:
            for rec in csv.DictReader(fh):
                try:
                    r, c = int(rec["row"]), int(rec["col"])
                except (KeyError, ValueError):
                    continue
                def num(key):
                    try:
                        v = float(rec.get(key) or "nan")
                        return v if np.isfinite(v) else np.nan
                    except (TypeError, ValueError):
                        return np.nan
                rows.append((r, c, num("temp_c"), rec.get("thermalclass") or ""))
        hot = [(r, c, t) for r, c, t, cls in rows if str(cls).strip().lower() == "hot"]
        if not hot:
            hot = [(r, c, t) for r, c, t, cls in rows if np.isfinite(t) and t >= 45.0]
        inp.springs = np.asarray(hot, dtype=np.float64).reshape(-1, 3) if hot else np.zeros((0, 3))
        inp.notes["wellsprings"] = {"path": str(ws), "records": len(rows), "hot_records": len(hot)}
    vt = _first_existing([MIRROR / "gdr_volcanic_vents_in_footprint.csv"])
    if vt is not None:
        rows = []
        with open(vt, newline="") as fh:
            for rec in csv.DictReader(fh):
                try:
                    rows.append((int(rec["row"]), int(rec["col"])))
                except (KeyError, ValueError):
                    continue
        inp.vents = np.asarray(rows, dtype=np.float64).reshape(-1, 2)
        inp.notes["vents"] = {"path": str(vt), "records": len(rows)}
    return inp


def catalogue_distance_px(labels: np.ndarray) -> np.ndarray:
    """Distance in pixels from every cell to the nearest provided-catalogue trace cell."""
    return ndimage.distance_transform_edt(~labels).astype(np.float32)




def masked_filter(image: np.ndarray, valid: np.ndarray, sigma: float) -> np.ndarray:
    """Gaussian smoothing that *ignores* invalid cells instead of treating them as zero.

    ``gems51.structfield.structure_tensor`` smooths ``nan_to_num(layer)`` directly.  At the
    boundary between data and no-data that is a step edge, and a step edge is exactly what a
    structure tensor detects, so the resulting lineament field rings along the entire footprint
    outline.  Normalised convolution (smooth the data, smooth the mask, divide) removes the
    artifact and leaves the physical edges.
    """
    img = np.where(valid, np.nan_to_num(image, nan=0.0, posinf=0.0, neginf=0.0), 0.0).astype(np.float32)
    num = ndimage.gaussian_filter(img, sigma)
    den = ndimage.gaussian_filter(valid.astype(np.float32), sigma)
    out = np.where(den > 0.30, num / np.maximum(den, 1e-6), 0.0)
    return out.astype(np.float32)


def layer_lineament_masked(layer: np.ndarray, valid: np.ndarray,
                           scales: tuple[float, ...] = (2.0, 5.0, 10.0),
                           coherence_sigma: float = 3.0) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Multi-scale structure-tensor lineament field with mask-aware smoothing.

    Returns (normalised strength, azimuth of the lineament, coherence), all float32.
    """
    best = np.zeros(layer.shape, dtype=np.float32)
    best_angle = np.zeros_like(best)
    best_coh = np.zeros_like(best)
    for sigma in scales:
        smooth = masked_filter(layer, valid, sigma)
        gy, gx = np.gradient(smooth)
        gx = gx.astype(np.float32); gy = gy.astype(np.float32)
        jxx = masked_filter(gx * gx, valid, coherence_sigma)
        jyy = masked_filter(gy * gy, valid, coherence_sigma)
        jxy = masked_filter(gx * gy, valid, coherence_sigma)
        trace = jxx + jyy
        coherence = np.sqrt(np.maximum((jxx - jyy) ** 2 + 4.0 * jxy ** 2, 0.0)) / (trace + 1e-9)
        strength = (np.sqrt(np.maximum(trace, 0.0)) * coherence).astype(np.float32)
        angle = (np.arctan2(gy, gx) + np.pi / 2.0).astype(np.float32)
        take = strength > best
        best = np.where(take, strength, best)
        best_angle = np.where(take, angle, best_angle)
        best_coh = np.where(take, coherence, best_coh)
    v = best[valid & np.isfinite(best)]
    hi = float(np.percentile(v, 98.0)) if v.size else 0.0
    hi = hi if hi > 0 else (float(v.max()) if v.size else 1.0)
    return (np.clip(best / max(hi, 1e-9), 0.0, 1.0).astype(np.float32),
            best_angle.astype(np.float32), best_coh.astype(np.float32))


def family_field(layers: dict[str, np.ndarray], names: list[str], valid: np.ndarray,
                 scales: tuple[float, ...] = (2.0, 5.0, 10.0)) -> dict[str, Any]:
    """Per-family multi-scale structure-tensor lineament field (max over member bands)."""
    strength = np.zeros(GRID, dtype=np.float32)
    angle = np.zeros(GRID, dtype=np.float32)
    coherence = np.zeros(GRID, dtype=np.float32)
    used = []
    for name in names:
        if name not in layers:
            continue
        layer = np.where(valid & np.isfinite(layers[name]), layers[name], np.nan)
        if not np.isfinite(layer[valid]).any():
            continue
        s, a, c = layer_lineament_masked(layer, valid, scales)
        take = s > strength
        strength = np.where(take, s, strength)
        angle = np.where(take, a, angle)
        coherence = np.where(take, c, coherence)
        used.append(name)
    return {"strength": strength, "angle": angle, "coherence": coherence, "bands": used}


def _line_means(field: np.ndarray, half_length: int, azimuths: int) -> list[np.ndarray]:
    """Mean of ``field`` along each of ``azimuths`` straight pixel lines through every cell.

    Exact shifted adds (no interpolation).  ``field`` may contain NaN for no-data; the mean is
    taken over the finite samples only, which also repairs the raster-edge truncation because the
    wrapped-in values come from cells that are NaN in the source.
    """
    f = np.where(np.isfinite(field), field, 0.0).astype(np.float32)
    good = np.isfinite(field).astype(np.float32)
    if half_length > 0:                      # roll wraps: kill the outermost sampled ring
        g = half_length
        f[:g] = 0.0; f[-g:] = 0.0; f[:, :g] = 0.0; f[:, -g:] = 0.0
        good[:g] = 0.0; good[-g:] = 0.0; good[:, :g] = 0.0; good[:, -g:] = 0.0
    out = []
    for k in range(azimuths):
        th = np.pi * k / azimuths
        dyv, dxv = np.sin(th), np.cos(th)
        acc = np.zeros_like(f)
        cnt = np.zeros_like(f)
        for t in range(-half_length, half_length + 1):
            sy, sx = int(round(t * dyv)), int(round(t * dxv))
            acc += np.roll(np.roll(f, -sy, axis=0), -sx, axis=1)
            cnt += np.roll(np.roll(good, -sy, axis=0), -sx, axis=1)
        out.append(acc / np.maximum(cnt, 1e-6))
    return out


def line_integral(field: np.ndarray, half_length: int = 6, azimuths: int = 8) -> np.ndarray:
    """Directional "fault-likeness": best straight-line mean minus its own perpendicular mean.

    A real fault is a *line*: the mean response along some azimuth greatly exceeds the mean
    across it.  With ``azimuths`` directions spanning 180 deg, the perpendicular of direction
    ``k`` is direction ``k + azimuths/2``, so the eight along-profiles already contain every
    cross-profile and the filter is a max of paired differences - the same primitive a geologist
    uses when tracing a lineament with a ruler, and the quantity no previous GEMSDOE artifact of
    this family optimises (they take a per-pixel ridge response and stop).
    """
    if azimuths % 2:
        raise ValueError("azimuths must be even so every direction has its perpendicular in the set")
    f = np.nan_to_num(field, nan=0.0).astype(np.float32)
    means = _line_means(f, half_length, azimuths)
    half = azimuths // 2
    score = np.zeros_like(f)
    for k in range(half):
        a, b = means[k], means[k + half]
        np.maximum(score, a - b, out=score)          # either polarity marks the same contact
        np.maximum(score, b - a, out=score)
    return np.clip(score, 0.0, None).astype(np.float32)


def proximity_boost(points: np.ndarray | None, valid: np.ndarray, scale_m: float,
                    cap_m: float, grid_shape=GRID) -> np.ndarray:
    """exp(-d/scale) over a point set, clipped to ``cap_m``; 0 where no point is within cap."""
    if points is None or len(points) == 0:
        return np.zeros(grid_shape, dtype=np.float32)
    out = np.zeros(grid_shape, dtype=np.float32)
    pts = np.asarray(points, dtype=np.float64)
    # rasterise points then distance-transform: exact on a uniform grid and O(N) not O(N*grid)
    seed = np.zeros(grid_shape, dtype=bool)
    r0 = np.clip(np.round(pts[:, 0]).astype(int), 0, grid_shape[0] - 1)
    c0 = np.clip(np.round(pts[:, 1]).astype(int), 0, grid_shape[1] - 1)
    seed[r0, c0] = True
    if not seed.any():
        return out
    d = ndimage.distance_transform_edt(~seed) * PIXEL_M
    near = d <= cap_m
    out[near] = np.exp(-d[near] / scale_m).astype(np.float32)
    return np.where(valid, out, 0.0).astype(np.float32)


def suppression(dist_m: np.ndarray | None, valid: np.ndarray, inner_m: float,
                outer_m: float) -> np.ndarray:
    """Multiplicative factor in [0,1]: 0 inside ``inner_m`` of a confounder, 1 beyond ``outer_m``.

    Road cuts, aggregate pits and closed mineral claims are the standard non-tectonic sources of
    linear topographic fabric in this part of the Basin and Range.  Treating them as a *cost*
    multiplier (rather than a model feature, as sibling repository GEMSDOE24 tested and rejected)
    removes candidate dots before the metric ever sees them.
    """
    if dist_m is None:
        return np.ones(valid.shape, dtype=np.float32)
    d = np.where(np.isfinite(dist_m), dist_m, 1e9)
    ramp = np.clip((d - inner_m) / max(outer_m - inner_m, 1e-6), 0.0, 1.0)
    return np.where(valid, 0.25 + 0.75 * ramp, 1.0).astype(np.float32)


def build_field(inp: Inputs, *, buffer_px: float = 2.0, weights=(0.75, 0.55),
                thermal_scale_m: float = 800.0, thermal_cap_m: float = 2500.0,
                use_line_integral: bool = True, use_thermal: bool = True,
                use_confounders: bool = True, edge_guard_px: float = 6.0) -> dict[str, Any]:
    """Assemble the belief field and every component of it, with the domain mask.

    ``edge_guard_px`` drops the outermost cells of the data footprint: no filter response there can
    be distinguished from the data-boundary artifact described in :func:`masked_filter`.
    """
    from .gridio import edge_distance_px
    valid = inp.footprint & (edge_distance_px() > edge_guard_px)
    scarp_valid = valid & (inp.scarp["valid"] > 0)
    fam_s = family_field(inp.scarp, SCARP_FAMILY, scarp_valid)
    fam_r = family_field(inp.radio, RADIO_FAMILY, valid)

    def norm(a: np.ndarray, m: np.ndarray) -> np.ndarray:
        v = a[m & np.isfinite(a)]
        if v.size == 0:
            return np.zeros_like(a)
        hi = float(np.percentile(v, 99.0)) or float(v.max())
        return np.clip(a / max(hi, 1e-9), 0.0, 1.0).astype(np.float32)

    s_n = norm(np.nan_to_num(fam_s["strength"] * (0.5 + 0.5 * fam_s["coherence"])), scarp_valid)
    detail_edge = {"edge_guard_px": edge_guard_px,
                   "footprint_px": int(inp.footprint.sum()), "guarded_px": int(valid.sum())}
    r_n = norm(np.nan_to_num(fam_r["strength"] * (0.5 + 0.5 * fam_r["coherence"])), valid)
    base = weights[0] * s_n + weights[1] * r_n
    base = np.clip(base / max(float(np.percentile(base[valid], 99.9)), 1e-9), 0.0, 1.0)

    detail: dict[str, Any] = {"edge_guard": detail_edge,
                              "scarp_bands": fam_s["bands"], "radio_bands": fam_r["bands"],
                              "scarp_valid_fraction": float(scarp_valid.sum() / max(valid.sum(), 1))}
    combo = base.copy()
    if use_line_integral:
        # line-likeness on the *coherently oriented* response, so blobs are punished
        li = line_integral(np.where(scarp_valid, fam_s["strength"] * fam_s["coherence"], np.nan),
                           half_length=6)
        li_n = norm(li, scarp_valid)
        detail["line_integral_p99"] = float(np.percentile(li_n[valid], 99.0))
        combo = 0.70 * base + 0.30 * li_n
        combo = np.clip(combo / max(float(np.percentile(combo[valid], 99.9)), 1e-9), 0.0, 1.0)
        detail["line_integral_weight"] = 0.30
    if use_thermal and inp.springs is not None and len(inp.springs):
        thr = proximity_boost(inp.springs[:, :2], valid, thermal_scale_m, thermal_cap_m)
        vent = proximity_boost(inp.vents, valid, thermal_scale_m, thermal_cap_m) \
            if inp.vents is not None and len(inp.vents) else np.zeros_like(thr)
        hot = float(np.nanmedian(inp.springs[:, 2])) if np.isfinite(inp.springs[:, 2]).any() else float("nan")
        detail["thermal"] = {"n_hot_springs": int(len(inp.springs)),
                             "median_temp_c": hot, "scale_m": thermal_scale_m, "cap_m": thermal_cap_m,
                             "cells_nonzero": int((thr > 0).sum()), "vent_cells": int((vent > 0).sum())}
        combo = np.clip(combo * (1.0 + 0.35 * np.maximum(thr, vent)), 0.0, 1.0)
    if use_confounders:
        sup = suppression(inp.roads_m, valid, 100.0, 500.0) * suppression(inp.claims_m, valid, 200.0, 900.0)
        detail["suppression"] = {"cells_below_half": int((sup < 0.63).sum()),
                                 "road_inner_m": 100.0, "road_outer_m": 500.0,
                                 "claim_inner_m": 200.0, "claim_outer_m": 900.0}
        combo = np.clip(combo * sup, 0.0, 1.0)

    dist = catalogue_distance_px(inp.labels)
    domain = valid & (dist > buffer_px)
    belief = np.where(domain, combo, 0.0).astype(np.float32)
    detail["domain_cells"] = int(domain.sum())
    detail["domain_fraction_of_footprint"] = float(domain.sum() / max(valid.sum(), 1))
    return {"belief": belief, "domain": domain, "catalogue_distance_px": dist,
            "scarp": s_n, "radiometric": r_n, "base": base, "details": detail}


DOMAIN = "footprint & catalogue_distance_px > buffer_px"
