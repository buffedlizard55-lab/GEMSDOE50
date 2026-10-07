import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from gems51 import uncertainty


def test_calibration_recovers_a_known_power_law():
    rng = np.random.default_rng(0)
    n = 4000
    nst = rng.integers(4, 60, n).astype(float)
    gap = rng.uniform(25, 350, n)
    depth = rng.uniform(0, 20, n)
    mag = rng.uniform(1.0, 4.0, n)
    truth = np.array([3.5, -0.7, 0.8, 0.02, 0.1])
    h = 10.0 ** (truth[0] + truth[1] * np.log10(nst) + truth[2] * np.log10(gap)
                 + truth[3] * depth + truth[4] * mag)
    outside = np.ones(n, bool)
    coef, report = uncertainty.calibrate(h, nst, gap, depth, mag, outside)
    assert report["fit_r2"] > 0.99
    assert np.allclose(coef, truth, atol=0.05)


def test_missing_metrics_get_the_documented_fallback():
    coef = np.array([2.2, -0.7, 0.8, 0.02, 0.2])
    values, bad = uncertainty.predict_m(coef, np.array([np.nan, 10.0]),
                                        np.array([np.nan, 100.0]),
                                        np.array([5.0, 5.0]), np.array([1.5, 1.5]))
    assert bad.tolist() == [True, False]
    assert values[0] == uncertainty.FALLBACK_H_ERR_M
    assert 100.0 < values[1] < 5000.0


def test_holds_out_the_footprint_population():
    rng = np.random.default_rng(1)
    n = 3000
    nst = rng.integers(5, 40, n).astype(float)
    gap = rng.uniform(40, 200, n)
    depth = rng.uniform(1, 15, n)
    mag = rng.uniform(1.0, 3.0, n)
    h = 10.0 ** (3.6 - 0.7 * np.log10(nst) + 0.8 * np.log10(gap) + 0.02 * depth)
    outside = rng.random(n) > 0.2
    _, report = uncertainty.calibrate(h, nst, gap, depth, mag, outside)
    assert report["footprint_holdout"]["n"] > 0
    assert report["footprint_holdout"]["within_factor_2_fraction"] > 0.5
