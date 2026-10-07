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
    session works, commits, and pushes only on `arena/5550c3e4-gemsdoe50`; open the pull request from
    that branch. This name is session-scoped, not a repository default for future sessions. Merge
    to `main` only when repository/environment policy permits it. Never switch or push another
    branch from this session.

## H61 — current status (2026-10-07): which file to submit, and the mandated seismic map

**Recommended file (YES, OK to submit):**
[`docs/downloads/gemsdoe50-h59-sharpened-scarp-scatter-90k-20261007T171954Z-allfinite.tif`](docs/downloads/gemsdoe50-h59-sharpened-scarp-scatter-90k-20261007T171954Z-allfinite.tif)
(SHA-256 `838f9502fd4a2720374559db0947fb3372f97629401a617e5c9c95c1b1ce8be5`, 90,000 dots), entry name `GEMSDOE50-H59-SHARPENED-SCARP-SCATTER-90K`, note (corrected —
the published one cites the retracted transfer model): "GEMSDOE50 H59 rev2: blue-noise scatter, 90,000 dots on a 3-px lattice, sampling a sharpened rank-mean of the official band-19 slope-edge map and USGS 3DEP LiDAR scarp descriptors; no dot on a supplied-catalogue pixel or any prior-artifact pixel. Research model; no organizer score."
Step-by-step guide: [`docs/how-to-submit.html`](docs/how-to-submit.html).

**Why this file (merge-time adjudication, [`evidence/h61_candidates.json`](evidence/h61_candidates.json)).**
While this session ran, two other sessions merged new candidates and `main` ended up naming two
different "current candidates" (the page led with H57; the H60 receipt recommended the sharpened-scarp
file). Rule: a file is eligible only if none of its dots reuses a pixel of the 61 registered prior
artifacts (charter item 2); eligible files are ranked by the repository's frozen gate. Result:
sharpened-scarp 90k **0.2125** > H60-union 0.2033 > H57 0.2025
(H57 is ineligible anyway: 27,248 of its dots reuse prior pixels). This session's independent
instrument agrees on the order (0.2492 vs H57 0.2178 pooled), but the lead is not uniform:
2/4 macrofolds vs H57, paired 16-subtile interval [-0.0225, +0.0539].
4,753 of its dots lie within 300 m of the supplied catalogue (1-px buffer). Proxy scores
are not organizer scores; expect roughly the low 0.2s.

**H61 (preregistered in [`docs/research/h61-hypotheses-preregistered.md`](docs/research/h61-hypotheses-preregistered.md);
developed as "H59" and renumbered at merge) — NO SLOT.** The mandated seismicity-lineation artifact was
built as specified (ComCat → Zaliapin–Ben-Zion declustering → unverified 2-D triangle screen →
location-error-deconvolved covariance → epicentral + up-dip corridors → snap to the H57 ridge): 31
lineations, 326 dots, DTI 0.0002, below random dots and translated corridors, and below smoothed
density on withheld faults (0.0007 vs 0.0093). Inside every H57-strength decile the corridors carry
*less* fault credit than the cells outside them; loosening every screen (up to 1,034 lineations) never
lifts that ratio above 0.97. A corridor/H57 hybrid (0.2088) and wider H57 spacing (4 px 0.1866, 5 px
0.1786) also lost. The H61 file is valid and unique but labelled **do not submit**.

**Corrections made this session:** the metric "reduces exactly" claim and the "3 px ⇒ no
competition" claim are false (errata in `docs/research/h56-diagnosis.md`,
`docs/research/h33-02778-study-20261007.md`, this README and the site); uniqueness was re-measured
against the full corpus of 309 distinct rasters; `scripts/check_submission.py` now accepts
zero-outside files (the portal scored such files); the preserved H57 band no longer says "Yes,
submit"; a third merge (PR #28, an "H60" ComCat seismicity-KDE file: frozen-frame DTI 0.0744, 14,392 reused prior pixels, a 0.54 score quoted from the retracted transfer
model) had hand-edited the pages and broken `main`'s CI — its banner is removed, its files are labelled, and
the checks pass again. Full working, flags F1–F13 and next steps:
[`docs/research/h61-verdict-20261007.md`](docs/research/h61-verdict-20261007.md).

