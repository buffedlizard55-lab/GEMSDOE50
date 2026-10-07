"""Tests for the local instruments.

The instruments must be *exactly* the official metric on a different truth raster, so these
tests pin that identity (an independent scorer) plus the per-dot bookkeeping the mass rule
and the site tables rely on.
"""

import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from gems51 import instruments
from gemsdoe50.metric import distance_weighted_tversky


def _fixture() -> tuple[np.ndarray, np.ndarray]:
    _rng = np.random.default_rng(11)
    truth = np.zeros((40, 40), dtype=bool)
    truth[5:25, 20] = True          # a vertical line
    truth[30, 5:30] = True          # a horizontal line
    prediction = np.zeros((40, 40), dtype=bool)
    prediction[10:30, 21] = True    # partially overlapping the vertical line
    prediction[35:38, 5:10] = True  # a block off the truth
    return truth, prediction


def test_instrument_score_equals_the_official_metric():
    truth, prediction = _fixture()
    mine = instruments.score(prediction, truth)
    official = distance_weighted_tversky(truth, prediction.astype(np.float32))
    assert abs(mine["dti"] - official.score) < 1e-12
    assert abs(mine["tp_weight"] - official.tp_weight) < 1e-9
    assert abs(mine["fp_weight"] - official.fp_weight) < 1e-9
    assert abs(mine["fn_weight"] - official.fn_weight) < 1e-9


def test_credit_per_dot_and_covered_fraction_are_consistent():
    truth, prediction = _fixture()
    result = instruments.score(prediction, truth)
    mass = int(prediction.sum())
    assert abs(result["credit_per_dot"] - result["tp_weight"] / mass) < 1e-12
    assert abs(result["covered_fraction"] - result["tp_weight"] / int(truth.sum())) < 1e-12
    zero = instruments.score(np.zeros_like(prediction), truth)
    assert zero["credit_per_dot"] == 0.0
    assert zero["dti"] == 0.0


def test_oracle_ceiling_is_one_and_beats_a_dot_prediction():
    truth, prediction = _fixture()
    ceiling = instruments.oracle_ceiling(truth)
    assert abs(ceiling - 1.0) < 1e-6  # the metric adds an epsilon to its denominator
    assert instruments.score(prediction, truth)["dti"] < ceiling


def test_all_instruments_returns_one_entry_per_truth_set():
    truth, prediction = _fixture()
    truths = {"a": truth, "b": np.roll(truth, 3, axis=0)}
    scores = instruments.all_instruments(prediction, truths)
    assert set(scores) == {"a", "b"}
    assert all("credit_per_dot" in value for value in scores.values())
