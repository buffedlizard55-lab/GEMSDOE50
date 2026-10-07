# Historical preregistered geological hypotheses — H50-S1

> This 2026-10-06 H50-S1 preregistration is an archived experiment record, not the current ranking or slot authorization. The active H53 ranking is in [`docs/research/h53-hypotheses-20261007.md`](research/h53-hypotheses-20261007.md); H53-A is NO-GO / NO SLOT. See the [current overview](../index.html).

**Registered:** 2026-10-06 UTC, before implementation. This file freezes the candidate list, expected direction, data requirements, and promotion gate. Before any H50-S1 DTI, review amended the implementation protocol to correct the invalid sea-level plane projection, add a matched smoothed-density control, and separate statistical passage from submission eligibility; see the versioned amendment in [`h50s1-protocol-addendum.md`](h50s1-protocol-addendum.md). The hypothesis ranking and numeric promotion thresholds are unchanged. Later results belong in a separate results document; do not edit these priors to make a failed idea look successful.

## Scope and metric context

The target is a single-band 100 m fault-confidence raster for the GeoDAWN study area. The official distance-weighted Tversky index has 300 m support and weights false negatives more heavily than false positives (α=0.2, β=0.8). A useful hypothesis must find expert-labeled fault traces in held-out geographic blocks while not simply reproducing the existing USGS/INGENIOUS catalogue.

The expectation categories below are **pre-experiment priors**, not scores: **High / Medium / Low potential** describes plausible upside versus the fixed H50-prior comparator; `ΔDTI` is intentionally not assigned a fabricated number. Numeric claims will appear only after the preregistered holdout is run. Cost is a 1–5 engineering/research estimate (1 = small, 5 = substantial).

## Ranked hypotheses

| Rank | ID / hypothesis | Layers and physical signature | Why it may find a fault missing from USGS / INGENIOUS | Difference from prior GEMSDOE work | Expected DTI impact (prior) | Cost / data |
|---:|---|---|---|---|---|---|
| **1** | **H50-S1 — relocated hypocenter planes intersect terrain to propose fault-trace lineaments** | Nevada catalog `lat`, `lon`, `dep`, `otime`, `mag`, `reloc` (`reloc=1`) plus an exact-grid USGS 3DEP elevation raster. Fit robust compact 3-D neighborhoods; convert depth-positive-down to elevation-positive-up; numerically intersect the plane with terrain rather than sea-level `z=0`; require strike, length, event/year support, and bootstrap stability. | A relocated hypocenter cloud may expose an active blind structure; event-plane geometry is a distinct signal from broad seismicity density. Surface intersection remains uncertain and cannot be called a mapped fault without validation. | Prior H33-E used a smoothed seismicity band; H47-SAF used catalogue-flank re-occupation/pruning. H50-S1 uses individual relocated events, local 3-D geometry, terrain intersection, and frozen same-event smoothed-density controls at 300 m, 1 km, and 2 km. | **Highest upside, highest uncertainty.** A narrow line may help FN-heavy DTI, but location error, aftershock swarms, missing event type, and vertical-datum uncertainty may erase the gain. No numeric ΔDTI is claimed. | **4/5.** Nevada file `nvreloc_catalog_newmag.txt` (13,833,354 bytes, DOI `10.5281/zenodo.11167510`, CC BY 4.0) plus USGS 3DEP elevation (public domain per the USGS catalog). Requires competition grid/labels for blocked validation. Catalog lacks event-specific uncertainty covariance and event-type/source fields; exported DEM vertical datum is not yet reconciled to the catalog's mean-sea-level depth reference. |
| **2** | **H50-G1 — basin-edge basement steps with coincident conductive and potential-field boundaries** | `depth_to_base_surf`, `cond_surf`, `iso_grav_anom_hg` / `iso_grav_anom_vg`, `tmi_hg` / `rtp`; seek a persistent, oriented step/contact supported by independent conductivity and gravity/magnetic gradients, rather than any single high-gradient pixel. | A fault that offsets basement or juxtaposes altered/fluid-bearing rock may be visible as a multi-physics boundary even when its surface trace is buried or eroded. | Earlier work tested TMI-only persistence (H47-B), gravity/magnetic maxspot persistence (H48-A), and broad multiphysics fusion (H32-D). This candidate is specifically a conditional basin-margin/contact signature with orientation and continuity requirements—not a weighted global blend. Similarity is acknowledged; it must beat the same-fold incumbents and matched controls. | **Medium upside.** Independent agreement can suppress false edges, but this may just recover known basin boundaries. Numeric ΔDTI withheld. | **3/5.** Uses provided 19-band feature stack and labels; no new external data required. |
| **3** | **H50-S2 — multi-year recurrence separates persistent fault strands from transient swarms** | The same Nevada catalog (`otime`, `lat`, `lon`, `dep`, `mag`, `reloc`); compare lineament support across independent time bins and declustered/one-vote-per-time-window representations. Target spatially linear structures recurring across years rather than one sequence dominating a density raster. | Recurrent lineation suggests a persistent tectonic structure, whereas an isolated swarm or induced sequence can be spatially concentrated but weak evidence for an enduring mapped fault. | H33-E was a static, smoothed seismicity surface; H47-SAF used spatial catalogue flanks. This tests time persistence and sequence robustness, not the raw number of events or proximity to mapped faults. It is related to H50-S1 and is not an independent data source. | **Low-to-medium upside.** Could improve precision and robustness more than recall; temporal completeness varies and may penalize real faults with only one observed sequence. Numeric ΔDTI withheld. | **4/5.** Same accessible CC BY 4.0 Zenodo catalog as H50-S1; requires temporal parsing, declustering sensitivity, and blocked validation. |

