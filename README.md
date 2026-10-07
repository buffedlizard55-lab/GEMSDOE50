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
   `h33-h33-2-b2-20261004T220000Z-e5eb6e7e` reportedly scored 0.2778 and whether a method could
   exceed the user-provided 0.3774 high-score claim (0.3195 is a separate, older owner-quoted
   snapshot). Never turn any owner/user report into an authenticated score without an organizer
   receipt/hash crosswalk.
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
12. **Keep score context honest.** The 0.2778 artifact attribution, 0.3195 historical snapshot,
    and user-provided 0.3774 high-score claim are unverified reports, not freshly checked leaderboard
    observations. This project does not scrape/poll the leaderboard or map a score to bytes without
    an organizer receipt. The 0.3774 claim is not treated as fact or as a proven ceiling.
13. **Follow competition rules.** External data must permit challenge use and sharing with the
    sponsor. AI use must be disclosed as required by the current NLR/DOE rules. Finalists must
    provide reproducible code/assets and documentation. Verify current official rules and deadline
    immediately before any real submission.
14. **Use Arena's fixed branch.** Each Arena session must stay on its assigned branch. This
    session works, commits, and pushes only on `arena/9df7242d-gemsdoe50`; open the pull request from
    that branch. This name is session-scoped, not a repository default for future sessions. Merge
    to `main` only when repository/environment policy permits it. Never switch or push another
    branch from this session.

## H57 — the current candidate: sharpened topographic-scarp scatter (this session)

**Read first:** [`docs/hypotheses-20261007-h57.md`](docs/hypotheses-20261007-h57.md) (five ranked
hypotheses with the fate of each), [`docs/research/h57-preregistration.md`](docs/research/h57-preregistration.md)
(the frozen protocol **and its declared post-hoc amendment**),
[`docs/research/h57-final-analysis.md`](docs/research/h57-final-analysis.md) (every table),
[`docs/research/h57-deviation-log.md`](docs/research/h57-deviation-log.md) (the three-pass record),
[`docs/research/h57-proxy-gap.md`](docs/research/h57-proxy-gap.md) (why the old proxy and the old mass
instrument were wrong), and
[`docs/research/gems-official-clarifications.md`](docs/research/gems-official-clarifications.md)
(official rulings and the source licence ledger).

**One-click download, and it is the first thing on the site:**
[`docs/downloads/gemsdoe50-h57-sharpened-scarp-scatter-90k-20261007T171954Z-allfinite.tif`](docs/downloads/gemsdoe50-h57-sharpened-scarp-scatter-90k-20261007T171954Z-allfinite.tif) — 90,000 predicted cells, values `0` / `1`,
`float32`, EPSG:32611, 3730 × 3292, **every one of the 12,279,160 cells finite and inside `[0, 1]`**,
SHA-256 `838f9502fd4a2720374559db0947fb3372f97629401a617e5c9c95c1b1ce8be5`. A `-nan.tif` sibling keeps NaN outside the study
footprint to match the official sample, and a `.zip` carries the all-finite GeoTIFF. Portal entry name
`GEMSDOE50-H57-SHARPENED-SCARP-SCATTER-90K`; the optional note is the `portal_note` field of
[`evidence/h57_build.json`](evidence/h57_build.json).

### What it is, and what changed after the first build

The field is a **sharpened NaN-aware rank-mean** of two families: the official layer 19
(detrended-elevation slope) *gradient magnitude*, a step-edge detector for a fault scarp, and the USGS
3DEP 1 m LiDAR scarp descriptor stack. Sharpening exponent **^16**, 90,000 dots on a 3 px lattice, one
per chosen block, on the strongest eligible cell of the block; never on a supplied catalogue cell and
never on a registered prior-artifact cell.

Two screens after the first frozen build changed the design, and both are declared post-hoc in the
preregistration because they were run **after** seeing the first build's numbers:

1. **A rank mean was compressing the peaks.** Raising the blend to a power lifted the off-catalogue
   DTI at 90,000 dots from **0.17142 to 0.23406** with everything else frozen — a 37 % gain on the same
   emitter, seed, lattice and pool — and the lift over a matched-mass uniform control from 1.33× to
   **1.84×** ([`evidence/h57_sharpen_sweep.json`](evidence/h57_sharpen_sweep.json),
   [`evidence/h57_sharpen_ext.json`](evidence/h57_sharpen_ext.json)). The response is monotone in the
   exponent to ^8, ^16 is the frozen value, and it turns over by ^32.
