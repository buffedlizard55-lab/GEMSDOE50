# GEMSDOE50 — seismic-geometry research for the DOE GEMS Prize

**Project aim:** maximize the probability of a strong result in the [DOE Geologic Enhanced Mapping System (GEMS) Prize Challenge, DrivenData competition 306](https://www.drivendata.org/competitions/306/competition-doe-gems/) by testing defensible hypotheses for previously unmapped faults in the GeoDAWN study area. Core values: **Maximize P(Win)** and **Own the Outcome**.

> **Read this charter before each work session.** It records the standing acceptance criteria and current evidence; historical artifacts are not automatically current evidence.

## Standing project brief

1. **Produce a genuinely new GeoTIFF only after validation.** Do not copy prior prediction pixels. The planned artifact must be a single-band float32 GeoTIFF on the actual competition grid, EPSG:32611, with the template's exact dimensions, transform, bounds, and nodata footprint. Check finite in-footprint predictions in `[0,1]` by reopening the written bytes. No artifact is eligible for manual review unless the preregistered statistical gate passes; a pass alone does not establish scientific or submission eligibility.
2. **Make any validated artifact easy to find.** The static site has an executive summary, a research-only download link only when the report hash matches the artifact bytes and the validation record matches the pinned grid/provenance, results, sources/limitations, and numbered manual submission instructions. No page may imply portal acceptance without an organizer receipt.
3. **Do the science before implementation.** Rank 3–5 distinct geological hypotheses and state the data/layers, physical rationale, novelty against prior GEMSDOE work, expected impact, implementation cost, and data/license requirements. The current ranking is in [`docs/hypotheses-preregistered.md`](docs/hypotheses-preregistered.md); implementation and controls are frozen in [`docs/h50s1-protocol-addendum.md`](docs/h50s1-protocol-addendum.md).
4. **Protect the weekly submission budget.** Test the leading candidate on the frozen spatial holdout against the fixed, same-fold incumbent and preregistered controls before using any of the three weekly scoring slots. Do not use a slot unless the candidate beats the holdout incumbent and all statistical and scientific eligibility gates pass. A local proxy score is not an organizer score or a prediction of private-test performance.
5. **Use compliant, traceable evidence.** Prefer official and peer-reviewed primary sources; link references, state rights and limitations, and pin hashes. External data must be licensed for the challenge and shareable with the sponsor for independent verification. Do not use the inherited mixed-network ComCat extract until its source-specific rights and uncertainty semantics are resolved; do not use the unlicensed GEMSDOE24 scarp derivative.
6. **Do not overstate seismicity methods.** H50-S1 is a 2-D raster adaptation of published 3-D earthquake-lineament methods, not a validated reproduction. The Nevada catalog has no per-event location covariance; its coordinates are not exact fault locations.
7. **Work autonomously and auditably.** Review sources, data, prior work, and constraints; record material decisions and irregularities; run multiple implementation/review passes; fix defects; and maintain next steps. Do not ask the owner to research or verify items that can be checked independently.
8. **Keep score context honest.** An archived GEMSDOE50 report associates `0.2778` with H33-2-B2, but the current GEMSDOE32 owner site describes H33-2-B2 as unscored and `0.2747` as a model projection. The `0.2778` score-to-artifact association remains unresolved. `0.3195` is owner-provided historical context only—not independently verified, not asserted as the current leader, and not mapped to a verified TIFF. Do not scrape, poll, or copy leaderboard data; see [DrivenData's Terms of Use](https://www.drivendata.org/termsofuse/).
9. **Follow current prize rules.** Verify the official deadline and current terms before deadline-dependent actions. Disclose AI assistance in any competition narrative as required by the rules. The project never submits through an automated portal client.
10. **Create and merge a pull request when checks pass.** This Arena session is fixed to branch `arena/2e04de3b-gemsdoe50`; do not switch branches or push elsewhere.

## Current evidence and decision — 2026-10-06

- The leading hypothesis is **H50-S1: local planes fit to waveform-relocated Nevada earthquakes, intersected with a grid-matched 3DEP terrain surface**. An earlier sea-level `z=0` projection was physically invalid and has been removed. The current terrain intersection uses an explicit zero-offset catalog/DEM vertical-datum approximation only for diagnosis; because a single 3DEP pixel-level datum and catalog-to-DEM conversion are not verified, the output cannot be called a validated surface fault.
- The three ranked, distinct hypotheses and comparison to prior GEMSDOE work are documented in [`docs/hypotheses-preregistered.md`](docs/hypotheses-preregistered.md). The alternatives include conditional multi-physics basin-edge contacts and multi-year seismicity recurrence. Their expected impacts are qualitative; no numeric DTI gain is claimed before evaluation.
- The Nevada relocated catalog is Trugman (2024), 2008–2023, 183,002 source rows, Zenodo v2, CC BY 4.0 (MD5 `38fa663f473378b61c74b597c53c416b`, 13,833,354 bytes). It lacks event-specific location covariance and event-type/source fields. The USGS 3DEP source states that 3DEP products are public domain, but the dynamic mosaic export does not verify one common vertical datum for every pixel. Input rights do not resolve the scientific limitations.
- Competition training rasters are pinned by SHA-256 and downloaded through public mirrors. Matching those hashes confirms the expected bytes, not independent authentication to DrivenData's official participant downloads. This caveat is retained in reports and blocks submission eligibility.
- The H50-S1 implementation includes a checked catalog parser, robust local 3-D geometry, terrain intersection, four frozen geographic macrofolds, same-grid incumbent comparisons, 32 spatial translations, 20 time shuffles, a same-event 300 m smoothed-density control, and byte-level TIFF checks. A research TIFF can be built only after every preregistered statistical component passes and positive candidate cells remain. Even then, scientific and provenance blockers keep the output research-only.
- The statistical promotion gate requires: at least `+0.005` pooled DTI over frozen H50-prior; positive paired delta in at least 3 of 4 macrofolds; 95% spatial-block bootstrap lower bound above zero; beating the 95th percentile of translation and time-shuffle controls; and strictly beating the same-event smoothed-density control. The protocol fixes a 37,612-cell prediction-mass budget and does not pad sparse maps with unsupported pixels.
- **No real H50-S1 DTI, result report, or new candidate TIFF has been produced.** No organizer score, portal upload, receipt, or weekly slot use is claimed. The required catalog, exact-grid 3DEP export, official-template inputs, and comparator files are not currently present in `.arena/run/inputs` / `.arena/run/prior` in this workspace; the committed GitHub Actions workflow is an acquisition route, not evidence that a run succeeded.
- The frozen spatial split and realized-mask hashes were committed before any H50-S1 DTI calculation: [`evidence/holdout-v1.json`](evidence/holdout-v1.json) and [`evidence/holdout-realized-v1.json`](evidence/holdout-realized-v1.json). Split-spec SHA-256: `78b6692155c6c6d5f9f19ccee6d595167c2065f1f25eb8d08636d1d9b285ff16`; realized-mask report SHA-256: `981b42e6d0310bf77f79c7c7662a0569c8d2e79514ef4e4a3624a5b07583ae3f`.
- Independent scientific/submission blockers still include event-location uncertainty, standard declustering and sensitivity, event-type/induced-event review, injection-site and mine/quarry exclusions, defensible catalog/DEM vertical-datum transformation, and authenticated competition-raster provenance. No weekly slot should be used while any are unmet.
- [`docs/research/data-rights-audit-20261006.md`](docs/research/data-rights-audit-20261006.md) documents the source/license review. The inherited mixed-network ComCat extract and GEMSDOE24 scarp derivative are excluded. The archived [`docs/report.html`](docs/report.html) is prior-work context only; its score associations are not organizer receipts or verified score-to-TIFF mappings.

## Executive summary and submission instructions

Static pages are generated by [`scripts/build_h50_site.py`](scripts/build_h50_site.py): [`index.html`](index.html), [`results.html`](results.html), [`methods.html`](methods.html), and [`submission.html`](submission.html). The site exposes a GeoTIFF download only if the report says it was built and its SHA-256 matches the on-disk file. It presents the statistical gate separately from scientific/submission eligibility and never automates portal access.

If a future verified run passes the statistical gate, the planned filename is `gemsdoe50-h50s1-relocated-planes-20261006-research.tif`. The planned optional note is “Terrain-intersected relocated Nevada event-plane lineaments; 300 m known-label exclusion; research diagnostic, not organizer-scored.” These are plans until a validated run actually builds the artifact. Re-check the current portal contract and verify downloaded bytes before any owner-approved manual upload. No upload receipt exists.

## Verified project references

| Source | Verified relevance | Link |
|---|---|---|
| Competition data, metric, format, and external-data rules | Challenge specifications; external data must be appropriately licensed and shareable with the sponsor | [Problem description](https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/) |
| DOE/NLR prize rules | AI-use disclosure, weekly feedback limits, final selection, reproducible finalist package | [Official rules PDF](https://docs.nlr.gov/docs/fy26osti/96647.pdf) |
| Leaderboard access restrictions | Do not automatically monitor/copy; manual monitoring/copying requires prior written consent | [DrivenData Terms of Use](https://www.drivendata.org/termsofuse/) |
| Nevada relocated catalog | Trugman (2024), Zenodo v2, CC BY 4.0 | [Zenodo record](https://zenodo.org/records/11167510) · [record API](https://zenodo.org/api/records/11167510) |
| Catalog paper | Relocation method and accuracy limitations | [Trugman (2024), DOI 10.1785/0220240106](https://doi.org/10.1785/0220240106) |
| 3DEP raw-data rights | USGS public-domain statement; does not resolve the mosaic's vertical datum | [USGS 3DEP data catalog](https://data.usgs.gov/datacatalog/data/USGS:77ae0551-c61e-4979-aedd-d797abdcde0e) · [3DEPElevation service](https://elevation.nationalmap.gov/arcgis/rest/services/3DEPElevation/ImageServer) |
| Seismicity-to-fault literature | Source methods; H50-S1 is an unvalidated raster adaptation | [Ouillon et al. (2008)](https://doi.org/10.1029/2007JB005032) · [Ouillon & Sornette (2011)](https://doi.org/10.1029/2010JB007752) · [Wang et al. (2013)](https://arxiv.org/abs/1304.6912) |
| Reference-solution notebook | Tversky training loss; not the authority for the official DTI implementation | [DrivenData reference solution](https://github.com/drivendataorg/gems-prize-reference-solution/blob/main/unet-mc-cv-reference-solution.ipynb) |
| Prior GEMSDOE work | Educational comparison only; no prior prediction pixels are copied | [GEMSDOE32](https://github.com/buffedlizard55-lab/GEMSDOE32) · [GEMSDOE47](https://github.com/buffedlizard55-lab/GEMSDOE47) · [GEMSDOE48](https://github.com/buffedlizard55-lab/GEMSDOE48) |

## Reproduction

Raw and large inputs stay in ignored `.arena/` or documented external storage, not Git. The repository's inherited history contains legacy external/derived data and prior artifacts; H50-S1 consumes only the pinned comparator rasters as baselines and excludes the mixed-network ComCat and third-party scarp derivative.

```bash
# Use the project virtual environment; system Python may not have the analysis stack.
/home/user/GEMSDOE50/.venv/bin/python -m pip install -e '.[test]'
/home/user/GEMSDOE50/.venv/bin/python -m pytest -q

# Downloads hash-pinned template/labels/catalog, then requests a grid-matched 3DEP DEM
# and writes a JSON acquisition sidecar. Raw inputs remain ignored under .arena/.
PYTHON=/home/user/GEMSDOE50/.venv/bin/python scripts/download_inputs.sh .arena/run/inputs

# Prior rasters are retrieved through GitHub Contents API and checked against pinned hashes.
GH_TOKEN="$(gh auth token)" scripts/fetch_comparators.sh .arena/run/prior

# Reconstruct the frozen masks without scoring (optional diagnostic).
/home/user/GEMSDOE50/.venv/bin/python scripts/freeze_holdout.py \
  --template .arena/run/inputs/example_submission.tif \
  --labels .arena/run/inputs/existing_faults.tif \
  --output .arena/run/recomputed-holdout.json

# Do not run while the listed scientific/provenance blockers remain. If they are later resolved
# and the work is authorized, this requires the DEM and .json sidecar.
/home/user/GEMSDOE50/.venv/bin/python scripts/run_experiment.py \
  --catalog .arena/run/inputs/nvreloc_catalog_newmag.txt \
  --template .arena/run/inputs/example_submission.tif \
  --labels .arena/run/inputs/existing_faults.tif \
  --dem .arena/run/inputs/3dep_dem_100m.tif \
  --dem-metadata .arena/run/inputs/3dep_dem_100m.json \
  --prior-dir .arena/run/prior \
  --time-shuffles 20
/home/user/GEMSDOE50/.venv/bin/python scripts/build_h50_site.py
```

The manually dispatched [H50-S1 research workflow](.github/workflows/h50s1-research.yml) is restricted to `arena/2e04de3b-gemsdoe50`. It runs tests, reacquires public inputs, verifies frozen masks before DTI, and publishes only a report/site and a research-only TIFF if the statistical gate passes. A workflow definition or successful test suite is not evidence of a completed experiment. No raw catalog, DEM, or comparator raster is committed.

## Remaining scientific gates and next actions

1. Do not run the real catalog/DTI experiment or use a weekly scoring slot while the scientific/provenance blockers above remain unresolved.
2. If those gates are later resolved and an experiment is authorized, audit downloaded event counts, depth/magnitude irregularities, spatial coverage, DEM provenance, and all input hashes before interpreting any score.
3. Run the registered holdout against H50-prior, descriptive secondary comparators, spatial/time controls, and the same-event density control. A statistical failure produces no candidate TIFF and no slot use.
4. Even if the statistical gate passes, keep any artifact research-only unless every scientific/provenance gate is resolved and the owner approves. Reopen and byte-validate any downloaded TIFF; do not claim portal acceptance without an organizer receipt.

## User's requested outcomes (preserved from the conversation brief, 2026-10-06)

> Build an auditable GEMSDOE50 research and submission workflow. Explain the historical `0.2778` and owner-provided `0.3195` context cautiously and do not scrape the live leaderboard. Research and rank 3–5 distinct geological hypotheses, documenting data, physical rationale, novelty versus prior work, expected impact, cost, and license requirements. Test the leading candidate on the frozen spatial holdout against the incumbent and controls before any weekly slot. Create a genuinely new competition-format TIFF with `[0,1]` predictions and the exact CRS/grid/transform only if the holdout supports it; make a verified artifact downloadable and document its filename, note, validation, sources, limitations, and manual submission steps. Work autonomously, use trusted sources, run multiple review/test passes, append this request to the README and reread it, and create and merge a PR when checks pass.