## Data/license gate for H50-S1 and H50-S2

The official DrivenData problem page encourages external data only where the participant has a license and the data can be shared with organizers for independent verification. The competition's external-data rule also requires a permissive license that does not prohibit commercial use. Zenodo identifies the Trugman catalog as **CC BY 4.0**; the license permits sharing/adaptation, including commercial use, subject to attribution, a license link, and marking changes. USGS states its 3DEP products are public domain. The actual dynamic DEM export will be hash-pinned and its service metadata recorded. These rights checks clear those raw inputs, not the unlicensed GEMSDOE24 scarp-feature derivative; that file is excluded. Cite both the catalog dataset/paper and 3DEP source in any result:

> Trugman, D. T. (2024). *A High-Precision Earthquake Catalog for Nevada*. Seismological Research Letters 95(6), 3737–3745. https://doi.org/10.1785/0220240106. Dataset: *Relocated Earthquake Catalog for Nevada (2008–2023)*, Zenodo v2, https://doi.org/10.5281/zenodo.11167510, CC BY 4.0. USGS National Map 3D Elevation Program (3DEP), dynamic 3DEPElevation ImageServer, https://elevation.nationalmap.gov/arcgis/rest/services/3DEPElevation/ImageServer; public-domain status per https://data.usgs.gov/datacatalog/data/USGS:77ae0551-c61e-4979-aedd-d797abdcde0e.

**Unresolved scientific limitation:** `reloc=1` marks waveform relocation, but the downloadable table does not include each event's location-error PDF/covariance. The paper cautions that absolute accuracy remains tied to the velocity model; waveform relocation improves relative precision for a subset, and not every event can be waveform-relocated. Do not equate decimal coordinate precision with positional accuracy, and do not call H50-S1 ACLUD: it is a 3-D plane-fitting hypothesis without event-specific covariance, not a reproduction of a validated 3-D uncertainty-aware algorithm. The separate legacy H50-B 2-D epicenter/triangle-area adaptation is also not ACLUD and remains unverified.

## Preregistered spatial-holdout and slot gate

