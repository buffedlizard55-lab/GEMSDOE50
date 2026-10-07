"""Tests for H61: the metric-algebra correction and the seismic-lineation pipeline."""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pytest
from rasterio.transform import Affine

from gemsdoe50 import h61
from gemsdoe50.metric import distance_weighted_tversky

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))


# --------------------------------------------------------------------------- metric algebra
def _line_case(offset_px: int, spacing: int) -> tuple[np.ndarray, np.ndarray]:
    """160-px vertical fault, dots every ``spacing`` px at ``offset_px``, plus 200 far FP dots."""
    truth = np.zeros((200, 200), dtype=bool)
    truth[20:180, 100] = True
    pred = np.zeros((200, 200), dtype=np.float32)
    pred[20:180:spacing, 100 + offset_px] = 1.0
    for r in range(20, 100, 4):
        for c in range(150, 190, 4):
            pred[r, c] = 1.0  # 20 x 10 = 200 dots, all > 3 px from the fault
    return truth, pred


@pytest.mark.parametrize(
    ("offset", "spacing", "official", "collapse"),
    [(0, 3, 0.6462, 0.6972), (1, 3, 0.4844, 0.5147), (0, 6, 0.4348, 0.4614)],
)
def test_official_score_is_not_the_claimed_exact_collapse(offset, spacing, official, collapse):
    truth, pred = _line_case(offset, spacing)
    res = distance_weighted_tversky(truth, pred)
    n = res.prediction_cells
    g = res.truth_cells
    t = res.tp_weight
    m = n - res.fp_weight  # sum of K at the prediction cells
    corrected = t / (0.2 * n + 0.8 * g + 0.2 * (t - m))
    claimed = t / (0.2 * n + 0.8 * g)
    assert res.score == pytest.approx(corrected, abs=1e-9)
    assert res.score == pytest.approx(official, abs=5e-4)
    assert claimed == pytest.approx(collapse, abs=5e-4)
    assert claimed - res.score > 0.02  # the repo's "exact" formula overstates the score


@pytest.mark.parametrize(("spacing", "per_dot"), [(1, 1.0), (2, 5 / 3), (3, 7 / 3), (4, 8 / 3), (5, 3.0), (6, 3.0)])
def test_dots_compete_below_six_pixels(spacing, per_dot):
    """Per-dot credit on a long straight fault; 3 px spacing is *not* competition-free."""
    truth = np.zeros((7, 400), dtype=bool)
    truth[3, :] = True
    pred = np.zeros_like(truth, dtype=np.float32)
    pred[3, 60:340:spacing] = 1.0
    res = distance_weighted_tversky(truth, pred)
    n = int(pred.sum())
    # interior credit per dot (edges add < 1 dot's worth of extra credit at each end)
    assert res.tp_weight / n == pytest.approx(per_dot, abs=4.0 / n + 1e-6)


# --------------------------------------------------------------------------- fast scorer
def test_fast_scorer_matches_official_instrument():
    import build_h61

    rng = np.random.default_rng(1)
    truth = np.zeros((120, 130), dtype=bool)
    truth[10:110, 40] = True
    truth[60, 20:120] = True
    pred = np.zeros_like(truth)
    pred.ravel()[rng.choice(truth.size, 300, replace=False)] = True
    core = np.zeros_like(truth)
    core[20:90, 15:100] = True
    sc = build_h61.FastScorer(truth)
    best = sc.best(pred)
    for te, pe in ((None, None), (core, core)):
        fast = sc.components(pred, best, te, pe)["score"]
        off = distance_weighted_tversky(truth, pred.astype(np.float32), truth_eval_mask=te,
                                        prediction_eval_mask=pe).score
        assert fast == pytest.approx(off, abs=1e-9)


# --------------------------------------------------------------------------- declustering
def test_zbz_flags_aftershocks_and_keeps_background():
    rng = np.random.default_rng(7)
    n_bg = 400
    bx, by = rng.uniform(0, 200, n_bg), rng.uniform(0, 200, n_bg)
    bt = np.sort(rng.uniform(0, 40, n_bg))
    bm = np.full(n_bg, 2.0)
    # one M6 mainshock at t=20 y with 150 aftershocks within 3 km and 0.5 y
    ax, ay = 100 + rng.normal(0, 1.0, 150), 100 + rng.normal(0, 1.0, 150)
    at = 20.0 + rng.exponential(0.05, 150)
    am = np.full(150, 2.0)
    x = np.concatenate([bx, [100.0], ax])
    y = np.concatenate([by, [100.0], ay])
    t = np.concatenate([bt, [20.0], at])
    m = np.concatenate([bm, [6.0], am])
    eta, parent = h61.zbz_nearest_neighbour(x, y, t, m)
    finite = np.isfinite(eta)
    gmm = h61._gmm_threshold(np.log10(eta[finite]))
    clustered = finite & (np.log10(np.where(finite, eta, 1.0)) < gmm["threshold"])
    after = np.arange(n_bg + 1, n_bg + 151)
    assert clustered[after].mean() > 0.9
    assert clustered[:n_bg].mean() < 0.2
    assert (parent[after] >= 0).all()


def test_triangle_keep_prefers_collinear_clusters():
    # A diagonal line: its x and y marginals are both spread, so the coordinate-permuted
    # reference does not collapse into a dense patch (an axis-parallel line would).
    rng = np.random.default_rng(3)
    s = np.linspace(10_000, 15_000, 200)
    line = np.column_stack([s, s + rng.normal(0, 20, 200)])
    bg = rng.uniform(0, 50_000, size=(400, 2))
    keep, rep = h61.triangle_keep(np.vstack([line, bg]))
    assert keep[:200].mean() > 0.8
    assert keep[200:].mean() < 0.2
    assert "UNVERIFIED" in rep["status"]


