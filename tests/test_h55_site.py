from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from html.parser import HTMLParser
from pathlib import Path

import numpy as np
import rasterio

ROOT = Path(__file__).parents[1]
REPORT = ROOT / "evidence/results/h55s1-evaluation-20261007.json"


class _Links(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.hrefs: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag != "a":
            return
        values = dict(attrs)
        if values.get("href"):
            self.hrefs.append(str(values["href"]))


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_h55_site_regeneration_is_deterministic_and_download_first():
    tracked = [
        ROOT / name
        for name in ("index.html", "results.html", "methods.html", "submission.html", "site.css")
    ]
    before = {path: path.read_bytes() for path in tracked}
    # The committed pages are produced by the two generators in sequence (the same
    # order as the site workflow): build_h55_site.py regenerates from committed
    # evidence, then build_h58_site.py reproduces the H57-scarpstep session's
    # preserved band (docs/fragments/) and inserts this session's H58 band.
    subprocess.run(
        [sys.executable, str(ROOT / "scripts/build_h55_site.py")],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    subprocess.run(
        [sys.executable, str(ROOT / "scripts/build_h58_site.py")],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    # H59 adds the single "start here" band (recommended download + verdict) at the very
    # top, the errata, and regenerates the docs/ submission pages.
    subprocess.run(
        [sys.executable, str(ROOT / "scripts/build_h59_site.py")],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    assert {path: path.read_bytes() for path in tracked} == before

    index = (ROOT / "index.html").read_text(encoding="utf-8")
    assert "Download portal-safe TIFF" in index
    # Charter rule: a one-click download and the executive summary sit at the very top of the
    # site.  Later sessions may legitimately place their own download band above this one, so the
    # assertion is about ordering and presence, not about which session's artifact is first.
    # The current top band is the H57-scarpstep session's; the H56 band below it was reworded
    # to "Previous candidate (H56)" by that session, and this session's H58 band follows it.
    start = index.index("Download the recommended GeoTIFF (H57, portal-safe)")
    assert start < index.index('<section class="main" id="h57">')
    assert '<a class="skip" href="#start">' in index
    assert "reduces exactly to <code>DTI = T / (0.2N + 0.8G)</code>" not in index
    assert "GEMSDOE50-H57-SCARPSTEP" in index[: index.index('<section class="main" id="h57">')]
    first_download = index.index("Download the current research candidate GeoTIFF (H57)")
    assert start < first_download
    assert "Previous candidate (H56)" in index
    assert "GEMSDOE50-H58-SEISLINEAGE-98598-C4FF6DB9" in index
    assert first_download < index.index("Executive summary")
    assert index.index("Download portal-safe TIFF") > first_download
    assert "NO SLOT" in index
    assert "0.019321" in index and "0.115822" in index
    assert "0.2778" in index and "UNSCORED" in index
    assert "user-provided 0.3774 claim" in index
    assert "Draft optional note (use only after rights clearance)" in index
    assert "mixed-network ComCat-derived geometry" in index
    assert "H53-A probe/TMI experiment: NO-GO / NO SLOT" in index


def test_h55_site_local_links_exist():
    for page_name in ("index.html", "results.html", "methods.html", "submission.html"):
        parser = _Links()
        parser.feed((ROOT / page_name).read_text(encoding="utf-8"))
        for href in parser.hrefs:
            if href.startswith(("http://", "https://", "#")):
                continue
            target = href.split("#", 1)[0]
            assert (ROOT / target).is_file(), f"broken local link in {page_name}: {href}"


def test_h55_artifact_range_grid_and_prior_pixel_exclusion():
    report = json.loads(REPORT.read_text(encoding="utf-8"))
    zero_meta = report["artifacts"]["recommended_portal_safe_zero_outside"]
    nan_meta = report["artifacts"]["sample_semantics_nan_outside"]
    zero_path = ROOT / zero_meta["path"]
    nan_path = ROOT / nan_meta["path"]
    assert _sha256(zero_path) == zero_meta["sha256"]
    assert _sha256(nan_path) == nan_meta["sha256"]

    with rasterio.open(zero_path) as zero_ds, rasterio.open(nan_path) as nan_ds:
        zero = zero_ds.read(1)
        nan = nan_ds.read(1)
        assert zero_ds.count == nan_ds.count == 1
        assert zero_ds.dtypes[0] == nan_ds.dtypes[0] == "float32"
        assert str(zero_ds.crs) == str(nan_ds.crs) == "EPSG:32611"
        assert zero_ds.shape == nan_ds.shape == (3730, 3292)
        assert zero_ds.transform == nan_ds.transform
        assert np.all(np.isfinite(zero))
        assert float(zero.min()) == 0.0 and float(zero.max()) == 1.0
        assert set(np.unique(zero)) == {0.0, 1.0}
        assert int(np.count_nonzero(zero)) == 13_591
        np.testing.assert_array_equal(zero > 0, np.isfinite(nan) & (nan > 0))

    with np.load(ROOT / "registry/prior_positive_union.npz", allow_pickle=False) as prior:
        shape = tuple(int(value) for value in prior["shape"])
        union = np.unpackbits(prior["packed"])[: int(np.prod(shape))].reshape(shape).astype(bool)
    assert not np.any((zero > 0) & union)
    assert report["prior_pixel_exclusion"]["candidate_exact_overlap_with_union"] == 0


def test_h55_prior_receipt_includes_latest_main_artifacts_and_exact_copy_groups():
    receipt = json.loads(
        (ROOT / "evidence/results/h55-prior-corpus-receipt-20261007.json").read_text(
            encoding="utf-8"
        )
    )
    assert receipt["schema"] == "gemsdoe50.h55-prior-corpus-receipt.v3"
    assert receipt["all_sha256_verified"] is True
    assert receipt["all_source_assertions"] == 65
    assert receipt["registered_sibling_entries"] == 50
    assert receipt["local_prior_entries"] == 15
    assert receipt["unique_source_paths"] == 64
    assert receipt["unique_filenames"] == 62
    assert receipt["unique_sha256"] == 61
    assert receipt["unique_positive_masks"] == 34

    source_paths = {entry["source_path"] for entry in receipt["entries"]}
    for prefix in (
        "gems52-union-",
        "gems52a-scarpdrainage-",
        "gemsdoe50-h53-tmiconj-",
        "gems50-h54-corpuscal-",
    ):
        assert any(prefix in source_path for source_path in source_paths)
    exact_copy_groups = [set(group["source_paths"]) for group in receipt["byte_identical_groups"]]
    assert {
        "docs/downloads/gemsdoe50-h53-tmiconj-20261007T0345Z.tif",
        "downloads/gemsdoe50-h53-tmiconj-20261007T0345Z.tif",
    } in exact_copy_groups

    with np.load(ROOT / "registry/prior_positive_union.npz", allow_pickle=False) as prior:
        assert int(prior["registry_entries"]) == 50
        assert int(prior["local_prior_entries"]) == 15
        assert int(prior["all_source_entries"]) == 65
        assert len(prior["sha256"]) == 61
        assert len(set(prior["positive_mask_sha256"].tolist())) == 34
        assert int(prior["positive_cells"]) == 1_405_451


def test_h53a_is_published_only_as_a_no_go_audit_record():
    evidence = json.loads(
        (ROOT / "evidence/h53-validation-20261007.json").read_text(encoding="utf-8")
    )
    artifact = evidence["candidate"]["artifact"]
    path = ROOT / artifact["path"]
    assert evidence["status"] == "NO_SLOT"
    assert evidence["decision"]["candidate_promotes"] is False
    assert artifact["positive_cells"] == 0
    assert _sha256(path) == artifact["sha256"]

    with rasterio.open(path) as ds, rasterio.open(ROOT / "data/grid/sample_submission.tif") as sample:
        values = ds.read(1)
        valid = np.isfinite(sample.read(1))
        assert ds.count == 1 and ds.dtypes[0] == "float32"
        assert str(ds.crs) == "EPSG:32611"
        assert ds.shape == sample.shape == (3730, 3292)
        assert ds.transform == sample.transform
        assert np.isfinite(values[valid]).all()
        assert np.isnan(values[~valid]).all()
        assert np.all((values[valid] >= 0) & (values[valid] <= 1))
        assert np.count_nonzero(values[valid]) == 0

    index = (ROOT / "index.html").read_text(encoding="utf-8")
    results = (ROOT / "results.html").read_text(encoding="utf-8")
    submission = (ROOT / "submission.html").read_text(encoding="utf-8")
    assert "Separate H53-A probe/TMI experiment: NO-GO / NO SLOT" in index
    assert 'id="h53a-no-go"' in results
    assert "Audit-only H53-A GeoTIFF" in results
    assert "Do not upload this all-zero file" in results
    assert "H53-A probe/TMI experiment: NO-GO / NO SLOT" in submission


def test_h56_conditional_score_table_uses_the_documented_g_value():
    g = 12_226
    cases = [(0.2778, 37_654, 4_809), (0.3774, 30_000, 5_956),
             (0.3774, 44_090, 7_019), (0.3774, 108_000, 11_843)]
    for score, mass, expected_credit in cases:
        credit = round(score * (0.2 * mass + 0.8 * g))
        assert credit == expected_credit

    diagnosis = (ROOT / "docs/research/h56-diagnosis.md").read_text(encoding="utf-8")
    assert "37,654 | 4,809 | 39.3 % | 0.1277" in diagnosis
    assert "30,000 | 5,956 | 48.7 % | **0.199**" in diagnosis
    assert "44,090 | 7,019 | 57.4 % | 0.159" in diagnosis
    assert "108,000 | 11,843 | 96.9 % | 0.110" in diagnosis