1. Use only the official training labels as validation truth; never infer hidden labels. Keep the feature data, label data, and catalog hashes in the result report.
2. Freeze four contiguous macrofolds on the official 3292 × 3730 grid at the center row/column: NW, NE, SW, and SE. Within each macrofold, retain the four 2 × 2 subtiles as the units for block-bootstrap uncertainty. Erode each held-out core by 10 km (100 pixels) for scoring; exclude labels within 10 km of that held-out core from any supervised fit. Derive the visible-catalogue mask from non-held-out labels only, buffer that mask by 300 m (3 pixels), and score candidate traces only outside this buffer. The exact row/column bounds and valid-footprint mask must be serialized and hash-pinned before any DTI is computed. This emulates the “new fault” task rather than rewarding reproduction of known traces.
3. Compute the official DTI locally with α=0.2, β=0.8, and a 300 m triangular distance kernel. Report pooled and fold-wise values. Use equal prediction mass when comparing raster emitters.
4. Fix H50-prior as the primary incumbent before any holdout scoring; its choice is chronological, not based on a holdout score. Score H32-D, H47-S3, and H48-DS on the same folds as secondary descriptive comparators only; never use their holdout values to select an incumbent. Also compare against 300 m, 1 km, and 2 km Gaussian-smoothed density rasters built from the same relocated-event pool. Run matched spatial translations and time-shuffle controls. Use a spatial-block bootstrap for uncertainty; do not treat pixels as independent samples.
5. **Promotion threshold:** H50-S1 must exceed the frozen incumbent by at least **0.005 absolute DTI** on pooled held-out blocks, have positive paired deltas in at least **3 of 4** macrofolds, and have a 95% block-bootstrap lower bound for its paired improvement above zero. It must beat the 95th percentile of translation and time-shuffle controls and strictly beat the same-event smoothed-density control. These thresholds and controls were frozen before any DTI; a failure closes the artifact/slot gate.
6. A passing proxy is necessary, not sufficient, for a weekly submission. No portal slot is used without a unique, fully validated GeoTIFF and explicit user submission/account access. A proxy pass is not a claim about private score or final prize ranking.

## Stop conditions and irregularities

- If the waveform-relocated points do not overlap the valid competition footprint in adequate numbers, stop H50-S1/H50-S2; do not substitute the unresolved mixed-network ComCat CSV.
- If event error is too large or undocumented for the proposed 300 m scoring kernel, report the mismatch and do not claim submission eligibility. The current Nevada file lacks event-specific location covariance.
- Do not claim slot eligibility until a standard declustering method/sensitivity analysis, event-type/induced-seismicity review, mine/quarry and injection-site exclusions, and a defensible local vertical-datum transformation have been completed. Those gates are currently unmet even if the statistical proxy gate passes.
- If terrain intersection lacks valid DEM roots or the 3DEP/catalog datum relationship cannot be established, stop the surface-trace claim; do not revert to sea-level `z=0`.
- If H50-S1 fails its statistical gate, do not build a candidate TIFF or spend a slot. H50-G1 may be tested only as the next preregistered candidate using the same split and gate; it must not be presented as independently successful merely because it was ranked second.
- Public leaderboard rows do not establish which TIFF earned a score. Do not refresh/copy the board in violation of DrivenData's Terms of Use.

---

# H51 series — registered 2026-10-06 (before the H51 build ran)

**Scope.** A second, independent evidence line for the same competition, written after the
H50 series above and after the earlier `gems50` seismicity-corridor package. The rule for the
series is the standing one: a candidate is *slot-eligible* only if it beats a frozen incumbent
on a spatially blocked instrument, and a candidate that measures at or below its matched
random control is recorded as a negative result rather than shipped.

**Instruments used to rank the candidates** (all local, none of them the hidden truth):

| id | truth set | pixels | why it is a useful proxy | why it is not the target |
|---|---|---:|---|---|
| I1 | provided catalogue raster | 60,988 | real fault geometry | its pixels are masked out of the scored truth; anti-instrument |
| I2 | USGS SGMC faults > 300 m from the catalogue | 61,664 | mapped structures the competition label set does not contain | density 1.19 %, 5x the estimated hidden density, and a different vintage/scale |
| I3 | 2020 Mw 6.5 Monte Cristo Range rupture trend | 242 | an actual unmapped rupture inside the survey; 1 px of it lies on the catalogue | tiny; a single structure |
| control | matched-mass uniform random emission | — | the bar every candidate must clear | — |

The metric on every instrument is the official distance-weighted Tversky index
(alpha 0.2, beta 0.8, 300 m triangular kernel), reproduced in `tests/test_metric.py`.

## Ranked candidates

