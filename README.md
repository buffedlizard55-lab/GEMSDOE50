# GEMSDOE50 — seismic-geometry research for the DOE GEMS Prize

**Project aim:** maximize the probability of a strong result in the [DOE Geologic Enhanced Mapping System (GEMS) Prize Challenge, DrivenData competition 306](https://www.drivendata.org/competitions/306/competition-doe-gems/), by finding defensible, previously unmapped fault traces in the GeoDAWN study area. Core values: **Maximize P(Win)** and **Own the Outcome**.

> **Read this charter before each work session.** It is the standing project purpose and the acceptance criteria for every experiment and deliverable.

## Standing project brief

1. **Deliver a new, unique GeoTIFF prediction.** Generate it from this repository's documented method and pinned inputs. Never copy a previous submission's prediction pixels; earlier artifacts may be inspected only for education, controls, or comparison. The intended download must be a single-band float32 GeoTIFF on the actual competition grid, EPSG:32611, 100 m resolution, with the official shape, transform, and bounds. Predictions must be finite and within `[0, 1]` wherever data are valid; outside-footprint handling must follow the official sample/template and be tested against the reported portal error `Predicted values must be in range [0, 1]`.
2. **Make the artifact easy to find and download.** Put a one-click download and a concise executive summary at the top of the site. Include a clear, numbered “how to submit” page, a unique submission name, and a short distinguishing note for the competition's optional note field. Do not imply portal acceptance when no upload receipt exists.
3. **Do the science before implementation.** Before writing a detector, list and rank 3–5 genuinely distinct geological hypotheses. Each must state the exact layers/data, physical signature, why it could detect a fault missing from USGS/INGENIOUS, how it differs from prior GEMSDOE work, expected DTI direction/impact, implementation cost, and data/license requirements. See the current audit in [`docs/research/hypothesis-ranking-20261006.md`](docs/research/hypothesis-ranking-20261006.md), the preregistered candidates in [`docs/hypotheses-preregistered.md`](docs/hypotheses-preregistered.md), and exact H50-S1 implementation choices/controls in [`docs/h50s1-protocol-addendum.md`](docs/h50s1-protocol-addendum.md). Re-check old work before calling any variant new.
4. **Protect the weekly submission budget.** Validate the leading hypothesis on a spatially blocked holdout against a frozen, same-fold incumbent and appropriate controls before using any of the competition's three weekly scoring slots. H50-S1 must also beat both smoothed-density baselines and pass formal aftershock, mine/injection-site, and event-location-uncertainty gates. A hypothesis that fails any gate is not slot-eligible. A local proxy score is not an organizer score or a prediction of private-test performance.
5. **Use compliant, traceable evidence.** Prefer official and peer-reviewed primary sources; link sources directly, state evidence and license status, pin file hashes, and disclose attribution/changes. External data may be used only where the competition permits it, the license permits commercial use, and the data can be shared with the organizers for independent verification. Do not use the scratch mixed-network USGS ComCat extract until its source-specific rights and location uncertainty are resolved.
6. **Do not overstate the literature.** H50-S1 is a 3-D local plane-fitting hypothesis on relocated Nevada events, but its catalog lacks per-event location covariance and it is not ACLUD. The already-implemented legacy H50-B method uses 2-D ComCat covariance/lineations; its 2-D triangle-area reduction of a 3-D tetrahedron statistic is explicitly **unverified**, and the builder does not apply the computed `keep` mask. Neither method is a validated transfer of the cited 3-D methods: [Ouillon et al. (2008)](https://doi.org/10.1029/2007JB005032), [Ouillon & Sornette (2011)](https://doi.org/10.1029/2010JB007752), and [Wang et al. (2013)](https://arxiv.org/abs/1304.6912).
7. **Work autonomously and auditably.** Review rules, data, sources, prior attempts, and limitations; record every material decision and irregularity; run multiple implementation/review passes; fix defects found; and maintain a concise next-steps list. Do not ask the owner to do research or resolve issues the agent can verify independently.
8. **Keep the score context honest.** The owner-quoted `0.3195` is historical, not the live leader. Prior sibling-repository notes contain conflicting historical leaderboard values and are not a fresh independent official check; do not repeat them as current official scores or map any score to a TIFF without organizer-verified provenance. DrivenData's Terms of Use prohibit automated monitoring/copying and manual monitoring/copying without prior written consent. This repository links to the official board but does not scrape, poll, or publish leaderboard snapshots.
9. **Follow the prize rules.** The September 2026 NLR/DOE rules require an AI-use disclosure in the narrative, permit up to three feedback submissions per week, and require selection of one final submission for both prize rounds. Finalists must provide reproducible code/assets and documentation. The competition ends December 3, 2026 at 23:59 UTC (verify the official page before any deadline-dependent action).
10. **Create and merge a PR when practical.** Keep all work on Arena's fixed branch `arena/c4f4db48-gemsdoe50`. Run tests and review the PR before merging. Do not switch branches or push elsewhere.

## Current evidence and decision (2026-10-06 UTC)

- This working branch contains the repository's inherited older GEMSDOE50 submission, research site, data, and workflows; these are preserved as project history, not silently treated as H50-S1 evidence. The standing charter, prior-work audit, 3–5-hypothesis ranking, and seismicity review are maintained here.
- The local ignored `.arena/cache/` bridge contains the competition feature, label, and template rasters. The assembled 19-band feature raster is 418,912,844 bytes with SHA-256 `4371c82e3b8339b807bdffcf4ef59a225520fe2988d521be208ae33743123bc5`; the label and example-submission rasters also match the bridge manifest. **Provenance caveat:** the bridge manifest points to the official data tab and public Dropbox mirrors, but this session did not authenticate to DrivenData and independently re-download the official bytes. Matching hashes establish consistency with the bridge manifest, not organizer provenance.
- The ranked lead remains **H50-S1**, a research hypothesis about waveform-relocated Nevada hypocenter planes and plausible z=0 trace projections. The catalog is public, 2008–2023, 183,002 rows, 103,976 waveform-relocated in the paper, CC BY 4.0, and has Zenodo MD5 `38fa663f473378b61c74b597c53c416b` (13,833,354 bytes). It does not provide per-event location covariance. The data file has **not yet been downloaded into this sandbox**: direct Zenodo `curl` fails TLS here. A manually dispatched GitHub Actions workflow now provides a pinned, auditable acquisition path; it has not yet been run.
- Four prior-work rasters are pinned for comparison only: H32-D, H47-S3, H48-DS, and the pre-existing `main`-branch GEMSDOE50 artifact `gems50-seislin-44709-20261006T2041Z-79e260ae.tif`. Their source commits/blob IDs and file hashes are pinned in the experiment code. The prior artifact's local claims are not an organizer score or verified score-to-TIFF mapping; no prior pixels are copied into the H50-S1 output.
- The H50-S1 implementation includes a format-checked Nevada catalog parser, robust local 3-D plane/lineament geometry, frozen spatial-mask reconstruction, the fixed same-grid incumbent, two matched Gaussian-smoothed relocated-event density controls (1 km and 2 km), translation/year-shuffle controls, and byte-level GeoTIFF validation. Its metric is transcribed from the official problem page's distance-weighted TP/FP/FN equations and tested against the published worked example and hand-calculated spatial cases. I reviewed the reference-solution notebook: it uses Tversky loss for model training but does not implement the official distance-weighted scoring evaluator, so it is not treated as metric authority. The real Nevada-catalog experiment has not run; **no H50-S1 DTI, result report, or new candidate TIFF, organizer score, portal upload, or weekly slot use is claimed**. A numerical pass would still be research-only because H50-S1 lacks formal aftershock declustering, mine/injection-site screening, and event-specific location uncertainty for its emitted corridor width. Validation in this checkout: **61 tests passed, 1 skipped**, `scripts/verify_claims.py` passed all guardrails, and `git diff --check` is clean. The prior TIFF in the repository is comparator-only.
- Pre-DTI review caught and corrected two evaluation issues: selecting the best baseline by the holdout score would leak labels, and subtile false-positive weighting must use neighboring truth in the metric halo even when a subtile has no truth of its own. H50-prior is now selected chronologically as the fixed incumbent; other comparators are descriptive only. Regression tests enforce both fixes, and evaluation refuses to run without all 20 preregistered time shuffles.
- The exact 3292 × 3730 four-macrofold split and 10 km/300 m mask rules are in [`evidence/holdout-v1.json`](evidence/holdout-v1.json). The realized valid, truth, and per-fold mask hashes are in [`evidence/holdout-realized-v1.json`](evidence/holdout-realized-v1.json). These were created and hash-pinned before any H50-S1 DTI computation. Split-spec SHA-256: `78b6692155c6c6d5f9f19ccee6d595167c2065f1f25eb8d08636d1d9b285ff16`; realized-mask report SHA-256: `981b42e6d0310bf77f79c7c7662a0569c8d2e79514ef4e4a3624a5b07583ae3f`.
- The method remains unvalidated against the hidden expert-labeled set. Existing mapped fault labels are an imperfect spatial proxy; catalog location error may exceed the 300 m metric support. No submission slot will be used unless the preregistered gate passes and an owner manually reviews the data provenance, method, and downloaded TIFF bytes.
- The inherited mixed-network ComCat extract under `data/external/` is not used by H50-S1; source-specific rights and shareability remain unresolved. The legacy H50-B 2-D covariance/lineation work is already implemented and is not new; its 2-D triangle-area statistic is an unverified adaptation, and its computed `keep` mask is not applied in the builder. The full audit and 3–5-hypothesis review are in `docs/research/`. One unintended automated request to the public leaderboard page occurred during prior research; no rows/scores were saved or used, and no further automated access will be made. User-reported historical score context is not presented as a current official score, and no score is mapped to a TIFF without verified provenance.

## Executive summary and submission instructions

Static site pages are generated at repository root by [`scripts/build_h50_site.py`](scripts/build_h50_site.py): [`index.html`](index.html), [`results.html`](results.html), [`methods.html`](methods.html), and [`submission.html`](submission.html). When the fixed branch is merged to `main`, the repository's existing GitHub Pages configuration serves the root site at [buffedlizard55-lab.github.io/GEMSDOE50](https://buffedlizard55-lab.github.io/GEMSDOE50/). The site labels the output **research-only** unless every gate passes, and even a local pass is only eligible for manual owner review—not an organizer score or upload receipt.

If (and only if) the protocol passes and the owner approves the artifact, `submission.html` provides a numbered manual portal checklist. The planned unique filename is `gemsdoe50-h50s1-relocated-planes-20261006-research.tif`; the short optional note is “Relocated Nevada event-plane lineaments; 300 m known-fault exclusion; research proxy, not organizer-scored.” The name is only a plan until the verified run produces the TIFF. Re-check the current portal specification and the report's on-disk SHA-256 before any manual upload. No automated portal access is used.

## Verified project references

| Source | Verified use | Link |
|---|---|---|
| Challenge overview and current deadline | Prize structure; external data must be appropriately licensed and shareable with organizers | [Competition page](https://www.drivendata.org/competitions/306/competition-doe-gems/) |
| Problem, data, metric, and TIFF contract | EPSG:32611, 100 m, single float32 band, `[0,1]`, null/NaN outside; DTI uses 300 m support, α=0.2, β=0.8 | [Problem description](https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/) |
| Prize rules | AI disclosure, 3 weekly feedback submissions, one final selection across both rounds, reproducible finalist package | [September 2026 official rules PDF](https://docs.nlr.gov/docs/fy26osti/96647.pdf) |
| Competition-specific rules entry | Points to the NLR/DOE rules | [DrivenData rules page](https://www.drivendata.org/competitions/306/competition-doe-gems/rules/) |
| Restrictions on leaderboard monitoring | No robot/automatic access for monitoring or copying; no manual monitoring/copying without written consent | [DrivenData Terms of Use](https://www.drivendata.org/termsofuse/) |
| Nevada relocated earthquake catalog | Trugman (2024), CC BY 4.0; metadata and exact downloadable file/checksum | [Zenodo record](https://zenodo.org/records/11167510) · [record API/file metadata](https://zenodo.org/api/records/11167510) |
| Catalog paper | 183,002 3-D-model locations; 103,976 additionally waveform-relocated; location quality depends on the regional velocity model | [Trugman (2024), DOI 10.1785/0220240106](https://doi.org/10.1785/0220240106) |
| Seismicity-to-fault literature | 3-D anisotropic clustering, spatial clustering/segmentation, and explicit location-uncertainty methods | [Ouillon et al. 2008](https://doi.org/10.1029/2007JB005032) · [Ouillon & Sornette 2011](https://doi.org/10.1029/2010JB007752) · [Wang et al. 2013](https://arxiv.org/abs/1304.6912) |
| Reference-solution notebook | Reviewed 2026-10-06: uses a Tversky training loss with α=0.2/β=0.8, but does not implement the official distance-weighted scoring evaluator; scoring authority is the problem-description page above. | [DrivenData reference solution](https://github.com/drivendataorg/gems-prize-reference-solution/blob/main/unet-mc-cv-reference-solution.ipynb) |
| Prior GEMSDOE experiments | Educational evidence only; prior outputs are never copied into this project's deliverable | [GEMSDOE32](https://github.com/buffedlizard55-lab/GEMSDOE32) · [GEMSDOE47](https://github.com/buffedlizard55-lab/GEMSDOE47) · [GEMSDOE48](https://github.com/buffedlizard55-lab/GEMSDOE48) |

## Reproduction

New H50-S1 raw and large inputs belong in ignored `.arena/` or documented external storage, not Git. The inherited `main` history also contains legacy external/derived data and a prior submission; H50-S1 does not consume those files except the pinned prior raster as a same-fold comparator. New deliverables, source/license notes, code, tests, and evidence reports belong in the repository.

```bash
python -m pip install -e '.[test]'
python -m pytest -q

# Public raster mirrors and the CC BY 4.0 catalog; all input hashes are checked.
scripts/download_inputs.sh .arena/run/inputs

# Prior maps are retrieved through GitHub Contents API and checked against pinned commits/hashes.
GH_TOKEN="$(gh auth token)" scripts/fetch_comparators.sh .arena/run/prior

# Optional no-score reconstruction; write to scratch and compare with the committed freeze.
python scripts/freeze_holdout.py \
  --template .arena/run/inputs/example_submission.tif \
  --labels .arena/run/inputs/existing_faults.tif \
  --output .arena/run/recomputed-holdout.json

# Reads the committed split and realized-mask hashes, then runs H50-S1, 20 time shuffles,
# 32 translations, same-fold baselines, and byte-level GeoTIFF checks.
python scripts/run_experiment.py \
  --catalog .arena/run/inputs/nvreloc_catalog_newmag.txt \
  --template .arena/run/inputs/example_submission.tif \
  --labels .arena/run/inputs/existing_faults.tif \
  --prior-dir .arena/run/prior
python scripts/build_h50_site.py
```

The manually dispatched [H50-S1 research workflow](.github/workflows/h50s1-research.yml) runs on `arena/c4f4db48-gemsdoe50` only. It verifies tests and the already-frozen masks before scoring, downloads no hidden labels, does not use the feature stack for H50-S1, and commits only the result report/site/research-only TIFF back to this fixed branch. A numerical score-gate pass cannot authorize a slot while the aftershock, mine/injection, and location-uncertainty gates remain open; no raw data are committed.

## Open gates / next actions

1. Dispatch the fixed-branch `H50-S1 preregistered research run` workflow to retrieve and verify the catalog, comparison rasters, and competition mirrors; raw inputs stay in ignored runner scratch.
2. Review the event-count, depth/magnitude irregularity, input provenance, and spatial-coverage audit; stop if relocated points do not overlap the valid footprint adequately.
3. Compute the frozen fold-wise DTI, 16-block bootstrap, fixed incumbent, both smoothed-density maps, and matched translation/year-shuffle controls. Regardless of numeric outcome, H50-S1 remains NO SLOT until formal aftershock declustering, mine/injection-site screening, and uncertainty-calibrated output width are resolved.
4. Independently re-open and byte-validate any generated unique GeoTIFF, update the static executive-summary/results/submission pages, and review source licenses, attribution, limitations, and AI disclosure.
5. Open/review a PR from the fixed Arena branch; merge only if the report, artifact, site, evidence, and source/confound controls agree. No upload is performed by this repository.