```bash
.venv/bin/python scripts/fetch_prior_corpus.py --out .arena/prior_corpus --receipt evidence/h61_prior_corpus_receipt.json
.venv/bin/python scripts/build_h61.py --stamp 20261007T205554Z      # deterministic: same bytes
.venv/bin/python scripts/h61_candidates.py                           # which file to submit
.venv/bin/python scripts/h61_uniqueness.py --candidate docs/downloads/<file>.tif
.venv/bin/python scripts/h61_sensitivity.py                          # post-hoc, exploratory
for b in h55 h58 h59 h60 h61; do python scripts/build_${b}_site.py; done
```

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
   the official metric reduces exactly to `DTI = T / (0.2N + 0.8G)` *(erratum, H61: false — exact only
   when T = M; see `docs/research/h61-verdict-20261007.md` §4)*, so every dot costs the same
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

## H59 — the current candidate of this session: sharpened topographic-scarp scatter (this session)

**Note on numbering.** This session's work was originally numbered H57, but unrelated H57 and H58
series were merged to `main` from other Arena sessions while this branch was in flight, so the series
was renumbered **H59** at merge time. The raster bytes were not changed by the rename; every hash in
`evidence/h59_build.json` was re-verified against the renamed files afterwards, and the `.zip` was
rebuilt so its internal entry name matches the delivered file.

**Read first:** [`docs/hypotheses-20261007-h59.md`](docs/hypotheses-20261007-h59.md),
[`docs/research/h59-preregistration.md`](docs/research/h59-preregistration.md) (the frozen protocol and
its declared **Amendment 1**),
[`docs/research/h59-final-analysis.md`](docs/research/h59-final-analysis.md),
[`docs/research/h59-deviation-log.md`](docs/research/h59-deviation-log.md) (the three-pass record),
[`docs/research/h59-proxy-gap.md`](docs/research/h59-proxy-gap.md), and
[`docs/research/gems-official-clarifications.md`](docs/research/gems-official-clarifications.md)
(official rulings and the source licence ledger).

**One-click download, and it is the first thing on the site:**
[`docs/downloads/gemsdoe50-h59-sharpened-scarp-scatter-90k-20261007T171954Z-allfinite.tif`](docs/downloads/gemsdoe50-h59-sharpened-scarp-scatter-90k-20261007T171954Z-allfinite.tif) — 90,000 predicted cells, values `0` / `1`,
`float32`, EPSG:32611, 3730 × 3292, **every one of the 12,279,160 cells finite and inside `[0, 1]`**,
SHA-256 `838f9502fd4a2720374559db0947fb3372f97629401a617e5c9c95c1b1ce8be5`. A `-nan.tif` sibling keeps NaN outside the study
footprint to match the official sample, and a `.zip` carries the all-finite GeoTIFF. Portal entry name
`GEMSDOE50-H59-SHARPENED-SCARP-SCATTER-90K`; the note is the `portal_note` field of
[`evidence/h59_build.json`](evidence/h59_build.json).

### What it is, and what changed after the first build

The field is a **sharpened NaN-aware rank-mean** of two families: the official layer 19
(detrended-elevation slope) *gradient magnitude*, a step-edge detector for a fault scarp, and the USGS
3DEP 1 m LiDAR scarp descriptor stack. Sharpening exponent **^16**, 90,000 dots on a 3 px lattice, one
per chosen block, on the strongest eligible cell of the block; never on a supplied catalogue cell and
never on a registered prior-artifact cell.

Two screens after the first frozen build changed the design; both are declared post-hoc in the
preregistration because they were run **after** the first build's numbers were seen:

1. **A rank mean was compressing the peaks.** Raising the blend to a power lifted the off-catalogue DTI
   at 90,000 dots from **0.17142 to 0.23406** with emitter, seed, lattice and pool frozen (+37 %), and
   the lift over a matched-mass uniform control from 1.33× to **1.84×**. The response is monotone to
   ^8, ^16 is the frozen value, and it turns over by ^32.
2. **The dot count was sized for the wrong frame.** Revision 1 spent 180,000 dots because the *proxy*
   prefers ~250,000. The proxy's truth (52,219 px) is ~4× denser on the ground than the hidden target
   (≈12,226 px), so it keeps repaying dots the hidden scoring would not. Under the repository's
   calibrated per-dot credit transfer (0.887) the sharpened field saturates at **90,000**; the marginal
   dot beyond it earns ~0.077 against a 0.2 false-positive charge. Proxy reading at 180,000 is 0.27864
   against 0.23406 at 90,000 — that disagreement is published, with a sensitivity table from transfer
   0.30 to 1.00.

