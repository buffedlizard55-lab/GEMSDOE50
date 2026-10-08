"""Tests for the H56 detector and emitter. No external data required."""
from __future__ import annotations

import numpy as np

from gemsdoe50 import h56


def _grid(n=60, m=60):
    return np.zeros((n, m), dtype=np.float64)


def test_kernel_offsets_match_triangular_support():
    dc, dr, w = h56.kernel_offsets(3)
    d = np.hypot(dc, dr)
    assert np.all(d <= 3.0 + 1e-12)
    assert np.allclose(w, np.maximum(1.0 - d / 3.0, 0.0))
    assert w.max() == 1.0


def test_score_dots_on_truth_is_one():
    truth = np.zeros((10, 10), dtype=bool)
    truth[4:7, 4] = True
    rows = np.array([4, 5, 6])
    cols = np.array([4, 4, 4])
    s = h56.score_dots(truth, rows, cols)
    assert abs(s["dti"] - 1.0) < 1e-6          # 1e-9 epsilon in the published denominator
    assert abs(s["credit_per_dot"] - 1.0) < 1e-9

    far = h56.score_dots(truth, np.array([0]), np.array([0]))
    assert far["dti"] == 0.0
    assert far["fp"] == 1.0  # one unmatched dot, no truth covered


def test_score_dots_matches_published_worked_example_identity():
    """TP + FN == |G| is an exact identity of the published equations."""
    rng = np.random.default_rng(0)
    truth = rng.random((40, 40)) < 0.05
    if not truth.any():
        truth[10, 10] = True
    rows = rng.integers(0, 40, 50)
    cols = rng.integers(0, 40, 50)
    s = h56.score_dots(truth, rows, cols)
    assert abs(s["tp"] + s["fn"] - s["g"]) < 1e-9


def test_emit_blue_noise_respects_euclidean_separation_and_budget():
    from scipy.spatial import cKDTree

    dens = np.ones((60, 60))
    dom = np.ones((60, 60), dtype=bool)
    min_sep_px = 3.0
    em = h56.emit_blue_noise(dens, dom, n_target=60, min_sep_px=min_sep_px, seed=1)
    assert em.rows.size == 60
    pts = np.column_stack([em.rows, em.cols]).astype(float)
    nearest, _ = cKDTree(pts).query(pts, k=2)
    assert float(nearest[:, 1].min()) >= min_sep_px
    assert dom[em.rows, em.cols].all()


def test_emit_blue_noise_can_use_trailing_edge_pixels():
    """Non-multiple grid edges must not disappear into block-reshape truncation."""
    density = np.zeros((8, 10))
    domain = np.zeros((8, 10), dtype=bool)
    density[-1, -1] = 1.0
    domain[-1, -1] = True
    em = h56.emit_blue_noise(density, domain, n_target=1, min_sep_px=3.0, seed=4)
    assert list(zip(em.rows.tolist(), em.cols.tolist())) == [(7, 9)]


def test_emit_blue_noise_does_not_relax_spacing_when_support_is_too_small():
    density = np.zeros((5, 5))
    domain = np.ones_like(density, dtype=bool)
    density[2, 2:4] = 1.0
    em = h56.emit_blue_noise(density, domain, n_target=2, min_sep_px=3.0, seed=2)
    assert em.rows.size == 1
    assert domain[em.rows, em.cols].all()


def test_emit_blue_noise_is_deterministic_for_a_fixed_seed():
    density = np.ones((25, 31))
    domain = np.ones_like(density, dtype=bool)
    first = h56.emit_blue_noise(density, domain, n_target=40, min_sep_px=3.0, seed=19)
    second = h56.emit_blue_noise(density, domain, n_target=40, min_sep_px=3.0, seed=19)
    assert np.array_equal(first.rows, second.rows)
    assert np.array_equal(first.cols, second.cols)


def test_emit_blue_noise_never_leaves_the_domain():
    dens = np.ones((30, 30))
    dom = np.zeros((30, 30), dtype=bool)
    dom[5:25, 5:25] = True
    em = h56.emit_blue_noise(dens, dom, n_target=25, min_sep_px=3.0, seed=2)
    assert dom[em.rows, em.cols].all()


def test_emit_blue_noise_never_leaves_the_domain_with_tiny_belief():
    """Tiny positive weights still produce only eligible candidates.

    The earlier block-argmax implementation could let an absolute tie jitter select a
    cell outside the domain. The weighted-race implementation samples directly from
    finite, positive-density cells, so neither jitter nor grid-edge truncation can do so.
    """
    rng = np.random.default_rng(11)
    dens = np.zeros((90, 90))
    dens[10:80, 10:80] = rng.random((70, 70)) * 1e-7  # tiny corridor-tail values
    dom = np.zeros((90, 90), dtype=bool)
    dom[10:80, 10:80] = True
    em = h56.emit_blue_noise(dens, dom, n_target=200, min_sep_px=3.0, seed=5)
    assert em.rows.size > 0
    assert dom[em.rows, em.cols].all()