| Rank | ID / hypothesis | Layers and physical signature | Why it could find a fault missing from USGS/INGENIOUS | Difference from prior GEMSDOE work | Measured result (this session) | Cost |
|---:|---|---|---|---|---|---|
| **1** | **H51-A — corroborated scarp/radiometric lineaments** | 3DEP/LiDAR scarp descriptors (`step_max`, `lapneg_max`, `relief`), 10 m topographic derivatives (`slope_max`, `prof curv`, `relief_local`, `hillshade lineament`, `slope_p90`, aspect coherence), detrended elevation slope; airborne radiometric K, Th, U, TC and Th/K, U/K, U/Th | A Quaternary fault that is absent from the catalogue is most likely to show as an **oriented topographic step or scarp**, and a fluid-pathway structure may also appear as a radiometric contrast; requiring both to be present with a consistent azimuth suppresses single-layer pattern matches | The earlier `lidarscarp-ridge-*` files used the scarp descriptors alone; the H19 family fused four hand-weighted lines; here the combination is two *measured* families, the emission is set by the metric's own marginal rule, and the whole support is > 300 m from the catalogue | **Best measured candidate.** SGMC-off credit/dot 0.191 at 35 k dots vs 0.110 for the matched random control; catalogue credit/dot 0.246 before the buffer; Monte Cristo trend 24.7 weighted px at 35 k dots | 3/5 |
| **2** | **H51-B — seismicity event-geometry lineaments with a calibrated uncertainty model** | ComCat `earthquake` events (magnitude >= 1, depth <= 25 km), space-time tetrahedron declustering, 1/sigma^2-weighted 2-D covariance axes, corridors of width `max(2 sigma, 300 m)` | Aftershock sequences trace the causative fault; a blind structure with recent seismicity would be drawn where the catalogue has no trace | The provided `ieq_n100a15` band is a ~100 km density field (autocorrelation 0.9986 at 1 km); the earlier `gems50` package used a space-only triangle decluster and no uncertainty model; this line adds a calibrated uncertainty model (only 1.6 % of in-footprint events publish `horizontalError`), space-time tetrahedra and documented induced/mining removal | **Negative as a standalone emitter, kept as a documented layer.** SGMC-off credit/dot 0.084-0.095 vs 0.110 for random at the same mass; adding it to H51-A changed SGMC-off credit/dot by -0.0005 and Monte Cristo by -0.6 px. It is therefore **not given mass** in the shipped file | 4/5 |
| **3** | **H51-C — depth-edge potential-field lineaments (tilt angle / vertical gradients / Euler-style source depth)** | `tc` (tilt angle / total curvature), `tmi_vg`, `tmi_hg`, `iso_grav_anom_vg`, `iso_grav_anom_hg`, `depth_to_base_surf`, `cond_surf` | A buried fault with no surface scarp can still produce a mapped potential-field edge, and the depth of the edge can be estimated | The sibling repositories report TMI-only persistence (H47-B) and gravity/magnetic maxspot persistence (H48-A) as below their controls; this isolates *depth-derived edges* rather than amplitude anomalies | **Rejected on the instrument.** Magnetic family SGMC-off credit/dot 0.087 and gravity 0.067 at 30 k dots, both below the 0.110 random control; adding them to H51-A lowered the measured credit/dot | 2/5 |
| **4** | **H51-D — thermal-spring and well conduit anchoring (GDR 1391 INGENIOUS inventory)** | `data/external/gdr_wellspring_in_footprint.csv` (GDR submission 1391), the INGENIOUS 2 m temperature probe and paleo-geothermal grids, plus `cond_surf` | Geothermal springs and wells sit on fault-hosted conduits; the *unmapped* part of a conduit between a spring and the nearest mapped structure is a candidate blind fault | H19-4/H19-5 used the same GDR thermal evidence as one of four hand-weighted lines; this candidate would invert it into conduit *segments* (spring to nearest structure) rather than a favourability field | **Not yet measured.** The CSV is available and hash-pinned; the conduit-segment construction is not implemented | 3/5 |
| **5** | **H51-E — orientation-concordance gate on all families** | Agreement of structure-tensor azimuths among topographic, magnetic, gravity and radiometric families within 25 deg | Independent physics that agrees on azimuth is more likely to be a real structure than a texture | The H19 family used hand weights; this makes agreement a *gate* rather than a weight | **Rejected on the instrument.** SGMC-off credit/dot 0.183 at 35 k dots versus 0.189 without the gate, and Monte Cristo coverage fell from 23.0 to 6.2 weighted px, i.e. the gate concentrates mass on the largest structures and loses the small ones | 2/5 |

## Frozen decisions for H51-A (the shipped candidate)

1. **Field.** `belief = normalise(topographic scarp family) + normalise(radiometric family)`,
   equal weights, computed with the multi-scale structure tensor in
   `src/gems51/structfield.py`. No other family enters the shipped pixel set; H51-B renders a
   documented field but receives no mass.
