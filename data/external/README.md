# Legacy external-data inventory — not authorized H50-S1 inputs

> This inventory was inherited from earlier `main` work. H50-S1 does **not** consume the mixed-network ComCat extract, SGMC, the GEMSDOE24 LiDAR scarp derivative, radiometrics, or other legacy-derived files. The mixed ComCat extract's source-specific rights, challenge-rule shareability, `horizontalError` units/meaning, and location uncertainty remain unresolved. Its scheduled/manual refresh workflows are disabled. Do not use these files as H50-S1 inputs without new source and scientific review.
>
> The public raw download of the GEMSDOE24 12-band scarp raster is not permission to reuse it. Its source repository has no root `LICENSE` and GitHub reports `licenseInfo:null`; the derived raster is excluded unless its reuse rights are clarified. Public-domain status of raw USGS 3DEP products does not automatically license a third party's derivative.

The table records inherited file metadata, not approval or verification of the associated processing claims.

| file | committed | bytes | sha256 |
|---|---|---:|---|
| `usgs_comcat_earthquakes.csv.gz` | yes | 9,473,544 | see `registry/sources.json` |
| `derived_sgmc_faults_100m_u8.tif` | yes | 213,034 | see `registry/sources.json` |
| `lidar_scarp_features_u8.tif` | no — 37 MB | 36,943,606 | `d580bb8bdcdb941e32fefb8b38044bc5bf04e199bf2e83498c3576e6fc465568` |
| `geodawn_rad_u8.tif` | no — 27 MB | 26,612,970 | `c22420f75999030d7cc65c9e31e50d232ea6158423bca051613a18a8b20ba682` |

The two large rasters are quantized legacy derivatives (LiDAR scarp descriptors and GeoDAWN radiometrics). Their inherited metadata points to USGS source products, but the rights to the derived rasters and their suitability for challenge use must be checked independently. Do not fetch or restore them for the current H50-S1 run.

## ComCat metadata correction

The inherited ComCat extract contains multiple preferred contributors. USGS documentation defines `net` as the preferred contributor and `sources` as contributing networks; this does not establish that every row is a USGS-owned/public-domain record. NCEDC's data terms are non-transferable and the challenge/sponsor-sharing fit was not established. The inherited summary's statements that the entire extract is public domain and that `horizontalError` is a 1-sigma value in km were not verified and have been removed from the corrected summary. Treat the field as uninterpreted metadata until its units/statistical semantics are established for each source. H50-S1 does not use this extract.

The historic Python utilities `scripts/prepare_data.py` and `scripts/prepare_seisridge_data.py` describe restoration from public sources. Do not execute those legacy builders for H50-S1. The separate, rights-audited H50-S1 input path is documented in [`docs/research/data-rights-audit-20261006.md`](../../docs/research/data-rights-audit-20261006.md); it uses the CC BY 4.0 Nevada relocated catalog and a new, hash-pinned USGS 3DEP grid export.