### Measured on the delivered bytes ([`evidence/h59_delivered_metrics.json`](evidence/h59_delivered_metrics.json))

| frame | truth px | DTI | NW / NE / SW / SE |
| --- | ---: | ---: | --- |
| `S_matched` (geometry-matched off-catalogue proxy) | 52,219 | **0.23028** | 0.1455 / 0.1500 / 0.0273 / 0.1294 |
| `S_raw` (unmodified proxy) | 61,664 | 0.24917 | — |
| `L` (supplied catalogue — negative control) | 60,988 | 0.03892 | — |

Controls at matched mass 90,000: whole-footprint uniform **0.12383** (lift **1.86×**),
same-pool uniform **0.11134** (lift **2.07×**); paired 32 × 32 px block
bootstrap **+0.1041**, 95 % interval **[+0.0948, +0.1141]**, positive
in 100/400 replicates. Uniqueness: **0** cells shared with the
61-artifact prior union, worst 800 m block IoU **0.0419** across 50 signature-pinned priors.

### Where 0.3774 stands, measured rather than asserted

The file earns **14,090** of truth-side credit at **27.0 %** coverage with
**82,971** of false-positive mass. A prediction with *zero* false positives at this
coverage would score **0.3160** — the file realises 73 % of its
own ceiling — and 0.3774 with perfect precision needs **32.7 %**
coverage. So on this frame the target is **not** reachable by precision alone: it needs roughly 3,000
more truth pixels covered, i.e. a field that finds fault pixels this one misses. The transfer model,
by contrast, puts the same bytes at **0.44** (saturated) at a transfer of 0.887 and 0.15 at 0.30.
Both readings are published; neither is an organizer score, and no score is claimed.

### Corrections this session

1. A 24.7 % LiDAR **dead zone** in the first revision (strict intersection) cost 21 % of truth credit;
   the NaN-aware mean fixed it (0.17990 → 0.21812 in that revision).
2. A **rank mean flattens the top** — corrected by the exponent sweep, worth +37 % proxy DTI.
3. **Dense emission is not better**: blobs and skeletonised 1 px lines lose to field-weighted spreading
   at matched painted count.
4. The **mass instrument was measuring specks**: random-pixel subsampling of the proxy truth severs
   connectivity and inflates the curve by 33 %; whole-component selection replaces it.
5. The **catalogue buffer is 1 px**, not 300 m, per staff rulings on the evaluation mask and on new
   geometry of existing systems; the apparent 3 px win on the proxy is a frame selection artefact and is
   labelled as one.
6. The **seismicity point-pattern term is at chance** here: implemented, measured, reported as a
   negative, and excluded from the artifact.

## H58 — the owner-mandated unique ComCat point-geometry artifact (this session)

**H58-S1** is the unique submission generated as the session's mandated deliverable: **declustered
USGS ComCat epicentre point geometry as the primary prediction field** — a genuinely new artifact,
not a variant of any prior file. H55 used the *relocated* catalogue (and failed its gate); H56
used ComCat lineations only as a 0.25-weight corroboration on the LiDAR scarp belief; no shipped
artifact made ComCat point geometry the primary field. (Renumbered from H57 to H58 because the
parallel H57 session's scarpstep artifact merged to `main` first via PRs #22/#23 and owns the H57
number; the repo convention is one unique number per hypothesis.) Preregistration (five ranked
hypotheses, frozen before any scoring):
[`docs/research/h58-hypotheses-preregistered.md`](docs/research/h58-hypotheses-preregistered.md).

**One-click download (site band below the H56 band):**
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
(median 0.88 km — a corridor prior, not a trace) → blue-noise emission at the metric's own 300 m
support (support caps at 98,598 cells) → placement step measured (identity kept; no ridge snap
improved the proxy). Pooled off-catalogue proxy DTI **0.0997** vs smoothed-density control
**0.1078**, matched random **0.1329**, H56 incumbent **0.1874**; the paired 16-subtile bootstrap
for candidate-minus-incumbent credit per dot is **[-0.1107, -0.0250]** — the candidate loses in
**all four** macrofolds, and its 1-pixel enrichment against proxy truth is 1.03x (chance level).
Uniqueness gate: worst full-pixel IoU **0.0166** against every prior artifact on disk, minimum
novel fraction at 2 px **0.7537**, zero exact overlap with the frozen 1,405,451-cell prior union,
no identical SHA-256 — **unique: true**. Format gate: NaN twin `all_checks_pass: true`; all-finite
twin entirely finite in [0, 1].

