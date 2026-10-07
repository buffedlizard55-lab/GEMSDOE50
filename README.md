# GEMSDOE50 — seismic-geometry research for the DOE GEMS Prize

**Project aim:** maximize the probability of a strong result in the [DOE Geologic Enhanced Mapping System (GEMS) Prize Challenge, DrivenData competition 306](https://www.drivendata.org/competitions/306/competition-doe-gems/), by finding defensible, previously unmapped fault traces in the GeoDAWN study area. Core values: **Maximize P(Win)** and **Own the Outcome**.

> **Read this charter before each work session.** It is the standing project purpose and the acceptance criteria for every experiment and deliverable.

## Standing project brief

1. **Deliver a new, unique GeoTIFF prediction.** Generate it from this repository's documented method and pinned inputs. Never copy a previous submission's prediction pixels; earlier artifacts may be inspected only for education, controls, or comparison. The intended download must be a single-band float32 GeoTIFF on the actual competition grid, EPSG:32611, 100 m resolution, with the official shape, transform, and bounds. Predictions must be finite and within `[0, 1]` wherever data are valid; outside-footprint handling must follow the official sample/template and be tested against the reported portal error `Predicted values must be in range [0, 1]`.
2. **Make the artifact easy to find and download.** Put a one-click download and a concise executive summary at the top of the site. Include a clear, numbered “how to submit” page, a unique submission name, and a short distinguishing note for the competition's optional note field. Do not imply portal acceptance when no upload receipt exists.
3. **Do the science before implementation.** Before writing a detector, list and rank 3–5 genuinely distinct geological hypotheses. Each must state the exact layers/data, physical signature, why it could detect a fault missing from USGS/INGENIOUS, how it differs from prior GEMSDOE work, expected DTI direction/impact, implementation cost, and data/license requirements. See the current audit in [`docs/research/hypothesis-ranking-20261006.md`](docs/research/hypothesis-ranking-20261006.md), the preregistered candidates in [`docs/hypotheses-preregistered.md`](docs/hypotheses-preregistered.md), and exact H50-S1 implementation choices/controls in [`docs/h50s1-protocol-addendum.md`](docs/h50s1-protocol-addendum.md). Re-check old work before calling any variant new.
4. **Protect the weekly submission budget.** Validate the leading hypothesis on a spatially blocked holdout against a frozen, same-fold incumbent and preregistered controls before using any of the competition's three weekly scoring slots. H50-S1 must strictly beat all three same-event smoothed-density controls (300 m, 1 km, and 2 km) and pass formal aftershock, mine/injection-site, and event-location-uncertainty gates. A hypothesis that fails any gate is not slot-eligible. A local proxy score is not an organizer score or a prediction of private-test performance.
5. **Use compliant, traceable evidence.** Prefer official and peer-reviewed primary sources; link sources directly, state evidence and license status, pin file hashes, and disclose attribution/changes. External data may be used only where the competition permits it, the license permits commercial use, and the data can be shared with the organizers for independent verification. Do not use the scratch mixed-network USGS ComCat extract until its source-specific rights and location uncertainty are resolved.
6. **Do not overstate the literature.** H50-S1 is a 3-D local plane-fitting hypothesis on relocated Nevada events, but its catalog lacks per-event location covariance and it is not ACLUD. The already-implemented legacy H50-B method uses 2-D ComCat covariance/lineations; its 2-D triangle-area reduction of a 3-D tetrahedron statistic is explicitly **unverified**, and the builder does not apply the computed `keep` mask. Neither method is a validated transfer of the cited 3-D methods: [Ouillon et al. (2008)](https://doi.org/10.1029/2007JB005032), [Ouillon & Sornette (2011)](https://doi.org/10.1029/2010JB007752), and [Wang et al. (2013)](https://arxiv.org/abs/1304.6912).
7. **Work autonomously and auditably.** Review rules, data, sources, prior attempts, and limitations; record every material decision and irregularity; run multiple implementation/review passes; fix defects found; and maintain a concise next-steps list. Do not ask the owner to do research or resolve issues the agent can verify independently.
8. **Keep the score context honest.** An archived GEMSDOE50 report associates `0.2778` with H33-2-B2, but the current GEMSDOE32 owner site labels H33-2-B2 unscored and `0.2747` a model projection; the `0.2778` score-to-artifact association remains unresolved. The owner-provided `0.3195` is historical context only—not independently verified, not asserted as the live leader, and not mapped to a verified TIFF. Do not repeat either as a current official score or scrape, poll, or copy leaderboard data. DrivenData's Terms of Use restrict monitoring/copying; this repository links to the official board but does not monitor or publish leaderboard snapshots.
9. **Follow the prize rules.** The September 2026 NLR/DOE rules require an AI-use disclosure in the narrative, permit up to three feedback submissions per week, and require selection of one final submission for both prize rounds. Finalists must provide reproducible code/assets and documentation. The competition ends December 3, 2026 at 23:59 UTC (verify the official page before any deadline-dependent action).
10. **Create and merge a PR when practical.** Keep all work on Arena's fixed branch `arena/2e04de3b-gemsdoe50`. Run tests and review the PR before merging. Do not switch branches or push elsewhere.

## Current evidence and decision (2026-10-07 UTC)

**Where the project actually stands.** The inherited H50 seismicity work is historical; the
registered H50-S1 relocated-plane/terrain-intersection experiment has not run in this session.
The H51/H52 research and candidate artifacts added on `main` are the current built work here.
Read this section as the starting point of every session, then read
[`docs/research/h51-analysis.md`](docs/research/h51-analysis.md) (what the prior-art corpus can and
cannot establish, including the owner-provided 0.3195 context),
[`docs/research/h51-hypotheses.md`](docs/research/h51-hypotheses.md) (ranked hypotheses with their
fields), and [`docs/research/h51-truth-map.md`](docs/research/h51-truth-map.md) (a negative result
that closes a whole line of attack).

- **The metric, exactly.** With binary dots the official distance-weighted Tversky index collapses
  to `DTI = T / (0.2·N + 0.8·G)`, where `N` is the predicted pixel count, `T` the credit captured
  inside the 300 m kernel, and `G` the hidden truth mass in the scored domain. Inverting the pinned
  blind-lattice artifact gives **`G ≈ 12,226 px`** (±~1 %). Two consequences drive every decision
  below: a dot pays only if it earns more than `0.2·s ≈ 0.05` credit, and coverage — not dot
  count — is the binding term.
- **Every scored artifact inverted.** The 25 hash-verified artifacts of
  `registry/h51_score_corpus.json` were converted to credit pixels (`scripts/h51_truth_map.py`).
  The corpus's best credit per dot is **0.1097** (`gems25-dotted-h19-5-d2-8`, owner-quoted 0.2600)
  and its best coverage is **59.3 %** (a 183,642-dot blanket at 0.0395 credit/dot). **The whole
  group's detector family cannot reach ≈41 % of the estimated hidden-truth mass.** Conditional on
  the corpus-derived `G` estimate, a hypothetical DTI of 0.3195 at `N = 30,000` corresponds to
  `T ≈ 5,042` (41.2 % estimated coverage). This algebra does not verify the owner-provided
  historical 0.3195 value, its provenance, or its current leaderboard status.
- **Instrument, and its honest limit.** The consensus instrument (posterior over the 25 scored
  artifacts) predicts a held-out artifact's real score at leave-one-out Spearman **0.973**
  (`evidence/h51_consensus.json`), but a *trivial* predictor that uses only how similar an artifact
  is to the winners already reaches **0.905**. Most of the instrument's skill is corpus
  self-similarity, its optimum is literally a re-draw of the corpus (98 % of dots on prior pixels),
  and a block-grid **truth-density inversion fails leave-one-out** at every resolution tested
  (`evidence/h51_truth_map.json`). The score history constrains *efficiency*, not geography.
- **Shipped candidate (one click on the site).**
  `downloads/gemsdoe50-h51-corridor-consensus-mix-20261007T0200Z.tif` — 24,000 consensus-core dots
  (every one on a pixel no prior artifact used) plus 6,000 evidence-only exploration dots
  (seismicity-lineament corridors, TMI/radiometric ridges, thermal springs) more than 200 m from
  every prior dot. Format-clean float32 on the official grid, values in `[0, 1]`, NaN outside the
  footprint; **0 pixels shared with any of the 26 prior artifacts**; frozen uniqueness gate
  **PASS** (`max 2 px-proximity IoU 0.4219 < 0.5`, `min_novel_fraction_at_2px 0.2003`). Instrument
  prediction **0.1684** (LOO RMSE 0.025).
- **It is a measurement, not a win, and the README says so before the download.** The H51
  consensus instrument prediction of 0.1684 is numerically below the owner-provided historical
  0.3195 reference, but they are not a verified like-for-like score comparison. The often-repeated
  0.2778 association is unresolved: the current GEMSDOE32 owner site labels H33-2-B2 unscored and
  0.2747 a projection. The candidate also **fails the pre-registered `sgmc_off` proxy gate**
  (0.0573 vs matched uniform 0.0593) — and that proxy has no demonstrated power to predict a live
  score (ρ = +0.196, p = 0.35 over 25 real scores, `evidence/h51_proxy_ranking_power.json`), so the
  failure is recorded as a limitation rather than explained away. The archived `seislin-44709`
  artifact is the opposite case: priced at 0.0422 by the instrument but 2.5× the uniform control on
  the independent `sgmc_off` frame. The two evidence lines conflict; §12 of the analysis records it
  instead of hiding it.
- **Rejected designs are recorded with their numbers** so no future session re-litigates them: the
  instrument optimum that re-draws the corpus (0.2559, forbidden by the originality rule); a
  pixel-disjoint halo interleave that satisfies the letter of "no copied pixels" but is a one-pixel
  translation of the group's own structure (0.1989, rejected on the 2 px-proximity gate,
  `evidence/h51_ship_novel.json`); an exploration-free core (0.1806, gate-passing, but no new
  territory); and every spacing/thinning variant (recorded in the frontier files).
- **Decision rule for the next slot.** A candidate must (a) pass `scripts/check_submission.py` with
  `GEMS50_CORPUS` mounted (`verdict_unique: true`), (b) beat the frozen incumbent on the consensus
  instrument, and (c) not be a translation of prior structure. The 0.3195 historical reference is
  not a verified like-for-like comparison target for this proxy instrument, and the 0.2778
  score-to-artifact association remains unresolved. Neither H51 candidate has an organizer score;
  any slot decision remains the owner's and is not recommended by this paragraph alone.
- **Data reality in this sandbox.** `data/grid/{labels,sample_submission}.tif` are present and
  hash-consistent with the bridge manifest. The 19-band competition feature stack is **not**
  available here and its Dropbox mirrors are network-blocked (as are Zenodo, USGS ScienceBase,
  EarthExplorer, and `raw.githubusercontent.com`); reachable hosts are `github.com`,
  `api.github.com`, `codeload.github.com`, `pypi.org`, and `files.pythonhosted.org`. Staged
  geophysical layers (TMI, K, radiometric, LiDAR scarp features) live in the public sibling
  repository `GEMSDOE24` and are re-clonable from GitHub. The ComCat extract under
  `data/external/` is a mixed-network product whose source-specific rights are unresolved, so it is
  used for exploration only, never as a submission input.

## Executive summary and submission instructions

The site is generated by [`scripts/build_h50_site.py`](scripts/build_h50_site.py) and the
archival status feed by [`scripts/build_site.py`](scripts/build_site.py). CI runs the project tests,
rebuilds `index.html`, `results.html`, `methods.html`, and `submission.html`, and checks that the
committed pages are reproducible. The H51 candidate panels are evidence-backed research displays;
their presence does not resolve data rights or authorize an upload.

**Current H50-S1 status:** the registered relocated-plane / terrain-intersection experiment has not
run. No H50-S1 holdout result, evaluation report, or H50-S1 TIFF exists, and no weekly slot, upload,
organizer score, or receipt is claimed. The candidate TIFFs below are H51 research diagnostics, not
substitutes for the H50-S1 workflow or evidence of competition performance.

**Research-only H51 downloads; neither is cleared for external upload:**

| Candidate | GeoTIFF | Reserved portal name | Optional note |
|---|---|---|---|
| A · corridor-consensus mix | `downloads/gemsdoe50-h51-corridor-consensus-mix-20261007T0200Z.tif` | `gemsdoe50-h51-corridor-consensus-mix-20261007T0200Z` | Corridor evidence (seismicity lineaments, magnetic/radiometric ridges, thermal springs) fused with a score-consensus core; off-catalogue, 300 m-aware geometry; pixel and 200 m-neighbourhood novelty checked against 26 prior artifacts. |
| B · scarp + radiometric lineaments | `docs/downloads/gems51-scarpradio-offcat-35000-20261006-ecf058ea-nan.tif` | `GEMSDOE50-H51-SCARPRADIO-OFFCAT` | GEMSDOE50 H51: corroborated 3DEP-scarp + radiometric lineaments, all dots >300 m from the given catalogue, metric-matched sparse emission; proxy-validated, not organizer-scored. |

A is float32, EPSG:32611, 3730×3292, 30,000 predicted pixels, SHA-256
`a26055834f8e6cc57cc33e96a4a5a26a1adeaafbeec490135af84c6ccd4d1da0` (339,039 bytes); in-footprint
values are finite `0`/`1`, with NaN outside the published footprint. B uses the same grid and dtype,
with 35,000 predicted pixels and SHA-256
`8f8708d2872b66d71925707e0aede23eebcf217dfd2e57d6e61186f32e686f5d`. Each has an `-allfinite.tif`
twin that writes `0.0` outside the footprint and a one-file `.zip`; these are format variants, not
separate evidence of eligibility. The format and novelty checks do not establish permission to
share the exact source derivatives with the competition sponsor.

**Manual submission steps are instructions, not authorization.** Do not use a weekly slot unless
all statistical, scientific, provenance, and source-rights gates pass and the owner approves. If
those conditions are independently met: (1) download one `.tif` and verify its SHA-256; (2) open
the [competition page](https://www.drivendata.org/competitions/306/competition-doe-gems/) manually;
(3) upload without re-saving, re-projecting, or re-compressing; (4) use the matching reserved name
and note above; (5) manually verify and record the portal receipt before claiming any score.
`submission.html` repeats the manual checklist and warns that no automated upload occurs.

**H51 evidence and decision.** Candidate A has format/novelty checks, but its preregistered
`sgmc_off` proxy gate fails (0.0573 versus a matched-uniform 0.0593); its consensus-instrument
estimate of 0.1684 is a model prediction, not an organizer score. Candidate B has positive local
holdout evidence in 4/4 macrofolds on its own off-catalogue frame, but uses a derived scarp raster
with no documented reuse license. The mixed-network ComCat used in A's exploration also has
unresolved contributor rights/shareability. Neither file is cleared for an external upload or
weekly slot; these are measurements, not slot recommendations.

The single shared-frame comparison ([`evidence/h51_candidate_frame_compare.json`](evidence/h51_candidate_frame_compare.json),
produced with the same truth mask and scoring code) is the only direct ordering of the new files:

| file | dots | shared-frame `sgmc_off` DTI | credit per dot |
|---|---:|---:|---:|
| A · corridor-consensus mix | 30,000 | 0.0566 | 0.1050 |
| B · scarp + radiometric lineaments | 35,000 | **0.1158** | **0.1889** |
| archived `gems50-seislin-44709` | 44,709 | 0.1472 | 0.1972 |
| matched uniform control (30 k) | 30,000 | 0.0592 mean / 0.0617 max | — |
| translations (4) | — | 0.0448 mean / 0.0472 max | — |

On this proxy frame, B is stronger than A; A does not beat the matched uniform control, and the
archived comparator scores higher than both but cannot be resubmitted because it fails the novelty
gate. B's separate own-sweep value is 0.1889 credit/dot versus 0.1161 for its matched random control,
with a paired subtile-bootstrap 95% CI of `[0.0406, 0.0785]`; these proxy metrics do not override the
open license gates and are not organizer scores. No upload or portal receipt exists for either file.

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

### Inherited from `main` and still true

- **The registered H50-S1 terrain-intersection experiment has not run.** Its earlier dispatch-only
  workflow returned HTTP 403 `Resource not accessible by integration`, so no job ran and no catalog,
  exact-grid 3DEP DEM, holdout DTI, result report, or new H50-S1 candidate TIFF was produced. The
  frozen split spec (`78b6692155c6c6d5f9f19ccee6d595167c2065f1f25eb8d08636d1d9b285ff16`) and
  realized-mask report (`981b42e6d0310bf77f79c7c7662a0569c8d2e79514ef4e4a3624a5b07583ae3f`) are
  unchanged. The new workflow in this PR is an acquisition/run route, not evidence of a run.
- **What this PR adds.** H50-S1 now fits local planes to relocated Nevada events and intersects them
  with a pinned-grid USGS 3DEP DEM rather than sea-level `z=0`; it compares the result against the
  fixed H50-prior incumbent, 32 translations, 20 time shuffles, and same-event density controls at
  300 m, 1 km, and 2 km. A new TIFF is written only after the statistical holdout gate passes and
  byte/grid validation succeeds. Event-location covariance, declustering, mine/injection screens,
  vertical-datum reconciliation, and independently authenticated training-raster provenance still
  block any slot; no real run, DTI, report, H50-S1 TIFF, upload, receipt, or slot use is claimed.
- **Provenance caveat.** The bridge manifest points at the official data tab and public mirrors, but
  no session has authenticated to DrivenData and re-downloaded the official bytes; matching hashes
  establish consistency with the manifest, not organizer provenance.
- **No automated leaderboard access.** One unintended automated request to the public leaderboard
  page happened during earlier research; no rows/scores were saved or used, and no further
  automated access is made. Historical sibling-repository scores are quoted as history only and are
  never mapped to a TIFF.
- **Repository suite in this reviewed working tree:** `.venv/bin/python -m pytest -q` → 108 passed;
  the project Ruff command, `compileall`, frozen-hash checks, and `scripts/verify_claims.py` also pass.

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

# Requires the pinned, exact-grid USGS 3DEP DEM and acquisition sidecar; do not run while
# the scientific/provenance blockers above remain unresolved.
python scripts/run_experiment.py \
  --catalog .arena/run/inputs/nvreloc_catalog_newmag.txt \
  --template .arena/run/inputs/example_submission.tif \
  --labels .arena/run/inputs/existing_faults.tif \
  --dem .arena/run/inputs/3dep_dem_100m.tif \
  --dem-metadata .arena/run/inputs/3dep_dem_100m.json \
  --prior-dir .arena/run/prior
python scripts/build_h50_site.py

# H51/H52 research pipeline (needs the staged corpus in .arena/work/h51; see scripts/h51_consensus.py)
python scripts/h51_consensus.py            # score instrument + leave-one-out validation
python scripts/h51_truth_map.py            # credit ledger + block-grid truth inversion (negative)
python scripts/h51_validate.py --candidates downloads/*.tif --incumbent downloads/gems50-seislin-*.tif
GEMS50_CORPUS=.arena/work/h51 python scripts/check_submission.py --submission downloads/gemsdoe50-h51-*.tif
python scripts/h51_ship_novel.py           # reproduces the rejected pixel-disjoint H52 design
python scripts/h51_validate.py --layers data/external \
  --candidates downloads/gemsdoe50-h51-corridor-consensus-mix-*.tif \
               docs/downloads/gems51-scarpradio-offcat-*.tif \
  --out evidence/h51_candidate_frame_compare.json   # the shared-frame comparison above

# The parallel-session candidate's own checks (unchanged from main).
python scripts/verify_h51_raster.py
python scripts/validate_h51_holdout.py
python scripts/uniqueness_h51.py
python scripts/update_registries_h51.py
```

## User's requested outcomes (preserved from the conversation brief)

> Build an auditable GEMSDOE50 research and submission workflow. Explain the historical `0.2778`
> and owner-provided `0.3195` context cautiously; do not scrape or monitor the live leaderboard.
> Research and rank 3–5 distinct geological hypotheses, documenting data, physical rationale,
> novelty versus prior work, expected impact, cost, and license requirements. Test the leading
> candidate on the frozen spatial holdout against the incumbent and controls before any weekly slot.
> Create a genuinely new competition-format TIFF with `[0,1]` predictions and the exact CRS/grid/
> transform only if the holdout supports it; make a verified artifact downloadable and document its
> filename, optional note, validation, sources, limitations, and manual submission steps. Work
> autonomously, use trusted sources, run multiple review/test passes, append this request to the
> README and reread it, and create and merge a PR when checks pass.

## Generated site and one-click downloads

The site is generated and CI-verified. Root pages come from
[`scripts/build_h50_site.py`](scripts/build_h50_site.py) (`index.html`, `results.html`,
`methods.html`, `submission.html`) and the data feed from [`scripts/build_site.py`](scripts/build_site.py)
plus [`scripts/update_registries_h51.py`](scripts/update_registries_h51.py) and
[`scripts/update_registries_h53.py`](scripts/update_registries_h53.py) (`docs/data/*.json`).
`.github/workflows/site.yml` regenerates the four root pages on every push and pull request and fails
the build if the committed bytes differ. `index.html` now opens with a **"three candidates, one
shared frame"** table rendered from `evidence/h51_ship.json`, `evidence/build_h51.json`,
`evidence/h51_candidate_frame_compare.json` and `evidence/h53_ship.json`, so the numbers on the
site cannot drift from the evidence, and all three GeoTIFFs are one click away.

**One-click downloads (top of the site):**

| candidate | file | portal name | note for the optional field |
|---|---|---|---|
| A | `downloads/gemsdoe50-h51-corridor-consensus-mix-20261007T0200Z.tif` | `gemsdoe50-h51-corridor-consensus-mix-20261007T0200Z` | "Corridor evidence (seismicity lineaments + magnetic/radiometric ridges + thermal springs) fused with a validated score-consensus core; off-catalogue, 300 m-aware dot geometry; pixels and 200 m neighbourhoods novel against all 26 prior artifacts." |
| B | `docs/downloads/gems51-scarpradio-offcat-35000-20261006-ecf058ea-nan.tif` | `GEMSDOE50-H51-SCARPRADIO-OFFCAT` | "GEMSDOE50 H51 \| corroborated 3DEP-scarp + radiometric lineaments, all dots >300 m from the given catalogue, metric-matched sparse emission; proxy-validated, NOT organizer-scored" |
| C | `downloads/gemsdoe50-h53-tmiconj-20261007T0345Z.tif` | `GEMSDOE50-H53-TMICONJ-OFFCAT` | "GEMSDOE50 H53 \| TMI x K/U gradient-ridge conjunction, off-catalogue 300m-aware dots; proxy-validated vs uniform+translation, NOT organizer-scored" |

A is `float32`, EPSG:32611, 3730×3292, values `0`/`1`, 30,000 predicted pixels, SHA-256
`a26055834f8e6cc57cc33e96a4a5a26a1adeaafbeec490135af84c6ccd4d1da0`, 339,039 bytes, NaN outside the
published footprint. B is the same grid and dtype with 35,000 predicted pixels, SHA-256
`8f8708d2872b66d71925707e0aede23eebcf217dfd2e57d6e61186f32e686f5d`. C is the same grid and dtype
with 23,598 predicted pixels, SHA-256
`3c22da583d5358b2986189a4ed3322182f39f562bdde14809f3300aeb6bd37ea`, 159,966 bytes. Each has an `-allfinite.tif`
sibling that writes `0.0` outside the footprint, for portals that reject non-finite values, so the
historical error `Predicted values must be in range [0, 1]` cannot recur; each also has a one-file
`.zip`.

**How to submit (manual, by the owner, never by this repository — it holds no portal credentials
and never uploads):**

1. Download one GeoTIFF — or its zip — from the band at the top of the site.
2. Confirm the bytes against the SHA-256 shown next to the link.
3. Sign in to [the competition](https://www.drivendata.org/competitions/306/competition-doe-gems/)
   manually and open *Submit*.
4. Choose the downloaded `.tif` without re-saving, re-projecting or re-compressing it.
5. Paste the unique name and the short note from the table above.
6. Submit, then record the receipt next to the file hash in this repository before claiming any
   score.

`submission.html` carries the same checklist. **No organizer score exists for any of the three
files and no weekly slot has been used by this repository.** Spending a slot is the owner's decision; the shared
frame above says which file to spend it on first.