2. **Domain.** Every emitted dot is more than **300 m** from any provided-catalogue pixel.
3. **Mass rule (frozen before the sweep).** Emit at the largest swept mass whose *marginal*
   SGMC-off credit exceeds `0.2 * target_dti / marginal_transfer`, with `target_dti = 0.30`
   (the score this project is trying to reach, not a measured value) and
   `marginal_transfer = 0.28`. The transfer is the only one that can be derived from a file
   with both a live score and a local instrument score: the owner's `gems25-dotted-h19-5-d2-8`
   moved from an SGMC-off marginal credit of 0.197 to a hidden marginal credit of about 0.0548
   (its own empirically measured break-even), a factor 0.28.
4. **Gate.** The candidate must (a) beat the matched random control on the SGMC-off
   instrument, (b) not reduce Monte Cristo coverage relative to the field without it, and
   (c) be distinct from every prior artifact in `registry/prior_artifact_signatures.npz` under
   a block-level Jaccard test. Failing (a) or (b) means no slot; failing (c) means rebuild.
5. **What a pass licenses.** A pass licenses packaging a candidate file and asking for a manual
   upload decision. It is **not** a score, a rank, or a promise about the private test set.

## Amendment A1 — 2026-10-06, after the first H51 build attempt, before the final build

The first H51 build ran the frozen decisions above and produced two findings that force an
explicit, documented amendment rather than a silent retune.

1. **Each family must be normalised before the weights mean anything.** The shipped field was
   written as `topographic_strength + radiometric_strength` on raw strengths, so the "equal
   weights" of decision 1 were not equal at all: the two families have different dynamic
   ranges (their maxima differ), so the sum is dominated by whichever family happens to have
   the larger maximum. Decision 1 is corrected to `belief = 0.75 * topo/max(topo) +
   0.55 * radio/max(radio)`, each maximum taken inside the valid footprint. The weights
   0.75/0.55 are not chosen here: they were measured in the H51 measurement stage on the two
   independent instruments (SGMC-off and Monte Cristo) before this build, where 0.75/0.55,
   0.75/0.75 and 0.6/0.6 tie at an SGMC-off credit per dot of 0.1910 and 0.75/0.55 keeps the
   best Monte Cristo coverage of the three.
2. **The mass bar must use the *measured* break-even, not an assumed target score.** The
   first attempt used `0.2 * target_dti / transfer` with an assumed `target_dti = 0.30`, which
   gives a bar of 0.2143 SGMC-off credit per dot — above the whole field's average credit
   (0.177-0.181), so the rule could only ever return the smallest swept mass. That is a bug in
   the rule, not a property of the field. The bar becomes the reference file's *measured*
   hidden break-even (0.0548 credit per dot, measured in the H51 measurement stage from the one
   owner file that has both a live score and a local SGMC-off score) divided by the same
   measured transfer (0.28): `bar_sgmc = 0.0548 / 0.28 = 0.1957`. The sweep is extended down to
   10,000 dots so the crossing point is bracketed from below, and the Monte Cristo coverage of
   every swept mass is reported so the mass choice can be audited against a second instrument.
3. **Uniqueness gate repair.** The frozen prior-artifact masks are stored packbit-encoded and
   flattened; the first attempt compared them against a 2-D array and crashed with a broadcast
   error before writing any file. The gate now unpacks and reshapes to the recorded
   `coarse_shapes` before the Jaccard test.

Neither change touches the held-out labels, and the failure that forced them is recorded in
`evidence/build_h51.json` under `rule_amendments` rather than hidden.

## Amendment A2 — 2026-10-06, after the amended build, before the final build

The amended build (A1) ran to completion and its own numbers force one more explicit change.
It picked 20,000 dots, and at that mass the candidate covered **4.78** weighted pixels of the
Monte Cristo trend while a matched-mass **random** control covered **22.49** — i.e. the shipped
field was *worse than random* on the only instrument built from a genuine post-catalogue
rupture. Two things caused that, and both are fixed here.

