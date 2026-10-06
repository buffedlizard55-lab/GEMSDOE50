from pathlib import Path

import numpy as np
import rasterio
from rasterio.transform import Affine

from gemsdoe50.catalog import CatalogEvents
from gemsdoe50.geometry import LineamentConfig, extract_h50s1_lineaments


def _synthetic_events() -> CatalogEvents:
    rng = np.random.default_rng(81)
    n = 48
    along = np.linspace(-2200, 2200, n)
    x = 500500 + rng.normal(0, 20, n)
    y = 3995000 + along
    depth = 6.0 + rng.normal(0, 0.25, n)
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


def test_surface_plane_projection_produces_stable_lineament(tmp_path: Path):
    template = tmp_path / "template.tif"
    transform = Affine(100, 0, 500000, 0, -100, 4000000)
    with rasterio.open(
        template,
        "w",
        driver="GTiff",
        width=100,
        height=100,
        count=1,
        dtype="float32",
        crs="EPSG:32611",
        transform=transform,
        nodata=np.nan,
    ) as dst:
        dst.write(np.zeros((100, 100), dtype=np.float32), 1)

    result = extract_h50s1_lineaments(
        _synthetic_events(),
        str(template),
        LineamentConfig(bootstrap_replicates=16),
    )
    assert result.metadata["counts"]["accepted_segments"] > 0
    assert result.metadata["positive_score_cells"] > 0
    assert 0 < result.score.max() <= 1
    # The vertical synthetic plane should project to its x≈500.5 km trace.
    positive = np.argwhere(result.score > 0)
    mean_col = float(positive[:, 1].mean())
    assert abs(mean_col - 5.0) < 2.0
