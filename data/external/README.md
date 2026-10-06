# External data: what is committed, what is restored, and how

| file | committed | bytes | sha256 |
|---|---|---|---|
| `usgs_comcat_earthquakes.csv.gz` | yes | 9,473,544 | see `registry/sources.json` |
| `derived_sgmc_faults_100m_u8.tif` | yes | 213,034 | see `registry/sources.json` |
| `lidar_scarp_features_u8.tif` | **no** — 37 MB | 36,943,606 | `d580bb8bdcdb941e32fefb8b38044bc5bf04e199bf2e83498c3576e6fc465568` |
| `geodawn_rad_u8.tif` | **no** — 27 MB | 26,612,970 | `c22420f75999030d7cc65c9e31e50d232ea6158423bca051613a18a8b20ba682` |

The two large rasters are quantised derivatives of official USGS products (USGS 3DEP 1 m DEM
tiles; GeoDAWN airborne radiometrics, DOI 10.5066/P93LGLVQ). They are kept out of git to respect
the repository's size conventions; the sibling repository `buffedlizard55-lab/GEMSDOE24` carries
byte-identical copies under `data/external/`, and the official products can be re-fetched from
the URLs in `registry/sources.json`. Verify a restored copy with:

```bash
sha256sum data/external/lidar_scarp_features_u8.tif data/external/geodawn_rad_u8.tif
```

`scripts/build_submission.py` reads them through `scripts/prepare_data.py`; if they are absent the
script names the two hashes above and stops rather than silently building a different file.
