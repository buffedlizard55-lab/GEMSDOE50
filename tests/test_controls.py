from pathlib import Path

import numpy as np
import pytest
import rasterio
from rasterio.transform import Affine

from gemsdoe50.catalog import CatalogEvents
from gemsdoe50.controls import build_smoothed_density_control


def _events() -> CatalogEvents:
    n = 3
    return CatalogEvents(
        evid=np.arange(n, dtype=np.int64),
        year=np.array([2010, 2012, 2015], dtype=np.int16),
        latitude=np.zeros(n),
        longitude=np.zeros(n),
        depth_km=np.ones(n, dtype=np.float32),
        magnitude=np.ones(n, dtype=np.float32),
        relocated=np.array([1, 1, 0], dtype=np.uint8),
        x_m=np.zeros(n, dtype=np.float64),
        y_m=np.zeros(n, dtype=np.float64),
        row=np.array([4, 4, 9], dtype=np.int32),
        col=np.array([4, 5, 9], dtype=np.int32),
        metadata={},
    )


def _template(path: Path, *, nodata: bool = False) -> None:
    values = np.zeros((12, 12), dtype=np.float32)
    if nodata:
        values[0, :] = np.nan
    with rasterio.open(
        path,
        "w",
        driver="GTiff",
        width=12,
        height=12,
        count=1,
        dtype="float32",
        crs="EPSG:32611",
        transform=Affine(100, 0, 500000, 0, -100, 4000000),
        nodata=np.nan,
    ) as output:
        output.write(values, 1)


def test_smoothed_density_control_uses_relocated_events_and_normalizes(tmp_path: Path):
    template = tmp_path / "template.tif"
    _template(template, nodata=True)

    score, metadata = build_smoothed_density_control(_events(), template, sigma_m=200)

    assert score.shape == (12, 12)
    assert np.isfinite(score).all()
    assert score.min() == 0.0
    assert score.max() == pytest.approx(1.0)
    assert score[4, 4] > score[8, 8]
    assert score[0, 5] == 0.0
    assert metadata["events_used"] == 2
    assert metadata["events_not_used"] == 0
    assert metadata["sigma_px"] == pytest.approx(2.0)
    assert len(metadata["score_map_sha256"]) == 64


def test_smoothed_density_control_rejects_empty_relocated_pool(tmp_path: Path):
    template = tmp_path / "template.tif"
    _template(template)
    events = _events()
    events = CatalogEvents(
        **{
            **events.__dict__,
            "relocated": np.zeros_like(events.relocated),
        }
    )

    with pytest.raises(ValueError, match="no relocated events"):
        build_smoothed_density_control(events, template)
