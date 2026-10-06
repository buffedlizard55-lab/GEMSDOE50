import numpy as np

from gemsdoe50.common import sha256_array
from gemsdoe50.evaluation import _top_n_prediction, allocate_largest_remainder
from gemsdoe50.holdout import build_spatial_blocks


def test_largest_remainder_allocations_sum_to_total():
    allocations = allocate_largest_remainder(101, [2, 3, 5])
    assert allocations == [20, 30, 51]
    assert sum(allocations) == 101


def test_top_n_uses_binary_equal_mass_and_reproducible_ties():
    scores = np.array([[0.9, 0.4, 0.4, 0.0]], dtype=np.float32)
    eligible = np.ones_like(scores, dtype=bool)
    first = _top_n_prediction(scores, eligible, 2, seed=72)
    second = _top_n_prediction(scores, eligible, 2, seed=72)
    assert np.array_equal(first, second)
    assert np.count_nonzero(first) == 2
    assert np.all(first[first > 0] == 1.0)


def test_frozen_split_reconstructs_exact_core_and_buffers():
    shape = (100, 120)
    valid = np.ones(shape, dtype=bool)
    truth = np.zeros(shape, dtype=bool)
    truth[25, 25] = True
    truth[25, 85] = True
    truth[75, 25] = True
    truth[75, 85] = True
    folds = []
    for fold_id, rows, cols in [
        ("NW", [0, 50], [0, 60]),
        ("NE", [0, 50], [60, 120]),
        ("SW", [50, 100], [0, 60]),
        ("SE", [50, 100], [60, 120]),
    ]:
        folds.append(
            {
                "id": fold_id,
                "rows": rows,
                "cols": cols,
                "subtile_row_bounds": [rows[0], 25 if rows[0] == 0 else 75, rows[1]],
                "subtile_col_bounds": [cols[0], 30 if cols[0] == 0 else 90, cols[1]],
            }
        )
    spec = {
        "schema": "gemsdoe50.spatial-holdout.v1",
        "grid": {
            "width": shape[1],
            "height": shape[0],
            "valid_mask_sha256": sha256_array(valid.astype(np.uint8)),
            "pixel_size_m": 100,
        },
        "rules": {
            "heldout_core_erode_pixels": 5,
            "visible_training_label_buffer_pixels": 3,
        },
        "macrofolds": folds,
    }
    blocks, realized = build_spatial_blocks(valid, truth, spec)
    assert [block.block_id for block in blocks] == ["NW", "NE", "SW", "SE"]
    assert all(len(block.subtile_masks) == 4 for block in blocks)
    assert realized["valid_mask_sha256"] == spec["grid"]["valid_mask_sha256"]
    assert sum(block.metadata["truth_cells"] for block in blocks) == 4
