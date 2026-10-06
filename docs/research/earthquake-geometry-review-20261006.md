# Earthquake-geometry review and eligibility decision

**Reviewed:** 2026-10-06 UTC, before any H50-S1 DTI calculation.  
**Decision:** Do not present the 2-D ComCat covariance/triangle-area method as new, and do not revive its mixed-network ComCat input for a competition artifact until source-specific rights are resolved. H50-S1 is a separate, already-implemented 3-D relocated-catalog experiment; it may be run as an exploratory blocked-holdout study, but it is not slot-eligible while its scientific controls below remain open.

## The user's 2-D proposal is already in this repository

The proposal to use epicenter covariance/eigenvalues for local linearity, uncertainty-scaled corridors, declustering, and a smoothed-density control is substantially the existing legacy **H50-B / H50-1 seismicity-lineament work**, not an untried detector:

- `src/gems50/lineation.py` computes local 2-D covariance axes, filters neighborhoods by linearity and location-error scale, and paints oriented line corridors. The paper it adapts (Ouillon, Ducorbier & Sornette, 2008) is explicitly a **3-D hypocenter** method.
- `src/gems50/decluster.py` contains both a nearest-neighbor space-time method and a 2-D triangle-area adaptation of the published 3-D tetrahedron statistic. The module already labels the triangle-area adaptation as this project's own, **unverified** method.
- `scripts/build_seisridge.py` computes the triangle-area filter, but the returned keep mask is not applied to the event arrays subsequently used for the lineation fits. Its nearest-neighbor declustering function is not called by that builder. Thus the existing run does not establish aftershock declustering.
- `src/gems50/catalog.py` removes some event types and uses ComCat `horizontalError` where present, but that does not screen earthquakes near injection/mine sites. Missing errors are imputed; that is not event-specific covariance. The existing code buffers known competition-label traces at raster emission, which is not the same as an independent source mask for mine/injection activity.
- `scripts/validate_seismicity.py` compares corridors with smoothed epicenter density and random controls on a legacy proxy frame. `evidence/falsification_test.json` records a prior local falsification result. These are historical project records, not a rerun on the frozen four-block holdout and not organizer scores.

The 2-D triangle-area statistic is **not** a validated transfer of the 3-D tetrahedron method. The literature sources available to this project describe 3-D event locations and/or explicit location uncertainty; the 2-D reduction, uncertainty handling, and raster corridor conversion require independent validation. See [Ouillon et al. (2008)](https://doi.org/10.1029/2007JB005032), [Ouillon & Sornette (2011)](https://doi.org/10.1029/2010JB007752), and [Wang et al. (2013)](https://arxiv.org/abs/1304.6912).

## Why the old ComCat experiment is not a competition candidate

The local ComCat export contains events from multiple contributing networks. The official USGS ComCat page describes a catalog whose source parameters and products are contributed by networks worldwide; a general USGS public-domain statement does not settle the rights or shareability of every contributor's records. The local export has not been audited record-by-record for those rights, so it is not used as an external competition input. See [USGS ComCat](https://earthquake.usgs.gov/data/comcat/index.php) and the competition's [external-data rule](https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/).

Additional scientific gaps in the legacy H50-B run are: no applied formal declustering in the main builder; no mine/injection-site exclusion; no frozen H50-S1 four-macrofold score; and no evidence that the lineation field beats density after those controls. Because the code and the old negative density comparison already exist, a parameter-tweaked rerun on the same questionable input would invite duplicate-work and holdout-selection risk. **Do not spend a weekly slot on H50-B.**

## H50-S1 is different, but also not yet submission-ready

H50-S1 reads the CC BY 4.0 Nevada relocated catalog from [Zenodo DOI 10.5281/zenodo.11167510](https://doi.org/10.5281/zenodo.11167510), fits local 3-D hypocenter planes, and projects only plausible planes to their z=0 intersection. It is not the user's 2-D ComCat covariance-lineation method. The paper/catalog table does not supply event-specific location covariance; the code's bootstrap tests orientation stability, **not** absolute location uncertainty or corridor width. The current H50-S1 implementation also uses one-event-per-250-m-cell-per-year deduplication rather than a formal space-time declusterer, and it has no applied independent mine/injection mask.

Before the first H50-S1 score, a smoothed-density baseline is added as a required control. The experiment may still be run as a **research-only exploratory test**, but a numerical pass cannot clear a submission slot until all three additional scientific gates pass:

1. a preregistered, documented aftershock/sequence-declustering control;
2. a documented screen/sensitivity for known mining and injection-related sites; and
3. event-location uncertainty suitable for the emitted corridor width, or an explicitly uncertainty-integrated replacement.

Known mapped-label buffers and the frozen spatial holdout remain in force. Failing any of the additional gates means **NO SLOT**, even if the score-only gate passes.

## Screen-data leads checked (not acquired or used)

- The NBMG [Geothermal Wells](https://data-nbmg.opendata.arcgis.com/datasets/72341ba987e34c12a575c83f1d7c5367_0/explore) layer is publicly downloadable, marked CC BY 4.0, and lists 2,854 records (data updated 2020). It is marked deprecated and includes well function/status fields; it is a potential **partial** injection-site screen, not a complete event-time operational history.
- NBMG's [Active Mines and Energy Producers 2019](https://data-nbmg.opendata.arcgis.com/datasets/a011a0ed4b0a43ef96731f2d32a7d3b1_0/explore) layer is CC BY 4.0 and has 156 records for sites with some production in 2017. Its metadata says mine markers generally represent a main pit/portal and are suitable only at about 1:1,000,000 scale; it is too coarse and old to claim comprehensive mining-event removal.
- The 2025 NBMG Active Mines layer declares a **custom license**, so it is not treated as competition-cleared without reviewing those terms.

These source checks establish that some licensed screening layers exist; they do **not** establish that all relevant 2008–2023 mining or injection activity is represented. None of these files has been downloaded into the H50-S1 run inputs.

## Irregularity and execution note

A single unintended automated request to the DrivenData leaderboard page occurred during prior research. No rows or scores were saved to the repository or used in analysis or artifact creation. No further automated access will be made; all score context remains as user-reported historical context, not a fresh official claim.

A manual H50-S1 workflow dispatch was attempted on the fixed Arena branch after pushing the reviewed code. GitHub returned HTTP 403, `Resource not accessible by integration`, so no job started, no catalog or raster inputs were acquired, and no DTI/TIFF was produced. Push, PR creation, and automated PR checks succeeded. The connected GitHub integration needs Actions workflow-dispatch permission before this research-only runner can be retried; no credentials were requested or stored.
