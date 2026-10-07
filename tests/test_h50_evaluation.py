import numpy as np
import pytest

from gemsdoe50.evaluation import PRIMARY_INCUMBENT_NAME, evaluate_hypothesis
from gemsdoe50.holdout import SpatialBlock


def _single_block() -> SpatialBlock:
    eligible = np.ones((8, 8), dtype=bool)
    truth = np.zeros((8, 8), dtype=bool)
    truth[4, 4] = True
    subtile = ("F1-00", (0, 8), (0, 8), eligible, truth)
    return SpatialBlock(
        block_id="F1",
        rows=(0, 8),
        cols=(0, 8),
        eligible=eligible,
        truth=truth,
        subtile_masks=(subtile,),
        metadata={},
    )


def test_incumbent_is_fixed_before_holdout_not_selected_by_best_score():
    prior = np.zeros((8, 8), dtype=np.float32)
    prior[0, 0] = 1.0
    stronger_secondary = np.zeros((8, 8), dtype=np.float32)
    stronger_secondary[4, 4] = 1.0
    empty = np.zeros((8, 8), dtype=np.float32)

    result = evaluate_hypothesis(
        prior.copy(),
        {
            "H32-D": stronger_secondary,
            "H47-S3": empty,
            "H48-DS": empty,
            "smoothed-density-1km": empty,
            "smoothed-density-2km": empty,
            PRIMARY_INCUMBENT_NAME: prior,
        },
        [_single_block()],
        split_sha256="0" * 64,
        input_hashes={},
        time_shuffle_maps={f"time-shuffle-{index:02d}": empty for index in range(20)},
    )

    assert result["method_results"]["H32-D"]["pooled"]["score"] > result[
        "method_results"][PRIMARY_INCUMBENT_NAME
    ]["pooled"]["score"]
    assert result["incumbent_method"] == PRIMARY_INCUMBENT_NAME
    assert result["candidate_minus_incumbent_pooled_dti"] == pytest.approx(0.0)
    assert "secondary comparator scores are descriptive only" in result[
        "incumbent_selection_policy"
    ]


def test_evaluation_refuses_to_choose_an_incumbent_from_holdout_scores():
    with pytest.raises(ValueError, match="do not select an incumbent from holdout scores"):
        evaluate_hypothesis(
            np.zeros((8, 8), dtype=np.float32),
            {"H32-D": np.zeros((8, 8), dtype=np.float32)},
            [_single_block()],
            split_sha256="0" * 64,
            input_hashes={},
        )


def test_evaluation_requires_both_smoothed_density_controls():
    empty = np.zeros((8, 8), dtype=np.float32)
    with pytest.raises(ValueError, match="smoothed-density controls are required"):
        evaluate_hypothesis(
            empty,
            {PRIMARY_INCUMBENT_NAME: empty},
            [_single_block()],
            split_sha256="0" * 64,
            input_hashes={},
            time_shuffle_maps={f"time-shuffle-{index:02d}": empty for index in range(20)},
        )


def test_density_gate_requires_strictly_beating_both_smoothed_maps():
    empty = np.zeros((8, 8), dtype=np.float32)
    candidate = empty.copy()
    candidate[4, 4] = 1.0
    result = evaluate_hypothesis(
        candidate,
        {
            PRIMARY_INCUMBENT_NAME: empty,
            "smoothed-density-1km": candidate.copy(),
            "smoothed-density-2km": empty,
        },
        [_single_block()],
        split_sha256="0" * 64,
        input_hashes={},
        time_shuffle_maps={f"time-shuffle-{index:02d}": empty for index in range(20)},
    )

    assert result["smoothed_density_controls"]["candidate_beats_both"] is False
    assert result["promotion_gate"]["components"]["beats_both_smoothed_density_controls"] is False


def test_evaluation_requires_all_preregistered_time_shuffle_controls():
    empty = np.zeros((8, 8), dtype=np.float32)
    with pytest.raises(ValueError, match="exactly 20 time-shuffle controls"):
        evaluate_hypothesis(
            empty,
            {
                PRIMARY_INCUMBENT_NAME: empty,
                "smoothed-density-1km": empty,
                "smoothed-density-2km": empty,
            },
            [_single_block()],
            split_sha256="0" * 64,
            input_hashes={},
            time_shuffle_maps={},
        )
