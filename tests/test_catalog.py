from pathlib import Path

import numpy as np
import rasterio
from pyproj import Transformer
from rasterio.transform import Affine

from gemsdoe50.catalog import _parse_documented_record, read_nevada_catalog


def test_parse_documented_catalog_record_with_negative_measurements():
    record = '228175 "2008-01-01 02:35:14.260" 36.715770 -116.311330 9.172000 0.280000 1'
    parsed = _parse_documented_record(record, 2)
    assert parsed == (228175, 2008, 36.715770, -116.311330, 9.172, 0.28, 1)


def test_read_catalog_projects_and_filters_to_template(tmp_path: Path):
    template = tmp_path / "template.tif"
    catalog = tmp_path / "catalog.txt"
    transform = Affine(100, 0, 500000, 0, -100, 4000000)
    raster = np.zeros((20, 20), dtype=np.float32)
    raster[0, 0] = np.nan
    with rasterio.open(
        template,
        "w",
        driver="GTiff",
        width=20,
        height=20,
        count=1,
        dtype="float32",
        crs="EPSG:32611",
        transform=transform,
        nodata=np.nan,
    ) as dst:
        dst.write(raster, 1)

    transformer = Transformer.from_crs("EPSG:32611", "EPSG:4326", always_xy=True)
    lon, lat = transformer.transform(501050, 3998950)
    outside_lon, outside_lat = transformer.transform(520000, 3998950)
    catalog.write_text(
        "evid otime lat lon dep mag reloc\n"
        f'1001 "2019-05-10 12:00:00.000" {lat:.8f} {lon:.8f} 5.0 1.2 1\n'
        f'1002 "2020-01-01 00:00:00.000" {outside_lat:.8f} {outside_lon:.8f} 2.0 0.1 0\n',
        encoding="utf-8",
    )

    result = read_nevada_catalog(catalog, template)
    assert result.evid.tolist() == [1001]
    assert result.year.tolist() == [2019]
    assert result.relocated.tolist() == [1]
    assert result.metadata["source_event_rows"] == 2
    assert result.metadata["in_template_valid_cells"] == 1
    assert result.metadata["outside_template_or_nodata"] == 1