def test_emit_blue_noise_prefers_high_belief():
    dens = np.zeros((90, 90))
    dens[:, 40:50] = 1.0
    dom = np.ones((90, 90), dtype=bool)
    em = h56.emit_blue_noise(dens, dom, n_target=100, min_sep_px=3.0, seed=3)
    share = np.mean((em.cols >= 40) & (em.cols < 50))
    assert share > 0.5, share


def test_emit_coverage_beats_naive_top_n_on_a_planted_density():
    """Greedy coverage must not pile dots one pixel deep on the strongest feature."""
    dens = np.zeros((120, 120))
    dens[10:14, 10:110] = 1.0      # a long line of belief
    dens[100:104, 10:110] = 0.5
    dom = np.ones((120, 120), dtype=bool)
    em = h56.emit_coverage(dens, dom, n_max=200, g_hat=1000.0)
    assert em.rows.size > 0
    assert len(set(zip(em.rows.tolist(), em.cols.tolist()))) == em.rows.size


def test_dedupe_removes_repeated_pixels():
    rows = np.array([1, 1, 2])
    cols = np.array([1, 1, 2])
    r, _c = h56.dedupe(rows, cols)
    assert r.size == 2


def test_snap_to_ridge_moves_a_dot_onto_the_ridge():
    ridge = np.zeros((40, 40))
    ridge[20, 25] = 1.0
    r, c, info = h56.snap_to_ridge(np.array([20]), np.array([22]), ridge, max_snap_px=3.0)
    assert (r[0], c[0]) == (20, 25)
    assert info["snapped"] == 1


def test_snap_to_ridge_leaves_a_dot_when_no_ridge_is_near():
    ridge = np.zeros((40, 40))
    ridge[0, 0] = 1.0
    r, c, info = h56.snap_to_ridge(np.array([20]), np.array([22]), ridge, max_snap_px=3.0)
    assert (r[0], c[0]) == (20, 22)
    assert info["snapped"] == 0


def test_gardner_knopoff_removes_only_smaller_nearby_later_events():
    spatial = np.array([[0.0, 0.0], [1.0, 0.0], [500.0, 500.0]])
    time_days = np.array([0.0, 10.0, 10.0])
    mag = np.array([5.0, 2.0, 5.0])
    keep, diag = h56.gardner_knopoff_keep(spatial, time_days, mag)
    assert keep[0] and keep[2]
    assert not keep[1]
    assert diag["removed"] == 1


def test_triangle_area_filter_flags_a_tight_cluster():
    rng = np.random.default_rng(0)
    tight = rng.normal(0, 50, size=(200, 2))
    loose = rng.uniform(0, 100_000, size=(200, 2))
    xy = np.vstack([tight, loose])
    keep, diag = h56.triangle_area_keep(xy, seed=1)
    assert keep[:200].mean() > keep[200:].mean()
    assert 0.0 <= diag["fraction_kept_clustered"] <= 1.0


def test_neighbourhood_lineations_recovers_a_planted_line():
    rng = np.random.default_rng(2)
    t = np.linspace(0, 30_000, 200)
    line = np.column_stack([t, np.zeros_like(t)]) + rng.normal(0, 80, size=(200, 2))
    noise = rng.uniform(0, 200_000, size=(200, 2))
    xy = np.vstack([line, noise])
    sigma = np.full(len(xy), 200.0)
    lin = h56.neighbourhood_lineations(xy, sigma, min_events=6, min_elongation=3.0, min_sigma1_m=300.0)
    assert len(lin) > 0
    strike = np.degrees(np.arctan2(lin.ux, lin.uy)) % 180.0
    near_ew = np.abs(strike - 90.0) < 12.0
    assert near_ew.mean() > 0.7


def test_snap_to_ridge_does_not_mutate_its_inputs():
    """Regression: np.asarray returns the caller's array, so an in-place snap silently
    rewrote the emission and produced a 16 % pixel-collision rate downstream."""
    ridge = np.zeros((40, 40))
    ridge[20, 25] = 1.0
    rows_in = np.array([20, 3])
    cols_in = np.array([22, 4])
    r0, c0 = rows_in.copy(), cols_in.copy()
    h56.snap_to_ridge(rows_in, cols_in, ridge, max_snap_px=3.0)
    assert np.array_equal(rows_in, r0) and np.array_equal(cols_in, c0)


def test_epicentral_sigma_uses_the_published_column_when_present():
    import pandas as pd
    df = pd.DataFrame({"horizontalError": [0.5, None, 0.0],
                       "time": ["2010-01-01T00:00:00.000Z"] * 3})
    sig = h56.epicentral_sigma_km(df, fallback_km=2.0, floor_km=0.2)
    assert sig[0] == 0.5     # the published column, used as-is
    assert sig[1] == 2.0     # NULL -> documented era-dependent fallback, never a silent zero
    assert sig[2] == 2.0     # an exact 0.0 is not a valid uncertainty -> treated as missing


def test_required_credit_matches_the_published_denominator():
    t = h56.required_credit(0.3774, 30_000, 12_226)
    dti = t / (0.2 * 30_000 + 0.8 * 12_226)
    assert abs(dti - 0.3774) < 1e-9
