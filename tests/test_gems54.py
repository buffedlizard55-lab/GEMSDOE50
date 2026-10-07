"""Invariant tests for :mod:`gems54` (the corpus-calibrated prior + expected-DTI emitter).

Small synthetic grids only: the point of these tests is the *algebra and the layout rules*, which
must hold independently of the 12.3M-cell competition raster.  The repository-level hygiene tests at
the bottom re-open the shipped artifact's bytes when it exists, and skip (not pass) when it does not.
"""
from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

import numpy as np
import pytest

from gems54.emitter import emit_stratified
from gems54.field import masked_filter
from gems54.truthmodel import (ALPHA, BETA, EPS, dti_weighted, expected_max_kernel,
                              kernel_weights)

ROOT = Path(__file__).resolve().parents[1]


# ---------------------------------------------------------------- filtering at the data boundary
def test_masked_filter_does_not_invent_a_lineament_at_the_data_edge():
    """The defect this module exists to avoid.

    A constant field that simply *stops* being measured is indistinguishable, for an unmasked
    Gaussian filter, from a step edge - and a step edge is what a structure tensor reports as a
    lineament.  Normalised convolution must give a flat response instead.
    """
    h, w = 60, 60
    valid = np.zeros((h, w), dtype=bool)
    valid[10:50, 10:50] = True
    field = np.where(valid, 0.42, np.nan).astype(np.float32)

    from scipy.ndimage import gaussian_filter
    naive_smooth = gaussian_filter(np.nan_to_num(field, nan=0.0).astype(np.float32), 3.0)
    gy, gx = np.gradient(naive_smooth)
    ring_naive = float(np.abs(gy[10:50, 10]).max())

    smooth = masked_filter(field, valid, 3.0)
    gy2, gx2 = np.gradient(smooth)
    ring_masked = float(np.abs(gy2[12:48, 12:48]).max())

    assert ring_naive > 0.01, "the naive filter must show the artifact for the test to mean anything"
    assert ring_masked < 1e-6, f"masked smoothing leaked a {ring_masked:.3g} edge into the interior"
    assert np.all(np.isfinite(smooth))


def test_masked_filter_is_the_identity_on_a_constant_valid_field():
    valid = np.ones((20, 20), dtype=bool)
    valid[:5] = False
    field = np.full((20, 20), 0.7, dtype=np.float32)
    field[~valid] = np.nan
    out = masked_filter(field, valid, 2.0)
    interior = out[8:18, 4:18]
    assert np.allclose(interior, 0.7, atol=1e-5)


# ---------------------------------------------------------------- metric algebra
def test_kernel_levels_match_the_official_distance_weight():
    k = kernel_weights()
    c = k.shape[0] // 2
    assert k[c, c] == pytest.approx(1.0)
    assert k[c, c + 1] == pytest.approx(2.0 / 3.0)          # d = 1 px, R = 3 px
    assert k[c, c + 2] == pytest.approx(1.0 / 3.0)
    assert k[c, c + 3] == 0.0                                # d = R exactly -> zero
    assert k[c - 1, c + 1] == pytest.approx(1.0 - np.sqrt(2.0) / 3.0)


def test_expected_max_kernel_is_exact_for_a_single_truth_cell():
    """One Bernoulli(0.5) truth cell: E[max_x k] = 0.5 k(d) - no independence approximation."""
    q = np.zeros((11, 11), dtype=np.float32)
    q[5, 5] = 0.5
    em = expected_max_kernel(q)
    assert em[5, 5] == pytest.approx(0.5, abs=1e-6)
    assert em[5, 6] == pytest.approx(0.5 * (2.0 / 3.0), abs=1e-6)
    assert em[5, 9] == pytest.approx(0.0, abs=1e-6)
    assert em.max() <= 1.0 + 1e-6


