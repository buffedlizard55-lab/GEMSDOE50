from pathlib import Path
from urllib.parse import parse_qs, urlparse

import numpy as np
import pytest
import rasterio
from rasterio.transform import Affine

from scripts.download_3dep_dem import IMAGE_SERVER, build_export_url


def _template(path: Path, *, pixel_size: float = 100.0, epsg: int = 32611) -> None:
    data = np.zeros((20, 30), dtype=np.float32)
    with rasterio.open(
        path,
        "w",
        driver="GTiff",
        width=30,
        height=20,
        count=1,
        dtype="float32",
        crs=f"EPSG:{epsg}",
        transform=Affine(pixel_size, 0, 500000, 0, -pixel_size, 4000000),
        nodata=np.nan,
    ) as output:
        output.write(data, 1)


def test_3dep_export_request_preserves_exact_template_grid(tmp_path: Path):
    template = tmp_path / "template.tif"
    _template(template)

    url, metadata = build_export_url(template)
    query = parse_qs(urlparse(url).query)

    assert url.startswith(f"{IMAGE_SERVER}/exportImage?")
    assert query["bboxSR"] == ["32611"]
    assert query["imageSR"] == ["32611"]
    assert query["size"] == ["30,20"]
    assert query["format"] == ["tiff"]
    assert query["pixelType"] == ["F32"]
    assert query["f"] == ["image"]
    assert metadata["grid"]["width"] == 30
    assert metadata["grid"]["height"] == 20
    assert metadata["grid"]["transform"] == list(Affine(100, 0, 500000, 0, -100, 4000000))


def test_3dep_export_rejects_non_100m_template(tmp_path: Path):
    template = tmp_path / "template.tif"
    _template(template, pixel_size=30)

    with pytest.raises(ValueError, match="expected 100 m"):
        build_export_url(template)


def test_3dep_export_rejects_wrong_crs(tmp_path: Path):
    template = tmp_path / "template.tif"
    _template(template, epsg=4326)

    with pytest.raises(ValueError, match="EPSG:32611"):
        build_export_url(template)
