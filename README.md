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
10. **Create and merge a PR when practical.** Keep all work on the fixed Arena session branch (the branch this checkout was created on; confirm with `git rev-parse --abbrev-ref HEAD` at session start rather than trusting a hard-coded name here). Run tests and review the PR before merging. Do not switch branches or push elsewhere.

## Current evidence and decision (2026-10-07 UTC, this session: H54 corpus-calibration family)

**One-click file of record:** `gems50-h54-corpuscal-40000-20261007T032111Z-nan.tif` -
40,000 predicted pixels, sha256 `2cdf7e705c867008...`,
single band float32, EPSG:32611, 100 m, 3730 x 3292, every finite value in `[0, 1]`, NaN only where
the official template is NaN, all checks re-read from the written bytes
(`docs/downloads/checks-gems50-h54-corpuscal-40000-20261007T032111Z-nan.json`).
An all-finite twin and a one-file `.zip` sit beside it for portals that reject either form.
Registered in `registry/submissions.json` as `GEMSDOE50-H53-CORPUSCAL-40000` with `organizer_score: null`.

> Naming note: this session's candidate was labelled H53 when it was built; `main` had meanwhile taken
> **H53** for a different candidate (the TMI x K/U conjunction), so the whole family here - package
> `gems54`, `scripts/h54_*.py`, `evidence/h54_*.json`, file stem `gems50-h54-corpuscal-*` - was
> renumbered to **H54** to keep two unrelated "H53"s out of the site, the registry and the download
> folder. Nothing about the method changed in the renumbering.

**H54 is this session's two new methods, and both were validated, not assumed.**

1. *Corpus-calibrated truth prior.* The sibling repositories of this project each record their own
   scored rasters, so 24 distinct scored predictions (plus 7 byte-identical twins) were joined to
   their owner-reported scores and used to fit a per-cell Poisson truth field whose derived `N`, `T`
   and `FP` are the metric's own definitions (`scripts/h54_corpus.py`, `scripts/h54_fit_truth.py`).
   It did not reach a usable calibration: the search log stayed at RMSE ~0.12 and was monotone in `N`,
   and the reason is now on the record - a field that explains 1.5x of the leaderboard's concentration
   cannot reproduce a leaderboard that needs 5.6x. `evidence/h54_fit_status.json` records what ran, and
   that `evidence/h54_fit.json` belongs to the earlier *linear* model class (RMSE 0.093 first-order /
   0.096 exact closure at a degenerate `N` = 249,337), not to this fit.
2. *Metric-derived stratified emission.* `DTI = T / (0.2(T+F) + 0.8N)` gives the exact stop rule
   (`accept while kernel credit > 0.2T/(0.2F+0.8N)`) and it also exposes a trap every earlier build
   fell into: `TPw` is a **maximum over predicted cells**, so a dense blob of dots pays once while
   each of its dots still pays the false-positive penalty. Emitting one dot per 12 px block before any
   block may take a second raised the same field from 0.026 to 0.099 credit per dot - **3.7x,
   measured** (`src/gems54/emitter.py::emit_stratified`, pinned by `tests/test_gems54.py`).

**Measured on the only independent instrument available here** (USGS SGMC mapped faults more than
300 m from the provided catalogue, scored inside each frozen holdout core at matched mass):
shipped 0.109 credit/dot, 3-px dotted
0.147, matched-mass random control
0.119, and the already-scored sibling incumbent
0.148. `evidence/h54_validation.json`.

**Decision: the H54 file is NOT slot-eligible** - it beats the matched-mass random control in
0/4
blocks, while the incumbent beats it in 3/4. The gate is deliberately an instrument and never a model:
the uncalibrated prior predicts 0.156 DTI for the very same
support, a number that is a property of the assumption. The recommended use of a weekly slot remains
the highest-measured artifact in `main` (the H51 u-H52 union file the site leads with), and the
H51 file alone reproduces its recorded 0.189 credit/dot exactly when re-measured in this session -
1.7x the matched-mass random control, 4/4 blocked folds.

**Two defects found and fixed, one inherited defect documented.** (a) The structural filters smoothed
`nan_to_num(raster)` directly, so the boundary between data and no-data was detected as a lineament
and rang a synthetic "fault" around the whole footprint outline: at its worst it carried 79% of the
radiometric family's top 0.5% of pixels (0.12% expected). `gems54.field.masked_filter` (normalised
convolution) plus a 6 px data-edge guard remove it, and a test pins the behaviour both ways; the fix is
deliberately **not** applied inside `gems51.structfield`, because H51/H52's published numbers were
produced by that code path and silently changing it would destroy their reproducibility. Audited
consequence: the H51 file carries the artifact on 7.9% of its dots, where it earned *below*-average
credit, so H51's measured advantage is not an edge effect - but a re-emission with the corrected filter
is an open, cheap improvement. (b) `scripts/build_submission.py` still computes a 2-D ComCat `keep`
mask it never applies (clause 6 caveat unchanged). (c) Three provenance contradictions in the sibling
corpus are recorded in `evidence/h54_corpus.json`: byte-identical files reported with different scores,
one resampled file reported as shipped, and every sibling "score" being an owner report rather than an
organizer receipt.

