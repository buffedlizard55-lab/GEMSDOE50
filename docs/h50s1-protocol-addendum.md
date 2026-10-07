# H50-S1 implementation protocol addendum

**Version 2 — amended 2026-10-06 UTC, before any H50-S1 DTI was computed.** The initial draft incorrectly intersected a fitted hypocenter plane with sea-level `z=0` and did not include a same-event smoothed-density comparator. Review caught both problems before the Nevada catalog was scored. This amendment keeps the hypothesis ranking and statistical promotion thresholds fixed, replaces the invalid sea-level projection with an explicit terrain-elevation intersection, adds the matched density control, and separates the statistical holdout gate from scientific/submission eligibility. No H50-S1 DTI, result, or TIFF existed when this amendment was made.

The previous `z=0` method was not physically valid as a land-surface trace. Do not use its implementation or describe its output as a surface projection.

## Fixed candidate construction

| Parameter | Frozen value |
|---|---:|
| Catalog rows admitted | Only `reloc = 1`, retained only when the projected event falls in a finite template cell |
| Local neighborhood radius | 2,500 m |
| Fit-seed spacing | One occupied 500 m cell |
| Event de-duplication | One observation per 250 m cell per origin year |
| Minimum neighborhood support | 10 de-duplicated events across at least 2 distinct years |
| Horizontal geometry | PCA linearity ≥ 0.70; 4σ minor-axis width ≤ 1,200 m; 5th–95th percentile trace length ≥ 1,500 m |
| Robust plane fit | Up to 3 orthogonal-residual trimming iterations using median + 3 × (1.4826 × MAD); at least 10 inliers must remain |
| 3-D geometry | Planarity ≥ 0.45; plane normal's horizontal norm ≥ 0.20; projected strike alignment with horizontal event axis ≥ 0.65 |
| Depth plausibility | Median event depth ≤ 20 km |
| Terrain intersection | Per-strike positions at ≤50 m spacing; bilinear DEM sampling; bracketed root search along the plane's horizontal dip-normal at ≤100 m intervals; root residual ≤5 m; at least 90% of sampled line positions must have a valid root; 95th-percentile horizontal extrapolation ≤10 km |
| Stability | 24 event-bootstrap resamples; 90th-percentile projected-strike angle ≤ 35° |
| Rasterization | Sample the DEM-intersection polyline every ≤50 m; one-pixel halo with 100 m Gaussian sigma; maximum confidence per pixel |
| Final prediction, only after statistical gate pass | Rank positive candidate cells, exclude all supplied known labels buffered by 300 m, emit up to 37,612 cells at `p=1`, other valid cells `p=0`, outside-template cells NaN |

These are label-blind engineering constants, not optimized on the holdout. The plane fit uses catalog depth as positive-down and converts it to `z_event = -1000 × depth_km` (positive-up). It solves the plane equation against the local terrain elevations rather than setting `z=0`.

**Vertical datum remains a scientific stop condition.** The catalog paper describes depths relative to mean sea level. The USGS 3DEP dynamic mosaic includes source-item metadata fields for `VerticalDatum`, but the exported mosaic does not establish that every pixel shares a single vertical datum or provide a catalog-to-DEM transformation. Version 2 records an explicit zero-offset NAVD88/MSL approximation only to produce diagnostic geometry. This is not a verified datum conversion; it blocks submission eligibility. If the source-item audit and a documented vertical transformation cannot resolve this before scoring, do not claim a physically validated land-surface trace.

## Frozen statistical scoring and controls

- Read the hash-pinned `evidence/holdout-v1.json` and realized mask hashes in `evidence/holdout-realized-v1.json`; the runner compares them before computing any DTI. Never overwrite or regenerate the committed holdout masks after seeing scores.
- Use 100 m pixels, 300 m triangular support, α=0.2, β=0.8, and ε=1e-9. For each method, select the same total of 37,612 binary-probability cells, allocated to macrofolds in proportion to eligible valid pixels with largest-remainder rounding. Ties use deterministic seeded selection. If a method has fewer positive cells, do not pad it with unsupported pixels.
- **Primary incumbent:** H50-prior, pinned before scoring and selected chronologically. H32-D, H47-S3, and H48-DS are secondary descriptive comparators; their holdout scores must never select the incumbent or affect the gate. No prior prediction pixels are copied into H50-S1.
- **Matched density control:** create relocated-event counts on the submission grid; smooth with a Gaussian standard deviation of 300 m; normalize to `[0,1]`. Use exactly the same `reloc=1` event input pool, fold masks, and prediction mass as H50-S1. The geometry candidate must strictly beat this control on pooled DTI. No declustering, event-type filter, uncertainty weighting, or site exclusion is applied to either map in this diagnostic comparison.
- **Spatial translations:** 32 no-wrap translations of the candidate score field by randomly selected 5–20 km offsets (seed 505006), preserving line geometry while disrupting map alignment. The candidate must exceed the 95th percentile of this control family.
- **Time shuffles:** 20 controls permute origin-year labels among relocated in-grid events (seed 505011), then refit the identical terrain-intersection pipeline. Both control families use the same folds and prediction budget; the candidate must exceed the time-shuffle 95th percentile.
- **Uncertainty:** compare candidate and frozen incumbent DTI in the 16 registered 2 × 2 macrofold subtiles, using a 3-pixel metric halo so cross-subtile matches are available without double-counting. Bootstrap the 16 paired subtile deltas 5,000 times (seed 505007), percentile 95% interval.
- **Statistical promotion gate:** pooled absolute improvement over H50-prior ≥0.005; positive paired deltas in ≥3/4 macrofolds; bootstrap lower bound >0; candidate strictly exceeds the 95th percentile of both translation and time-shuffle families; and candidate strictly beats the 300 m smoothed-density control. All are necessary.
- **Artifact gate:** write a new competition-format TIFF only when every statistical promotion component passes and positive candidate pixels remain after the 300 m known-label exclusion. A failed gate writes no new TIFF. If a statistical pass yields a research TIFF, it remains explicitly research-only unless the separate scientific/submission eligibility gate also passes.

