# Data-rights and provenance audit — 2026-10-06

**Scope:** inputs considered for H50-S1 and legacy datasets that could otherwise be mistaken as approved. This audit records the official/trusted source statements checked during this session; it is not legal advice. The H50-S1 experiment has not produced a score or a submission. Large rasters remain outside Git.

## Input disposition

| Input | Source and verified rights/provenance | H50-S1 disposition |
|---|---|---|
| Nevada relocated earthquake catalog (`nvreloc_catalog_newmag.txt`) | Zenodo record DOI [10.5281/zenodo.11167510](https://zenodo.org/records/11167510) lists CC BY 4.0. That license permits commercial sharing/adaptation subject to attribution, license link, and change notice. Competition rules require external data to be usable for the challenge and shareable with the sponsor for verification. The data table lacks event-specific location covariance and event-type/source fields. | Cleared as an external data-license input if the report provides attribution and shares the exact input with the sponsor; scientific limitations remain a submission blocker. |
| USGS 3DEP DEM export | Official [USGS Data Catalog](https://data.usgs.gov/datacatalog/data/USGS:77ae0551-c61e-4979-aedd-d797abdcde0e) says all 3DEP products are public domain. The [3DEPElevation ImageServer](https://elevation.nationalmap.gov/arcgis/rest/services/3DEPElevation/ImageServer) exposes a multi-resolution mosaic and `VerticalDatum` item metadata. The exported grid is a dynamically resampled image; the export alone does not establish a single vertical datum for every pixel. | Rights-cleared for a grid-exact diagnostic DEM. The terrain intersection uses a zero-offset vertical-datum approximation and is therefore **not** submission eligible. Service metadata, request URL/parameters, grid, and SHA-256 must travel with every run. |
| Competition training labels and sample template | The repository's bridge manifest records SHA-256 pins, and the files are served from public Dropbox mirrors. Byte agreement verifies those pinned files, but this workflow has not authenticated to DrivenData or independently retrieved the participant downloads. | Use only for the local spatial proxy, with the provenance caveat in every report. Do not claim the mirror is independently authenticated as the official competition source. |
| GEMSDOE24 12-band LiDAR scarp derivative | GitHub reports the raw file is publicly downloadable, but `GEMSDOE24` returns `licenseInfo:null`, has no root `LICENSE`, and has no explicit license on the derived raster. Public-domain status of 3DEP source data does not itself establish rights in another repository's derived artifact. | **Not used, not scored, not copied, and not included in any candidate.** Reuse rights remain unresolved. A copy previously inspected in ignored `.arena/` scratch is not a project input. |
| Inherited mixed-network USGS ComCat extract | The USGS ComCat documentation distinguishes `net` (preferred contributor) from `sources` (contributing networks). The extracted rows include multiple contributor codes. USGS-public-domain status cannot be applied wholesale to all origins. NCEDC publishes a non-transferable license for its data; challenge/sponsor-sharing fit was not established. `horizontalError` units and its interpretation as 1-sigma remain unverified for this mixed-source extract. | **Not used.** Do not use for H50-S1 until source-specific rights, challenge sharing, field units/meaning, event type, and scientific suitability are reviewed. Existing legacy summaries overstated rights and uncertainty semantics; corrected summaries are maintained here and in the external-data inventory. |
| Nevada wells, mine/quarry points, and induced-event records | Candidate portals include Nevada Division of Minerals and EPA; their inspected pages did not establish a complete georeferenced inventory with item-level reuse rights suitable for this challenge. State/tribal EPA annual UIC spreadsheets are aggregate inventory, not a complete point layer; EPA aquifer exemptions are not a full well inventory. | No such external dataset is included in the H50-S1 input set. Site/anthropogenic exclusions are unmet scientific eligibility gates. |

## Corrections and limitations

- Public availability is not itself a license. Do not reuse the GEMSDOE24 scarp-feature raster without explicit permission/licensing.
- Do not describe the mixed ComCat extract as wholly public domain. `net` identifies a preferred contributor; it is not a blanket rights statement for every row or network.
- Do not describe `horizontalError` as a 1-sigma value or assume its units without source-specific documentation. It is not used by H50-S1.
- No standard earthquake declustering, per-event uncertainty propagation, induced-event classification, injection-well exclusion, or mine/quarry false-positive exclusion has been completed for H50-S1. The method must not be represented as satisfying those conditions.
- Nevada catalog depth is described relative to mean sea level; 3DEP pixel-level vertical-datum compatibility is not verified. A terrain-intersected line made using zero offset is only a diagnostic, not a scientifically validated surface trace.

## Historical score context

- `0.2778`: an archived project report associates this value with a legacy H33-2-B2 artifact, but no organizer receipt authenticates the score or maps it to the TIFF. The current [GEMSDOE32 owner page](https://buffedlizard55-lab.github.io/GEMSDOE32/docs/index.html) labels H33-2-B2 unscored and 0.2747 a model projection. The 0.2778 association remains unresolved.
- `0.3195`: owner-provided historical context only; not independently checked, not established as the current lead, and not mapped to a verified artifact.
- No fresh DrivenData leaderboard monitoring, scraping, copying, or snapshotting was performed. No historical value is presented as an official score for H50-S1.

## Sources checked

- DrivenData challenge data/metric page: <https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/>
- Creative Commons Attribution 4.0 deed: <https://creativecommons.org/licenses/by/4.0/deed.en>
- USGS 3DEP 1 m DEM data catalog: <https://data.usgs.gov/datacatalog/data/USGS:77ae0551-c61e-4979-aedd-d797abdcde0e>
- USGS 3DEPElevation service: <https://elevation.nationalmap.gov/arcgis/rest/services/3DEPElevation/ImageServer>
- USGS ComCat documentation: <https://earthquake.usgs.gov/data/comcat/index.php>
- NCEDC published data/acknowledgement terms: <https://ncedc.org/ncedc/catalog-search.html>
- EPA UIC inventory and aquifer-exemption layers: <https://www.epa.gov/uic/uic-injection-well-inventory> · <https://www.epa.gov/uic/aquifer-exemptions-map>
- NDOM open-data portal (item terms must be reviewed individually): <https://data-ndom.opendata.arcgis.com/>
