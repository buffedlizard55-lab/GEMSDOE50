from pathlib import Path

import numpy as np
import pytest
import rasterio
from rasterio.transform import Affine

from gemsdoe50.catalog import CatalogEvents
from gemsdoe50.geometry import LineamentConfig, extract_h50s1_lineaments


def _events(*, dipping: bool = False) -> CatalogEvents:
    rng = np.random.default_rng(81)
    if not dipping:
        n = 48
        along = np.linspace(-2200, 2200, n)
        x = 500500 + rng.normal(0, 20, n)
        y = 3995000 + along
        depth = 6.0 + rng.normal(0, 0.25, n)
    else:
        along = np.linspace(-2200, 2200, 12)
        dip = np.array([-300.0, -100.0, 100.0, 300.0])
        along_mesh, dip_mesh = np.meshgrid(along, dip, indexing="ij")
        x = (500500.0 + dip_mesh).ravel()
        y = (3995000.0 + along_mesh).ravel()
        # x + z is constant for the plane; z=-depth is positive-up.
        depth = (5.0 + dip_mesh / 1000.0).ravel()
        n = x.size
    years = np.resize(np.array([2008, 2011, 2016, 2021], dtype=np.int16), n)
    return CatalogEvents(
        evid=np.arange(n, dtype=np.int64),
        year=years,
        latitude=np.zeros(n),
        longitude=np.zeros(n),
        depth_km=depth.astype(np.float32),
        magnitude=np.ones(n, dtype=np.float32),
        relocated=np.ones(n, dtype=np.uint8),
        x_m=x.astype(np.float64),
        y_m=y.astype(np.float64),
        row=np.floor((4000000 - y) / 100).astype(np.int32),
        col=np.floor((x - 500000) / 100).astype(np.int32),
        metadata={},
    )


def _write_raster(path: Path, data: np.ndarray, transform: Affine) -> None:
    with rasterio.open(
        path,
        "w",
        driver="GTiff",
        width=data.shape[1],
        height=data.shape[0],
        count=1,
        dtype="float32",
        crs="EPSG:32611",
        transform=transform,
        nodata=np.nan,
    ) as dst:
        dst.write(data.astype(np.float32), 1)


def test_vertical_plane_intersects_constant_terrain_at_its_horizontal_trace(tmp_path: Path):
    template = tmp_path / "template.tif"
    dem = tmp_path / "dem.tif"
    transform = Affine(100, 0, 500000, 0, -100, 4000000)
    _write_raster(template, np.zeros((100, 100), dtype=np.float32), transform)
    _write_raster(dem, np.full((100, 100), 1000.0, dtype=np.float32), transform)

    result = extract_h50s1_lineaments(
        _events(),
        str(template),
        str(dem),
        LineamentConfig(bootstrap_replicates=16),
    )
    assert result.metadata["counts"]["accepted_segments"] > 0
    assert result.metadata["positive_score_cells"] > 0
    assert 0 < result.score.max() <= 1
    positive = np.argwhere(result.score > 0)
    mean_col = float(positive[:, 1].mean())
    assert abs(mean_col - 5.0) < 2.0
    assert result.metadata["surface_projection"]["datum_conversion_verified"] is False


def test_dipping_plane_intersects_local_dem_not_sea_level(tmp_path: Path):
    template = tmp_path / "template.tif"
    dem = tmp_path / "dem.tif"
    transform = Affine(100, 0, 490000, 0, -100, 4000000)
    _write_raster(template, np.zeros((100, 150), dtype=np.float32), transform)
    _write_raster(dem, np.full((100, 150), 2000.0, dtype=np.float32), transform)

    result = extract_h50s1_lineaments(
        _events(dipping=True),
        str(template),
        str(dem),
        LineamentConfig(bootstrap_replicates=12),
    )

    assert result.metadata["counts"]["accepted_segments"] > 0
    positive = np.argwhere(result.score > 0)
    mean_col = float(positive[:, 1].mean())
    # Plane is x + z = 495,500 m. At DEM elevation 2,000 m,
    # the terrain intersection is x=493,500 m (column 35), not the
    # invalid sea-level z=0 intersection at x=495,500 m (column 55).
    assert mean_col == pytest.approx(35.0, abs=2.0)
    assert abs(mean_col - 55.0) > 15.0


def test_surface_dem_must_exactly_match_template_grid(tmp_path: Path):
    template = tmp_path / "template.tif"
    dem = tmp_path / "dem.tif"
    _write_raster(template, np.zeros((100, 100), dtype=np.float32), Affine(100, 0, 500000, 0, -100, 4000000))
    _write_raster(dem, np.ones((100, 100), dtype=np.float32), Affine(100, 0, 500100, 0, -100, 4000000))

    with pytest.raises(ValueError, match="raster grid mismatch"):
        extract_h50s1_lineaments(_events(), str(template), str(dem))