def test_triangle_reference_collapses_for_axis_parallel_lines():
    """Documented limitation: permuting x and y keeps both marginals, so an axis-parallel
    cluster recreates a dense patch in the reference and the 5 % rule becomes strict."""
    rng = np.random.default_rng(3)
    line = np.column_stack([np.linspace(0, 5000, 200), 2000 + rng.normal(0, 20, 200)])
    bg = rng.uniform(0, 50_000, size=(200, 2))
    keep, _ = h61.triangle_keep(np.vstack([line, bg]))
    assert keep[:200].mean() < 0.8


# --------------------------------------------------------------------------- lineations / corridors
def _events(x, y, depth=6.0, herr=0.3):
    n = x.size
    return h61.Events(
        x=x, y=y, depth_km=np.full(n, depth), mag=np.full(n, 2.0), t_years=np.arange(n, dtype=float),
        herr_km=np.full(n, herr), derr_km=np.full(n, 1.0), herr_imputed=np.zeros(n, dtype=bool),
    )


def test_lineation_recovers_azimuth_and_rejects_blobs():
    rng = np.random.default_rng(11)
    s = np.linspace(-7000, 7000, 20)  # ~740 m spacing: 12 neighbours span ~8 km
    az = np.deg2rad(30.0)
    x = 300_000 + s * np.cos(az) + rng.normal(0, 50, s.size)
    y = 4_300_000 + s * np.sin(az) + rng.normal(0, 50, s.size)
    lins, _rep = h61.neighbourhood_lineations(_events(x, y))
    assert len(lins) >= 1
    ang = np.degrees(np.arctan2(lins.uy, lins.ux)) % 180.0
    assert np.all(np.minimum(np.abs(ang - 30.0), 180.0 - np.abs(ang - 30.0)) < 5.0)
    blob = _events(300_000 + rng.normal(0, 1500, 80), 4_300_000 + rng.normal(0, 1500, 80))
    lins2, _ = h61.neighbourhood_lineations(blob)
    assert len(lins2) == 0


def test_frozen_length_rule_rejects_dense_lines():
    """Documented design flaw of the frozen constants (see the post-run section of the
    preregistration): 12 nearest neighbours of a dense sequence span too little length to
    pass sqrt(lambda1 - sigma^2) >= 1 km, so dense, clearly linear seismicity is rejected."""
    rng = np.random.default_rng(11)
    s = np.linspace(-4000, 4000, 60)  # ~135 m spacing
    x = 300_000 + s * np.cos(0.5) + rng.normal(0, 50, s.size)
    y = 4_300_000 + s * np.sin(0.5) + rng.normal(0, 50, s.size)
    lins, rep = h61.neighbourhood_lineations(_events(x, y))
    assert len(lins) == 0
    assert rep["fail_length"] == rep["neighbourhoods_with_min_events"]


def test_corridor_geometry_updip_offset():
    lins = h61.Lineations(
        cx=np.array([0.0]), cy=np.array([0.0]), ux=np.array([0.0]), uy=np.array([1.0]),
        half_len_m=np.array([3000.0]), sigma_loc_km=np.array([0.3]), z_km=np.array([5.0]),
        sz_km=np.array([1.0]), n_events=np.array([10]), elongation=np.array([5.0]),
    )
    cors = h61.corridor_geometry(lins)
    assert [c["kind"] for c in cors] == [0, 1, 2]
    expected = 5.0 / np.tan(np.deg2rad(60.0)) * 1000.0
    assert abs(cors[1]["offset_m"]) == pytest.approx(expected)
    assert cors[1]["cx"] == pytest.approx(-expected)  # normal of a north axis points west
    assert cors[0]["half_w_m"] == pytest.approx(300.0)
    assert h61.W_U_KM[0] * 1000 <= cors[1]["half_w_m"] <= h61.W_U_KM[1] * 1000


def test_snap_moves_dots_onto_the_ridge_inside_the_corridor():
    shape = (100, 100)
    transform = Affine(100.0, 0.0, 0.0, 0.0, -100.0, 10_000.0)
    ridge = np.zeros(shape, dtype=np.float32)
    ridge[:, 57] = 1.0  # ridge 7 px east of the corridor axis at column 50
    eligible = np.ones(shape, dtype=bool)
    cor = [{"lineation": 0, "kind": 0, "ux": 0.0, "uy": 1.0, "cx": 5050.0, "cy": 5000.0,
            "half_len_m": 3000.0, "half_w_m": 1000.0, "offset_m": 0.0}]
    cand = h61.snap_corridor_dots(cor, ridge, eligible, transform)
    assert cand["rows"].size > 10
    assert np.all(cand["cols"] == 57)
    acc = h61.greedy_spaced(cand["rows"], cand["cols"], cand["vals"], shape)
    r = cand["rows"][acc]
    assert np.all(np.diff(np.sort(r)) >= 3)
    union = h61.corridor_union(cor, shape, transform)
    assert union[50, 50] and union[50, 59] and not union[50, 61]


def test_stratified_enrichment_detects_informative_corridor():
    rng = np.random.default_rng(5)
    belief = rng.uniform(size=(60, 60)).astype(np.float32)
    corridor = np.zeros((60, 60), dtype=bool)
    corridor[:, :20] = True
    k = np.where(corridor, 0.5, 0.1).astype(np.float32)
    enr = h61.stratified_corridor_enrichment(k, belief, corridor, np.ones((60, 60), dtype=bool))
    assert enr["median_ratio"] == pytest.approx(5.0)
    assert enr["strata_with_ratio_gt_1"] == 10
