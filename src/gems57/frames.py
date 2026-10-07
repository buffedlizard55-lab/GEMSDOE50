"""Frozen validation frames and spatial macrofolds for the H57 candidate.

Two independent instruments are defined here.  Both are frozen before any model is
trained, and both are used unchanged for every reported number.

Frame ``L`` — label-recovery frame
    Ground truth is the supplied catalogue itself (``data/grid/labels.tif``).  A
    model is trained on three of the four macrofolds and scored on the fourth, so
    no pixel of the scored block is ever seen during fitting.  This measures
    whether the feature stack can locate faults at all, and how far the skill
    transfers across space.

Frame ``S`` — off-catalogue frame
    Ground truth is the USGS State Geologic Map Compilation (SGMC) fault pixels
    that lie inside the supplied study footprint and **more than 300 m from every
    supplied catalogue pixel**.  This is the closest available public stand-in for
    the competition's target, which the organizer defines as faults that are *not*
    in the public USGS database.  It is a proxy: SGMC is dominated by older
    bedrock faults, while the hidden target is young surface faulting.  The proxy
    gap is measured, not assumed (see ``docs/research/h57-proxy-gap.md``).

Macrofolds are a 2 x 2 split of the study footprint by its own bounding box, so
every fold is spatially contiguous and the folds are disjoint.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np

N_FOLDS = 4
MACROFOLD_NAMES = ["NW", "NE", "SW", "SE"]
CATALOGUE_BUFFER_M = 300.0
CATALOGUE_BUFFER_PX = 3


def load_labels(path: Path | str = "data/grid/labels.tif") -> tuple[np.ndarray, np.ndarray]:
    import rasterio

    with rasterio.open(path) as src:
        arr = src.read(1)
    return arr, arr != -1


def load_sgmc_offcatalogue(
    path: Path | str = "data/external/derived_sgmc_faults_100m_u8.tif",
    labels_path: Path | str = "data/grid/labels.tif",
    *,
    buffer_px: int = CATALOGUE_BUFFER_PX,
) -> np.ndarray:
    """SGMC fault pixels inside the footprint and > ``buffer_px`` from the catalogue."""
    import rasterio
    from scipy import ndimage

    with rasterio.open(path) as src:
        sgmc = src.read(1)
        if src.nodata is not None:
            sgmc = np.where(sgmc == src.nodata, 0, sgmc)
    labels, footprint = load_labels(labels_path)
    cat = labels == 1
    d = ndimage.distance_transform_edt(~cat)
    return (sgmc > 0) & footprint & (d > buffer_px)


def macrofolds(footprint: np.ndarray, n: int = N_FOLDS) -> tuple[np.ndarray, list[str]]:
    """Return an int8 fold map over the footprint's own bounding box (row-major)."""
    rows = np.where(footprint.any(axis=1))[0]
    cols = np.where(footprint.any(axis=0))[0]
    r0, r1 = int(rows.min()), int(rows.max()) + 1
    c0, c1 = int(cols.min()), int(cols.max()) + 1
    side = int(np.ceil(np.sqrt(n)))
    if side * side != n:
        raise ValueError("only square fold counts are supported")
    fold = np.full(footprint.shape, -1, dtype=np.int8)
    rr = np.linspace(r0, r1, side + 1).astype(int)
    cc = np.linspace(c0, c1, side + 1).astype(int)
    for i in range(side):
        for j in range(side):
            blk = np.s_[rr[i] : rr[i + 1], cc[j] : cc[j + 1]]
            fold[blk] = i * side + j
    fold[~footprint] = -1
    return fold, MACROFOLD_NAMES


def offcatalogue_dti(
    prediction: np.ndarray, truth: np.ndarray, footprint: np.ndarray
) -> float:
    """Official DTI of ``prediction`` against ``truth`` evaluated inside the footprint."""
    from gems57.metric import evaluate

    p = np.where(footprint, np.nan_to_num(prediction, nan=0.0), 0.0)
    return evaluate(p, truth & footprint).dti


def novelty_mask(union_path: Path | str | None = None) -> np.ndarray | None:
    """Optional prior-positive union, used only for the uniqueness gate."""
    if union_path is None:
        return None
    path = Path(union_path)
    if not path.exists():
        return None
    z = np.load(path)
    key = "union" if "union" in z else list(z.keys())[0]
    return z[key].astype(bool)