def test_dti_closure_identity_holds_on_random_cases():
    """DTI must equal T / (alpha(T+F) + beta N); the emitter's stop rule is derived from this."""
    rng = np.random.default_rng(11)
    for _ in range(4):
        truth = (rng.random((40, 40)) < 0.02)
        pred = (rng.random((40, 40)) < 0.03)
        res = dti_weighted(pred, truth.astype(np.float32))
        t, f, n = res["tp"], res["fp"], float(truth.sum())
        closed = t / (ALPHA * (t + f) + BETA * n + EPS)
        assert res["dti"] == pytest.approx(closed, rel=1e-6, abs=1e-9)


def test_dominated_emission_is_never_preferred():
    """Adding a dot far from every truth pixel must lower DTI (the FP term is not optional)."""
    from scipy.ndimage import distance_transform_edt
    rng = np.random.default_rng(3)
    truth = (rng.random((40, 40)) < 0.02)
    truth[20, 20] = True                                   # guarantee one covered cell
    far = np.unravel_index(int(np.argmax(distance_transform_edt(~truth))), truth.shape)
    assert far != (20, 20) and distance_transform_edt(~truth)[far] > 4.0
    w = truth.astype(np.float32) * 0.9
    support = np.zeros((40, 40), dtype=bool)
    support[20, 20] = True
    base = dti_weighted(support, w)["dti"]
    support[far] = True                                    # >4 px from every truth pixel
    assert dti_weighted(support, w)["dti"] < base


