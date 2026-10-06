import numpy as np
import pytest

from gemsdoe50.metric import distance_weighted_tversky


def test_exact_match_scores_one():
    truth = np.zeros((20, 20), dtype=bool)
    prediction = np.zeros((20, 20), dtype=np.float32)
    truth[10, 10] = True
    prediction[10, 10] = 1.0
    result = distance_weighted_tversky(truth, prediction)
    assert result.tp_weight == pytest.approx(1.0)
    assert result.fp_weight == pytest.approx(0.0)
    assert result.fn_weight == pytest.approx(0.0)
    assert result.score == pytest.approx(1.0, abs=2e-9)


def test_triangular_distance_kernel_and_fp_discount():
    truth = np.zeros((20, 20), dtype=bool)
    prediction = np.zeros((20, 20), dtype=np.float32)
    truth[10, 10] = True
    prediction[10, 11] = 1.0  # 100 m, kernel = 2/3
    result = distance_weighted_tversky(truth, prediction)
    assert result.tp_weight == pytest.approx(2 / 3)
    assert result.fn_weight == pytest.approx(1 / 3)
    assert result.fp_weight == pytest.approx(1 / 3)
    assert result.score == pytest.approx(2 / 3, abs=1e-8)


def test_evaluation_masks_allow_halo_context_without_double_counting():
    truth = np.zeros((20, 20), dtype=bool)
    prediction = np.zeros((20, 20), dtype=np.float32)
    truth[10, 5] = True
    truth[10, 14] = True
    prediction[10, 5] = 1.0
    prediction[10, 14] = 1.0
    truth_eval = np.zeros_like(truth)
    prediction_eval = np.zeros_like(truth)
    truth_eval[10, 5] = True
    prediction_eval[10, 5] = True
    result = distance_weighted_tversky(
        truth,
        prediction,
        truth_eval_mask=truth_eval,
        prediction_eval_mask=prediction_eval,
    )
    assert result.truth_cells == 1
    assert result.prediction_cells == 1
    assert result.score == pytest.approx(1.0, abs=2e-9)


def test_no_prediction_and_no_truth_are_finite_zero():
    empty = np.zeros((12, 12), dtype=bool)
    prediction = np.zeros((12, 12), dtype=np.float32)
    assert distance_weighted_tversky(empty, prediction).score == 0.0
    truth = empty.copy()
    truth[5, 5] = True
    assert distance_weighted_tversky(truth, prediction).score == 0.0


def test_invalid_values_are_rejected():
    truth = np.zeros((4, 4), dtype=bool)
    with pytest.raises(ValueError, match="NaN or infinity"):
        distance_weighted_tversky(truth, np.full((4, 4), np.nan))
    with pytest.raises(ValueError, match=r"in \[0, 1\]"):
        distance_weighted_tversky(truth, np.full((4, 4), 1.01))
