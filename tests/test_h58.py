"""Tests for the H58 ComCat point-geometry pipeline. No network or big data required."""
from __future__ import annotations

import gzip

import numpy as np
import pandas as pd
import pytest
import rasterio
from rasterio.transform import from_origin

from gemsdoe50 import h56, h58

CSV_COLUMNS = [
    "time", "latitude", "longitude", "depth", "mag", "magType", "nst", "gap", "dmin",
    "rms", "net", "id", "updated", "place", "type", "horizontalError", "depthError",
    "magError", "magNst", "status", "locationSource", "magSource",
]


def _write_csv(path, rows):
    df = pd.DataFrame(rows, columns=CSV_COLUMNS)
    df.to_csv(path, index=False)


def _row(lon, lat, mag=2.0, depth=8.0, etype="earthquake", herr=0.5, t="2020-01-01T00:00:00.000Z"):
    return {
        "time": t, "latitude": lat, "longitude": lon, "depth": depth, "mag": mag,
        "magType": "ml", "nst": 10, "gap": 50.0, "dmin": 1.0, "rms": 0.2, "net": "nn",
        "id": "x1", "updated": t, "place": "test", "type": etype, "horizontalError": herr,
        "depthError": 0.3, "magError": 0.1, "magNst": 5, "status": "reviewed",
        "locationSource": "nn", "magSource": "nn",
    }


def _row_at(x_m, y_m, **kw):
    """A catalog row whose UTM position is exactly (x_m, y_m) inside the template."""
    from pyproj import Transformer

    lon, lat = Transformer.from_crs("EPSG:32611", "EPSG:4326", always_xy=True).transform(x_m, y_m)
    return _row(lon, lat, **kw)


def _template(path, shape=(200, 200)):
    profile = {
        "driver": "GTiff", "height": shape[0], "width": shape[1], "count": 1,
        "dtype": "float32", "crs": "EPSG:32611",
        "transform": from_origin(243350.0, 4508550.0, 100.0, 100.0),
    }
    with rasterio.open(path, "w", **profile) as dst:
        dst.write(np.zeros(shape, dtype=np.float32), 1)


def test_load_comcat_rejects_drifted_bytes(tmp_path):
    bad = tmp_path / "bad.csv.gz"
    with gzip.open(bad, "wt") as fh:
        fh.write("time,latitude\n2020-01-01,39.0\n")
    with pytest.raises(ValueError, match="hash mismatch"):
        h58.load_comcat(bad)


def test_anthropogenic_centres_extracts_blast_sites(tmp_path):
    csv = tmp_path / "cat.csv.gz"
    with gzip.open(csv, "wt", newline="") as fh:
        w = pd.DataFrame(
            [_row(-119.0, 39.0, etype="explosion"), _row(-119.5, 39.5, etype="earthquake")],
            columns=CSV_COLUMNS,
        )
        w.to_csv(fh, index=False)
    centres = h58._anthropogenic_centres(csv)
    assert centres.shape == (1, 2)


def _unpin(monkeypatch, csv_path):
    """Point the module's hash pin at the synthetic test extract."""
    import hashlib

    digest = hashlib.sha256(csv_path.read_bytes()).hexdigest()
    monkeypatch.setattr(h58, "COMCAT_SHA256", digest)


def test_build_event_frame_screens_projects_and_declusters(tmp_path, monkeypatch):
    csv = tmp_path / "cat.csv.gz"
    cx, cy = 243350.0 + 100.0 * 100, 4508550.0 - 100.0 * 100  # template centre
    rows = [
        _row_at(cx, cy),                                      # in grid, kept
        _row_at(cx, cy, mag=0.5),                             # below magnitude floor
        _row_at(cx - 15_000.0, cy, etype="quarry blast"),     # anthropogenic type (site far away)
        _row_at(cx, cy, depth=80.0),                          # too deep
        _row_at(cx, cy, herr=99.0),                           # location error too large
        _row_at(cx + 25_000.0, cy),                           # outside the grid rectangle
    ]
    _write_csv(csv, rows)
    _unpin(monkeypatch, csv)
    template = tmp_path / "template.tif"
    _template(template)
    frame, report = h58.build_event_frame(csv, template)
    # one tectonic, in-grid, M>=1.5, depth<25, h_err<=10 event survives the screens
    assert report["tectonic_screen"]["after_non_tectonic"] == 5
    assert report["footprint"]["events_in_bounds"] == 1
    assert len(frame) >= 1
    assert frame.metadata["catalog"]["rows"] == 6
    # declustering ran and recorded its diagnostics
    assert "decluster" in report
    assert report["events_after_decluster"] == len(frame)


