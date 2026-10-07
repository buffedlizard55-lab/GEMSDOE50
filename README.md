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
10. **Create and merge a PR when practical.** Keep all work on your own session's fixed Arena branch.
    This charter has now been carried forward and merged by three concurrent sessions working on this
    same repository — `arena/5e2ce8c3-gemsdoe50` (wrote this top-level charter and the
    corridor-consensus-mix candidate below), `arena/a51bdd46-gemsdoe50` (wrote the H52 section below,
    merged second), and `arena/2e04de3b-gemsdoe50` (wrote the H50-S1 terrain-intersection auditability
    work reflected throughout this file, merged third). Run tests and review the PR before merging. Do
    not switch branches or push elsewhere. Before opening a PR, fetch and merge `origin/main` to check
    for this kind of concurrent drift — do not wait until the end of a long session to check.

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

## H54 (2026-10-07, this session) - corpus-calibrated truth prior, metric-derived stratified emission

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

## Executive summary and submission instructions

The site is generated by [`scripts/build_h50_site.py`](scripts/build_h50_site.py) and the
archival status feed by [`scripts/build_site.py`](scripts/build_site.py) plus
[`scripts/update_registries_h51.py`](scripts/update_registries_h51.py) and
[`scripts/update_registries_h53.py`](scripts/update_registries_h53.py). CI runs the project tests,
rebuilds `index.html`, `results.html`, `methods.html`, and `submission.html`, and checks that the
committed pages are reproducible. The candidate panels are evidence-backed research displays;
their presence does not resolve data rights or authorize an upload. `index.html`'s hero download is
**H52**, the strongest candidate on the shared frame below; the other three files remain one click
away as separately tracked, independently built candidates from three concurrent Arena sessions.

**Current H50-S1 status:** the registered relocated-plane / terrain-intersection experiment has not
run. No H50-S1 holdout result, evaluation report, or H50-S1 TIFF exists, and no weekly slot, upload,
organizer score, or receipt is claimed. The candidate TIFFs below are H51/H52/H53 research
diagnostics, not substitutes for the H50-S1 workflow or evidence of competition performance.

**Research-only downloads; none is cleared for external upload:**

| Candidate | GeoTIFF | Reserved portal name | Optional note |
|---|---|---|---|
| A · corridor-consensus mix | `downloads/gemsdoe50-h51-corridor-consensus-mix-20261007T0200Z.tif` | `gemsdoe50-h51-corridor-consensus-mix-20261007T0200Z` | Corridor evidence (seismicity lineaments, magnetic/radiometric ridges, thermal springs) fused with a score-consensus core; off-catalogue, 300 m-aware geometry; pixel and 200 m-neighbourhood novelty checked against 26 prior artifacts. |
| B · scarp + radiometric lineaments | `docs/downloads/gems51-scarpradio-offcat-35000-20261006-ecf058ea-nan.tif` | `GEMSDOE50-H51-SCARPRADIO-OFFCAT` | GEMSDOE50 H51: corroborated 3DEP-scarp + radiometric lineaments, all dots >300 m from the given catalogue, metric-matched sparse emission; proxy-validated, not organizer-scored. |
| C · TMI x K/U gradient-ridge conjunction | `downloads/gemsdoe50-h53-tmiconj-20261007T0345Z.tif` | `GEMSDOE50-H53-TMICONJ-OFFCAT` | GEMSDOE50 H53: TMI x K/U gradient-ridge conjunction, off-catalogue 300 m-aware dots; proxy-validated vs uniform + translation controls, not organizer-scored. |
| D · H51 ∪ scarp-matched-filter+drainage (hero download) | `docs/downloads/gems52-union-h51-h52a-offcat-44828-20261007T021528Z-990213fd-nan.tif` | `GEMSDOE50-H52-UNION-OFFCAT` | GEMSDOE50 H52: H51 scarp+radiometric UNION H52-A scarp-matched-filter+drainage; disclosed fusion of this project's own validated prior work (~78% of its mass is H51's), not an independently new method; strongest candidate on the shared frame below; proxy-validated, not organizer-scored. |

A is float32, EPSG:32611, 3730×3292, 30,000 predicted pixels, SHA-256
`a26055834f8e6cc57cc33e96a4a5a26a1adeaafbeec490135af84c6ccd4d1da0` (339,039 bytes); in-footprint
values are finite `0`/`1`, with NaN outside the published footprint. B uses the same grid and dtype,
with 35,000 predicted pixels and SHA-256
`8f8708d2872b66d71925707e0aede23eebcf217dfd2e57d6e61186f32e686f5d`. C is the same grid and dtype
with 23,598 predicted pixels, SHA-256
`3c22da583d5358b2986189a4ed3322182f39f562bdde14809f3300aeb6bd37ea` (159,966 bytes). D is the same
grid and dtype with 44,828 predicted pixels, SHA-256
`15468475cc99b9106b9959c95add9966ad38678329435daa3a9cbf7e8ccc9a21` (355,561 bytes); a standalone,
near-independent sibling (`GEMSDOE50-H52A-SCARPDRAINAGE-OFFCAT`, only 1.7% cell overlap with B) is
also available, see `submission.html`. Each has an `-allfinite.tif` twin that writes `0.0` outside
the footprint and a one-file `.zip`; these are format variants, not separate evidence of
eligibility. The format and novelty checks do not establish permission to share the exact source
derivatives with the competition sponsor.

