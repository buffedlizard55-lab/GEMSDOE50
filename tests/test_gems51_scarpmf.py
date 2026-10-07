"""Tests for the H52-A azimuth-specific matched filter (src/gems51/scarpmf.py)."""

import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from gems51 import scarpmf


def _synthetic_scarp(n: int = 60, step_m: float = 5.0) -> np.ndarray:
    """A flat plain with a single north-south scarp (a step in elevation) at the midline,
    plus a gentle regional tilt that detrending must remove."""
    _yy, xx = np.meshgrid(np.arange(n), np.arange(n), indexing="ij")
    regional_tilt = 0.01 * xx.astype(np.float32)   # 1 cm/px synthetic regional slope
    scarp = np.where(xx >= n // 2, step_m, 0.0).astype(np.float32)
    return (regional_tilt + scarp).astype(np.float32)


def test_detrend_removes_regional_tilt_but_keeps_the_local_step():
    dem = _synthetic_scarp()
    valid = np.ones(dem.shape, dtype=bool)
    det = scarpmf.detrend(dem, valid, sigma_px=15.0)
    # far from the scarp the detrended surface should be close to flat (tilt removed)
    left_tail = det[:, :5]
    assert float(np.std(left_tail)) < 1.0
    # a visible step must remain across the scarp line in the interior rows
    across = det[30, 20:40]
    assert float(across.max() - across.min()) > 1.0


def test_matched_filter_peaks_on_a_north_south_scarp_with_the_right_azimuth():
    dem = _synthetic_scarp()
    valid = np.ones(dem.shape, dtype=bool)
    det = scarpmf.detrend(dem, valid, sigma_px=15.0)
    mf = scarpmf.matched_filter(det, valid)
    strength = mf["strength"]
    # response should be concentrated near the scarp (column ~30), not at the plain's edges
    column_profile = strength[10:-10, :].mean(axis=0)
    peak_col = int(np.argmax(column_profile))
    assert 25 <= peak_col <= 35
    assert column_profile[peak_col] > 3.0 * column_profile[:10].mean()
    # the scarp runs constant-along-rows / varying-along-columns; in this kernel's azimuth
    # convention (see scarpmf._step_kernel) that is matched by an azimuth near 90 degrees,
    # not near 0/180 (which would match a step that varies along rows instead).
    peak_azimuths = mf["azimuth_deg"][15:-15, peak_col]
    near_match = np.abs(peak_azimuths - 90.0)
    assert float(np.median(near_match)) < 45.0


def test_matched_filter_strength_is_bounded_in_unit_interval():
    rng = np.random.default_rng(11)
    dem = rng.normal(scale=2.0, size=(50, 50)).astype(np.float32)
    valid = np.ones(dem.shape, dtype=bool)
    det = scarpmf.detrend(dem, valid, sigma_px=10.0)
    mf = scarpmf.matched_filter(det, valid)
    assert float(mf["strength"].min()) >= 0.0
    assert float(mf["strength"].max()) <= 1.0 + 1e-6


def test_flat_surface_produces_near_zero_matched_filter_response():
    dem = np.full((40, 40), 1500.0, dtype=np.float32)
    valid = np.ones(dem.shape, dtype=bool)
    det = scarpmf.detrend(dem, valid, sigma_px=10.0)
    assert float(np.abs(det).max()) < 1e-4
