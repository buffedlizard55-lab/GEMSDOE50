"""H59 regression tests.

Three groups:

1. The published metric.  The kernel profile and the closed form for unit-height
   binary predictions are properties of the organizers' definition, so they are
   asserted directly; the empty-truth branch that crashed the block bootstrap is
   pinned here so it cannot regress.
2. The delivered artifact.  Every format claim on the site is re-derived from the
   bytes on disk, because the historical portal rejection was a format failure and
   the whole point of the all-finite raster is that this cannot happen again.
3. The evidence chain.  Hashes, the receipt, the zip and the novelty gate are
   cross-checked against the committed registry, so a hand-edited number in a JSON
   file fails the suite.
"""

from __future__ import annotations

import hashlib
import json
import zipfile
from pathlib import Path

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[1]
BUILD = ROOT / "evidence/h59_build.json"
CHECK = ROOT / "evidence/h59_check.json"
VALID = ROOT / "evidence/h59_validation.json"
UNION = ROOT / "registry/prior_positive_union.npz"
LABELS = ROOT / "data/grid/labels.tif"

GRID = {"crs": "EPSG:32611", "width": 3292, "height": 3730,
        "transform": (100.0, 0.0, 243350.0, 0.0, -100.0, 4508550.0)}


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for blk in iter(lambda: fh.read(1 << 20), b""):
            h.update(blk)
    return h.hexdigest()


def _receipt() -> dict:
    if not BUILD.exists():
        pytest.skip("H59 build receipt absent")
    return json.loads(BUILD.read_text(encoding="utf-8"))


def _built_arrays():
    pytest.importorskip("rasterio")
    import rasterio

    rec = _receipt()
    allfin = ROOT / rec["files"]["allfinite_tif"]["path"]
    nanf = ROOT / rec["files"]["nan_tif"]["path"]
    if not allfin.exists() or not nanf.exists():
        pytest.skip("H59 rasters absent")
    with rasterio.open(allfin) as src:
        arr = src.read(1)
        profile = {
            "driver": src.driver, "count": src.count, "dtypes": src.dtypes,
            "crs": src.crs.to_string() if src.crs else None,
            "width": src.width, "height": src.height,
            "transform": tuple(round(float(v), 6) for v in tuple(src.transform)[:6]),
        }
    with rasterio.open(nanf) as src:
        nan_arr = src.read(1)
    return rec, arr, nan_arr, profile, allfin, nanf


# --------------------------------------------------------------------------- 1
def test_kernel_profile_is_the_published_triangle():
    from gems59.metric import kernel

    d = np.array([0.0, 1.0, 2.0, 3.0, 4.0])
    assert kernel(d) == pytest.approx([1.0, 2.0 / 3.0, 1.0 / 3.0, 0.0, 0.0])


def test_tp_plus_fn_equals_truth_mass_for_binary_predictions():
    from gems59.metric import evaluate

    rng = np.random.default_rng(0)
    truth = np.zeros((80, 80), bool)
    truth[20:60, 40] = True
    truth[45, 10:35] = True
    pred = (rng.random((80, 80)) < 0.02).astype(np.float32)
    parts = evaluate(pred, truth)
    assert parts.tp_w + parts.fn_w == pytest.approx(parts.n_truth, abs=1e-9)


def test_perfect_and_empty_predictions_bracket_the_metric():
    from gems59.metric import evaluate

    truth = np.zeros((60, 60), bool)
    truth[15:45, 30] = True
    assert evaluate(truth.astype(np.float32), truth).dti == pytest.approx(1.0, abs=1e-6)
    assert evaluate(np.zeros((60, 60), np.float32), truth).dti == 0.0


def test_binary_prediction_matches_the_closed_form():
    from gems59.metric import binary_identity, evaluate

    rng = np.random.default_rng(1)
    truth = (rng.random((90, 90)) < 0.01)
    pred = (rng.random((90, 90)) < 0.02).astype(np.float32)
    assert evaluate(pred, truth).dti == pytest.approx(binary_identity(pred, truth), abs=1e-9)


def test_empty_truth_tile_charges_the_whole_prediction_mass():
    """The branch that raised ``UnboundLocalError`` during the block bootstrap."""
    from gems59.metric import evaluate

    pred = np.zeros((32, 32), np.float32)
    pred[3, 4] = 1.0
    pred[10, 10] = 1.0
    parts = evaluate(pred, np.zeros((32, 32), bool))
    assert parts.tp_w == 0.0
    assert parts.fp_w == pytest.approx(2.0)
    assert parts.fn_w == 0.0
    assert parts.dti == 0.0


def test_scaling_all_probabilities_up_never_lowers_the_score():
    """DTI = cT / (0.8G + 0.2c(T + FP)) is increasing in c, so a uniform shrink is
    strictly bad: this is why the artifact keeps unit-height dots."""
    from gems59.metric import evaluate

    rng = np.random.default_rng(2)
    truth = np.zeros((70, 70), bool)
    truth[10:60, 35] = True
    base = (rng.random((70, 70)) < 0.05).astype(np.float32)
    full = evaluate(base, truth).dti
    for c in (0.25, 0.5, 0.9):
        assert evaluate(base * c, truth).dti < full