> **Decision: NO SLOT.** This is the requested unique deliverable and a recorded negative result,
> not a submission recommendation — exactly as the prior measurements predicted (H55 failed as a
> primary seismicity detector with a better-located catalogue; H56's ComCat-lineation component
> measured neutral, lift 0.96-0.99). H56 remains the best-measured candidate on this branch. No
> weekly slot was used; do not upload H58-S1.

**Defect found and fixed in shared code (disclosed, not hidden).** The H58 build exposed a latent
bug in `gemsdoe50.h56.emit_blue_noise`: its tie-breaker jitter was an *absolute* `1e-6`, so in
blocks whose belief spread is below ~1e-6 (H58 corridor tails) the jitter dominated the values and
`argmax` could pick a cell **outside** the emission domain — 5,631 of 98,598 emitted dots landed on
prior-union/catalogue cells before the fix. The jitter now scales with each block's own maximum
(`src/gemsdoe50/h56.py`), with a regression test (`tests/test_h56.py`). **H56's and H55's shipped
bytes are unaffected** (verified: 0 dots outside their domains); a future H56 rebuild would differ
in low-belief/near-tie blocks. This is recorded here because the shared emitter changed.

**Reproduce:**

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

## H57 — former candidate (superseded 2026-10-07: reuses 27,248 prior pixels), and an honest retraction

**Download (one click, portal-safe):**
[`docs/downloads/gemsdoe50-h57-scarpstep-80000-20261007T1830Z-allfinite.tif`](docs/downloads/gemsdoe50-h57-scarpstep-80000-20261007T1830Z-allfinite.tif)
— SHA-256 `8027c4e9fe0f789e2d7180a7ccc031abec90b391cf9e42ebcc125752af9fb696`, 395,743 bytes,
80,000 predicted cells, 3 px minimum Chebyshev spacing, zero dots within 300 m of the given
catalogue, every cell finite and in `[0,1]`. NaN-outside twin, `.zip`, unique entry name
`GEMSDOE50-H57-SCARPSTEP`, the portal note, and the step-by-step upload guide are on
[`submission.html`](submission.html). **It is fine to download and submit this file**: it is this
project's own construction from public layers, it copies no prior submission pixel (maximum
full-pixel IoU 0.0248 against the 26 pinned prior artifacts), and it uses **no earthquake
catalogue**, so the unresolved ComCat contributor rights and sponsor-sharing question that blocks
H56 does not apply.

**What was measured.** The earlier screen's top channels were elevation itself (`dem_mean` 3.665,
`det_elev` 3.657) because F1's truth is USGS SGMC faults, which live in the mountains: an
unstratified F1 result is a terrain confound. `scripts/h57_stratified.py` re-screens inside five
mean-elevation percentile strata and admits only channels that win 5/5; H57's two families survive
(LiDAR scarp 2.41–2.73, topographic step 2.11–2.61) while the whole geodetic-strain family
(0.28–0.38), every magnetic and radiometric channel (0.42–0.98) and every residualised 9×9 row are
rejected. On the frozen spatially-blocked gate H57 pools **0.2025** against a matched-mass uniform
control of 0.1053 (1.92×), positive in **4/4** macrofolds, paired 95 % CI [+0.0626, +0.1330] — the
strongest result this repository has measured, versus 0.1021 for the incumbent
`gems51-scarpradio-offcat-35000` and 0.0878 for the corpus's top artifact
(`g32_h33b2_02778.tif`, owner-reported 0.2778).

**The retraction.** H57's earlier "modelled hidden DTI 0.385–0.394" came from multiplying F1 credit
per dot by an assumed transfer factor of 1.8–2.0. Fitting that factor on the 21 scored corpus
artifacts gives **R² = −0.872** — worse than predicting the mean — because the artifacts that score
0.26–0.28 on the hidden frame have *lower* F1 credit per dot (0.064) than artifacts that score 0.03.
The corpus-calibrated model (`h = 0.5305 − 0.1669·F1_c_per_dot − 0.0390·ln N`, R² = 0.651) puts
H57's expected competition score at **≈0.23** (indicative band 0.05–0.41), with P(>0.2778) ≈ 29 %
and **P(>0.3774) ≈ 4 %**. The F1 coefficient is negative but not significant (t = −1.05): the
defensible statement is that F1 selectivity is *not measurably helping*, not that it hurts.
**No page in this repository may claim H57 beats the public best 0.3774**, and the 0.386 figure
below for H56 is likewise a model, not an organizer score.