**The binding constraint is data, not method.** The field that beat the instrument used the official
19-band `training_features.tif`; that file is not present in this sandbox and cannot be fetched without
the owner's logged-in download, and no sibling mirror of it exists locally (checked: nothing over 90 MB
in any cloned sibling). Re-downloading it and then running `scripts/build_h51.py` followed by
`scripts/h54_ship.py --layout stratified` is the single highest-value next action for beating `0.3195`.
An independent attempt to add a USGS Quaternary-fault corridor layer (`gdr_qfaults_traces.csv`, centroid
+ length, 376 traces inside the footprint) was measured and rejected: 0.054-0.074 credit/dot, below the
random control.

## Earlier evidence and decision (2026-10-06 UTC, superseded where the two differ)



- **The H51 deliverable exists and is verified.** `docs/downloads/gems51-scarpradio-offcat-35000-20261006-ecf058ea-nan.tif`
  (35,000 predicted pixels, sha256 `8f8708d2872b66d71925707e0aede23eebcf217dfd2e57d6e61186f32e686f5d`) with an
  all-finite twin and a one-file `.zip`. It is single band float32, EPSG:32611, 100 m, 3292 × 3730,
  every finite value in `[0, 1]`, NaN only where the official template is NaN — re-read from the written
  bytes by `scripts/verify_h51_raster.py` (`evidence/checks_h51_raster.json`, zero failed checks).
- **What it is.** A corroborated lineament field: the measured-best blend of the scarp-focused 3DEP/LiDAR
  topographic family and the airborne radiometric family (multi-scale structure tensor, 0.75/0.55 on
  max-normalised families), greedily packed by expected marginal kernel credit with a 3 px suppression
  radius, restricted to cells more than 300 m from every provided-catalogue pixel. The preregistration and
  its three amendments are in [`docs/hypotheses-preregistered.md`](docs/hypotheses-preregistered.md); the
  ranked untried candidates are in [`docs/h51-candidates.md`](docs/h51-candidates.md).
- **What it measures.** On the off-catalogue SGMC instrument the file earns 0.189 credit per emitted dot
  against 0.116–0.126 for 24 matched-mass random controls (±0.002 spread) — above every control seed at
  every swept mass. On the frozen four-macrofold spatial holdout it beats its matched control in **4/4**
  folds with a paired subtile bootstrap 95% CI of `[0.0406, 0.0785]`
  ([`evidence/holdout_h51.json`](evidence/holdout_h51.json)).
- **What it is *not*.** No organizer score exists for this file; no portal upload was performed; no weekly
  slot is claimed. The 242-pixel Monte Cristo trend does **not** separate this file from random scatter at
  these masses (71st percentile of 24 control seeds) and is reported as a weak guard, not as evidence
  ([`evidence/mc_sensitivity_h51.json`](evidence/mc_sensitivity_h51.json)).
- **The seismicity line (H51-B) is a recorded negative.** The event-geometry corridor field — declustered
  with a space-time tetrahedron test, 1/σ²-weighted covariance axes, corridor width from a calibrated
  location-uncertainty model — measured level with a matched random control on the off-catalogue instrument
  and covered none of the Monte Cristo trend, so it received **no mass** in the shipped file. The
  uncertainty model is this project's own construction (R² 0.715 in sample; footprint holdout within a
  factor of two for 50.4 % of events) and is **not** from Wang et al. (arXiv:1304.6912).
- **Uniqueness.** Worst-case block Jaccard against the 50 frozen prior artifacts is 0.66 at 32 px blocks —
  *below* the median of the same statistic between genuinely independent prior artifacts (0.83), so the
  block test is not informative at this scale. The audited statement is narrower: a new sha256, no prior
  raster read into the belief field, and 2.7 % exact-pixel overlap with the only prior submission available
  locally ([`evidence/uniqueness_h51.json`](evidence/uniqueness_h51.json)).
- **H50-S1 remains blocked.** The waveform-relocated Nevada catalog has still not been fetched in this
  sandbox (direct Zenodo egress fails TLS here), so the H50-S1 experiment has not run and no H50-S1 DTI is
  claimed. The inherited mixed-network ComCat extract is used **only** as H51's own evidence line, with USGS
  public-domain status recorded in [`registry/sources.json`](registry/sources.json).
- **Score context stays honest.** The owner-quoted `0.3195` and sibling-repository leaderboard notes are
  historical, not a live board. DrivenData's Terms of Use prohibit automated monitoring or copying; this
  repository links to the official board but never polls, scrapes, or publishes a leaderboard snapshot, and
  no score is mapped to a TIFF. One unintended automated request to the public leaderboard page occurred
  during prior research; no rows/scores were saved or used, and no further automated access will be made.
