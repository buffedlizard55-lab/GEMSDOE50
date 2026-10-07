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
    tracked = [ROOT / name for name in (
        "index.html", "results.html", "methods.html", "submission.html", "site.css"
    )]
    before = {path: path.read_bytes() for path in tracked}
    subprocess.run(
        [sys.executable, str(ROOT / "scripts/build_h55_site.py")],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    assert {path: path.read_bytes() for path in tracked} == before

    index = (ROOT / "index.html").read_text(encoding="utf-8")
    assert "Download portal-safe TIFF" in index
    assert index.index("Download portal-safe TIFF") < index.index("Executive summary")
    assert "NO SLOT" in index
    assert "0.019551" in index and "0.115822" in index
    assert "0.2778" in index and "UNSCORED" in index


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
        assert int(np.count_nonzero(zero)) == 13_710
        np.testing.assert_array_equal(zero > 0, np.isfinite(nan) & (nan > 0))

    with np.load(ROOT / "registry/prior_positive_union.npz", allow_pickle=False) as prior:
        shape = tuple(int(value) for value in prior["shape"])
        union = np.unpackbits(prior["packed"])[: int(np.prod(shape))].reshape(shape).astype(bool)
    assert not np.any((zero > 0) & union)
    assert report["prior_pixel_exclusion"]["candidate_exact_overlap_with_union"] == 0
