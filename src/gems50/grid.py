"""The competition grid, taken from the organiser's own sample submission.

Facts established by reading the organiser files (not assumed):

===============================  =============================================
item                             value
===============================  =============================================
CRS                              EPSG:32611 (UTM 11N)
cell size                        100 m
width x height                   3292 x 3730
origin (x, y)                    243350.0, 4508550.0
bounds                           x 243350..572550, y 4135550..4508550
dtype                            float32
nodata tag on sample             nan
valid-mask cells (finite)        5,167,373
invalid cells (nan)              7,111,787
sample values                    0.0 and 1.0 only
cells equal to 1.0               60,988
===============================  =============================================

The 60,988 cells equal to 1.0 in the organiser's ``sample_submission.tif`` are exactly
the 60,988 cells equal to 1 in ``labels.tif``: the sample submission is the *existing
fault catalogue* rasterised, with the survey footprint set to nan.  This is used here
only as a format template and as a validity mask; it is never treated as truth for a
hidden set, because the competition states the hidden set is *not* in that catalogue.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np
import rasterio

REPO = Path(__file__).resolve().parents[2]
GRID_DIR = REPO / "data" / "grid"
SAMPLE_SUBMISSION = GRID_DIR / "sample_submission.tif"
LABELS = GRID_DIR / "labels.tif"

#: Published by the organiser (page 967): the triangular kernel support.
RANGE_M = 300.0
CELL_M = 100.0

#: Kernel half-width in cells; ``RANGE_M / CELL_M`` = 3.
R_PX = int(round(RANGE_M / CELL_M))


@dataclass(frozen=True)
class Grid:
    """Geometry of the competition raster."""

    width: int
    height: int
    transform: tuple
    crs: str

    @property
    def shape(self) -> tuple[int, int]:
        return (self.height, self.width)

    @property
    def bounds(self) -> tuple[float, float, float, float]:
        left, top = self.transform[2], self.transform[5]
        return (
            left,
            top - self.height * self.transform[4],
            left + self.width * self.transform[0],
            top,
        )

    def col_row(self, x: np.ndarray, y: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
        """Projected metres -> (col, row) integer arrays (top-left corner convention)."""
        a, _, c, _, e, f = self.transform
        col = np.floor((np.asarray(x) - c) / a).astype(np.int64)
        row = np.floor((np.asarray(y) - f) / e).astype(np.int64)
        return col, row

    def xy(self, col: np.ndarray, row: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
        """(col, row) -> projected metres at cell centres."""
        a, _, c, _, e, f = self.transform
        return c + (np.asarray(col) + 0.5) * a, f + (np.asarray(row) + 0.5) * e


def load_grid() -> Grid:
    """Read the grid geometry from the organiser's sample submission."""
    with rasterio.open(SAMPLE_SUBMISSION) as src:
        return Grid(
            width=src.width,
            height=src.height,
            transform=tuple(src.transform)[:6],
            crs=src.crs.to_string(),
        )


def load_valid_mask() -> np.ndarray:
    """Boolean raster: True where the organiser's template is finite (inside the survey).

    Also asserts the structural facts listed in the module docstring so that a changed
    template cannot silently change the pipeline.
    """
    with rasterio.open(SAMPLE_SUBMISSION) as src:
        a = src.read(1)
        assert src.count == 1, "template is not single band"
        assert src.crs.to_string() == "EPSG:32611", src.crs
        assert (src.width, src.height) == (3292, 3730), (src.width, src.height)
        assert src.dtypes[0] == "float32", src.dtypes
    return np.isfinite(a)


def load_labels() -> np.ndarray:
    """The organiser's public fault catalogue (1 = mapped fault, 0 = none, -1 = nan mask)."""
    with rasterio.open(LABELS) as src:
        lab = src.read(1)
    out = np.zeros(lab.shape, dtype=bool)
    out[lab == 1] = True
    return out