## Scientific eligibility gate — not satisfied by this diagnostic

A statistical holdout pass alone does **not** authorize a weekly slot. The current protocol/run must not be described as satisfying the following until the evidence exists:

1. Event-specific horizontal/vertical location-error covariance is not present in the Nevada table. Coordinate decimal precision is not a substitute.
2. No standard declustering method or sensitivity analysis has been applied. Aftershock sequences/swarms may dominate plane fits and time-shuffle results.
3. The table has no event-type, induced-event, or network-source fields sufficient for a documented anthropogenic screening.
4. No complete, reusable inventory of injection wells, geothermal sites, operating/legacy mines, quarries, roads, channels, or other terrain breaks has been applied as a false-positive exclusion.
5. The catalog-depth/DEM vertical datum has not been exactly reconciled.
6. Competition label/template hashes match the recorded source-bridge bytes, but this workflow has not independently authenticated the public mirrors against a participant-authenticated DrivenData download.

Every listed item is a failed gate, not a silently accepted assumption. Therefore, no weekly slot should be used even if the statistical proxy gate passes.

## Inputs, permissions, and audit pins

- Nevada catalog: `nvreloc_catalog_newmag.txt`, Zenodo DOI `10.5281/zenodo.11167510`, CC BY 4.0; expected size 13,833,354 bytes, Zenodo MD5 `38fa663f473378b61c74b597c53c416b`. Attribute Trugman (2024), link the DOI and license, and disclose processing changes. Its downloadable table lacks per-event uncertainty covariance and event-type/source fields.
- USGS 3DEP DEM: acquire a single-band float32 image from the official [3DEPElevation ImageServer](https://elevation.nationalmap.gov/arcgis/rest/services/3DEPElevation/ImageServer), requested at the exact submission grid. USGS states 3DEP products are public domain in its [data catalog](https://data.usgs.gov/datacatalog/data/USGS:77ae0551-c61e-4979-aedd-d797abdcde0e). Keep the request parameters, service metadata, response hash, and grid audit sidecar next to the ignored DEM. The service mosaic's pixel-level vertical datum is not treated as verified.
- The derived GEMSDOE24 scarp TIFF is **not** an input. Its public repository has no explicit license, and raw 3DEP public-domain status does not by itself license a third party's derived raster.
- The inherited mixed-network ComCat extract is **not** an input. Its source-specific reuse rights are unresolved; `net` is the preferred contributor, not a statement that every contributing network's data are USGS public domain. The inherited `horizontalError` field's units and statistical interpretation remain unverified.
- Competition template and label rasters are pinned by SHA-256 in the split file and acquired via public mirrors. Matching the pinned bytes does not independently authenticate those mirrors as official originals.
- Catalog, DEM, and raster data stay in ignored `.arena/` scratch. The result report records raw-input hashes, code commit, mask hashes, data rights, statistical eligibility, and TIFF byte validation.
- No organizer score, hidden labels, portal upload, or current leaderboard reading is used.

## Auditable sources

- Competition metric and external-data requirement: <https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/>
- Nevada catalog record and license: <https://zenodo.org/records/11167510>
- Nevada catalog paper, including depth reference and location-quality discussion: <https://doi.org/10.1785/0220240106>
- USGS 3DEP ImageServer metadata/export service: <https://elevation.nationalmap.gov/arcgis/rest/services/3DEPElevation/ImageServer>
- USGS 3DEP public-domain statement: <https://data.usgs.gov/datacatalog/data/USGS:77ae0551-c61e-4979-aedd-d797abdcde0e>
- Nearest-neighbor declustering methodology (not implemented in this version): Zaliapin & Ben-Zion (2020), <https://doi.org/10.1029/2018JB017120>.
