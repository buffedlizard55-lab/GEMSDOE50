import numpy as np
import pytest

from gemsdoe50.catalog import CatalogEvents
from scripts.run_experiment import _smoothed_density_control


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


def test_smoothed_density_uses_only_relocated_events_and_respects_valid_mask():
    valid = np.ones((20, 20), dtype=bool)
    valid[0, 0] = False
    density = _smoothed_density_control(
        _events(),
        valid,
        pixel_size_m=100.0,
        sigma_m=200.0,
    )

    assert density.dtype == np.float32
    assert density.shape == valid.shape
    assert density.max() == pytest.approx(1.0)
    assert density[0, 0] == 0
    assert density[5, 5] > density[15, 15]
    assert np.all((density >= 0) & (density <= 1))


def test_smoothed_density_rejects_events_outside_valid_footprint():
    valid = np.ones((20, 20), dtype=bool)
    valid[5, 5] = False
    with pytest.raises(ValueError, match="outside the valid density-control footprint"):
        _smoothed_density_control(
            _events(),
            valid,
            pixel_size_m=100.0,
            sigma_m=200.0,
        )
