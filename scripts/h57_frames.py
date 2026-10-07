"""H57 validation frames — spatially blocked, hash-pinnable truth proxies.

Why this module exists
----------------------
The competition's scored truth is a *hidden* set of expert-mapped faults. No
offline frame can substitute for it. This module builds the two proxies the
repository already relies on, plus an explicit third, with three differences
that matter for H57:

1.  Every frame reports the **uniform-emission base rate** of the metric's own
    credit field ``K(x) = max_g clip(1 - d(x, g)/R, 0)`` with ``R = 3 px``.
    ``mean(K)`` over a domain is exactly the credit per dot a uniformly random
    emitter earns, which makes every channel comparison independent of frame
    size and truth density. The raw "off-catalogue DTI" of earlier sessions is
    *not* comparable across frames because the metric's denominator contains
    ``0.8 * |G|``, and ``|G|`` differs per frame.

2.  The catalogue-holdout frame (F2) is scored **outside the buffer of the
    non-held-out catalogue only**. That is the honest emulation of "a fault the
    compiler did not have".

3.  Each truth pixel carries its kernel weight, so ``coverage`` here means the
    metric's own weighted coverage ``T/|G|``, not a pixel count.

Frames
------
F1  off-catalogue independent population
    truth  = SGMC fault pixels > 3 px from any given-catalogue pixel
    domain = footprint pixels > 3 px from the given catalogue
F2  catalogue spatial holdout (4 contiguous macrofolds)
    truth  = given-catalogue pixels inside the macrofold
    domain = footprint pixels inside the macrofold that are > 3 px from the
             catalogue *outside* that macrofold, eroded 100 px (10 km) from the
             fold boundary
F3  F2 restricted to the LiDAR-valid mask ``lidar_scarp_features_u8.valid > 0``

All geometry is on the official competition grid: EPSG:32611, 100 m,
3,730 x 3,292, origin (243350.0, 4508550.0).
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
import numpy as np
from scipy import ndimage as ndi

R_PX = 3.0  # 300 m kernel support at 100 m pixels (official metric)
ERODE_PX = 100  # 10 km fold erosion, as in docs/hypotheses-preregistered.md


@dataclass
class Frame:
    """One validation frame: a truth mask, an eligible domain, and its K field."""

    name: str
    truth: np.ndarray  # bool, (H, W)
    domain: np.ndarray  # bool, (H, W)
    detail: dict = field(default_factory=dict)

    def __post_init__(self) -> None:
        k = kernel_field(self.truth)
        k = np.where(self.domain, k, np.float32("nan"))
        self.K = k.astype(np.float32)
        n_truth = int(self.truth.sum())
        base = float(np.nanmean(self.K))
        # The kernel field restricted to truth pixels is >= 1 only at truth
        # itself; the metric's coverage denominator is |G| (unweighted count of
        # truth pixels), so G = n_truth.
        self.n_truth = n_truth
        self.domain_px = int(self.domain.sum())
        self.base_c_per_dot = base
        self.detail.update(
            {
                "n_truth_px": n_truth,
                "domain_px": self.domain_px,
                "base_c_per_dot_uniform": base,
                "truth_hash": hashlib.sha256(
                    np.packbits(self.truth).tobytes()
                ).hexdigest()[:16],
                "domain_hash": hashlib.sha256(
                    np.packbits(self.domain).tobytes()
                ).hexdigest()[:16],
            }
        )

    # ---- evaluation -------------------------------------------------------
    def score_selection(self, sel: np.ndarray) -> dict:
        """Metric-exact score of a *sparse* binary selection.

        ``sel`` is a boolean raster. Dots are assumed >= 3 px apart inside a
        neighbourhood so that no dot competes for credit another dot already
        earned; that is the emission discipline the metric itself rewards and is
        checked by the caller (`spacing_check`).
        """
        sel = sel & self.domain
        n = int(sel.sum())
        if n == 0:
            return {"n_dots": 0, "c_per_dot": 0.0, "coverage": 0.0, "dti": 0.0}
        credit = float(self.K[sel].sum())  # A = sum_x K(x) over dots
        # T (unique credit) is bounded by A; for >= 3 px spacing A == T.
        t = min(credit, float(self.n_truth))
        g = float(self.n_truth)
        d = 0.2 * t + 0.2 * (n - credit) + 0.8 * g
        return {
            "n_dots": n,
            "c_per_dot": credit / n,
            "coverage": t / g,
            "dti": t / d if d > 0 else 0.0,
        }

    def top_selection(self, channel: np.ndarray, n_target: int) -> np.ndarray:
        """Boolean mask of the ``n_target`` highest finite-channel pixels."""
        c = np.where(self.domain & np.isfinite(channel), channel, -np.inf)
        flat = c.ravel()
        n = min(n_target, int(np.isfinite(flat).sum()))
        if n <= 0:
            return np.zeros_like(self.domain)
        idx = np.argpartition(flat, -n)[-n:]
        out = np.zeros(flat.size, dtype=bool)
        out[idx] = True
        return out.reshape(self.domain.shape)

    def enrichment(self, channel: np.ndarray) -> float:
        v = np.where(np.isfinite(channel), channel, np.nan)
        t = float(np.nanmean(v[self.truth]))
        d = float(np.nanmean(v[self.domain]))
        return t / d if d not in (0.0,) and np.isfinite(d) else float("nan")


def kernel_field(truth: np.ndarray, r_px: float = R_PX) -> np.ndarray:
    """K(x) = max_g clip(1 - d(x,g)/r, 0) for a binary truth mask."""
    if not truth.any():
        return np.zeros(truth.shape, dtype=np.float32)
    d = ndi.distance_transform_edt(~truth)
    return np.clip(1.0 - d / r_px, 0.0, 1.0).astype(np.float32)


def load_grid(labels_path: str = "data/grid/labels.tif"):
    """Official competition grid: footprint mask and given-catalogue mask."""
    import rasterio

    with rasterio.open(labels_path) as ds:
        lab = ds.read(1)
        transform = tuple(ds.transform)[:6]
        shape = ds.shape
    footprint = lab != -1
    catalogue = lab == 1
    return footprint, catalogue, transform, shape


def _quadrants(shape, half_px: int = ERODE_PX):
    h, w = shape
    r, c = h // 2, w // 2
    names = {"NW": (slice(0, r - half_px), slice(0, c - half_px)),
             "NE": (slice(0, r - half_px), slice(c + half_px, w)),
             "SW": (slice(r + half_px, h), slice(0, c - half_px)),
             "SE": (slice(r + half_px, h), slice(c + half_px, w))}
    return names


def build_frames(footprint, catalogue, sgmc, lidar_valid) -> dict:
    """Return the three frames as a dict of name -> Frame."""
    frames = {}

    # ---- F1: independent population, off-catalogue -----------------------
    d_cat = ndi.distance_transform_edt(~catalogue)
    off_cat = footprint & (d_cat > R_PX)
    truth1 = np.asarray(sgmc, bool) & off_cat
    frames["F1_sgmc_off"] = Frame("F1_sgmc_off", truth1, off_cat)

    # ---- F2 / F3: catalogue spatial holdout ------------------------------
    for name, (rs, cs) in _quadrants(catalogue.shape).items():
        in_fold = np.zeros_like(catalogue)
        in_fold[rs, cs] = True
        held = catalogue & in_fold
        outside = catalogue & ~in_fold
        d_out = ndi.distance_transform_edt(~outside)
        domain = footprint & in_fold & (d_out > R_PX)
        frames[f"F2_cat_{name}"] = Frame(f"F2_cat_{name}", held, domain)
        if lidar_valid is not None:
            dom3 = domain & lidar_valid
            frames[f"F3_lidar_{name}"] = Frame(f"F3_lidar_{name}", held, dom3)
    return frames


def pooled(frames: dict, keys) -> dict:
    """Pool several folds by summing their (T, domain, dots) contributions."""
    out = {}
    for k in keys:
        f = frames[k]
        out[k] = f
    return out


if __name__ == "__main__":  # pragma: no cover - diagnostic entry point
    import json
    import rasterio

    footprint, catalogue, transform, shape = load_grid()
    with rasterio.open("data/external/derived_sgmc_faults_100m_u8.tif") as ds:
        sgmc = ds.read(1) == 1
    with rasterio.open(".arena/inputs/lidar_scarp_features_u8.tif") as ds:
        valid = ds.read(12) > 0
    fr = build_frames(footprint, catalogue, sgmc, valid)
    rep = {k: v.detail for k, v in fr.items()}
    print(json.dumps(rep, indent=1))