# ---------------------------------------------------------------- stratified layout
def test_emit_stratified_places_one_dot_per_block_per_round():
    field = np.zeros((40, 40), dtype=np.float32)
    field[5:9, 5:9] = 1.0                       # a bright blob spanning four 4-px blocks
    field[20:35, 20:35] = 0.5                    # a broad, dimmer region
    blocks = {(r // 4, c // 4) for r, c in np.argwhere(field > 0)}
    assert len(blocks) == 20
    sup, info = emit_stratified(field, np.ones((40, 40), dtype=bool), 20, block=4)
    picked = {(r // 4, c // 4) for r, c in np.argwhere(sup)}
    assert info["mass"] == 20 and picked == blocks, \
        "round 1 must occupy every block exactly once, best block first"
    assert sup[5:9, 5:9].sum() == 4, "one dot per occupied block inside the bright blob"
    sup25, _ = emit_stratified(field, np.ones((40, 40), dtype=bool), 25, block=4)
    counts = np.bincount([b[0] * 10 + b[1] for b in
                          ((r // 4, c // 4) for r, c in np.argwhere(sup25))])
    assert counts.max() == 2, "a second dot per block only after every block has one"
    assert sup25.sum() == 25


def test_emit_stratified_rounds_and_degrades_to_topn():
    field = np.zeros((20, 20), dtype=np.float32)
    field[2, 2] = 3.0
    field[2, 3] = 2.0
    field[3, 2] = 1.0
    sup, info = emit_stratified(field, np.ones((20, 20), dtype=bool), 3, block=8)
    assert sup[2, 2] and sup[2, 3] and sup[3, 2]          # all three cells, one per round
    assert info["rounds"] == 3                             # one rank level per round
    # determinism: same input, same support (no hidden RNG)
    sup2, _ = emit_stratified(field, np.ones((20, 20), dtype=bool), 3, block=8)
    assert np.array_equal(sup, sup2)


def test_emit_stratified_respects_the_domain_mask():
    field = np.ones((20, 20), dtype=np.float32)
    allowed = np.zeros((20, 20), dtype=bool)
    allowed[10:14, 10:14] = True
    sup, info = emit_stratified(field, allowed, 4, block=4)
    assert sup.sum() == 4
    assert {(r // 4, c // 4) for r, c in np.argwhere(sup)} == {(2, 2), (2, 3), (3, 2), (3, 3)}
    sup_out, _ = emit_stratified(field, allowed, 40, block=4)
    assert sup_out.sum() == 16, "the emission saturates inside the domain instead of leaking out"
    assert not sup_out[~allowed].any(), "the emitter must not step outside the allowed domain"


def test_emit_stratified_rejects_a_block_larger_than_the_grid():
    with pytest.raises(ValueError):
        emit_stratified(np.ones((5, 5), dtype=np.float32), np.ones((5, 5), dtype=bool), 3, block=9)


# ---------------------------------------------------------------- shipped-artifact hygiene
SHIP = ROOT / "evidence" / "h54_ship.json"


@pytest.mark.skipif(not SHIP.exists(), reason="no H53 build evidence in this checkout")
def test_shipped_raster_matches_its_receipt_byte_for_byte():
    ship = json.loads(SHIP.read_text(encoding="utf-8"))
    path = ROOT / ship["outputs"]["primary_nan"]["path"]
    assert path.exists(), f"registry points at a missing file: {path}"
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    assert digest == ship["outputs"]["primary_nan"]["sha256"]
    import rasterio
    with rasterio.open(path) as ds:
        assert ds.count == 1 and ds.dtypes[0] == "float32"
        assert "32611" in str(ds.crs)
        assert (ds.height, ds.width) == (3730, 3292)
        a = ds.read(1)
    fin = np.isfinite(a)
    assert fin.sum() > 0 and a[fin].min() >= 0.0 and a[fin].max() <= 1.0
    assert int((a > 0).sum()) == ship["mass"]


@pytest.mark.skipif(not SHIP.exists(), reason="no H53 build evidence in this checkout")
def test_receipt_does_not_claim_a_score_and_registry_records_the_same_hash():
    ship = json.loads(SHIP.read_text(encoding="utf-8"))
    assert "not organizer-scored" in ship["submission_note"].lower()
    reg = json.loads((ROOT / "registry" / "submissions.json").read_text(encoding="utf-8"))
    entry = next((e for e in reg["submissions"] if e.get("name") == ship["submission_name"]), None)
    assert entry is not None, "the shipped artifact must be registered"
    assert entry["organizer_score"] is None and entry["submitted_utc"] is None
    assert entry["sha256"] == ship["outputs"]["primary_nan"]["sha256"]


@pytest.mark.skipif(not (ROOT / "index.html").exists(), reason="site not built in this checkout")
def test_every_download_raster_is_linked_from_the_site_or_the_registry():
    """The user must never have to guess which file to download.

    A raster that is *not* linked from the published page and *not* in the registry is a stale
    build left behind by an aborted run: it must be deleted or published, not parked here.
    """
    ship = json.loads(SHIP.read_text(encoding="utf-8")) if SHIP.exists() else None
    pages = "".join((ROOT / p).read_text(encoding="utf-8")
                    for p in ("index.html", "results.html", "submission.html", "methods.html")
                    if (ROOT / p).exists())
    reg = (ROOT / "registry" / "submissions.json").read_text(encoding="utf-8")
    orphans = []
    for tif in sorted((ROOT / "docs" / "downloads").glob("*.tif")):
        if tif.name not in pages and tif.name not in reg:
            orphans.append(tif.name)
    assert not orphans, f"unlinked rasters in docs/downloads (publish or delete): {orphans}"
    if ship:                                     # the current primary must be the *linked* one
        linked = re.findall(r'href="(docs/downloads/[^"]+\.tif)"', pages)
        assert ship["outputs"]["primary_nan"]["path"] in linked


@pytest.mark.skipif(not SHIP.exists(), reason="no H53 build evidence in this checkout")
def test_the_emission_domain_excludes_the_near_catalogue_and_the_data_edge():
    """Two hard rules of the design, checked against the shipped bytes, not against the code."""
    import rasterio
    from gems54.gridio import catalogue_distance, edge_distance_px, footprint
    ship = json.loads(SHIP.read_text(encoding="utf-8"))
    path = ROOT / ship["outputs"]["primary_nan"]["path"]
    with rasterio.open(path) as ds:
        sup = np.isfinite(ds.read(1)) & (ds.read(1) > 0)
    assert not (sup & (catalogue_distance() <= float(ship["domain"]["buffer_px"]))).any(), \
        "a dot sits inside the catalogue buffer the design promises to keep"
    assert not (sup & (edge_distance_px() <= float(ship["domain"]["edge_guard_px"]))).any(), \
        "a dot sits on the data-edge guard band where every filter is untrustworthy"
    assert not (sup & ~footprint()).any()
