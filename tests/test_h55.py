from __future__ import annotations

import numpy as np

from gems55.ridge import _dynamic_path
from gems55.seismic import (
    CatalogFrame,
    H55Config,
    _normalised_triangle_stat,
    _sequence_thin,
    fit_axes,
)


def _frame(x, y, time_days, magnitude, year=None):
    n = len(x)
    return CatalogFrame(
        evid=np.arange(1, n + 1, dtype=np.int64),
        time_days=np.asarray(time_days, dtype=np.float64),
        year=np.asarray(year if year is not None else np.full(n, 2020), dtype=np.int16),
        x_m=np.asarray(x, dtype=np.float64),
        y_m=np.asarray(y, dtype=np.float64),
        depth_km=np.full(n, 5.0, dtype=np.float32),
        magnitude=np.asarray(magnitude, dtype=np.float32),
        row=np.zeros(n, dtype=np.int32),
        col=np.zeros(n, dtype=np.int32),
        metadata={},
    )


def test_sequence_thinning_is_space_and_time_aware_and_keeps_largest():
    frame = _frame(
        x=[10, 20, 30, 40],
        y=[10, 20, 30, 40],
        time_days=[1, 2, 100, 101],
        magnitude=[1.0, 2.0, 0.5, 1.5],
    )
    thinned, report = _sequence_thin(frame, H55Config())
    assert thinned.evid.tolist() == [2, 4]
    assert report["events_removed"] == 2


def test_normalized_triangle_stat_is_scale_invariant():
    rng = np.random.default_rng(7)
    points = rng.random((80, 2))
    original = _normalised_triangle_stat(points, 20)
    translated_and_scaled = _normalised_triangle_stat(points * 17.0 + [200.0, -40.0], 20)
    np.testing.assert_allclose(original, translated_and_scaled, rtol=1e-11, atol=1e-12)


def test_dynamic_path_follows_ridge_without_jumping_more_than_two_bins():
    local = np.zeros((20, 11), dtype=np.float64)
    target = np.clip(np.arange(20) // 3 + 2, 0, 10)
    local[np.arange(20), target] = 2.0
    path = _dynamic_path(local)
    assert np.all(np.abs(np.diff(path)) <= 2)
    assert np.mean(path == target) > 0.9


def test_fit_axes_recovers_recurrent_linear_direction():
    rng = np.random.default_rng(19)
    x = np.linspace(0, 5_000, 60)
    y = rng.normal(0, 60, size=x.size)
    years = np.tile(np.arange(2010, 2016), 10)
    frame = _frame(x, y, np.arange(x.size) * 100.0, np.ones(x.size), years)
    config = H55Config(
        seed_cell_m=2_000,
        neighbourhood_radius_m=10_000,
        min_events=10,
        min_years=3,
        min_linearity=0.6,
        min_length_m=1_500,
    )
    segments = fit_axes(frame, np.full(x.size, 0.05), config)
    assert len(segments) >= 2
    assert np.all(np.abs(segments.ux) > 0.98)
    assert np.all(segments.linearity > 0.9)
    assert np.all(segments.n_years == 6)
