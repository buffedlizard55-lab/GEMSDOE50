"""A calibrated epicentral-uncertainty model for ComCat events in the GeoDAWN footprint.

The problem this solves (measured, not assumed)
-----------------------------------------------
ComCat's own ``horizontalError`` is the quantity Wang et al. (2013) need, but inside the
GeoDAWN footprint it is essentially absent: of 33,485 in-footprint ``earthquake`` events
with magnitude >= 1.0 and depth <= 25 km, only **532** (1.6 %) carry it, because the
in-footprint catalogue is almost entirely the ``nn`` (Nevada Regional Network) contribution
and ``nn`` does not publish ``horizontalError``.  The 62,547 ``nc`` events that do publish
it lie east of the footprint (eastern Sierra / Long Valley).

What is done instead
--------------------
1. A least-squares model for log10(h_err) is fitted on the 142,382 catalogue events that
   carry **both** ``horizontalError`` and the quality metrics (``nst``, ``gap``, ``depth``,
   ``mag``).  R^2 and the residual scatter are reported, never assumed.
2. The calibration set is restricted to events **outside** the footprint, so the 532
   in-footprint events with a documented value are a genuine holdout.
3. The model is applied to the in-footprint events that lack ``horizontalError``, and the
   holdout error is reported as the honest accuracy of the imputation.
4. Anything else (``nst``/``gap`` missing too) keeps a documented constant fallback whose
   value and population are reported.

This is this project's own construction and is flagged as such; it is *not* part of the
cited papers, which take per-event uncertainty as given.
"""
from __future__ import annotations

import numpy as np

from .notes import MEASURED, OWN

FEATURE_NAMES = ("intercept", "log10_nst", "log10_gap", "depth_km", "mag")
FALLBACK_H_ERR_M = 5000.0


def _design(nst: np.ndarray, gap: np.ndarray, depth: np.ndarray, mag: np.ndarray) -> np.ndarray:
    return np.column_stack([
        np.ones(len(nst)),
        np.log10(np.clip(nst, 1.0, None)),
        np.log10(np.clip(gap, 1.0, None)),
        np.nan_to_num(depth, nan=5.0),
        np.nan_to_num(mag, nan=1.5),
    ])


def calibrate(
    h_err_m: np.ndarray,
    nst: np.ndarray,
    gap: np.ndarray,
    depth: np.ndarray,
    mag: np.ndarray,
    outside_footprint: np.ndarray,
) -> tuple[np.ndarray, dict]:
    """Fit log10(h_err) on the calibration population; validate on the footprint holdout."""
    usable = (
        np.isfinite(h_err_m) & (h_err_m > 0)
        & np.isfinite(nst) & np.isfinite(gap)
    )
    fit_mask = usable & outside_footprint
    test_mask = usable & ~outside_footprint
    X = _design(nst, gap, depth, mag)
    y = np.log10(np.clip(h_err_m, 1e-6, None))

    coef, *_ = np.linalg.lstsq(X[fit_mask], y[fit_mask], rcond=None)
    pred_fit = X[fit_mask] @ coef
    ss_res = float(np.sum((y[fit_mask] - pred_fit) ** 2))
    ss_tot = float(np.sum((y[fit_mask] - y[fit_mask].mean()) ** 2))
    r2 = 1.0 - ss_res / ss_tot if ss_tot > 0 else float("nan")
    resid_sigma = float(np.std(y[fit_mask] - pred_fit))

    report: dict = {
        "class": OWN,
        "model": "log10(h_err_m) = a0 + a1*log10(nst) + a2*log10(gap) + a3*depth_km + a4*mag",
        "coefficients": {name: float(value) for name, value in zip(FEATURE_NAMES, coef)},
        "fit_population": int(fit_mask.sum()),
        "fit_r2": r2,
        "fit_residual_sigma_log10": resid_sigma,
        "fit_ratio_sigma": float(10.0 ** resid_sigma),
    }
    if test_mask.any():
        pred_test = X[test_mask] @ coef
        obs = h_err_m[test_mask]
        pred = 10.0 ** pred_test
        ratio = pred / obs
        report["footprint_holdout"] = {
            "n": int(test_mask.sum()),
            "median_observed_m": float(np.median(obs)),
            "median_predicted_m": float(np.median(pred)),
            "median_ratio_pred_over_obs": float(np.median(ratio)),
            "log10_rmse": float(np.sqrt(np.mean((pred_test - y[test_mask]) ** 2))),
            "within_factor_2_fraction": float(np.mean((ratio > 0.5) & (ratio < 2.0))),
        }
    return coef, report


def predict_m(
    coef: np.ndarray,
    nst: np.ndarray,
    gap: np.ndarray,
    depth: np.ndarray,
    mag: np.ndarray,
) -> np.ndarray:
    """Model epicentral 1-sigma in metres; the documented constant if inputs are missing."""
    bad = ~(np.isfinite(nst) & np.isfinite(gap))
    out = np.full(len(nst), FALLBACK_H_ERR_M, dtype=np.float64)
    ok = ~bad
    if ok.any():
        out[ok] = 10.0 ** (_design(nst[ok], gap[ok], depth[ok], mag[ok]) @ coef)
    return np.clip(out, 50.0, 20000.0), bad


def summarise(values: np.ndarray, bad: np.ndarray) -> dict:
    return {
        "median_m": float(np.median(values)),
        "p10_m": float(np.percentile(values, 10)),
        "p90_m": float(np.percentile(values, 90)),
        "fallback_population": int(bad.sum()),
        "fallback_value_m": FALLBACK_H_ERR_M,
        "class": MEASURED,
    }