**What beating 0.3774 would require.** `T > 0.3774·(0.2N + 11,271)`, i.e. 6,518 credit pixels at
N = 30,000 (1.25× the best absolute credit ever observed, 5,223) or 10,292 at N = 80,000 (1.97×).
The corpus's top seven artifacts all sit in the narrow mass band 37,654–44,090, so the route is
*credit per dot* — the same credit with far fewer dots — not more dots. That is the next experiment.

Full working: [`docs/research/h57-verdict-20261007.md`](docs/research/h57-verdict-20261007.md)
(§7 lists the flagged irregularities, including the F2 name collision between this repository's
catalogue-holdout frame and the H52 register's INGENIOUS-holdout frame).
## H60 — official-stack belief field, the union arm, and the price of novelty (2026-10-07)

**Question.** Does the organizer's own 19-band `training_features.tif` carry off-catalogue fault
information that the owner-derived LiDAR/topographic-step families behind H57 do not — and can a
*maximally* novel placement be built that still scores? **Answers: yes it carries information — the
union arm beats the older H57 on both instruments — and maximal novelty is bought with score.** H60
is still a **NO SLOT** result, because the current candidate merged on main (the sibling session's
H59 topographic-scarp scatter) ranks higher on the same frozen gate; it does **not** replace it.

**Naming note.** This series was developed as "H59" and renamed **H60** during the merge, because
the sibling session merged on main already owns the H59 label (`docs/research/h59-*.md`,
`h59.html`).

**Screen (measured, `evidence/h59_screen.json`).** 17 `tf` channels × {`raw`, `grad`, `ridge2`} at
30,000 dots, scored on the off-catalogue F1 frame inside **five elevation strata** (the stratifier
matters: F1 truth is USGS SGMC fault pixels, which live in the mountains). Winners, all 5/5 strata:
`raw::det_elev_slope` **2.198**, `raw::det_elev` **2.193**, `grad::det_elev_slope` **2.064**,
`grad::tc` **1.969**, `raw::iso_grav_anom` **1.909**, `ridge2::geod_dilaterate` **1.887**,
`ridge2::det_elev_slope` **1.877**, `ridge2::tc` 1.491. Failures: every magnetic amplitude channel
(0.50–0.98), the shipped gravity-gradient products (0.31–1.29), raw geodetic strain (0.28–0.38),
`depth_to_base_surf` (0.33–1.18). **This corrects the earlier "official raw bands lose" claim** —
detrended elevation and its slope do carry off-catalogue information.

**Arms (measured).** | candidate | dots | frozen gate | matched uniform | folds |
|---|---|---|---|---|---|
H57-scarpstep (incumbent) | 80,000 | **0.2025** | 0.1053 | 4/4 |
H59-union-d0 | 75,308 | **0.2033** | 0.1050 | 4/4 |
H59-union-d2 (max novelty) | 75,308 | 0.0618 | 0.0917 | **0/4** |
H59-official-stack alone | 50,000 | 0.1224 | 0.0749 | 4/4 |
On the second (pooled off-catalogue F1) instrument the union arm scores 0.1018 vs H57's 0.0914
(uniform 0.0421). So H59-union leads both proxies — by **+0.0008** on the gate. That is inside the
instrument's noise, so the decision receipt records a tie and **NO SLOT**
([`evidence/h59_gate_decision.json`](evidence/h59_gate_decision.json)).

**The finding worth keeping: novelty past the corpus is bought with score.** Two arms were emitted
from the same belief field at the same mass: one forbids only prior-*pixel* reuse (0 of 1,405,451
prior cells reused; 0.437 of dots >2 px from every prior dot; gate 0.2033), the other excludes a
Euclidean disk of radius 2 around every prior cell so *every* dot is >2 px from every prior dot
(novel fraction 0.714, satisfying the repository's 0.5 threshold). The second collapses to
**0.0618** — below its own matched uniform control (0.0917) and losing **0/4** macrofolds. The 0.5
novelty threshold is therefore a **copy detector, not a placement constraint**; the binding charter
rule is zero reused prior pixels, which H59-union satisfies *(erratum, H61: H57 does not — 27,248 of
its 80,000 dots are on the prior union, per `evidence/h60_gate_decision.json`)* (max full-pixel IoU 0.204
against this project's own H57; no byte-identical file).

**Hidden-frame models disagree, and one of them fails a sanity check.** Transfer (retracted, R² =
−0.87), mass (R² = 0.515) and corpus-calibrated (R² = 0.651) models give H57 0.1428 / 0.1761 /
**0.2286** and H59-union 0.1623 / 0.1788 / **0.2237** — opposite signs. Applied to the
maximal-novelty control the corpus-calibrated model predicts 0.2518, its highest value anywhere,
while that control scores 0.0618 and loses to uniform in every fold. Model-implied numbers are
therefore reported as indicative only and are not used to choose between the two files.

**Published artifact (alternative, not the recommendation).**
`docs/downloads/gemsdoe50-h59-union-d0-75308-20261007T2250Z-allfinite.tif` (+ `-nan.tif` twin and
`.zip`), SHA-256 `143bae71968c5fc2b70b2de579e6a33f61d9d3e07beac13f20272760758b3bda`, 75,308 cells,
draft name `GEMSDOE50-H59-UNION-75308`; every cell finite and in [0,1], every dot ≥300 m from the
given catalogue and on no prior positive pixel. The site leads with H57 and says plainly that H57 is
the file to submit; [`docs/downloads/README.md`](docs/downloads/README.md) labels every file in the
download directory.

**Next experiment (H60), in priority order.** (1) **The mass axis on the frozen gate**: the sweep
and the arms disagree about the optimum number of dots, and the frozen gate is the only instrument
with a matched control at every mass — measure 20k/30k/40k/50k/60k on H57's own field before any new
family is tried; (2) only then, a genuinely new *family*: the screen's `grad::tc` (magnetic tilt
gradient) and `ridge2::geod_dilaterate` (geodetic dilatation-ridge) are the two unexploited winners
that are not topography; (3) resolve the strict-novelty threshold's semantics in the charter so it
stops being read as a placement rule.

Full working: [`docs/research/h60-verdict-20261007.md`](docs/research/h60-verdict-20261007.md)
(§7 lists the flagged limitations, including the missing H59 preregistration document — the H59
arms and the novelty control were defined after the screen was seen, so H59 is
hypothesis-generating, not confirmatory).

## Standing project prompt — read at the start of every session (2026-10-07)

This is the owner's standing instruction for this project, restated item by item (not a verbatim
transcript) so it is read every time the project is worked on. It sits above the session-scoped
charter items where they differ.

1. **The goal is to place at the top of the DrivenData #306 DOE GEMS Prize leaderboard**
   (<https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/>). The verified
   public leader on 2026-10-07 is **0.3774 (xiaofanhu)**; the design target is to beat it. The
   metric is the distance-weighted Tversky index (alpha=0.2, beta=0.8, R=300 m); for binary dots
   it is `DTI = T / (0.2N + 0.8G + 0.2(T − M))` with `M = Σ K(dot)` — **not** the
   `T / (0.2N + 0.8G)` collapse earlier sessions wrote (exact only when T = M; dots < 6 px apart
   compete). See `docs/research/h61-verdict-20261007.md` §4 and `tests/test_h61.py`.
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
   unverified; say so everywhere. References named by the owner: Ouillon, Ducorbier & Sornette
   (2008) JGR 113, B01306, doi:10.1029/2007JB005032; Ouillon & Sornette (2011) JGR 116, B02306,
   doi:10.1029/2010JB007752; Wang, Ouillon, Woessner, Sornette & Husen (2013) arXiv:1304.6912.
4. **Answer at PhD level, from verified sources, with links for manual review**: why the
   group's best artifact reportedly scored 0.2778 (GEMSDOE32
   `h33-h33-2-b2-20261004T220000Z-e5eb6e7e-zeros`), and whether a submission can exceed it and the
   leader. Keep deep geothermal research from official sources in `docs/research/`. Never turn an owner/user report into an authenticated score without an organizer
   receipt. Flag irregularities; no hallucinations; verify line by line.
5. **Protect the weekly feedback slots.** Preregister 3-5 untried hypotheses before implementing
   (layers combined, physical signature or transform, why it catches faults the catalogue misses,
   how it differs from what the repository already tried); rank them by expected DTI improvement
   and cost; validate the top candidate on the frozen
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
   (`arena/5550c3e4-gemsdoe50` for the 2026-10-07 H61 session); open the pull request from it;
   merge to `main` when the checks
   pass. Keep large scratch data out of Git; keep hash-pinned derivatives needed to reproduce.
   End every session with suggested next work, limitations, and any access still required.
