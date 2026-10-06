"""Verification of the metric against the published equations, by three independent routes.

Route 1: the published equations transcribed directly, O(|G| * N) -- ``metric.brute_force``.
Route 2: the exact vectorised implementation -- ``metric.dti_parts``.
Route 3: the closed-form algebra -- ``metric.algebra_rhs``.
Plus the structural facts asserted by the organiser's own files (grid.py docstring).
"""

from __future__ import annotations

import numpy as np
import pytest

from gems50 import grid, metric


def _random_case(seed: int, shape=(41, 47), density=0.01, offsets=3):
    rng = np.random.default_rng(seed)
    truth = rng.random(shape) < density
    if not truth.any():
        truth[5, 5] = True
    pred = np.zeros(shape, dtype=np.float32)
    n = rng.integers(5, 40)
    rows = rng.integers(0, shape[0], n)
    cols = rng.integers(0, shape[1], n)
    vals = rng.choice([1.0, 0.5, 0.25, 0.9], size=n)
    pred[rows, cols] = vals
    return pred, truth


@pytest.mark.parametrize("seed", range(8))
def test_exact_vs_brute_force(seed):
    pred, truth = _random_case(seed)
    a = metric.dti_parts(pred, truth)
    b = metric.brute_force(pred, truth)
    # float32 accumulation in the vectorised route; agreement to 1e-6 relative
    assert a.tpw == pytest.approx(b["tpw"], rel=1e-6, abs=1e-6)
    assert a.fpw == pytest.approx(b["fpw"], rel=1e-6, abs=1e-6)
    assert a.fnw == pytest.approx(b["fnw"], rel=1e-6, abs=1e-6)
    assert a.value == pytest.approx(b["dti"], rel=1e-6)


@pytest.mark.parametrize("seed", range(8))
def test_identity_and_algebra(seed):
    pred, truth = _random_case(seed)
    r = metric.dti_parts(pred, truth)
    # identity: FNw = |G| - TPw
    assert r.fnw == pytest.approx(r.truth_cells - r.tpw, abs=1e-9)
    # algebra: DTI = T / (0.2 (T + S - M) + 0.8 |G|)
    closed = metric.algebra_rhs(r.tpw, r.mass, r.best_cover, r.truth_cells)
    assert r.value == pytest.approx(closed, rel=1e-9)
    # and the algebra's mass identity S = M + FPw
    assert r.mass == pytest.approx(r.best_cover + r.fpw, abs=1e-9)


def test_no_wrap_around():
    """A prediction at the left edge must not score against truth at the right edge."""
    truth = np.zeros((20, 40), dtype=bool)
    truth[10, 39] = True
    pred = np.zeros((20, 40), dtype=np.float32)
    pred[10, 0] = 1.0
    r = metric.dti_parts(pred, truth)
    assert r.tpw == 0.0
    assert r.fpw == pytest.approx(1.0)


def test_perfect_prediction_scores_one():
    truth = np.zeros((30, 30), dtype=bool)
    truth[5:25, 5] = True
    pred = truth.astype(np.float32)
    r = metric.dti_parts(pred, truth)
    assert r.value == pytest.approx(1.0)
    assert r.tpw == pytest.approx(r.truth_cells)


def test_empty_prediction_is_zero():
    truth = np.zeros((10, 10), dtype=bool)
    truth[2, 2] = True
    pred = np.zeros((10, 10), dtype=np.float32)
    r = metric.dti_parts(pred, truth)
    assert r.value == 0.0
    assert r.fnw == 1.0


def test_marginal_rule_is_exact():
    """A new dot that becomes the best cover of its own truth cell pays iff w > 0.2*DTI.

    Setup: two distant truth cells; the base prediction already covers one of them
    perfectly.  A second dot near the other cell changes TPw by w (it becomes that cell's
    best cover), M by w and S by 1, so the published metric must improve exactly when
    ``w > 0.2 * DTI_base``.  The test asserts that this holds for every distance in and
    just outside the kernel support.
    """
    truth = np.zeros((9, 60), dtype=bool)
    truth[4, 10] = True
    truth[4, 50] = True
    base_pred = np.zeros((9, 60), dtype=np.float32)
    base_pred[4, 50] = 1.0  # covers the far cell perfectly
    base = metric.dti_parts(base_pred, truth)
    assert base.value == pytest.approx(1.0 / (0.2 * (1 + 1 - 1) + 0.8 * 2))

    for dist in range(1, 6):
        pred = base_pred.copy()
        pred[4, 10 + dist] = 1.0
        new = metric.dti_parts(pred, truth)
        w = max(1.0 - dist / 3.0, 0.0)
        should_improve = w > metric.credit_bar(base.value)
        assert (new.value > base.value) == should_improve, (
            f"dist={dist} w={w:.3f} bar={metric.credit_bar(base.value):.4f} "
            f"base={base.value:.4f} new={new.value:.4f}")

    # the exact multi-truth-cell criterion agrees with the numbers above
    for dist in range(1, 6):
        w = max(1.0 - dist / 3.0, 0.0)
        assert metric.marginal_condition(w, delta_t=w, current_dti=base.value) == (
            w > metric.credit_bar(base.value))


def test_organiser_sample_is_a_legal_submission():
    """The organiser's own template must satisfy the format the site promises to meet."""
    import rasterio

    with rasterio.open(grid.SAMPLE_SUBMISSION) as src:
        a = src.read(1)
        assert src.count == 1
        assert src.dtypes[0] == "float32"
        assert str(src.crs) == "EPSG:32611"
        assert (src.width, src.height) == (3292, 3730)
        assert float(src.transform.a) == 100.0
    finite = np.isfinite(a)
    assert finite.sum() == 5_167_373
    assert a[finite].min() >= 0.0 and a[finite].max() <= 1.0