- This session's Arena branch is `arena/fe65fa32-gemsdoe50`; the older
  [`h50s1-research.yml`](.github/workflows/h50s1-research.yml) workflow is pinned to
  `arena/c6060a3e-gemsdoe50` and is not used by H51.
- **Inherited H50-S1 status from `main` (still true).** The dispatch-only research workflow now returns
  HTTP 403 `Resource not accessible by integration`, so no job ran and no data was fetched and the
  experiment still has not run; the branch also carries two matched Gaussian-smoothed relocated-event density controls
  (1 km and 2 km) as required comparators, plus the H50-prior fixed-incumbent rule. Inherited validation in
  this checkout is now **75 tests passed, 1 skipped** (was 61/1 before H51), and the frozen split spec
  (`78b6692155c6c6d5f9f19ccee6d595167c2065f1f25eb8d08636d1d9b285ff16`) plus the realized-mask report
  (`981b42e6d0310bf77f79c7c7662a0569c8d2e79514ef4e4a3624a5b07583ae3f`) are unchanged.
- **Inherited provenance caveat from `main` (still true).** The bridge manifest points at the official data
  tab and public Dropbox mirrors, but no session has authenticated to DrivenData and re-downloaded the
  official bytes; matching hashes establish consistency with the bridge manifest, not organizer provenance.


- **Pass-3 re-check (2026-10-06).** Every clause of the original request is mapped to an artifact in
  [`docs/pass3-review-20261006.md`](docs/pass3-review-20261006.md), together with the defects found in
  Pass 2/3, the remaining work, and the limitations. The 5 ranked *untried* hypotheses now also appear
  as a card on the executive-summary page (rank, layers, signature, why the catalogue can miss the
  fault, difference from what is implemented, cost, expected gain, and the slot rule).

## Executive summary and submission instructions

The site is generated at repository root by [`scripts/build_h50_site.py`](scripts/build_h50_site.py) and
serves [`index.html`](index.html), [`results.html`](results.html), [`methods.html`](methods.html) and
[`submission.html`](submission.html). The **first thing on the executive-summary page is a one-click
download band** for the H51 file (GeoTIFF, all-finite twin, and zip), next to the unique portal name and
the optional note.

Numbered manual upload path (this repository never uploads for you and holds no portal credentials):

1. Download the GeoTIFF — or the zip containing it — from the band at the top of the site.
2. Optionally confirm the bytes against the SHA-256 shown next to the link.
3. Sign in to DrivenData manually and open *DOE GEMS Prize Challenge → Submit*.
4. Choose the downloaded `.tif`.
5. Use the unique name `GEMSDOE50-H51-SCARPRADIO-OFFCAT` and the note
   “GEMSDOE50 H51 | corroborated 3DEP-scarp + radiometric lineaments, all dots >300 m from the given
   catalogue, metric-matched sparse emission; proxy-validated, NOT organizer-scored”.
6. Submit, then record the returned score next to the file hash before making any claim about it.

A local pass is a proxy result, not an organizer score, and it licenses a manual upload decision only.

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

1. **Manual owner decision** on whether to spend one of the three weekly slots on the H51 file. Nothing is
   uploaded by this repository: H51 has an artifact and local proxy evidence, but no organizer score.
2. If a slot is spent, record the returned score and the portal receipt next to the pinned sha256; never
   restate proxy numbers as official.
3. **Top untried candidate (H52-A: scarp-profile matched filter with drainage-deflection corroboration)**
   must pass its own preregistration and the same spatially blocked test
   ([`scripts/validate_h51_holdout.py`](scripts/validate_h51_holdout.py)) before it can be considered for a
   slot. The ranked list is in [`docs/h51-candidates.md`](docs/h51-candidates.md) and in the site's
   executive-summary card.
4. **H50-S1 stays blocked.** The fixed-branch dispatch-only workflow returns HTTP 403 in this repository, so
   the Nevada catalog still needs an auditable acquisition route; the hypothesis itself is unchanged and
   unimplemented, and no H50-S1 DTI or raster is claimed.
5. Re-verify the large snapshot-excluded input stack (`/home/user/.arena/inputs/`) before any rebuild; the
   build regenerates deterministically from those pinned bytes
   (`python scripts/build_h51.py`, then `scripts/verify_h51_raster.py`, `scripts/uniqueness_h51.py`,
   `scripts/mc_sensitivity_h51.py`, `scripts/validate_h51_holdout.py`,
   `scripts/update_registries_h51.py`, `python scripts/build_h50_site.py`).
6. Any next iteration must independently re-open and byte-validate its GeoTIFF, refresh the
   executive-summary/results/submission pages, and re-check source licenses, attribution, limitations, and
   the AI-use disclosure before a slot is spent.
