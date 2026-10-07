"""Unit tests for the H52 coincidence emitter and the budget-curve inversion.

These guard the two pieces of arithmetic that the shipped artifact depends on:
the emitter's separation/budget contract, and the closed-form solve that turns two
organizer scores into (truth mass, weighted credit).
"""
from __future__ import annotations

import importlib.util
from pathlib import Path

import numpy as np
import pytest

from gemsdoe50.coincidence import coincidence_score, greedy_isolated_emission

REPO = Path(__file__).resolve().parents[1]


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module


# --------------------------------------------------------------- coincidence ---


def test_coincidence_score_counts_agreeing_families():
    p = np.zeros((3, 4, 4), np.float32)
    p[:, 0, 0] = 1.0                      # all three families agree
    p[:2, 1, 1] = 1.0                     # two agree
    p[0, 2, 2] = 0.5                      # none reach tau
    score = coincidence_score(p, tau=0.90)
    # score = (number of agreeing families) + 0.5 * mean normalised excess
    assert score[0, 0] == pytest.approx(3.5)
    assert score[1, 1] == pytest.approx(2.5)
    assert score[2, 2] == 0.0
    assert score.max() <= 3.5


def test_coincidence_score_is_bounded_and_monotone_in_agreement():
    rng = np.random.default_rng(0)
    p = rng.random((8, 32, 32)).astype(np.float32)
    score = coincidence_score(p, tau=0.90)
    n = (p >= 0.90).sum(axis=0)
    assert score.min() >= 0.0
    assert score.max() <= p.shape[0] + 0.5
    # the integer part is the agreement count: strength only breaks ties within a count
    assert np.all(score >= n)
    assert np.all(score < n + 0.5 + 1e-6)
    assert int(n.max()) <= p.shape[0]


def test_coincidence_score_rejects_bad_inputs():
    with pytest.raises(ValueError):
        coincidence_score(np.zeros((4, 4), np.float32))
    with pytest.raises(ValueError):
        coincidence_score(np.zeros((2, 4, 4), np.float32), tau=1.5)


# ------------------------------------------------------------------ emitter ---


def test_emitter_respects_budget_and_separation():
    rng = np.random.default_rng(7)
    score = rng.random((60, 60))
    allowed = np.ones((60, 60), bool)
    out = greedy_isolated_emission(score, allowed, 50, block_radius_px=2)
    assert int(out.sum()) == 50
    rows, cols = np.nonzero(out)
    for i in range(rows.size):
        di = np.abs(rows - rows[i])
        dj = np.abs(cols - cols[i])
        close = (di <= 2) & (dj <= 2)
        assert close.sum() == 1, "dots must be at least 3 px apart in Chebyshev distance"


def test_emitter_is_deterministic_and_takes_the_highest_scores_first():
    rng = np.random.default_rng(11)
    score = rng.random((40, 40))
    allowed = np.ones((40, 40), bool)
    a = greedy_isolated_emission(score, allowed, 20, 2)
    b = greedy_isolated_emission(score, allowed, 20, 2)
    assert np.array_equal(a, b)
    picked = np.sort(score[a])[::-1]
    assert picked[0] == pytest.approx(score.max())
    assert (picked > 0.5).all(), "20 well-separated picks out of 1600 cells must be high scorers"


def test_emitter_never_leaves_the_allowed_mask():
    rng = np.random.default_rng(3)
    score = rng.random((30, 30))
    allowed = np.zeros((30, 30), bool)
    allowed[5:15, 5:15] = True
    out = greedy_isolated_emission(score, allowed, 1000, 2)
    assert not np.any(out & ~allowed)
    # at most ceil(10/3) = 4 dots per axis can fit with >= 3 px separation
    assert 1 <= int(out.sum()) <= 16


def test_emitter_edge_cases():
    score = np.ones((5, 5))
    assert greedy_isolated_emission(score, np.zeros((5, 5), bool), 10, 2).sum() == 0
    assert greedy_isolated_emission(score, np.ones((5, 5), bool), 0, 2).sum() == 0
    with pytest.raises(ValueError):
        greedy_isolated_emission(score, np.ones((4, 4), bool), 1, 2)


# ------------------------------------------------------- budget-curve solve ---


def test_metric_inversion_recovers_known_masses():
    mod = load_module("h52_budget_curve", REPO / "scripts" / "h52_budget_curve.py")
    # synthetic: G = 10000 truth pixels, a child subset whose weighted credit is 4000
    alpha, beta, g, t = 0.2, 0.8, 10000.0, 4000.0
    n_parent, n_child = 50000, 40000
    s_parent = t / (alpha * n_parent + beta * g)
    s_child = t / (alpha * n_child + beta * g)
    inv = mod.invert_metric(n_parent, s_parent, n_child, s_child)
    assert inv["truth_mass_G"] == pytest.approx(g, rel=1e-9)
    assert inv["child_weighted_credit_T"] == pytest.approx(t, rel=1e-9)


def test_metric_inversion_on_the_recorded_pair():
    mod = load_module("h52_budget_curve", REPO / "scripts" / "h52_budget_curve.py")
    inv = mod.invert_metric(44090, 0.2600, 37654, 0.2778)
    assert inv["truth_mass_G"] == pytest.approx(14088.75, rel=1e-4)
    assert inv["child_weighted_credit_T"] == pytest.approx(5223.14, rel=1e-4)
    assert inv["parent_dti_recomputed"] == pytest.approx(0.2600, abs=1e-9)
    assert inv["child_dti_recomputed"] == pytest.approx(0.2778, abs=1e-9)
