from pathlib import Path

import numpy as np
import rasterio
from rasterio.transform import Affine

from gemsdoe50.raster import validate_submission, write_submission


def test_written_bytes_match_template_contract_and_range(tmp_path: Path):
    template = tmp_path / "template.tif"
    output = tmp_path / "candidate.tif"
    data = np.zeros((20, 30), dtype=np.float32)
    data[:, :2] = np.nan
    transform = Affine(100, 0, 500000, 0, -100, 4000000)
    with rasterio.open(
        template,
        "w",
        driver="GTiff",
        width=30,
        height=20,
        count=1,
        dtype="float32",
        crs="EPSG:32611",
        transform=transform,
        nodata=np.nan,
    ) as dst:
        dst.write(data, 1)
    valid = np.isfinite(data)
    prediction = np.zeros_like(data)
    prediction[5, 5] = 1.0
    prediction[6, 5] = 0.25
    report = write_submission(template, output, prediction, valid)
    reopened = validate_submission(output, template)
    assert report["sha256"] == reopened["sha256"]
    assert reopened["dtype"] == "float32"
    assert reopened["crs"] == "EPSG:32611"
    assert reopened["positive_cells"] == 2
    assert reopened["minimum_valid_value"] == 0.0
    assert reopened["maximum_valid_value"] == 1.0
    with rasterio.open(output) as ds:
        bytes_on_disk = ds.read(1)
    assert np.isnan(bytes_on_disk[:, :2]).all()
    assert np.isfinite(bytes_on_disk[:, 2:]).all()