def test_build_event_frame_applies_anthropogenic_site_buffer(tmp_path, monkeypatch):
    csv = tmp_path / "cat.csv.gz"
    # two tectonic events 1 km apart, one blast site between them
    cx, cy = 243350.0 + 100.0 * 100, 4508550.0 - 100.0 * 100  # template centre
    rows = [
        _row_at(cx - 400.0, cy),
        _row_at(cx + 400.0, cy),   # ~0.8 km east of the first
        _row_at(cx, cy, etype="mining explosion"),
    ]
    _write_csv(csv, rows)
    _unpin(monkeypatch, csv)
    template = tmp_path / "template.tif"
    _template(template)
    frame, report = h58.build_event_frame(csv, template)
    # the 3 km site buffer around the blast removes both nearby tectonic events
    assert report["anthropogenic_site_screen"]["events_removed"] == 2
    assert len(frame) == 0 or report["events_after_decluster"] == len(frame)


def test_corridor_belief_recovers_a_linear_cluster(tmp_path):
    template = tmp_path / "template.tif"
    _template(template, shape=(200, 200))
    with rasterio.open(template) as ds:
        shape = ds.shape
        transform = ds.transform
    rng = np.random.default_rng(3)
    x = np.linspace(243500.0, 243500.0 + 100 * 150, 40)
    y = np.full(40, 4_500_000.0) + rng.normal(0, 30.0, 40)
    frame = h58.EventFrame(
        x_m=x, y_m=y, sigma_km=np.full(40, 0.4), row=np.zeros(40, dtype=np.int32),
        col=np.zeros(40, dtype=np.int32), mag=np.ones(40, dtype=np.float32),
        time_days=np.arange(40, dtype=np.float64), year=np.full(40, 2020, dtype=np.int16),
        metadata={},
    )
    belief, lin, report = h58.corridor_belief(frame, shape, transform)
    assert len(lin) >= 1
    assert report["lineations"] == len(lin)
    assert float(belief.max()) <= 1.0
    assert float(belief.max()) > 0.0
    # the corridor lights up near the planted line (row of y = 4,500,000 m)
    row_line = int((transform.f - 4_500_000.0) / 100.0)
    band = belief[max(0, row_line - 3): row_line + 4, :]
    assert float(band.max()) > 0.5


def test_density_control_field_is_normalised_and_masked():
    frame = h58.EventFrame(
        x_m=np.zeros(4), y_m=np.zeros(4), sigma_km=np.ones(4),
        row=np.array([5, 5, 6, 60], dtype=np.int32),
        col=np.array([5, 6, 5, 60], dtype=np.int32),
        mag=np.ones(4, dtype=np.float32), time_days=np.zeros(4), year=np.ones(4, dtype=np.int16),
        metadata={},
    )
    valid = np.zeros((100, 100), dtype=bool)
    valid[10:20, 10:20] = True
    field = h58.density_control_field(frame, (100, 100), valid, sigma_m=500.0)
    assert float(field.max()) <= 1.0
    assert float(field.max()) > 0.0
    assert np.all(field[~valid] == 0.0)


def test_modelled_hidden_dti_formula_and_saturation():
    # c/dot 0.1, n = 30,000: T = 0.1 * (12226/61664) * 4.2 * 30000 = 2472.6...
    m = h58.modelled_hidden_dti(0.1, 30_000)
    expected_t = 0.1 * (h58.G_HIDDEN / h58.SGMC_OFF_TRUTH_PX) * h58.TRANSFER * 30_000
    assert abs(m["T_modelled"] - expected_t) < 1e-6
    assert abs(m["dti_modelled"] - expected_t / (0.2 * 30_000 + 0.8 * h58.G_HIDDEN)) < 1e-12
    assert not m["T_saturated"]
    # huge credit saturates at the physical cap T <= G
    big = h58.modelled_hidden_dti(10.0, 200_000)
    assert big["T_saturated"]
    assert abs(big["dti_modelled"] - h58.G_HIDDEN / (0.2 * 200_000 + 0.8 * h58.G_HIDDEN)) < 1e-12


def test_frozen_constants_are_preregistered():
    assert h58.MIN_MAG == 1.5
    assert h58.MAX_DEPTH_KM == 25.0
    assert h58.EMIT_MIN_SEP_PX == 3.0
    assert h58.TRIANGLE_SEED == 20_261_007
    assert h58.MASSES[0] == 30_000 and h58.MASSES[-1] == 220_000
    assert h58.G_HIDDEN == 12_226 and h58.TRANSFER == 4.2


def test_emit_respects_prior_union_exclusion():
    """The H58 emission domain is novel_allowed; the fixed emitter must stay inside it."""
    rng = np.random.default_rng(7)
    shape = (120, 120)
    belief = np.zeros(shape, dtype=np.float32)
    belief[10:110, 10:110] = rng.random((100, 100)).astype(np.float32) * 1e-7
    novel_allowed = np.zeros(shape, dtype=bool)
    novel_allowed[10:110, 10:110] = True
    novel_allowed[50:60, 50:60] = False  # a prior-union hole
    em = h56.emit_blue_noise(belief, novel_allowed, n_target=100, min_sep_px=3.0, seed=9)
    assert em.rows.size > 0
    assert novel_allowed[em.rows, em.cols].all()