**Manual submission steps are instructions, not authorization.** Do not use a weekly slot unless
all statistical, scientific, provenance, and source-rights gates pass and the owner approves. If
those conditions are independently met: (1) download one `.tif` and verify its SHA-256; (2) open
the [competition page](https://www.drivendata.org/competitions/306/competition-doe-gems/) manually;
(3) upload without re-saving, re-projecting, or re-compressing; (4) use the matching reserved name
and note above; (5) manually verify and record the portal receipt before claiming any score.
`submission.html` repeats the manual checklist and warns that no automated upload occurs.

**Evidence and decision.** Candidate A has format/novelty checks, but its preregistered
`sgmc_off` proxy gate fails (0.0573 versus a matched-uniform 0.0593); its consensus-instrument
estimate of 0.1684 is a model prediction, not an organizer score. Candidate B has positive local
holdout evidence in 4/4 macrofolds on its own off-catalogue frame, but uses a derived scarp raster
with no documented reuse license. Candidate C requires cross-physics agreement (TMI x K/U) before
emitting and beats its own uniform/translation controls in 4/4 quadrants, but scores well below B
and D on the shared frame. Candidate D (H52) passed a dedicated spatially blocked holdout (beats B
in 3/4 macrofolds, a matched random control in 4/4, bootstrap 95% CI entirely positive) and is the
strongest candidate on the shared frame, but is a disclosed pixel superset of B — not an
independently-derived result — and inherits B's same unresolved scarp-raster/ComCat licensing
caveats. The mixed-network ComCat used in A's exploration also has unresolved contributor
rights/shareability. No file is cleared for an external upload or weekly slot; these are
measurements, not slot recommendations.

The single shared-frame comparison ([`evidence/h51_candidate_frame_compare.json`](evidence/h51_candidate_frame_compare.json)
and `evidence/h53_validation_final.json`, produced with the same truth mask and scoring code) is the
only direct ordering of the four files:

| file | dots | shared-frame `sgmc_off` DTI | credit per dot |
|---|---:|---:|---:|
| A · corridor-consensus mix | 30,000 | 0.0566 | 0.1050 |
| B · scarp + radiometric lineaments | 35,000 | 0.1158 | 0.1889 |
| C · TMI x K/U conjunction | 23,598 | 0.0565 | 0.1303 |
| **D · H52 (H51 ∪ H52-A)** | 44,828 | **0.1518** | 0.2007 |
| archived `gems50-seislin-44709` (not resubmittable) | 44,709 | 0.1472 | 0.1972 |
| matched uniform control (30 k, A/B) | 30,000 | 0.0592 mean / 0.0617 max | — |
| translations (4, A/B) | — | 0.0448 mean / 0.0472 max | — |

On this proxy frame, D (H52) is the strongest in-repo candidate, ahead of the archived
non-resubmittable incumbent, B, C, and A in that order; A does not beat the matched uniform control.
B's separate own-sweep value is 0.1889 credit/dot versus 0.1161 for its matched random control, with
a paired subtile-bootstrap 95% CI of `[0.0406, 0.0785]`; these proxy metrics do not override the open
license gates and are not organizer scores. No upload or portal receipt exists for any file.

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

This is a condensed paraphrase, not the user's verbatim original message text (see "What this
session left honestly unfinished" below for why a true verbatim embed has not been produced).

See "## Executive summary and submission instructions" near the top of this README for the current
one-click downloads, portal names/notes, and manual submission steps — that section was updated by
the third concurrent session (terrain-intersection work) with more cautious, up-to-date license
language and is the single copy this README maintains, to avoid the two sections drifting apart.

## H52 (2026-10-07, concurrent session `arena/a51bdd46-gemsdoe50`) — a second, independently built and validated candidate

This section was written by a **second Arena session working on this same repository at the same
time** as the corridor-consensus-mix work above. It implemented and validated the top-ranked
*untried* hypothesis from `docs/h51-candidates.md` (scarp-profile matched filter + independent
drainage-deflection corroboration) before either session had seen the other's commits, then merged
second and reconciled the two lines of work in this PR. It is kept as its own section, not
interleaved with the text above, so neither session's numbers are misattributed to the other.

### What was built

- **H52-A** (`src/gems51/scarpmf.py` + `src/gems51/drainage.py`, 8 new passing unit tests): a signed,
  azimuth-specific scarp-cross-section matched filter on detrended `topo_u8` elevation, corroborated
  by an independent channel-deflection/knickpoint test from `pysheds` D8 flow routing at the same
  azimuth — the first candidate in this project's history to require two independent physical
  quantities to agree rather than OR-ing/summing layers. `training_features.tif` (needed for the
  originally proposed `det_elev`/`det_elev_slope` bands) is confirmed **permanently unobtainable**
  in this sandbox; `topo_u8` + `pysheds` routing was substituted as a different implementation of the
  same physical test, recorded as an irregularity in `docs/h52a-protocol.md`.
- **H52 = H51 ∪ H52-A**: a mechanical pixel union of H51's fixed 35,000-dot file with H52-A's
  10,000-dot file (only 172 pixels coincide), with no new tunable threshold.

### What it measures, and how it cross-checks against the corridor-consensus work above

On the exact same off-catalogue SGMC frame the parallel session used to build
`evidence/h51_candidate_frame_compare.json` (confirmed by this session's own, independently computed
`evidence/build_h51.json` DTI for the scarp+radiometric file matching that file's row to 10
significant figures — same truth mask, same scoring code, not a re-tuned metric):

| candidate | dots | SGMC-off DTI (shared frame) |
|---|---:|---:|
| **H52 = H51 ∪ H52-A (this session)** | 44,828 | **0.1518** |
| Frozen prior incumbent `gems50-seislin-44709` (not resubmittable) | 44,048 | 0.1472 |
| H51 alone, scarp + radiometric | 35,000 | 0.1158 |
| Corridor-consensus-mix (parallel session's shipped candidate above) | 30,000 | 0.0566 (below its own matched uniform control) |

H52 is the strongest file either session has produced on this shared, apples-to-apples frame. It
also passed a dedicated spatially-blocked holdout test before being written up here: it beats H51 in
3/4 frozen macrofolds and a matched-mass random control in 4/4, with a paired subtile bootstrap 95%
CI entirely positive, `[0.0063, 0.0174]` (`evidence/holdout_h52.json`,
`docs/h52a-protocol.md` Amendments B1–B2 for the full promotion-gate record).

### The disclosure this section exists to make explicit

**H52 is a literal pixel superset of H51.** All 35,000 of H51's dots are included unchanged; H52-A
contributes 9,828 genuinely new dots after removing the 172 that already coincided with H51. That
means roughly **78% of H52's emitted mass is H51's own prior output** — only about 22% is the output
of a method never built before this session. H51 has never been uploaded to the DrivenData portal
(`organizer_score: null`, `submitted_utc: null` in `registry/submissions.json`), so this is not
"copying a previous *submission's* pixels" in the sense the project's own rule 1 (above) prohibits —
but it is an internal fusion of this project's own prior and new work, and the site, registry, and
this README describe it that way everywhere, never as an independently-derived new hypothesis.
**H52-A standalone** (only 1.7% cell overlap with H51) is offered as the genuinely independent
artifact for anyone who does not want a fused file — see `submission.html` for both unique names and
notes.

### Deep-research deliverable from this session

`docs/research/geothermal-vents-20261007.md` is a sourced, link-verified research note on what
actually controls blind geothermal systems in the Great Basin (USGS/DOE/NBMG "play fairway"
literature), which surfaces a free, CC-BY-4.0 source — GDR submission 1391 / the INGENIOUS project —
that could supply a substitute for the still-unobtainable `training_features.tif` magnetic/gravity/
`det_elev` bands, plus genuine mapped geothermal-vent and paleo-spring point data. That source is
**not fetchable from this sandbox** (same `SSL_ERROR_SYSCALL` network ceiling documented for every
other non-GitHub host this project has tried); it is recorded as two new, unimplemented H54-A/H54-B
candidates in `docs/h51-candidates.md` Part 3 for whichever session gets normal network egress next.

### What this session left honestly unfinished

- **The full, verbatim original mega-prompt is not embedded in this README.** This agent's available
  session memory preserves a condensed/paraphrased form of the user's instructions across a long
  multi-session task, not the literal original message text, so a true verbatim embed cannot be
  produced without risking fabrication of wording the user never wrote. The "Standing project brief"
  at the top of this README is the faithful distilled charter actually re-read each session; the
  exact original text should be pasted in directly by the user if a literal verbatim copy is
  required.
- H54-A/H54-B (above) are named and sourced but not implemented.
- No portal upload has been made for any file this project has produced (H50-prior, the
  corridor-consensus-mix candidate, H51, H52-A, H52, or the third concurrent session's H53 TMI x
  K/U conjunction file); every `organizer_score` in `registry/submissions.json` is `null`.
- A third Arena session (`arena/7a17402d-gemsdoe50`) built and shipped H53-A/B/C (a TMI x K/U
  gradient-ridge conjunction family) concurrently with this section and merged into `main` third;
  its numbers are folded into the "Executive summary" table above and into
  `registry/hypotheses.json`/`registry/sources.json`, not restated here to avoid a fourth
  diverging narrative. See `docs/research/h53-hypotheses.md` and `docs/research/h53-analysis.md`
  for that session's own write-up.
