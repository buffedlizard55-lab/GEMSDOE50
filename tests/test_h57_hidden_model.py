"""Unit tests for the H57 hidden-frame calibration maths.

The calibration script inverts the official metric's identity

    DTI = T / (0.2 N + 0.8 G)

on 21 scored corpus artifacts.  Every number in `docs/research/h57-verdict-20261007.md`
section 4 depends on that inversion and on the least-squares fit being implemented
correctly, so both are tested here on synthetic inputs where the right answer is known.

These tests deliberately do **not** assert anything about the hidden labels: they only
check the algebra.
"""

from __future__ import annotations

import itertools

import numpy as np

from scripts.h57_hidden_model import CANDIDATE, normal_sf, ols, solve_n_from_h


def test_solve_n_round_trips_the_metric_identity():
    """Recovering N from (score, h) must invert the identity exactly."""
    g = 14088.75
    for n in (15000.0, 37654.0, 80000.0, 264247.0):
        for credit_per_dot in (0.03, 0.064, 0.1387):
            t = credit_per_dot * n
            dti = t / (0.2 * n + 0.8 * g)
            # h is credit per dot *on the same dot set*, so the inverse is exact
            recovered = solve_n_from_h(dti, credit_per_dot, g)
            assert abs(recovered - n) / n < 1e-9, (n, credit_per_dot, recovered)


def test_solve_n_returns_none_when_the_score_implies_no_credit():
    """A score is impossible when the implied denominator exceeds the credit."""
    # h <= 0.2 * score means T <= 0.2 * score * N, i.e. no non-negative solution.
    assert solve_n_from_h(0.26, 0.001, 14088.75) is None


def test_normal_sf_is_the_upper_tail():
    assert abs(normal_sf(0.0) - 0.5) < 1e-12
    assert abs(normal_sf(-1.959963984540054) - 0.975) < 1e-6
    assert normal_sf(10.0) < 1e-20


def test_ols_recovers_a_known_plane_with_standard_errors():
    rng = np.random.default_rng(7)
    n = 200
    x1 = rng.uniform(0.03, 0.20, n)
    x2 = np.log(rng.uniform(2e4, 3e5, n))
    y = 0.5 - 0.3 * x1 - 0.04 * x2 + rng.normal(0.0, 0.005, n)
    beta, r2, sd, se = ols(np.column_stack([x1, x2]), y)
    assert r2 > 0.9
    assert abs(beta[1] + 0.3) < 0.05
    assert abs(beta[2] + 0.04) < 0.005
    assert np.all(se > 0)
    assert sd > 0


def test_ols_flags_a_meaningless_single_regressor():
    """The transfer model's failure mode: R^2 can go negative, and must not be clipped."""
    rng = np.random.default_rng(11)
    x = rng.uniform(0.04, 0.20, 30)
    y = rng.normal(0.05, 0.03, 30)  # no relationship at all
    _, r2, _, _ = ols(x[:, None], y)
    assert r2 < 0.2  # a slope-including fit on noise cannot do much
    # the corpus's own transfer fit is worse than the mean, which is why the receipt
    # reports r2 = -0.87 rather than a clipped non-negative number
    assert r2 > -1.0


def test_candidate_table_is_monotone_in_credit_per_dot():
    """The measured belief-field table must show credit per dot falling with mass.

    If a future edit transcribes a wrong pair, the fit silently changes; this catches it.
    """
    masses = [n for n, _ in CANDIDATE]
    credits = [c for _, c in CANDIDATE]
    assert masses == sorted(masses)
    assert all(b <= a for a, b in itertools.pairwise(credits)), credits
    assert 0.0 < credits[-1] < credits[0] < 1.0
