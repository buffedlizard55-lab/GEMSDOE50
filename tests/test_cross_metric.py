"""Two independent implementations of the organiser's metric must agree.

``gems50.metric.score`` (the sibling session's implementation, the one the merged
pipeline builds with) and ``gems50.dti.dti_parts`` (this session's implementation, used
by the seismicity pipeline and its audit) were written independently from the published
equations.  If they ever disagree, one of them is wrong and no shipped number can be
trusted, so the agreement is asserted here rather than assumed.
"""

from __future__ import annotations

import numpy as np
import pytest

from gems50 import dti, metric


def _case(seed: int, shape=(37, 41)) -> tuple[np.ndarray, np.ndarray]:
    rng = np.random.default_rng(seed)
    truth = rng.random(shape) < 0.02
    truth[3, 3] = True
    pred = np.zeros(shape, dtype=np.float32)
    n = int(rng.integers(4, 30))
    pred[rng.integers(0, shape[0], n), rng.integers(0, shape[1], n)] = rng.random(n)
    return pred, truth


@pytest.mark.parametrize("seed", [1, 2, 3, 4, 5])
def test_scores_agree(seed):
    pred, truth = _case(seed)
    mine = dti.dti_parts(pred, truth)
    theirs = metric.score(pred, truth)
    assert mine.value == pytest.approx(float(theirs["dti"]), rel=1e-6, abs=1e-9)


def test_agreement_on_the_real_grids():
    """The same check on the real catalogue and the shipped submission, if present."""
    from pathlib import Path

    import rasterio

    from gems50 import grid_io

    tif = Path(__file__).resolve().parents[1] / "docs" / "downloads" / "gemsdoe50-seis-ridge-v1.tif"
    if not tif.exists():
        pytest.skip("shipped submission not present")
    with rasterio.open(tif) as src:
        pred = src.read(1)
    pred = np.nan_to_num(pred).astype(np.float32)
    truth = grid_io.load_labels()
    assert dti.dti_parts(pred, truth).value == pytest.approx(float(metric.score(pred, truth)["dti"]), rel=1e-6, abs=1e-9)
