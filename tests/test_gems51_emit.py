"""Tests for the H51 metric-matched emission machinery.

These pin the properties the shipped file relies on:

* the triangular kernel is the official 300 m kernel on a 100 m grid;
* the expected-credit field is the kernel correlation of the belief, so a dot's marginal
  credit is exactly its expected kernel overlap with the truth proxy;
* the greedy packer honours its mass cap, its suppression radius and its validity mask, and
  is deterministic;
* ``choose_mass`` reads the *marginal* credit of each swept increment, which is the rule the
  preregistration uses (amendment A1).
"""

import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from gems51 import emit


def test_kernel_is_the_official_300m_triangle():
    kernel = emit.kernel_weights(3.0)
    assert kernel.shape == (7, 7)
    assert kernel[3, 3] == 1.0
    assert kernel[3, 0] == 0.0          # 300 m away contributes nothing
    assert abs(kernel[3, 2] - 2.0 / 3.0) < 1e-6   # 100 m away
    assert abs(kernel[1, 3] - 1.0 / 3.0) < 1e-6   # 200 m away
    assert np.allclose(kernel, kernel[::-1, ::-1])
    assert kernel.min() >= 0.0


def test_expected_credit_field_is_the_kernel_correlation():
    belief = np.zeros((11, 11), dtype=np.float32)
    belief[5, 5] = 1.0
    credit = emit.expected_credit_field(belief)
    assert abs(credit[5, 5] - 1.0) < 1e-6
    assert abs(credit[5, 7] - (1.0 - 2.0 / 3.0)) < 1e-6
    assert credit[5, 8] == 0.0
    assert credit.sum() > 0.0


def test_pack_honours_mass_suppression_and_mask():
    rng = np.random.default_rng(3)
    belief = rng.random((60, 60)).astype(np.float32)
    valid = np.ones((60, 60), dtype=bool)
    valid[:10, :] = False
    support, info = emit.pack(belief, 40, valid=valid, suppression_px=3.0)
    assert info["mass"] == 40
    assert int(support.sum()) == 40
    assert not support[~valid].any()
    # every accepted dot blocks a 3 px disc, so two dots are never closer than the radius
    rows, cols = np.nonzero(support)
    from scipy.spatial import cKDTree

    distances, _ = cKDTree(np.column_stack([rows, cols])).query(
        np.column_stack([rows, cols]), k=2)
    assert distances[:, 1].min() > 3.0
    again, _ = emit.pack(belief, 40, valid=valid, suppression_px=3.0)
    assert np.array_equal(support, again)


def test_pack_caps_at_the_available_support():
    belief = np.zeros((30, 30), dtype=np.float32)
    belief[15, 15] = 1.0
    support, info = emit.pack(belief, 10_000, suppression_px=3.0)
    assert info["mass"] == int(support.sum())
    assert info["mass"] < 10_000


def test_choose_mass_reads_marginal_credit_and_has_a_lower_anchor():
    """The rule must keep the smaller mass once an increment falls below the bar."""
    sweep = {
        100: {"n_dots": 100, "instruments": {"sgmc_off": {"tp_weight": 20.0}}},
        200: {"n_dots": 200, "instruments": {"sgmc_off": {"tp_weight": 39.0}}},
        300: {"n_dots": 300, "instruments": {"sgmc_off": {"tp_weight": 50.0}}},
    }
    chosen = emit.choose_mass(sweep, target_dti=0.30)
    # 100 -> 200 gains 19/100 = 0.19 (above 0.06), 200 -> 300 gains 11/100 = 0.11 (still above)
    assert chosen["chosen_mass"] == 300
    sweep[400] = {"n_dots": 400, "instruments": {"sgmc_off": {"tp_weight": 52.0}}}
    chosen = emit.choose_mass(sweep, target_dti=0.30)
    # 300 -> 400 gains 2/100 = 0.02, below the bar, so the previous mass is kept
    assert chosen["chosen_mass"] == 300
    assert chosen["table"][-1]["kept"] is False


def test_sweep_scores_every_mass_on_every_instrument():
    belief = np.zeros((40, 40), dtype=np.float32)
    belief[20, 20] = 1.0
    belief[10, 10] = 0.5
    truths = {"a": belief.astype(bool), "b": np.zeros_like(belief, dtype=bool)}
    truths["b"][30, 30] = True
    out = emit.sweep(belief, [1, 2], truths)
    assert set(out) == {1, 2}
    assert out[2]["instruments"]["a"]["truth_cells"] == 2
    assert out[2]["instruments"]["b"]["dti"] == 0.0