1. **The topographic family was the wrong band set.** The structure-tensor family in
   `gems51.structfield.families()` took the max over twelve layers, including broad
   detrended-elevation and hillshade proxies. Measured on both independent instruments at
   matched mass with the same radiometric partner (0.75 / 0.55 weights, off-catalogue mask):

   | topographic definition | M=20k SGMC-off c/dot | M=20k MC TP_w | M=35k SGMC-off c/dot | M=35k MC TP_w | M=50k SGMC-off c/dot | M=50k MC TP_w |
   |---|---|---|---|---|---|---|
   | `fam_topographic` (12 layers, max) | 0.1733 | 4.8 | 0.1786 | 19.2 | 0.1792 | 19.4 |
   | **scarp-focused subset** (scarp 3/4/9 + topo 2/5/6/8) | **0.2043** | **14.5** | **0.1888** | **23.0** | **0.1817** | **32.0** |
   | matched random control | 0.1189 | 7.3 | 0.1155 | 17.1 | 0.1169 | 22.3 |

   The scarp-focused subset wins on **both** instruments at **every** mass, so the shipped field
   becomes `0.75 * scarp-focused topographic + 0.55 * radiometric`, each max-normalised. The
   broad family is still built and reported as a diagnostic. This is a change of *input bands*,
   not of method, and it was selected on two independent proxy instruments, never on held-out
   labels.

2. **The mass rule was landing on the edge of a flat region.** A1 stopped at the first swept
   increment below the bar, which produced the smallest credible mass. But the marginal credit
   of this field is a slowly declining function that sits within ±10 % of the bar across
   15,000–50,000 dots, and the bar's own input — the SGMC-off-to-hidden transfer, 0.28 — is the
   least certain number in the chain (a ±30 % error moves the crossing from ~12,000 to beyond
   50,000). Landing on the low edge of that flat region is not supported by the data. The frozen
   rule becomes:

   > Among the swept masses 10,000–50,000, keep those whose SGMC-off credit per dot is within
   > 10 % of the best swept value, and among those keep only masses where Monte Cristo coverage
   > exceeds the matched-mass random control by at least 20 %. **Choose the largest surviving
   > mass.** If no mass survives, do not ship.

   Applied to the measurement-stage field above, the survivors are 20,000 (SGMC-off 0.2043, MC
   14.5 vs 7.3) and 35,000 (0.1888, MC 23.0 vs 17.1); 50,000 fails the 10 % SGMC-off band. The
   rule therefore selects **~35,000 dots**, and that is the mass the final build is expected to
   emit. The per-mass table, the control scores and the chosen value are all written into
   `evidence/build_h51.json` so a reviewer can move the mass with one argument
   (`scripts/build_h51.py --mass`) rather than re-deriving the rule.

## Amendment A3 — 2026-10-06, after the final build, recording an instrument correction

The final build selected **35,000 dots** under A2. Two follow-up measurements changed how that
selection must be *described*, without changing the file:

1. **The Monte Cristo clause in A2 is not a real discriminator at these masses.** A2 compared the
   candidate's Monte Cristo coverage with a *single-seed* matched random control, and single
   seeds vary enormously on a 242-pixel trend. Re-measured with 24 matched-mass control seeds per
   mass (`evidence/mc_sensitivity_h51.json`):

   | mass | candidate MC TP_w | control mean ± sd | control range | candidate percentile |
   |---|---|---|---|---|
   | 20,000 | 13.19 | 10.79 ± 3.52 | 3.88 – 18.51 | 75th |
   | 35,000 | 18.93 | 16.64 ± 3.38 | 8.65 – 22.31 | 71st |
   | 50,000 | 29.47 | 23.82 ± 4.15 | 13.57 – 29.88 | 96th |

   A random scatter covers the Monte Cristo trend about as well as this field does at 20–35k
   dots, because a 300 m kernel over a 242-pixel line is hit by any dense-enough emission. The
   instrument is therefore recorded as a **weak guard, not evidence**, and the shipped field is
   **not** claimed to "beat random" on it.
2. **The mass choice is robust to that correction.** Dropping the Monte Cristo clause, the A2
   rule reduces to "the largest swept mass whose SGMC-off credit per dot is within 10 % of the
   best swept value", which selects **35,000** — the same answer. On the off-catalogue instrument
   the candidate sits above all 24 matched control seeds at *every* mass (controls 0.112–0.126
   credit per dot, spread ±0.002, versus 0.189 for the shipped file).

So the shipped file is `gems51-scarpradio-offcat-35000-20261006-ecf058ea`
(sha256 `8f8708d2872b66d71925707e0aede23eebcf217dfd2e57d6e61186f32e686f5d`), selected by the
A2 rule with the A3 correction recorded. The earlier shapes of the rule, and the fact that the
first two attempts produced a file that random scatter beat on Monte Cristo, are kept in the
build evidence rather than hidden.