2. **The dot count was sized for the unsharpened field.** The first build spent 180,000 dots because
   the *proxy* prefers about 250,000. The proxy is not the target: its truth (52,219 px) is four times
   denser on the ground than the hidden target (≈12,226 px), so it keeps repaying dots the hidden
   scoring would not. Under the repository's calibrated per-dot credit transfer (0.887) the sharpened
   field saturates at **90,000** dots, and the marginal dot beyond it earns ~0.077 against a 0.2
   false-positive charge. The proxy reads 0.23028 at 90,000 and 0.27864 at 180,000 — that disagreement
   is reported, not hidden, and the sensitivity table on the site shows the modelled score at transfer
   factors from 0.30 to 1.00.

### Measured (official metric, frozen frames, controls matched mass and pool)

| frame | truth px | DTI | NW / NE / SW / SE |
| --- | ---: | ---: | --- |
| `S_matched` (geometry-matched off-catalogue proxy) | 52,219 | **0.23028** | 0.2072 / 0.2450 / 0.1394 / 0.2762 |
| `S_raw` (the repository's unmodified proxy) | 61,664 | 0.24917 | 0.2282 / 0.2735 / 0.1394 / 0.2767 |
| `L` (the supplied catalogue — a negative control) | 60,988 | 0.03892 | 0.0364 / 0.0363 / 0.0463 / 0.0433 |

Controls at matched mass 90,000: whole-footprint uniform **0.12383** (lift **1.86×**),
same-pool uniform **0.11134** (lift **2.07×**); paired 32 × 32 px block
bootstrap candidate − uniform **+0.1041**, 95 % interval
**[+0.0948, +0.1141]**, positive in 400/400
replicates. Uniqueness: **0** cells shared with the 61-artifact prior union, worst 800 m block IoU
**0.0419** across 50 signature-pinned priors. The novelty constraint costs **0.00343**
of proxy DTI (1.48 %) by direct measurement — the cheapest novelty
guarantee measured in this repository, and the cheapest of the session: it moved
28,811 dots off prior-artifact cells.

### The honest limit of the 0.3774 target

Measured on the delivered bytes ([`evidence/h57_delivered_metrics.json`](evidence/h57_delivered_metrics.json)),
not on a screen: the file paints 90,000 cells, earns **14,090** of truth-side credit on the
geometry-matched frame (**27.0 %** coverage of 52,219 px) and carries **82,971** of
false-positive mass. With unit-height binary dots the metric is
`DTI = T / (T + 0.2·FP_w + 0.8·(G − T))`, so:

* a prediction with **zero** false-positive mass and this coverage would score
  **0.3160** — the file's own ceiling on this frame, of which it realises **73 %**;
* that ceiling is **below the 0.3774 target**, so on this frame the target cannot be reached by
  precision alone at all: reaching 0.3774 with perfect precision needs **32.7 %** coverage against
  the present 27.0 %, i.e. about **2,966 more proxy-truth pixels covered at no additional
  false-positive mass**;
* the **transfer model** — hidden credit ≈ 0.887 × proxy credit, hidden mass ≈ 12,226 px — puts the
  same file at **0.44**, i.e. saturated. That is the model's most aggressive corner; at a
  transfer of 0.30 the same bytes model 0.15. It is a model, not a score.

The honest reading: the artifact is a good *ranker* (2.07× a same-pool uniform scatter, 4/4 macrofolds,
bootstrap interval [+0.0948, +0.1141]) and its remaining weakness is precision, not recall. Nothing in
this repository has yet produced a 0.3774-class score, and no organizer score exists for this file.

### Corrections this session (details in the deviation log)

1. **A 24.7 % dead zone.** The first build required both families to be finite; the LiDAR stack is
   undefined on 1,274,189 footprint cells, costing 21 % of truth-side credit. Fixed with the NaN-aware
   mean (0.17990 → 0.21812 in that revision's own frame).
2. **A rank mean flattens the top.** Corrected by the exponent sweep (§ above), worth +37 % proxy DTI.
3. **Dense emission is not better.** Blobs and skeletonised 1 px lines both lose to field-weighted
   spreading at matched painted count.
4. **The mass instrument was measuring specks.** Random-pixel subsampling of the proxy truth severs
   line connectivity and inflates the curve by 33 %; whole-component selection replaces it.
5. **The catalogue buffer was too wide.** Staff ruled only pixel-exact catalogue cells are masked and
   that new-fault truth can occur within 300 m of a known trace; the frozen buffer is 1 px, and the
   apparent 3 px win on the proxy is a selection artefact, labelled as one.
6. **The seismicity point-pattern term is at chance.** Implemented, rendered, audited, excluded and
   reported as a negative rather than shipped.

### H57 versus the rest of the repository, both readings

Absolute proxy DTI at its own operating point, H57 revision 2 is the strongest artifact here
(0.23028 against revision 1's 0.21812, H56's 0.18647, H52-C's 0.14875, H51's 0.11614). Lift over
a matched-mass control, H56 (1.51×) and H51 (1.81×) are comparable at their much smaller masses — but
lift falls steeply with mass, which is exactly why the comparison is quoted at matched conditions on
the site and not across operating points. H57 revision 2 is recommended because it has the best
absolute measurement **and** no unresolved data rights: its only inputs are the competition's own stack
and public-domain USGS 3DEP products. H56's ComCat-derived corroboration still carries an open
contributor-rights question.

## H56 — the best-measured design in this repository, and an H51 provenance correction (this session)

Read [`docs/research/h56-diagnosis.md`](docs/research/h56-diagnosis.md) (why the 0.2778 artifact
topped the corpus, and the arithmetic of what 0.3774 requires) and
[`docs/hypotheses-20261007-h56.md`](docs/hypotheses-20261007-h56.md) (five untried hypotheses,
screened and ranked; four negative results recorded rather than buried). This session's candidate
is numbered **H56** because `main` already carries unrelated H52, H53, H54 and H55 candidates.

**One-click download (top of the site):**
`docs/downloads/gemsdoe50-h56-scarpdisperse-90000-allfinite.tif` — 90,000 predicted pixels, values
`0` / `1`, `float32`, EPSG:32611, 3730x3292, identical bounds and transform to the official
template, **every one of the 12,279,160 cells finite and inside `[0, 1]`**. A `-nan.tif` sibling
keeps `NaN` outside the study footprint to match the official sample, and a `.zip` carries the
all-finite GeoTIFF. The all-finite variant is the primary download precisely because the portal
once rejected an upload with `Predicted values must be in range [0, 1]`: a non-finite cell makes a
plain `min()/max()` validator see `NaN`, and `NaN <= 1` is false.

**Measured.** Off-catalogue DTI **0.1874** against a matched-mass uniform control 0.1401 (**1.34x**;
1.59x at 30,000 dots), versus 0.1468 for the best prior artifact on that frame. Frozen blocked
holdout: **4/4** macrofolds positive, paired block-bootstrap 95% CI **[0.0261, 0.0854]**, beats
translation controls 4/4. Format gate `all_checks_pass: true`. Uniqueness gate: worst full-pixel
IoU **0.0154** against every prior artifact on disk, minimum novel fraction at 2 px 0.4805, no SHA
match. Modelled hidden DTI **0.386** — that is a **model with a stated transfer assumption, not a
receipt**; `docs/research/h56-diagnosis.md` sections 5 and 9 state the assumption and what beating
0.3774 would actually require. It is numerically above the user-provided 0.3774 claim only under
that model and does not show that any real organizer score exceeded it. **No weekly slot has been
used; do not upload H56 until mixed-network ComCat contributor rights and sponsor-sharing
eligibility are cleared.**

**Three findings that are binding on anything built afterwards.**

1. **The corpus's structural flaw is emission geometry, not detector content.** For binary unit dots
   the official metric reduces exactly to `DTI = T / (0.2N + 0.8G)`, so every dot costs the same
   0.2 in the denominator no matter what it earns. Top-*N* selection piles dots a few pixels deep on
   the strongest feature, where the `max` in the numerator saturates and the cost does not. H56
   emits **variable-density blue noise at exactly 3 px** — `R = 300 m`, the coarsest spacing at
   which two dots never compete for the same truth pixel — which is also the geometry measured on
   the group's best off-catalogue prior artifact.
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

**Reproduce:**

```bash
# needs the three staged GeoDAWN rasters; see .arena/work/g24/data/external or the sibling repo
python scripts/build_h56.py --layers .arena/work/g24/data/external --out docs/downloads
python scripts/validate_h56.py --truth-mode sgmc_off --out evidence/h56_holdout_offcat.json
python scripts/h56_uniqueness.py --novel-threshold 0.45
python scripts/h56_holdout.py --n-boot 200        # frozen macrofold split
```

## Current outcome — 2026-10-07 UTC

### This session's own artifact — H52-C (eight-family coincidence)

The branch `arena/685c6059-gemsdoe50` also ships a file this session built and validated itself, kept
separate from the H52/H52A/H53/H54/H55 artifacts that other sessions track (nothing here reads their
pixels):

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
* Budget: the recorded nested pair solves the metric exactly (G = 14,088.75 px, T = 5,223.14 px), which
  yields the marginal-value rule (bar = 0.0588) and the ten-budget curve; the modelled optimum at 120k
  comes from a saturation cap, so the shipped 80k sits inside the measured plateau deliberately
  (`docs/h52-decision.md`, `evidence/h52_budget_curve.json`).
* Delivery: the H52-C band at the top of `index.html` (immediately below the other sessions' bands)
  carries the download links, the unique portal name `GEMSDOE50-H52-COINCIDENCE8-OFFCAT-80000` and a
  172-character note.

> **Not organizer-scored, no slot used.** The per-dot proxy quality of H52-C (0.1446) is below every
> incumbent-family artifact measured (0.1573-0.1704) and the receipt records that an SGMC-family
> submission scored 0.0512 on the hidden labels, so nothing here licenses a score claim.

### One-click H55 research artifact

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

> **Decision: NO SLOT. Do not spend a weekly submission on H55-S1.** The file is the requested
> unique competition-format deliverable and a reproducible negative experiment, not a submission
> recommendation. No portal upload or weekly slot was used.

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
| DrivenData GEMS forum rulings (R5, R6, R7) | the scoring mask, the definition of a "new fault", and the refusal to disclose label sources | quoted staff statements on the official community forum; read 2026-10-07 | [11516](https://community.drivendata.org/t/scoring-clarification-are-known-usgs-ingenious-faults-masked-when-scoring-and-are-they-in-the-final-round-label-set/11516) · [11536](https://community.drivendata.org/t/where-do-you-draw-the-line/11536) · [11527](https://community.drivendata.org/t/how-were-the-new-test-faults-identified-data-sources-and-fault-types/11527) |
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
* No upload occurred. No result is a current leaderboard observation or prediction of a prize win.

## Manual submission guide (not recommended for H55)

Only if the owner explicitly overrides the frozen no-slot rule:

1. Download the all-finite TIFF above and verify SHA-256
   `7a366b7bbe431533a9d4246cbcdde34eb379ebb34fa116a8667431916506498d`.
2. Open the official competition manually and confirm the current rules, deadline, remaining weekly
   feedback slots, external-data disclosure requirements, and AI disclosure.
3. Upload the single `.tif` unchanged; do not re-save, reproject, unzip into another raster, or alter
   nodata metadata.
4. Use unique name `GEMSDOE50-H55-SEISGEOM-RIDGESNAP-13591-BCB60D89`.
5. Optional note: “H55-S1 research artifact: space-time-thinned CC BY 4.0 relocated earthquake
   point geometry; recurrent local 2-D covariance axes; cross-axis 3DEP/radiometric ridge snap;
   supplied-fault and complete prior-pixel exclusion; 13,591 binary cells; local gate NO SLOT.”
6. Save the portal's submission ID/receipt and exact returned error or score before making any
   score-to-file claim.

The site has the same guide at [`submission.html`](submission.html).

Full review, evidence hashes, alternative explanations, official rules, and unresolved source/receipt issues: [`docs/research/h33-score-review-20261007.md`](docs/research/h33-score-review-20261007.md). No live leaderboard was queried in this review.

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
