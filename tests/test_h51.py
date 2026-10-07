"""Hand-computable checks for the H51 kernels, packer, and metric identity.

Every assertion here is either arithmetic that can be done on paper or an invariant that the
shipped emission pipeline depends on (grid constants, maximum-vs-sum credit semantics, the
minimum-separation promise, and the exact ``TP_w + FN_w = truth mass`` identity).
"""

import numpy as np
import pytest

from gemsdoe50 import h51


def test_grid_constants_match_the_competition_raster():
    assert h51.GRID_SHAPE == (3730, 3292)
    assert h51.GRID_CRS == "EPSG:32611"
    assert tuple(h51.GRID_TRANSFORM) == (100.0, 0.0, 243350.0, 0.0, -100.0, 4508550.0)
    assert h51.RADIUS_M == 300.0
    assert h51.PIXEL_M == 100.0


def test_kernel_from_distance_is_the_published_triangle():
    got = h51.kernel_from_distance(np.array([0.0, 1.0, 2.0, 3.0, 4.0]))
    assert got[0] == pytest.approx(1.0)
    assert got[1] == pytest.approx(2 / 3)
    assert got[2] == pytest.approx(1 / 3)
    assert got[3] == pytest.approx(0.0)
    assert got[4] == pytest.approx(0.0)


def test_credit_field_is_a_maximum_and_support_field_is_a_sum():
    dots = np.zeros((11, 11), bool)
    dots[5, 4] = True
    dots[5, 6] = True
    credit = h51.credit_field(dots)
    support = h51.support_field(dots)
    # the midpoint is 1 px from each dot: max kernel = 2/3, summed kernel mass = 4/3
    assert credit[5, 5] == pytest.approx(2 / 3)
    assert support[5, 5] == pytest.approx(4 / 3)
    # 3 px from the nearest dot and 5 px from the other: both terms vanish
    assert credit[5, 1] == pytest.approx(0.0)
    assert support[5, 1] == pytest.approx(0.0)
    assert np.all(support + 1e-9 >= credit)


def test_place_dots_ordered_prefix_is_the_place_dots_set():
    rng = np.random.default_rng(7)
    belief = rng.random((40, 40)).astype(np.float32)
    allowed = np.ones((40, 40), bool)
    params = h51.EmissionParams(spacing_px=2.8, budget=25, belief_floor=0.0, pool_factor=8)
    order = h51.place_dots_ordered(belief, allowed, params)
    dots = h51.place_dots(belief, allowed, params)
    assert order.size == 25
    assert np.array_equal(np.sort(order), np.flatnonzero(dots.ravel()))


def test_place_dots_honours_minimum_separation_and_budget():
    rng = np.random.default_rng(11)
    belief = rng.random((60, 60)).astype(np.float32)
    spacing = 2.8
    dots = h51.place_dots(belief, np.ones((60, 60), bool), h51.EmissionParams(
        spacing_px=spacing, budget=40, belief_floor=0.0, pool_factor=20))
    rows, cols = np.nonzero(dots)
    assert rows.size == 40
    delta = np.hypot(rows[:, None] - rows[None, :], cols[:, None] - cols[None, :])
    assert delta[delta > 0].min() + 1e-9 >= spacing


def test_place_dots_never_leaves_the_allowed_domain():
    allowed = np.zeros((20, 20), bool)
    allowed[5:10, 5:10] = True
    dots = h51.place_dots(np.ones((20, 20), np.float32), allowed, h51.EmissionParams(
        spacing_px=2.0, budget=50, belief_floor=0.0, pool_factor=8))
    assert dots.any()
    assert not (dots & ~allowed).any()


def test_belief_floor_stops_placement():
    belief = np.zeros((20, 20), np.float32)
    belief[3, 3] = 1.0
    dots = h51.place_dots(belief, np.ones((20, 20), bool), h51.EmissionParams(
        spacing_px=2.0, budget=10, belief_floor=0.5, pool_factor=8))
    assert dots.sum() == 1
    assert dots[3, 3]


def test_normalize01_is_bounded_and_flat_input_maps_to_zero():
    out = h51.normalize01(np.array([[0.0, 1.0], [2.0, 3.0]]))
    assert out.min() == 0.0
    assert out.max() == 1.0
    assert np.allclose(h51.normalize01(np.full((2, 2), 5.0)), 0.0)


def test_score_components_satisfy_the_exact_metric_identity():
    truth = np.zeros((30, 30), bool)
    truth[10, 5:15] = True
    pred = np.zeros((30, 30), bool)
    pred[11, 5:15] = True
    mask = np.ones((30, 30), bool)
    comp = h51.score_components(truth, pred, mask)
    truth_mass = float(truth.sum())
    # TP_w + FN_w = |truth| exactly (the same max appears in both sums)
    assert comp["tp"] + comp["fn"] == pytest.approx(truth_mass)
    # the closed-form predictor and the component-wise scoring agree
    assert h51.predicted_score(comp["tp"], comp["fp"], truth_mass) == pytest.approx(comp["dti"])


def test_distance_to_mask_is_zero_on_the_mask():
    m = np.zeros((9, 9), bool)
    m[4, 4] = True
    d = h51.distance_to_mask(m)
    assert d[4, 4] == 0.0
    assert d[4, 5] == pytest.approx(1.0)
    assert d[0, 0] == pytest.approx(np.hypot(4, 4))