# --------------------------------------------------------------------------- 2
def test_delivered_raster_passes_the_plain_range_check():
    rec, arr, _nan, profile, _a, _n = _built_arrays()
    finite = np.isfinite(arr)
    assert finite.all(), "this artifact must contain no NaN or Inf at all"
    # the exact test that the portal is described as running
    assert float(np.min(arr)) >= 0.0
    assert float(np.max(arr)) <= 1.0
    assert int(((arr < 0) | (arr > 1)).sum()) == 0
    assert profile["count"] == 1
    assert profile["dtypes"][0] == "float32"
    assert profile["crs"] == GRID["crs"]
    assert (profile["width"], profile["height"]) == (GRID["width"], GRID["height"])
    assert profile["transform"] == GRID["transform"]
    assert rec["reread"]["in_range_check_plain_minmax"] is True


def test_nan_twin_keeps_the_sample_convention():
    rec, arr, nan_arr, _p, _a, _n = _built_arrays()
    import rasterio

    with rasterio.open(ROOT / rec["files"]["nan_tif"]["path"]) as src:
        labels = src.read(1, masked=False)
    footprint = np.isfinite(labels)
    assert np.isfinite(arr[footprint]).all()
    assert np.isnan(nan_arr[~footprint]).all()
    assert np.isnan(nan_arr[footprint]).sum() == 0


def test_values_are_binary_and_the_count_matches_the_receipt():
    rec, arr, _nan, _p, _a, _n = _built_arrays()
    values = np.unique(arr)
    assert values.tolist() == [0.0, 1.0]
    assert int((arr > 0).sum()) == rec["reread"]["positive_cells"] == rec["frozen"]["mass"]


def test_no_dot_on_the_catalogue_and_none_outside_the_footprint():
    _rec, arr, _nan, _p, _a, _n = _built_arrays()
    import rasterio

    with rasterio.open(LABELS) as src:
        labels = src.read(1)
    pos = arr > 0
    assert int((pos & (labels == 1)).sum()) == 0
    assert int((pos & (labels == -1)).sum()) == 0


# --------------------------------------------------------------------------- 3
def test_receipt_hashes_match_the_bytes_on_disk():
    rec, _arr, _nan, _p, allfin, nanf = _built_arrays()
    assert _sha256(allfin) == rec["files"]["allfinite_tif"]["sha256"]
    assert _sha256(nanf) == rec["files"]["nan_tif"]["sha256"]
    assert _sha256(ROOT / rec["files"]["zip"]["path"]) == rec["files"]["zip"]["sha256"]
    assert allfin.stat().st_size == rec["files"]["allfinite_tif"]["bytes"]


def test_zip_contains_exactly_the_all_finite_raster():
    rec = _receipt()
    zpath = ROOT / rec["files"]["zip"]["path"]
    if not zpath.exists():
        pytest.skip("zip absent")
    with zipfile.ZipFile(zpath) as zf:
        assert zf.namelist() == [Path(rec["files"]["allfinite_tif"]["path"]).name]


def test_novelty_gate_is_zero_exact_overlap_and_the_check_agrees():
    rec, arr, _nan, _p, _a, _n = _built_arrays()
    if not UNION.exists():
        pytest.skip("prior union absent")
    z = np.load(UNION)
    shape = tuple(int(x) for x in z["shape"])
    union = np.unpackbits(z["packed"])[: shape[0] * shape[1]].reshape(shape).astype(bool)
    assert int(((arr > 0) & union).sum()) == 0
    assert rec["dots_on_prior_union"] == 0
    chk = json.loads(CHECK.read_text(encoding="utf-8"))
    assert chk["uniqueness"]["exact_overlap_cells"] == 0
    assert chk["all_checks_pass"] is True
    assert chk["uniqueness"]["worst_block8_iou"] < 0.25


def test_validation_evidence_is_internally_consistent():
    v = json.loads(VALID.read_text(encoding="utf-8"))
    fm = v["frames"]["S_matched"]
    assert len(fm["folds"]) == 4
    assert all(f["dti"] > 0 for f in fm["folds"])
    boot = v["controls"]["paired_bootstrap_candidate_minus_uniform"]
    assert boot["ci95"][0] > 0, "the artifact must beat the control at the interval level"
    fra = v["controls"]["matched_mass_uniform_frozen_pool"]
    assert fra["eligible_cells"] == _receipt()["eligible_cells"]
    assert fm["dti"] > v["controls"]["matched_mass_uniform_matched_frame"]["mean"]


def test_site_renders_the_receipt_hash():
    """The published page must quote the receipt, not a hand-typed copy of it."""
    rec = _receipt()
    page = ROOT / "h59.html"
    if not page.exists():
        pytest.skip("site page absent")
    text = page.read_text(encoding="utf-8")
    assert rec["files"]["allfinite_tif"]["sha256"] in text
    assert rec["portal_name"] in text
    assert Path(rec["files"]["allfinite_tif"]["path"]).name in text
