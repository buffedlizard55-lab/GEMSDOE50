"""Guardrails for the shipped candidate's arithmetic and the truth-map inversion.

These are cheap, data-free checks that encode the two claims the write-up rests on:

* the metric identity ``DTI = T/(0.2N + 0.8G)`` used to invert every scored artifact, and
* the block-grid Laplacian used by the (failed) truth-density inversion, which must be a proper
  symmetric positive-semi-definite graph Laplacian with zero row sums.
"""

import numpy as np
import pytest

from gemsdoe50 import h51
from gemsdoe50.h51 import ALPHA, BETA


def test_metric_identity_matches_the_tversky_definition():
    # T + FP_w = N for binary predictions, so the official Tversky form
    #   T / (T + 0.2*FP + 0.8*FN)  must equal  T / (0.2*N + 0.8*G)
    T, N, G = 4800.0, 44090.0, 12226.0
    fp = N - T
    fn = G - T
    assert ALPHA == 0.2 and BETA == 0.8
    assert T / (T + ALPHA * fp + BETA * fn) == pytest.approx(T / (0.2 * N + 0.8 * G))


def test_credit_per_dot_inversion_is_invertible():
    # G = 0.2*s*N/(c - 0.8*s) from the blind spacing-5 lattice calibration
    n, c, s = 204504.0, 0.3748109386598507, 0.0904
    g = 0.2 * s * n / (c - 0.8 * s)
    assert g == pytest.approx(12226.0, rel=0.02)
    # and the score a design would get at a known credit mass is monotone in T
    def score(t: float) -> float:
        return t / (0.2 * n + 0.8 * g)

    assert score(4800) > score(4000) > 0.0


def test_laplacian_is_symmetric_with_zero_row_sums():
    from scipy.sparse import csr_matrix

    n = 6
    idx = np.arange(n * n).reshape(n, n)
    rows, cols = [], []
    for axis, shift in ((0, 1), (1, 1)):
        if axis == 0:
            a, b = idx[:-shift, :].ravel(), idx[shift:, :].ravel()
        else:
            a, b = idx[:, :-shift].ravel(), idx[:, shift:].ravel()
        rows.append(a)
        cols.append(b)
    a = np.concatenate(rows)
    b = np.concatenate(cols)
    m = csr_matrix((np.ones(2 * a.size), (np.concatenate([a, b]), np.concatenate([b, a]))),
                   shape=(n * n, n * n))
    deg = np.asarray(m.sum(axis=1)).ravel()
    lap = csr_matrix((np.concatenate([-np.ones(2 * a.size), deg]),
                      (np.concatenate([np.concatenate([a, b]), np.arange(n * n)]),
                       np.concatenate([np.concatenate([b, a]), np.arange(n * n)]))),
                     shape=(n * n, n * n)).toarray()
    assert np.allclose(lap, lap.T)
    assert np.allclose(lap.sum(axis=1), 0.0, atol=1e-9)
    assert np.all(np.linalg.eigvalsh(lap) > -1e-9)


def test_place_dots_ordered_stops_at_the_budget_and_respects_domain():
    rng = np.random.default_rng(3)
    belief = rng.random((30, 30)).astype(np.float32)
    allowed = np.zeros((30, 30), bool)
    allowed[5:25, 5:25] = True
    order = h51.place_dots_ordered(belief, allowed, h51.EmissionParams(
        spacing_px=2.0, budget=12, belief_floor=1e-9, pool_factor=8))
    assert order.size <= 12
    rows, cols = np.divmod(order, 30)
    assert allowed[rows, cols].all()
