"""Line-by-line verification of the metric implementation.

Every assertion here is hand-computable, or is the worked example printed on the
official competition page.
"""

import numpy as np
import pytest

from gems50 import metric


def test_kernel_matches_published_definition():
    # k(d) = max(1 - d/R, 0), R = 300 m = 3 px
    assert metric.kernel(0.0) == 1.0
    assert metric.kernel(1.0) == pytest.approx(2 / 3)
    assert metric.kernel(3.0) == 0.0
    assert metric.kernel(3.5) == 0.0


def test_official_scoring_example():
    # Problem description, "Scoring example":
    #   TPw = 3.00, FPw = 1.89, FNw = 2.00  ->  DTI = 0.60
    got = metric.tversky_index(3.00, 1.89, 2.00)
    assert got == pytest.approx(3.00 / (3.00 + 0.2 * 1.89 + 0.8 * 2.00), rel=1e-12)
    assert got == pytest.approx(0.60, abs=0.005)


def test_perfect_prediction_is_one():
    truth = np.zeros((20, 20), dtype=bool)
    truth[5, 5] = True
    pred = np.zeros((20, 20))
    pred[5, 5] = 1.0
    r = metric.score(pred, truth)
    assert r["tp_w"] == pytest.approx(1.0)
    assert r["fp_w"] == pytest.approx(0.0)
    assert r["fn_w"] == pytest.approx(0.0)
    assert r["dti"] == pytest.approx(1.0, abs=1e-6)


def test_hand_computed_one_pixel_offset():
    # truth at (10,10); prediction at (10,12) -> d = 2 px -> k = 1/3
    # TPw = 1/3 ; FPw = 1 - 1/3 = 2/3 ; FNw = 1 - 1/3 = 2/3
    # DTI = (1/3) / (1/3 + 0.2*(2/3) + 0.8*(2/3)) = (1/3)/1 = 1/3
    truth = np.zeros((20, 20), dtype=bool)
    truth[10, 10] = True
    pred = np.zeros((20, 20))
    pred[10, 12] = 1.0
    r = metric.score(pred, truth)
    assert r["tp_w"] == pytest.approx(1 / 3)
    assert r["fp_w"] == pytest.approx(2 / 3)
    assert r["fn_w"] == pytest.approx(2 / 3)
    assert r["dti"] == pytest.approx(1 / 3)
    # identity TPw + FNw = |G|
    assert r["tp_plus_fn_minus_g"] == pytest.approx(0.0, abs=1e-9)


def test_distance_beyond_radius_earns_nothing():
    truth = np.zeros((20, 20), dtype=bool)
    truth[5, 5] = True
    pred = np.zeros((20, 20))
    pred[9, 9] = 1.0  # 4 px away in both axes -> > 3 px
    r = metric.score(pred, truth)
    assert r["tp_w"] == pytest.approx(0.0)
    assert r["fp_w"] == pytest.approx(1.0)
    assert r["fn_w"] == pytest.approx(1.0)
    assert r["dti"] == pytest.approx(0.0, abs=1e-8)


def test_graded_prediction_is_dominated_by_its_own_threshold():
    rng = np.random.default_rng(0)
    truth = np.zeros((60, 60), dtype=bool)
    truth[rng.integers(0, 60, 40), rng.integers(0, 60, 40)] = True
    pred = rng.random((60, 60)) * (rng.random((60, 60)) < 0.2) * np.isfinite(1.0)
    base = metric.score(pred, truth)["dti"]
    for lam in (0.25, 0.5, 0.75):
        assert metric.score(pred * lam, truth)["dti"] < base


def test_coverage_inversion_matches_forward_metric():
    # Build a synthetic case with known coverage/FP and check eq. (3) inverts it.
    truth = np.zeros((200, 200), dtype=bool)
    truth[50:150, 50:54] = True          # 400 truth pixels
    g = truth.sum()
    pred = np.zeros((200, 200))
    # predict every 3rd pixel along one column-line of truth -> high coverage, few FPs
    pred[50:150:3, 50] = 1.0
    r = metric.score(pred, truth)
    x = r["tp_w"] / g
    rho = r["fp_w"] / g
    s = r["dti"]
    assert s == pytest.approx(x / (0.2 * x + 0.2 * rho + 0.8), rel=1e-9)
    assert metric.coverage_required(s, rho) == pytest.approx(x, rel=1e-9)


def test_marginal_threshold_values():
    # at s = 0.3195 the bar is 0.2*s = 0.0639 (i.e. a dot must land within 280.8 m)
    assert metric.marginal_threshold(0.3195) == pytest.approx(0.0639, abs=1e-6)
    assert metric.max_distance_for_credit(metric.marginal_threshold(0.3195)) \
        == pytest.approx(280.8, abs=0.05)
    assert metric.max_distance_for_credit(metric.marginal_threshold(0.5)) \
        == pytest.approx(270.0, abs=0.05)
