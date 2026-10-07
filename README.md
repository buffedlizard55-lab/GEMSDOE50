# GEMSDOE50 — earthquake point geometry for omitted-fault mapping

**Project aim:** maximize the probability of a strong result in the
[DOE Geologic Enhanced Mapping System (GEMS) Prize Challenge](https://www.drivendata.org/competitions/306/competition-doe-gems/)
by finding defensible fault traces omitted from the supplied catalogue. Core values:
**Maximize P(Win)** and **Own the Outcome**.

> **Read this charter before every work session.** It governs the research, code, artifact, site,
> and submission decision. A local proxy result is never an organizer score.

## Standing governing charter

1. **Review before building.** Review the complete repository, competition prompt, supplied
   GEMSDOE results, source rights, and prior attempts. Explain at PhD level why GEMSDOE32 artifact
   `h33-h33-2-b2-20261004T220000Z-e5eb6e7e` was associated with 0.2778 and whether a method could
   exceed the public leaderboard leader. The 2026-10-07 leaderboard snapshot displays xiaofanhu at
   0.3774 (rank 1) and extradr19 at 0.2778 (rank 13), but no receipt/hash crosswalk ties either score
   to a TIFF. Treat the 0.3195 value as a separate older owner-quoted snapshot. Never turn a score
   observation into an artifact attribution without an organizer receipt/hash crosswalk.
2. **Deliver a genuinely new raster.** Build a unique competition-grid GeoTIFF from documented
   inputs and code. Never copy prior prediction pixels; prior files may be used only for learning,
   controls, and comparison. Run full-resolution byte and pixel/proximity comparisons against every
   listed prior artifact, not merely coarse signatures.
3. **Use earthquake point geometry, not earthquake density, as the candidate.** Acquire a public,
   eligible event catalogue; record official URL, attribution, license, exact bytes, and external-
   data eligibility. Space-time thin/decluster it, screen known mining/injection or explicit
   anthropogenic sites, compute local two-dimensional covariance eigenstructure, retain recurrent
   well-sampled linear neighborhoods, broaden them under explicit location-width assumptions,
   score only outside supplied-fault buffers, and snap placement across-axis to an independent
   layer ridge. Smoothed density is a control, never the H55 prediction.
4. **Do not overstate the literature.** The H55 normalized 2-D triangle-area background test is an
   **unverified project adaptation**. It is not the published three-dimensional tetrahedron method
   of Ouillon and Sornette and is not ACLUD. The relocated catalogue has no event-specific
   covariance; width sensitivity is not measured location error.
5. **Preregister 3–5 hypotheses before implementation.** Rank them by expected DTI improvement and
   cost. For every row, identify exact layers, physical transform/signature, why it can expose an
   omitted rather than catalogued fault, how it differs from repository methods, and any free
   official external source/license. Do not call a repeated method novel.
6. **Protect three weekly feedback slots.** Evaluate the top candidate on the frozen spatially
   blocked holdout before a slot. Require matched density, random, translation, incumbent,
   macrofold, bootstrap, format, scientific-validity, rights, and uniqueness gates. Do not submit
   or recommend a slot unless it beats the frozen current best under the preregistered rules.
7. **Honor the TIFF contract.** One float32 band; EPSG:32611; official shape, transform, resolution,
   and bounds; probability values in closed interval `[0,1]`. Re-read the written file and
   explicitly prevent recurrence of portal error `Predicted values must be in range [0, 1]`.
   Preserve a NaN-outside sample-semantic file and an all-finite zero-outside twin when portal
   behavior and the published local checker differ.
8. **Put the decision before the download.** The GitHub Pages landing page must be clean, simple,
   auditable, and begin with an obvious one-click TIFF link plus an executive summary and visible
   slot decision. Include a numbered submission guide, unique name, short note, source/license
   table, limitations/irregularities, evidence links, and required access. Do not imply portal
   acceptance or a leaderboard score.
9. **Make the result reproducible.** Commit source, tests, frozen parameters, source receipts,
   checksums, direct-comparison evidence, and review notes. Keep large scratch corpora out of Git;
   retain compact hash-pinned derivatives needed to reproduce final placement.
10. **Run three passes.** Pass 1 implements and verifies. Pass 2 reviews bugs, assumptions, data
    leakage, edge cases, format, and scientific claims and fixes defects. Pass 3 rechecks every
    requirement and makes final quality improvements. Record negative results rather than tuning
    them away.
11. **Work autonomously and line by line.** Use official/trusted sources, link them for manual
    review, flag irregularities, state limitations and required access, and never ask the owner to
    perform research that can be completed in the repository.
12. **Keep score context honest.** The live public leaderboard was checked on 2026-10-07: it
    displayed xiaofanhu at 0.3774 (rank 1) and extradr19 at 0.2778 (rank 13). Preserve that dated
    observation with a link, but do not infer a TIFF/hash or organizer receipt from a leaderboard
    row. The H33-B2-to-0.2778 attribution and the older 0.3195 snapshot remain unresolved reports;
    no local proxy or transfer model is an organizer score.
13. **Follow competition rules.** External data must permit challenge use and sharing with the
    sponsor. AI use must be disclosed as required by the current NLR/DOE rules. Finalists must
    provide reproducible code/assets and documentation. Verify current official rules and deadline
    immediately before any real submission.
14. **Use Arena's fixed branch.** Each Arena session must stay on its assigned branch. This
    session works, commits, and pushes only on the Arena-assigned branch `arena/d0c4e2dc-gemsdoe50`;
    open any pull request from that branch. This name is session-scoped, not a repository default
    for future sessions. Merge to `main` only when repository/environment policy permits it. Never
    switch or push another branch from this session.

## H56 — historical best-measured local design; NO SLOT (and an H51 provenance correction)

Read [`docs/research/h56-diagnosis.md`](docs/research/h56-diagnosis.md) (conditional analysis of the
0.2778 leaderboard observation and what 0.3774 would require; no TIFF/hash crosswalk is established) and
[`docs/hypotheses-20261007-h56.md`](docs/hypotheses-20261007-h56.md) (five untried hypotheses,
screened and ranked; four negative results recorded rather than buried). This session's candidate
was numbered **H56** because `main` already carried unrelated H52, H53, H54 and H55 research artifacts.

**Historical audit download (not a submission):**
`docs/downloads/gemsdoe50-h56-scarpdisperse-90000-allfinite.tif` — 90,000 predicted pixels, values
`0` / `1`, `float32`, EPSG:32611, 3730x3292, identical bounds and transform to the official
template, **every one of the 12,279,160 cells finite and inside `[0, 1]`**. A `-nan.tif` sibling
keeps `NaN` outside the study footprint to match the official sample, and a `.zip` carries the
all-finite GeoTIFF. The all-finite variant is the primary download precisely because the portal
once rejected an upload with `Predicted values must be in range [0, 1]`: a non-finite cell makes a
plain `min()/max()` validator see `NaN`, and `NaN <= 1` is false. **NO-GO:** the historical H56 TIFF has a measured 1.0 px minimum nearest-neighbour distance, not the claimed 3.0 px, and its ComCat-derived corroboration has unresolved sponsor-sharing rights. The raster is retained only for research/audit; its historical entry name/note are not authorized. See the byte-level [spacing audit](evidence/emitter-spacing-audit-20261007.json).

**Measured on the exact historical bytes (not a submission recommendation).** Off-catalogue DTI **0.1874** against a matched-mass uniform control 0.1401 (**1.34x**;
1.59x at 30,000 dots), versus 0.1468 for the best prior artifact on that frame. Frozen blocked
holdout: **4/4** macrofolds positive, paired block-bootstrap 95% CI **[0.0261, 0.0854]**, beats
translation controls 4/4. Format gate `all_checks_pass: true`. Uniqueness gate: worst full-pixel
IoU **0.0154** against every prior artifact on disk, minimum novel fraction at 2 px 0.4805, no SHA
match. Legacy modelled hidden DTI **0.386** — a **transfer-model output, not a score or forecast**;
it used the simplified metric reduction later clarified below and has not been recalculated under
the exact directional-credit expression. `docs/research/h56-diagnosis.md` records its assumptions. Its nominal 0.386 value is not comparable
to the observed public leader and does not show that any real organizer score exceeded it. **NO-GO: no weekly slot was
used; do not upload H56.** The historical raster also fails its claimed Euclidean-spacing gate,
and mixed-network ComCat contributor rights and sponsor-sharing eligibility remain unresolved.

**Three findings that are binding on anything built afterwards.**

1. **H56/H58 did not enforce their claimed spacing; the exact metric also needs both directional
   credit terms.** For binary unit dots, let `T = TP_w`, `M = sum_x max_g k(d(x,g))` over
   predicted cells, `N` be the prediction count, and `G` the truth count. The exact expression is
   `DTI = T / (0.2N + 0.8G + 0.2(T-M) + ε)`; the often-quoted `T/(0.2N + 0.8G)` is valid only
   when `T=M`. A 3-pixel nearest-neighbour rule does not prove that equality or make full 300 m
   kernel footprints disjoint. Top-*N* selection can still pile dots on a feature where truth-side
   credit saturates. Earlier H56/H58 protocols used a 3-pixel (300 m) Euclidean minimum-separation
   design rule, not a proven metric optimum. The 2026-10-07 byte audit found the old
   `h56.emit_blue_noise` implementation only picked one cell per 3×3 block and did not reject
   cross-block neighbours. The actual H56 90,000-dot and H58 98,598-dot rasters each have a
   measured 1-pixel nearest-neighbour minimum; H57's separate emitter measures 3 px. The shared
   H56 emitter is now fixed and tests check Euclidean nearest-neighbour distance. Historical
   H56/H58 TIFFs were not rewritten. See
   [`evidence/emitter-spacing-audit-20261007.json`](evidence/emitter-spacing-audit-20261007.json).
2. **Only the LiDAR surface-morphology family carries information about faults the given catalogue
   does not contain.** Channel screen, enrichment over the scored domain: LiDAR up-face residual
   **1.42**, relief 1.40, the scarp family 1.21-1.42; **every** magnetic and radiometric residual
   1.02-1.09 (TMI gradient 1.02).
3. **A statistic the H51 series was ranked on does not exist.** The `rho = +0.566` / `+0.534`
   magnetic alignment attributed to `evidence/h51_residual_alignment.json` is not in that file,
   which measures `f_gmtmi95` at `+0.125` raw (p = 0.552), partial `-0.385`. The real provenance is
   `evidence/h51_truth_map.json` key `/grids/32/phi[919] = 0.5662404620083589` (one spatial block's
   phi for one artifact grid) and unrelated `fold_aucs` / `null_aucs` in the sibling `GEMSDOE24`
   audit. H51-A's rank-1 position is withdrawn in place in
   [`docs/research/h51-hypotheses.md`](docs/research/h51-hypotheses.md) with all four claims struck
   through, and the magnetic family is independently rejected by the channel screen. This is the
   most consequential irregularity found in the project so far and it is recorded, not quietly
   fixed.

**Research rerun only (not byte-identical; not a submission):** the historical TIFF was not
regenerated. The shared emitter has changed, so the commands below would create a different H56
raster; source rights and all submission gates would still need a fresh review. Do not use a rerun
as an upload candidate.

```bash
# needs the three staged GeoDAWN rasters; see .arena/work/g24/data/external or the sibling repo
python scripts/build_h56.py --layers .arena/work/g24/data/external --out docs/downloads
python scripts/validate_h56.py --truth-mode sgmc_off --out evidence/h56_holdout_offcat.json
python scripts/h56_uniqueness.py --novel-threshold 0.45
python scripts/h56_holdout.py --n-boot 200        # frozen macrofold split
```

## H58 — historical ComCat point-geometry experiment; NO SLOT

**H58-S1** is a unique research-only TIFF generated during that session, not an organizer upload:
**declustered USGS ComCat epicentre point geometry as the primary prediction field** — a new
artifact, not a variant of any prior file. The frozen gates returned NO SLOT; do not repackage or
resubmit it as a new method. H55 used the *relocated* catalogue (and failed its gate); H56
used ComCat lineations only as a 0.25-weight corroboration on the LiDAR scarp belief; no shipped
artifact made ComCat point geometry the primary field. (Renumbered from H57 to H58 because the
parallel H57 session's scarpstep artifact merged to `main` first via PRs #22/#23 and owns the H57
number; the repo convention is one unique number per hypothesis.) Preregistration (five ranked
hypotheses, frozen before any scoring):
[`docs/research/h58-hypotheses-preregistered.md`](docs/research/h58-hypotheses-preregistered.md).

**Historical audit download (not a submission):**
`docs/downloads/gemsdoe50-h58-seislineage-98598-20261007T180223Z-c4ff6db9-allfinite.tif` — 98,598
predicted cells, values `{0, 1}`, `float32`, EPSG:32611, 3730x3292, identical bounds and transform
to the official template, **every one of the 12,279,160 cells finite and inside `[0, 1]`** (the
portal-safe variant that cannot reproduce `Predicted values must be in range [0, 1]`). A `-nan.tif`
twin keeps the official sample's footprint semantics and passes `all_checks_pass`, and a `.zip`
carries the all-finite GeoTIFF.

**Measured (frozen gates, all recorded in `evidence/h58_build.json`).** 222,939 ComCat rows →
93,934 in-grid → 68,645 after the tectonic/magnitude/depth/location screens, the 3 km
anthropogenic-site buffer (522 explicit blast/mine centres), and the 2-D triangle-area
declustering (unverified adaptation of Ouillon & Sornette 2011) → 1,374 linear, well-sampled 2-D
covariance lineations → corridors whose half-width is the catalogue's own `horizontalError`
(median 0.88 km — a corridor prior, not a trace) → historical block-quantised emission (support
caps at 98,598 cells; a later byte audit measured 1 px minimum nearest-neighbour spacing, so this
was not a true 300 m Poisson-disk realization) → placement step measured (identity kept; no ridge
snap improved the proxy). Pooled off-catalogue proxy DTI **0.0997** vs smoothed-density control
**0.1078**, matched random **0.1329**, H56 incumbent **0.1874**; the paired 16-subtile bootstrap
for candidate-minus-incumbent credit per dot is **[-0.1107, -0.0250]** — the candidate loses in
**all four** macrofolds, and its 1-pixel enrichment against proxy truth is 1.03x (chance level).
Uniqueness gate: worst full-pixel IoU **0.0166** against every prior artifact on disk, minimum
novel fraction at 2 px **0.7537**, zero exact overlap with the frozen 1,405,451-cell prior union,
no identical SHA-256 — **unique: true**. Format gate: NaN twin `all_checks_pass: true`; all-finite
twin entirely finite in [0, 1].

> **Decision: NO SLOT.** H58 is a recorded negative research result, not a submission
> recommendation or current lead. It loses to the density, random, and H56 controls; H55 also failed
> as a primary seismicity detector, while H56's ComCat-lineation component measured neutral. H56
> remains the best-measured local design, but its historical TIFF fails spacing and its rights gate
> is unresolved. Do not upload, relabel, or repackage H58-S1.

**Emitter defects found in review (disclosed; historical TIFFs not rewritten).** The first H58
review found that an *absolute* `1e-6` tie-breaker could override tiny belief values and choose a
cell outside the emission domain; 5,631 of 98,598 dots were outside the prior-union/catalogue mask
before that fix. The tie perturbation was corrected, and the historical H56/H55 files remained
byte-unchanged (the first correction concerned only future builds).

A second line-by-line audit found a separate defect: the old `emit_blue_noise` implementation
selected one pixel per rounded-size block but had no cross-block Euclidean rejection pass. The old
test checked only block uniqueness, not the claimed minimum distance. Exact nearest-neighbour audit
of written TIFFs measured **1.0 px** minimum for H56 (90,000 dots) and H58 (98,598 dots), while
H57's separate emitter measured 3.0 px. `emit_blue_noise` is now a weighted exponential-race
sampler with an exact Euclidean spatial-hash exclusion; the regression tests assert the actual
nearest-neighbour distance and trailing-edge eligibility. The fix affects future builds only. H56
and H58 retain their original bytes and **must not be described as 3-pixel-separated**; both remain
historical research artifacts, and H58's decision remains NO SLOT. See
[`evidence/emitter-spacing-audit-20261007.json`](evidence/emitter-spacing-audit-20261007.json).

**Build-code note:** H58&rsquo;s stored TIFFs were not regenerated after fixing the shared emitter. The
current builder calls the corrected code and therefore will not recreate the historical TIFF bytes;
rerunning it would be a changed research experiment, not an authorized H58 resubmission. Do not run
it to repackage or relabel H58-S1.

```bash
python3 -m venv .venv && .venv/bin/pip install numpy scipy rasterio pyproj pandas pytest ruff
.venv/bin/pip install -e . --no-deps
bash scripts/restore_inputs.sh .arena/inputs        # hash-pinned LiDAR/radiometric rasters
PYTHONPATH=src .venv/bin/python scripts/build_h58.py
PYTHONPATH=src .venv/bin/python scripts/h58_uniqueness.py
PYTHONPATH=src .venv/bin/python scripts/check_submission.py \
  --submission docs/downloads/gemsdoe50-h58-seislineage-98598-20261007T180223Z-c4ff6db9-nan.tif \
  --out docs/downloads/checks-gemsdoe50-h58-seislineage-98598-20261007T180223Z-c4ff6db9-nan.tif.json
python scripts/build_h55_site.py && python scripts/build_h58_site.py
PYTHONPATH=src .venv/bin/python -m pytest -q
```

## Current outcome — 2026-10-07 UTC

### This session's own artifact — H52-C (eight-family coincidence)

A prior H52-C session (recorded on branch `arena/685c6059-gemsdoe50`) built a separate research
artifact; this is historical context, not the active branch or a submission recommendation. It was
kept separate from the H52/H52A/H53/H54/H55 artifacts that other sessions track (nothing here reads
their prediction pixels):

* **Portal file (NaN outside the footprint):**
  [`gems50-h52-coincidence8-80000-20261007T032938Z-nanoutside.tif`](docs/downloads/gems50-h52-coincidence8-80000-20261007T032938Z-nanoutside.tif), SHA-256
  `c8292db9e2c6d16b99a32ceae3d1652eb15019c8faa6f9d8b6d8b052d15dd582`, 417,986 bytes, 80,000 positive cells.
* **All-finite twin:** [`gems50-h52-coincidence8-80000-20261007T032938Z.tif`](docs/downloads/gems50-h52-coincidence8-80000-20261007T032938Z.tif), SHA-256 `a2ed87fac9fdb4b9604ab2850b5f750eefe51fa9795caa6a503fc4739de6475d`.
* **Single-file zip:** [`gems50-h52-coincidence8-80000-20261007T032938Z-nanoutside.zip`](docs/downloads/gems50-h52-coincidence8-80000-20261007T032938Z-nanoutside.zip), SHA-256 `6dc41bd5598495748eee22f85fca2f82cb3c938afe6eaecf8c839e47768d498c`.
* Format: one float32 band, EPSG:32611, 3,730 x 3,292, 100 m, values in `{0, 1}`, zero values outside
  the study footprint, zero dots on the provided catalogue, no nodata sentinel — re-read from the written
  bytes by `scripts/uniqueness_h52_coincidence.py` (`evidence/h52_uniqueness.json`, all checks pass).
* Method: eight evidence families (detrended elevation and slope, 10 m topographic descriptors, USGS
  3DEP-1 m lidar scarp descriptors, two independent radiometric mosaics, potential field, geodetic
  strain, and the competition's own seismicity bands), each ranked within itself by multi-scale
  structure-tensor saliency, combined as `families >= 0.90 + 0.5 x mean normalised excess`, emitted
  greedily at >= 3 px separation with a 200 m catalogue buffer. Builder:
  `scripts/build_h52_coincidence.py`; inputs restored and hash-verified by `scripts/restore_inputs.sh`;
  two independent builds produced byte-identical output.
* Evidence: instrument calibration reproduces the published ordering of ten known artifacts
  (Spearman 0.805, p = 0.005) and 4/4 spatially blocked folds beat a matched-mass random control
  (`evidence/h52_validation_80k.json`); 57.2% of the dots are >= 300 m from every dot of the 16 prior
  artifacts compared and 87.8% lie outside the union of all prior supports
  (`registry/prior_artifact_sources.tsv`).
* Budget: a legacy nested-pair model gives G ≈14,088.75 px and T ≈5,223.14 px only under the
  simplified DTI equation and unverified score-to-file associations; 3 px spacing does not make that
  inversion exact. Its marginal-value rule and ten-budget curve are conditional models, not verified
  score arithmetic; the modelled 120k optimum comes from a saturation cap. See
  (`docs/h52-decision.md`, `evidence/h52_budget_curve.json`).
* Delivery: the H52-C band at the top of `index.html` (immediately below the other sessions' bands)
  carried download links and a historical portal name/note. The current site removes portal
  instructions for this below-incumbent research artifact; no H52-C portal name or note is authorized.

> **Not organizer-scored, no slot used.** The per-dot proxy quality of H52-C (0.1446) is below every
> incumbent-family artifact measured (0.1573-0.1704) and the receipt records that an SGMC-family
> submission scored 0.0512 on the hidden labels, so nothing here licenses a score claim.

### Historical H55 research artifact — NO SLOT

**All-finite portal-range-safe TIFF:**
[`gemsdoe50-h55-seisgeom-ridgesnap-13591-20261007-bcb60d89-zeros.tif`](docs/downloads/gemsdoe50-h55-seisgeom-ridgesnap-13591-20261007-bcb60d89-zeros.tif)

* SHA-256: `7a366b7bbe431533a9d4246cbcdde34eb379ebb34fa116a8667431916506498d`
* 103,444 bytes; one float32 band; EPSG:32611; 3,730 x 3,292; 100 m
* values exactly `{0,1}`; every one of 12,279,160 cells is finite and in `[0,1]`
* 13,591 positive cells; zero exact positive-pixel overlap with the complete frozen prior union

**Sample-footprint-semantic twin:**
[`gemsdoe50-h55-seisgeom-ridgesnap-13591-20261007-bcb60d89-nan.tif`](docs/downloads/gemsdoe50-h55-seisgeom-ridgesnap-13591-20261007-bcb60d89-nan.tif),
SHA-256 `cd7f765a95ea9c71b22abffbf330434597c28057f8a80ed723b753cd0a32d3c6`.
It uses NaN only outside the official footprint and passes the repository's published-format checker.

> **Decision: NO SLOT. Do not spend a weekly submission on H55-S1.** The TIFF is a historical
> research artifact and negative experiment, not a current candidate or a submission
> recommendation. No portal name/note, portal upload, or weekly slot is authorized.

### Why the candidate did not pass

The exact catalog has 183,002 source events. Filters retain 15,017 relocated, in-footprint,
non-negative-depth events after site screens; 90-day/250 m sequence thinning leaves 7,325; the
unverified normalized triangle test leaves 3,145; and covariance/recurrence/bootstrap gates accept
299 local axes. Frozen 3-pixel spacing cannot supply the target 35,000 cells from those corridors,
so the central 600 m realization emits 13,591.

On the same SGMC-off proxy frame:

| method | pooled DTI | credit / dot | dots |
| --- | ---: | ---: | ---: |
| H55-S1 300 m | 0.011069 | 0.068256 | 8,278 |
| **H55-S1 600 m** | **0.019321** | **0.074141** | **13,591** |
| H55-S1 1,000 m | 0.030960 | 0.078040 | 21,332 |
| density 1 km | 0.046524 | 0.075258 | 35,000 |
| density 2 km | 0.045898 | 0.074250 | 35,000 |
| matched random, novelty-constrained | 0.028893 | 0.046676 | 35,000 |
| **frozen Candidate B** | **0.115822** | **0.188856** | **35,000** |

H55 loses to Candidate B in all four macrofolds. The paired 16-subtile credit-per-dot bootstrap
95% interval is `[-0.118959, -0.037294]`. It fails mass, width consistency, density, random,
incumbent, bootstrap, formal-declustering-validation, complete anthropogenic-inventory,
event-uncertainty, and ComCat-rights gates.
The negative sign is not ambiguous.

## Why H33-B2 reportedly reached 0.2778

The exact H33-B2 files are measurable: 37,654 binary cells, with verified zero-outside SHA-256
`c55bafc...6fa9`. GEMSDOE32's own audit describes them as a 40,199-cell, owner-reported 0.2708 base
with all 2,545 cells within two pixels of the supplied catalogue removed. That repository labels the
candidate **UNSCORED** and projects **0.274673**. No organizer receipt links these bytes to 0.2778.

Conditionally accepting the report, the mechanism is metric economy. The official triangular
300 m distance-weighted Tversky score rewards only the maximum nearby prediction for each hidden
truth cell. A redundant/no-credit binary dot adds false-positive mass; deleting it reduces the
weighted denominator without lowering true-positive credit. B2 deleted locations close to known
catalogue faults—the wrong target for omitted-fault scoring—while retaining its parent's sparse
support. It was a pruning operation, not a new geological detector.

Under the repository's explicit hidden-mass model (`G about 12,226`, matched-mass ratio 1.188), a
37,654-dot result at 0.2778 corresponds to about 4,759 weighted credit pixels, 38.9% modeled
coverage, and 0.1264 credit per dot. A 0.3195 result would need about 5,465 credits at the same mass
(+14.8%), or about 4,982 credits / 0.166 per dot at 30,000 cells. **Exceeding 0.3195 is possible in
principle but is not supported by a passing method here.** It requires genuinely new coverage and
higher precision, not another blend or pruning sweep. Full derivation and evidentiary labels:
[`docs/research/h55-final-analysis.md`](docs/research/h55-final-analysis.md). For the user-provided
0.3774 claim and the later H53-A probe/TMI no-go review, see
[`docs/research/h33-score-review-20261007.md`](docs/research/h33-score-review-20261007.md). The
0.3195 calculations above are retained as an older conditional scenario, not as the current-high
claim.

## H53-A probe/TMI test — archived NO-GO (this Arena branch)

H53-A is a **separate experiment** from the TMI-conjunction H53 artifact already in the repository.
Its four hypotheses were ranked before implementation; the preregistered probe point-pattern/TMI
lineation detector accepted **0/145 clusters**, emitted **0 cells**, and scored DTI **0.000000** on
the frozen local proxy versus **0.136074** for the comparator (paired spatial-subtile bootstrap 95%
interval `[-0.169861, -0.079791]`). Decision: **NO-GO / NO SLOT**. No weekly feedback slot was used.

The generated file
[`gemsdoe50-h53-probe-tmi-pointlineation-20261007-44afc05b.tif`](docs/downloads/gemsdoe50-h53-probe-tmi-pointlineation-20261007-44afc05b.tif)
is a format-valid, all-zero research artifact retained for audit only. **Do not upload it.** Its
SHA-256 is `5f2fd91ad46a3602c03802e0f7773fd466b08e47cbfcf40ff796ffc2b956a382`; it is not the H56
one-click candidate and not a positive geological prediction. See the four-hypothesis ranking,
frozen preregistration, validation evidence, and three-pass review in
[`docs/research/h53-hypotheses-20261007.md`](docs/research/h53-hypotheses-20261007.md),
[`docs/research/h53-preregistration-20261007.md`](docs/research/h53-preregistration-20261007.md),
[`evidence/h53-validation-20261007.json`](evidence/h53-validation-20261007.json), and
[`docs/pass3-review-20261007.md`](docs/pass3-review-20261007.md).

## H55 method and preregistration

The five hypotheses were ranked before H55 scoring in
[`docs/research/h55-hypotheses-preregistered.md`](docs/research/h55-hypotheses-preregistered.md).
Exact constants were frozen in
[`docs/research/h55-protocol-addendum.md`](docs/research/h55-protocol-addendum.md).

H55-S1 uses only relocated earthquake points for its candidate geometry. It:

1. checks the exact CC BY 4.0 Trugman catalog bytes and schema;
2. filters depth/footprint, GDR hot-feature buffers, and explicit ComCat anthropogenic event sites;
3. retains the largest event in each 250 m x 250 m x 90-day space-time cell;
4. compares normalized nearest-neighbor triangle areas with 32 uniform-footprint catalogues;
5. fits full local 2-D covariance eigenvectors and requires event/year/linearity/length/bootstrap
   stability;
6. dynamically snaps only cross-axis to a 70/30 3DEP scarp/radiometric ridge field;
7. applies 300/600/1,000 m width sensitivity and a 300 m supplied-fault exclusion;
8. packs binary dots and compares with density, random, translations, and Candidate B;
9. excludes the positive-pixel union of every registered prior artifact from final placement.

The implementation/review deviations are preserved in
[`docs/research/h55-deviation-log.md`](docs/research/h55-deviation-log.md). In particular, Pass 2
fixed an evaluator bug so the official-label realization—not SGMC truth—reconstructs the frozen
fold geometry before SGMC-off scoring.

## Direct novelty and format evidence

The 50-row sibling registry was retrieved from GitHub and every expected SHA-256 was verified;
15 in-repository H50/H51/H52/H52A/H53/H54 TIFF source paths were then added. In total, 65 source
assertions represent 64 distinct source paths, 62 comparison filenames, 61 byte-distinct TIFFs,
and 34 distinct positive masks. The receipt explicitly groups byte-identical copies and
finite/NaN twins with equivalent positive support. The compact frozen union is
`registry/prior_positive_union.npz` (SHA-256
`bfaf83edf47bf7c48309f692a670f3b6d92f492081a120d85dedc30b462578a6`). H55 has zero exact
intersection with its 1,405,451 positive cells.

A second direct full-resolution check against all 62 comparison files reports:

* no identical SHA-256;
* maximum 200 m-proximity IoU `0.040107` (gate `<0.5`);
* minimum per-file fraction of H55 dots more than 200 m away `0.475682`;
* verdict `unique: true`;
* NaN twin format checks all pass; finite values are exactly 0 and 1.

Evidence:
[`h55s1-full-corpus-check-20261007.json`](evidence/results/h55s1-full-corpus-check-20261007.json) and
[`h55-prior-corpus-receipt-20261007.json`](evidence/results/h55-prior-corpus-receipt-20261007.json).

## Integrated H54 research from latest main

While this pull request was awaiting integration, main added a separate H54 corpus-calibrated field
and metric-derived stratified emitter. Its file of record is
[`gems50-h54-corpuscal-40000-20261007T032111Z-nan.tif`](docs/downloads/gems50-h54-corpuscal-40000-20261007T032111Z-nan.tif)
(SHA-256 `2cdf7e705c867008b0dc86d3e7481bf43aef44240508312d270c97ebd192c81b`),
with an [all-finite twin](docs/downloads/gems50-h54-corpuscal-40000-20261007T032111Z-zeros.tif).
H54 emits 40,000 binary cells and passes its NaN-outside format receipt, but it did not beat its
matched-mass random control in every frozen block. Its decision is therefore also **NO SLOT**; its
model-implied DTI is not an organizer score.

H54 exposed a real footprint-edge filtering artifact and measured a 3.7x credit-per-dot gain from
stratified rather than dense top-N emission on the same proxy field. Its attempted calibration uses
owner-reported sibling scores, has unresolved provenance contradictions, and did not produce a
usable fit. See [`evidence/h54_validation.json`](evidence/h54_validation.json),
[`evidence/h54_fit_status.json`](evidence/h54_fit_status.json), and
[`evidence/h54_ship.json`](evidence/h54_ship.json). Both H54 TIFF twins are included in H55's strict
prior corpus before the final H55 rerun.

## Source and license ledger

| source | exact use | rights / eligibility | official or review link |
| --- | --- | --- | --- |
| DrivenData DOE GEMS problem/rules | metric, grid, format, external-data and slot rules | competition terms; verify immediately before upload | [problem](https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/) · [competition](https://www.drivendata.org/competitions/306/competition-doe-gems/) |
| Trugman, *Relocated Earthquake Catalog for Nevada (2008–2023)* | **candidate point geometry** | CC BY 4.0; commercial reuse/adaptation and sponsor sharing allowed with attribution; receipt pins exact file | [Zenodo 11167510](https://zenodo.org/records/11167510) · [receipt](registry/nvreloc_catalog_receipt.json) |
| USGS 3DEP-derived scarp descriptors | independent placement ridge | U.S. public domain; inherited owner-derived raster, hash recorded in H55 report | [3DEP](https://www.usgs.gov/3d-elevation-program) |
| USGS airborne K/Th/U/TC raster | independent placement ridge | U.S. public domain; inherited owner-derived raster, hash recorded in H55 report | [USGS copyright/credits](https://www.usgs.gov/information-policies-and-instructions/copyrights-and-credits) |
| GDR submission 1391 hot features | conservative geothermal-operation exclusion | CC BY 4.0; incomplete inventory | [GDR 1391](https://gdr.openei.org/submissions/1391) |
| USGS FDSN/ComCat mixed-network export | only explicit blast/mine/quarry **exclusion** locations | contributor-specific redistribution unresolved; therefore a scientific/compliance blocker, not claimed cleared | [FDSN event service](https://earthquake.usgs.gov/fdsnws/event/1/) |
| USGS State Geologic Map Compilation | off-catalogue validation instrument only | U.S. public domain; not a prediction input | [SGMC product](https://ngmdb.usgs.gov/Prodesc/proddesc_99016.htm) |
| competition template and supplied labels | grid, supplied-fault exclusion, frozen folds | competition terms; bytes match the repository's pinned public bridge, not a fresh authenticated portal download | [problem data description](https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/) |

Catalog attribution: **Trugman, D. T. (2024), Relocated Earthquake Catalog for Nevada
(2008–2023), Zenodo v2, DOI 10.5281/zenodo.11167510, CC BY 4.0.** The repository records all
changes (projection, filtering, thinning, screening, and derived geometry).

## Limitations and irregularities

* The H33 0.2778 attribution is not organizer-confirmed; GEMSDOE32 itself says `UNSCORED` and
  projects 0.274673.
* The 250 m/90-day largest-event rule is deterministic sequence thinning, not a validated
  ETAS/Reasenberg/Gardner-Knopoff aftershock-declustering model.
* H55's mine/injection screen is conservative but incomplete. Explicit ComCat event types and GDR
  hot features are not a dated statewide operations inventory.
* The mixed-network ComCat export is publicly accessible but its contributor-specific competition
  redistribution rights are unresolved. This alone prevents an unqualified eligibility claim.
* The relocated catalog has no event-specific horizontal covariance. Decimal precision is not
  location accuracy, bootstrap strike stability is not position uncertainty, and the three widths
  are assumptions.
* The normalized 2-D triangle test is unverified. It is not a published transfer of the 3-D
  Ouillon/Sornette statistic.
* Earthquake lineations can be dipping faults, swarms, induced sequences, depth trends, or
  catalogue/network artifacts; they are not automatically surface traces.
* SGMC-off is a real but incomplete mapped-fault proxy. It is not hidden expert truth, and local DTI
  cannot be compared numerically with a leaderboard score.
* The 35,000-cell target was infeasible under frozen 3-pixel spacing; the honest artifact has 13,591
  cells and records the failure in its name and report.
* The all-finite twin addresses the historical range-parser error, while the NaN twin follows the
  sample footprint semantics. No portal receipt establishes which behavior the current portal
  prefers.
* No upload occurred. Offline proxy values and transfer-model outputs are not leaderboard scores. A one-time public leaderboard check on 2026-10-07 is documented separately; it does not map score rows to local TIFF bytes.

## Submission guide — current decision NO-GO / NO SLOT

Do not upload H55, H56, H57, H58, or any other historical TIFF linked in this README. H55 and
H58 failed their frozen gates; H56 and H58 also have a measured 1.0 px minimum spacing in the
historical rasters, and H56/H57 source-rights gates remain unresolved. No historical portal name or
note is authorized. `submission.html` is the public guide and is explicitly archive-only / NO-GO.

A future submission requires a separately preregistered, genuinely untried lead; exactly 37,612-dot
incumbent and matched-control baselines before testing it; a frozen holdout improvement; verified
source rights and sponsor-sharing permission; scientific, format, and uniqueness passes; an explicit
one-choice GO; then a portal name/note and an exact-byte receipt. Until then, no upload instructions
or entry name are provided.

The [`submission.html`](submission.html) page keeps historical files available for audit but labels
them as research-only and withdraws their old upload instructions.

Full review, evidence hashes, alternative explanations, official rules, and unresolved source/receipt
issues: [`docs/research/h33-score-review-20261007.md`](docs/research/h33-score-review-20261007.md).
The public leaderboard was checked once on 2026-10-07; xiaofanhu appeared at 0.3774 (rank 1) and
extradr19 at 0.2778 (rank 13). The H33-B2-to-0.2778 TIFF attribution remains unresolved.

## Reproduction

Use the repository virtual environment in this sandbox (system Python is PEP-668 managed):

```bash
# Tests
PYTHONPATH=src .venv/bin/python -m pytest -q

# Rebuild the hash-deduplicated prior union (requires the receipt-pinned scratch corpus)
PYTHONPATH=src .venv/bin/python scripts/build_prior_union.py

# Exact H55 build and local evaluation
PYTHONPATH=src .venv/bin/python scripts/build_h55.py

# Full-resolution uniqueness (requires the scratch corpus whose acquisition receipt is committed)
GEMS50_CORPUS=.arena/prior_corpus PYTHONPATH=src .venv/bin/python \
  scripts/check_submission.py \
  --submission docs/downloads/gemsdoe50-h55-seisgeom-ridgesnap-13591-20261007-bcb60d89-nan.tif \
  --out evidence/results/h55s1-full-corpus-check-20261007.json

# Regenerate the four GitHub Pages files from the machine-readable H55 report
PYTHONPATH=src .venv/bin/python scripts/build_h55_site.py
```

Primary evidence:

* [`evidence/results/h55s1-evaluation-20261007.json`](evidence/results/h55s1-evaluation-20261007.json)
* [`evidence/results/h55s1-full-corpus-check-20261007.json`](evidence/results/h55s1-full-corpus-check-20261007.json)
* [`evidence/results/h55-prior-corpus-receipt-20261007.json`](evidence/results/h55-prior-corpus-receipt-20261007.json)
* [`registry/nvreloc_catalog_receipt.json`](registry/nvreloc_catalog_receipt.json)
* [`docs/research/h55-final-analysis.md`](docs/research/h55-final-analysis.md)
* [`docs/research/h55-deviation-log.md`](docs/research/h55-deviation-log.md)

## Three-pass review record

* **Pass 1 — implementation/verification:** acquired and checksum-verified the exact CC BY catalog;
  froze hypotheses and constants before score computation; implemented screening, time-space
  thinning, 32-catalog background test, local eigensystems, recurrence/bootstrap gates, dynamic
  independent-ridge snap, width sensitivity, controls, TIFF writer, and unit tests.
* **Pass 2 — bugs/assumptions/edges:** found and fixed misuse of SGMC truth when reconstructing the
  frozen split; corrected filenames/notes to use actual emitted mass; reviewed datetime thinning;
  added a complete prior-positive exclusion union; reran every candidate/control/holdout score;
  direct-checked all prior files; separated all-finite and NaN semantics; documented incomplete
  anthropogenic and uncertainty gates.
* **Pass 3 — full requirements/quality:** rechecked charter line by line; consolidated H33 score
  attribution and 0.3195 algebra; added the source/license table, executive guide, obvious site
  download, exact hashes, full-corpus receipt, negative decision, and reproducible commands;
  integrated latest-main H52/H52A/H53/H54 priors, distinguished byte copies from
  prediction-equivalent twins, rebuilt the strict exclusion and all H55 outputs; reran tests, deterministic build/hash
  checks, format/range checks, and site-link validation before PR.

## H57 — historical research artifact; NO-GO / NO SLOT (2026-10-07)

The H57 TIFF is retained for audit, not as the current candidate or a submission recommendation:
[`docs/downloads/gemsdoe50-h57-scarpstep-80000-20261007T1830Z-allfinite.tif`](docs/downloads/gemsdoe50-h57-scarpstep-80000-20261007T1830Z-allfinite.tif)
(SHA-256 `8027c4e9fe0f789e2d7180a7ccc031abec90b391cf9e42ebcc125752af9fb696`, 80,000 cells).
Its separate emitter measures a 3.0 px nearest-neighbour minimum, but the auxiliary topographic
source lineage and sponsor-sharing eligibility have not been cleared. A valid format, low prior
IoU, or correct spacing does not waive the source-rights gate. **Do not upload H57. No portal name
or short note is authorized.** The current submission guide labels the preserved download as
historical and NO-GO.

**What was measured (offline only).** After elevation-stratified screening, the LiDAR-scarp and
topographic-step families survived 5/5 strata, while elevation confounding was reduced. The frozen
spatially blocked local proxy measured pooled DTI **0.2025** against **0.1053** for the matched
uniform control, positive in 4/4 macrofolds, with paired 95% CI [+0.0626, +0.1330]. Those are local
proxy measurements on the frozen evaluation, not organizer scores or hidden-label results.

**Transfer-model correction.** An earlier linear transfer factor that produced a 0.385–0.394 hidden
DTI has been retracted: its corpus fit was worse than predicting the mean (R² = −0.872). A later
corpus-calibrated model estimated ≈0.23 with a broad 0.05–0.41 band, but this remains assumption-
dependent modeling and is not a score or a basis for submission. The fitted F1 coefficient was
negative but not significant; it does not show that F1 selectivity helps or hurts competition
performance. See the [H57 verdict](docs/research/h57-verdict-20261007.md) and its dated addendum.

**Leaderboard context, checked 2026-10-07.** The public page displayed xiaofanhu at **0.3774**
(rank 1) and extradr19 at **0.2778** (rank 13). This verifies the displayed leaderboard values,
not a score-to-TIFF hash crosswalk: in particular, the local H33-B2 TIFF attribution remains
unresolved. No H57 proxy or transfer-model number is numerically interchangeable with those
leaderboard scores. See the [score-provenance review](docs/research/h33-score-review-20261007.md)
and [public leaderboard](https://www.drivendata.org/competitions/306/competition-doe-gems/leaderboard/).

**Current decision: NO-GO / NO SLOT.** No historical H55/H56/H57/H58 file is cleared for upload.
The unapproved H59 standalone-radiometric shortlist has been explicitly withdrawn; no H59 code or
TIFF was built. Before testing a new lead, rerun the incumbent and matched controls at exactly
37,612 dots; then
preregister a genuinely untried charter-compliant hypothesis and apply the frozen holdout, rights,
science, format, and uniqueness gates. Do not repackage or relabel H55 or H58.

## Standing project prompt — read at the start of every session (2026-10-07)

This is the owner's standing instruction for this project, kept verbatim in summary so it is read
every time the project is worked on. It sits above the session-scoped charter items where they
differ.

1. **The goal is to place at the top of the DrivenData #306 DOE GEMS Prize leaderboard**
   (<https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/>). The verified
   public leader on 2026-10-07 is **0.3774 (xiaofanhu)**; the design target is to beat it. The
   metric is the distance-weighted Tversky index (alpha=0.2, beta=0.8, R=300 m); use the full
   published TP/FP/FN equations for binary dots. With `T=TP_w`, predicted-side matched credit
   `M=sum_x max_g k(d(x,g))`, prediction count `N`, and truth count `G`, the exact denominator is
   `0.2N + 0.8G + 0.2(T-M)` (plus epsilon). The shorter `0.2N+0.8G` form requires `T=M` and is
   not justified by nearest-neighbour spacing alone.
2. **MUST GENERATE A UNIQUE TIF SUBMISSION for the competition.** Never copy a previous submission;
   prior files are for learning, controls, and comparison only. The generated submission must be
   **obvious to download** (one click, top of the site / executive summary) and **it must be
   obvious whether it is OK to download and submit** (an unmissable gate decision on the file's
   band). A unique entry name and a short note are required on the submission form.
3. **The mandated method for this session's artifact** is seismicity lineation from the point
   pattern, not the density band: epicentres from a public catalogue (USGS ComCat; record the
   official URL and licence first and confirm the external-data rule allows it), decluster,
   remove known injection and mining sites, compute eigenvalues of the 2-D covariance per
   epicentre neighbourhood, keep linear well-sampled neighbourhoods, output a corridor oriented
   along the principal axis with width set by catalog location error (a corridor prior, not a
   trace), score only corridors outside existing-fault buffers, falsify against smoothed
   earthquake density, normalize to [0, 1], write the required GeoTIFF, run the uniqueness gate
   against all prior submissions, and snap the corridor to another layer's ridge in the placement
   step. The 2-D reduction of Ouillon & Sornette's 3-D tetrahedron test is our adaptation and is
   unverified; say so everywhere.
4. **Answer at PhD level, from verified sources, with links for manual review**: why the
   group's best artifact reportedly scored 0.2778, and whether a submission can exceed the
   leader. Never turn an owner/user report into an authenticated score without an organizer
   receipt. Flag irregularities; no hallucinations; verify line by line.
5. **Protect the weekly feedback slots.** Preregister 3-5 hypotheses before implementing; rank
   them by expected DTI improvement and cost; validate the top candidate on the frozen
   spatially-blocked holdout before touching a slot; do not spend a slot on an idea that has not
   beaten the current holdout best. If a candidate needs new external data, name the specific
   free official source and check it is obtainable first.
6. **Site requirements.** A clean, simple GitHub Pages site: the one-click download and the
   executive summary at the very top; an executive-summary/submission subpage explaining exactly
   how to submit (including the historical `Predicted values must be in range [0, 1]` portal
   error and how the shipped bytes avoid it); official verified source links; limitations and
   irregularities; no implication of portal acceptance or a leaderboard score.
7. **Core values.** Maximize P(Win): weigh tradeoffs and choose the path that maximizes the
   probability of winning. Own the Outcome: own results end to end, act without waiting for
   permission, treat failure and success as signals. Work autonomously; no manual input; work
   line by line; verify everything; run three passes (implement, review/fix, re-check).
8. **Session mechanics.** Work, commit, and push only on this session's assigned branch
   (`arena/d0c4e2dc-gemsdoe50` for this session); open the pull request from it; merge to `main`
   when the checks pass. Keep large scratch data out of Git; keep hash-pinned derivatives needed to reproduce.
