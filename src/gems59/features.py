"""Feature assembly for the H57 candidate, on the official competition grid.

Every raster used here is georeferenced identically to
``data/grid/sample_submission.tif`` (EPSG:32611, 100 m, transform
(100, 0, 243350, 0, -100, 4508550), 3292 x 3730).  That identity was asserted at
load time by :func:`assert_grid`, not assumed.

Provenance of each source is recorded in ``data/external/sources_h57.json`` and in
the report written by ``scripts/build_h57.py``.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import rasterio

GRID = {
    "crs": "EPSG:32611",
    "width": 3292,
    "height": 3730,
    "transform": (100.0, 0.0, 243350.0, 0.0, -100.0, 4508550.0),
}

# Official feature-stack band descriptions, read from the file's own band tags
# (see tests/test_h59.py::test_official_band_descriptions_match_contract).
OFFICIAL_BANDS = 19


def assert_grid(path: Path | str, width: int = GRID["width"], height: int = GRID["height"]) -> None:
    """Raise unless the raster is exactly the competition grid."""
    with rasterio.open(path) as src:
        if (src.width, src.height) != (width, height):
            raise ValueError(f"{path}: shape {(src.width, src.height)} != {(width, height)}")
        if src.crs is None or src.crs.to_string() != GRID["crs"]:
            raise ValueError(f"{path}: crs {src.crs} != {GRID['crs']}")
        tf = tuple(round(v, 6) for v in tuple(src.transform)[:6])
        if tf != GRID["transform"]:
            raise ValueError(f"{path}: transform {tf} != {GRID['transform']}")


def read_bands(path: Path | str, bands: list[int] | None = None) -> np.ndarray:
    """Read selected 1-based bands as a float32 (n, H, W) array, NaN-passthrough."""
    with rasterio.open(path) as src:
        idx = bands if bands is not None else list(range(1, src.count + 1))
        arr = src.read(idx).astype(np.float32)
        nod = src.nodata
    if nod is not None:
        arr[arr == np.float32(nod)] = np.nan
    # The official stack uses -3.4028235e38 as its nodata sentinel; the reference
    # notebook maps values < -1e38 to NaN (cell 5 of the reference solution).
    arr[arr < -1e37] = np.nan
    return arr


def grad_magnitude(a: np.ndarray) -> np.ndarray:
    """Sobel gradient magnitude, NaN-aware via edge padding."""
    from scipy import ndimage

    filled = np.nan_to_num(a, nan=0.0)
    gy = ndimage.sobel(filled, axis=0, mode="nearest")
    gx = ndimage.sobel(filled, axis=1, mode="nearest")
    m = np.hypot(gx, gy)
    m[np.isnan(a)] = np.nan
    return m.astype(np.float32)


def structure_tensor_saliency(a: np.ndarray, sigma: float) -> np.ndarray:
    """Multiscale line/edge saliency of a scalar field.

    Uses the eigenvalues of the Gaussian-windowed structure tensor at scale
    ``sigma`` (pixels).  A linear feature has one dominant gradient direction, so
    the "coherence" ``(l1 - l2) / (l1 + l2 + eps)`` is large exactly on
    curvilinear features, and is invariant to the field's absolute amplitude.
    """
    from scipy import ndimage

    filled = np.nan_to_num(a, nan=0.0)
    gy = ndimage.gaussian_filter(filled, sigma, order=(1, 0), mode="nearest")
    gx = ndimage.gaussian_filter(filled, sigma, order=(0, 1), mode="nearest")
    jxx = ndimage.gaussian_filter(gx * gx, sigma, mode="nearest")
    jyy = ndimage.gaussian_filter(gy * gy, sigma, mode="nearest")
    jxy = ndimage.gaussian_filter(gx * gy, sigma, mode="nearest")
    tr = jxx + jyy
    det = jxx * jyy - jxy * jxy
    disc = np.sqrt(np.maximum(tr * tr / 4.0 - det, 0.0))
    l1 = tr / 2.0 + disc
    l2 = tr / 2.0 - disc
    coh = (l1 - l2) / (l1 + l2 + 1e-12)
    out = (coh * np.sqrt(np.maximum(l1, 0.0))).astype(np.float32)
    out[np.isnan(a)] = np.nan
    return out


def rank_normalise(a: np.ndarray, mask: np.ndarray) -> np.ndarray:
    """Map the finite values inside ``mask`` to [0, 1] by rank; NaN elsewhere.

    Non-finite inputs are excluded from the ranking and stay NaN in the output.
    (An earlier revision ranked NaN together with real values, which put the
    nodata pixels at the *top* of the ranking; that defect is fixed here and is
    recorded in the deviation log.)
    """
    out = np.full(a.shape, np.nan, dtype=np.float32)
    sel = mask & np.isfinite(a)
    n = int(sel.sum())
    if n == 0:
        return out
    v = a[sel]
    order = np.argsort(np.argsort(v, kind="stable"), kind="stable").astype(np.float32)
    out[sel] = order / max(n - 1, 1)
    return out


def block_mean90(a: np.ndarray, mask: np.ndarray, block: int = 10) -> np.ndarray:
    """Coarse 10 x 10 (1 km) block mean, restricted to ``mask``; NaN-aware."""
    h, w = a.shape
    hh, ww = (h // block) * block, (w // block) * block
    sub = np.where(mask[:hh, :ww], a[:hh, :ww], np.nan)
    with np.errstate(invalid="ignore"):
        m = np.nanmean(sub.reshape(hh // block, block, ww // block, block), axis=(1, 3))
    return m.astype(np.float32)
