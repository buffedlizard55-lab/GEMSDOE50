"""Independent local *instruments* (proxies), never an organizer score.

Four truth sets are available without the hidden labels:

``catalogue``
    the provided USGS/INGENIOUS fault raster.  This is the competition's *given* label set,
    and it is the anti-instrument for this project's goal: its pixels are masked out of the
    scored truth, so a submission that simply covers it earns nothing.
``sgmc_off``
    USGS State Geologic Map Compilation faults that lie more than 300 m from the given
    catalogue: a broad inventory of mapped structures the competition's label set does
    not contain.  Used by the sibling repositories for the same purpose.
``monte_cristo``
    the 2020 Mw 6.5 Monte Cristo Range rupture trend - a fault that ruptured in 2020 and is
    absent from the given catalogue.  The corridor detector is only ever allowed to see
    events older than the mainshock when this instrument is used for a *falsification*
    test; see ``scripts/build_h51.py`` for the non-circular (pre-mainshock) form.
``sgmc_all``
    the whole SGMC inventory, for context only.

Every score uses the official distance-weighted Tversky definition from
``gemsdoe50.metric``, which reproduces the competition page's worked example
(TP=3.00, FP=1.89, FN=2.00 -> 0.60) in the repository test suite.
"""
from __future__ import annotations

import numpy as np

from gemsdoe50.metric import distance_weighted_tversky


def score(prediction: np.ndarray, truth: np.ndarray, mass: int | None = None) -> dict:
    if mass is None:
        mass = int(np.count_nonzero(prediction > 0))
    binary = (np.asarray(prediction) > 0).astype(np.float32)
    result = distance_weighted_tversky(truth.astype(bool), binary)
    truth_cells = max(int(np.count_nonzero(truth)), 1)
    return {
        "dti": float(result.score),
        "tp_weight": float(result.tp_weight),
        "fp_weight": float(result.fp_weight),
        "fn_weight": float(result.fn_weight),
        "truth_cells": int(result.truth_cells),
        "prediction_cells": int(result.prediction_cells),
        "credit_per_dot": float(result.tp_weight) / max(mass, 1),
        "covered_fraction": float(result.tp_weight) / truth_cells,
    }


def all_instruments(prediction: np.ndarray, truths: dict[str, np.ndarray]) -> dict:
    return {name: score(prediction, truth) for name, truth in truths.items()}


def oracle_ceiling(truth: np.ndarray) -> float:
    """DTI of the perfect answer, as a scale reference for the instrument."""
    return score(truth.astype(np.float32), truth)["dti"]
