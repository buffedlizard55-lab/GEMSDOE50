from pathlib import Path

import numpy as np
import pytest
import rasterio
from rasterio.transform import Affine

from gemsdoe50.catalog import CatalogEvents
from gemsdoe50.controls import build_smoothed_density_control


def _events() -> CatalogEvents:
    return CatalogEvents(
        evid=np.array([1, 2, 3]),
        year=np.array([2020, 2021, 2022]),
        latitude=np.zeros(3),
        longitude=np.zeros(3),
        depth_km=np.zeros(3),
        magnitude=np.ones(3),
        relocated=np.array([1, 1, 0], dtype=np.uint8),
        x_m=np.zeros(3),
        y_m=np.zeros(3),
        row=np.array([5, 6, 15]),
        col=np.array([5, 6, 15]),
        metadata={},
    )


def _template(path: Path, valid: np.ndarray) -> None:
    values = np.where(valid, 0.0, np.nan).astype(np.float32)
    with rasterio.open(
        path,
        "w",
        driver="GTiff",
        width=valid.shape[1],
        height=valid.shape[0],
        count=1,
        dtype="float32",
        crs="EPSG:32611",
        transform=Affine(100, 0, 500000, 0, -100, 4100000),
        nodata=np.nan,
    ) as output:
        output.write(values, 1)


def test_smoothed_density_uses_only_relocated_events_and_respects_valid_mask(tmp_path: Path):
    valid = np.ones((20, 20), dtype=bool)
    valid[0, 0] = False
    template = tmp_path / "template.tif"
    _template(template, valid)

    density, metadata = build_smoothed_density_control(_events(), template, sigma_m=200.0)

    assert density.dtype == np.float32
    assert density.shape == valid.shape
    assert density.max() == pytest.approx(1.0)
    assert density[0, 0] == 0
    assert density[5, 5] > density[15, 15]
    assert np.all((density >= 0) & (density <= 1))
    assert metadata["events_used"] == 2


def test_smoothed_density_rejects_events_outside_valid_footprint(tmp_path: Path):
    valid = np.ones((20, 20), dtype=bool)
    valid[5, 5] = False
    template = tmp_path / "template.tif"
    _template(template, valid)

    with pytest.raises(ValueError, match="outside the valid density-control footprint"):
        build_smoothed_density_control(_events(), template, sigma_m=200.0)
