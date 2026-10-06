"""Tests for the structure-tensor lineament fields and the concordance diagnostic.

The synthetic cases are deliberately small and analytic: a vertical step edge has a known
lineament azimuth (vertical, because the gradient is horizontal), an isotropic random field
has near-zero coherence, and two families with the same azimuth must be counted as agreeing
while two perpendicular families must not.
"""

import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from gems51 import structfield


def _step_edge(n: int = 80) -> np.ndarray:
    layer = np.zeros((n, n), dtype=np.float32)
    layer[:, n // 2:] = 1.0
    return layer


def _strength_and_angle(layer: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    layer = np.where(layer > 0, layer, np.nan)
    return structfield.layer_lineament(layer, np.ones(layer.shape, bool))


def test_step_edge_produces_a_lineament_with_the_expected_azimuth():
    strength, angle, coherence = _strength_and_angle(_step_edge())
    # average along the edge and ignore the outer 10 px, where np.gradient's one-sided
    # difference at the array border adds an artefact ridge
    interior = strength[10:-10, :]
    profile = interior.mean(axis=0)
    edge_peak = int(np.argmax(profile))
    assert 36 <= edge_peak <= 44  # the 1 px step is smoothed to a narrow ridge
    assert profile[edge_peak] > 3.0 * profile[:20].mean()
    # the gradient of a vertical step points horizontally, so the lineament is vertical
    azimuth = np.degrees(angle)[40, edge_peak] % 180.0
    assert min(abs(azimuth - 90.0), abs(azimuth - 90.0 + 180.0)) < 12.0
    assert coherence[40, edge_peak] > 0.9


def test_a_coherent_edge_scores_higher_coherence_than_isotropic_noise():
    """Coherence alone is not a threshold (isotropic noise still has a Rayleigh-like
    ratio); what matters is that a real edge sits far above the noise population."""
    rng = np.random.default_rng(7)
    noise = rng.normal(size=(80, 80)).astype(np.float32)
    _, _, noise_coherence = structfield.layer_lineament(noise, np.ones(noise.shape, bool))
    _, _, edge_coherence = _strength_and_angle(_step_edge())
    assert float(np.median(noise_coherence)) < 0.6
    assert float(np.percentile(noise_coherence, 99)) < 0.95
    assert float(edge_coherence[40, 40]) > 0.99


def test_concordance_counts_two_agreeing_families_but_not_perpendicular_ones():
    layer = _step_edge()
    valid = np.ones(layer.shape, dtype=bool)
    base = structfield.layer_lineament(np.where(layer > 0, layer, np.nan), valid)
    rotated = np.rot90(np.where(layer > 0, layer, np.nan)).copy()
    other = structfield.layer_lineament(rotated, valid)
    agreeing = {
        "a": {"strength": base[0], "angle": base[1], "coherence": base[2]},
        "b": {"strength": base[0], "angle": base[1], "coherence": base[2]},
    }
    count, _, info = structfield.concordance(agreeing, valid, strength_percentile=90.0)
    assert info["cells_with_2plus_families"] > 0
    assert count.max() == 2
    perpendicular = {
        "a": {"strength": base[0], "angle": base[1], "coherence": base[2]},
        "b": {"strength": other[0], "angle": other[1], "coherence": other[2]},
    }
    count_perp, _, info_perp = structfield.concordance(perpendicular, valid, strength_percentile=90.0)
    assert info_perp["cells_with_2plus_families"] < info["cells_with_2plus_families"]


def test_concordance_is_shape_agnostic_and_fuse_is_bounded():
    layer = _step_edge(40)
    valid = np.ones(layer.shape, dtype=bool)
    s, a, c = structfield.layer_lineament(np.where(layer > 0, layer, np.nan), valid)
    fams = {"a": {"strength": s, "angle": a, "coherence": c},
            "b": {"strength": s * 0.5, "angle": a, "coherence": c}}
    count, best_angle, _ = structfield.concordance(fams, valid)
    assert count.shape == valid.shape
    belief = structfield.fuse(fams, count)
    assert belief.shape == valid.shape
    assert 0.0 <= float(belief.min()) and float(belief.max()) <= 1.0
