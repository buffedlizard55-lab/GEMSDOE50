# Historical H51 analysis — legacy score model, superseded decision

> **SUPERSEDED (2026-10-07): do not use this document as current upload advice.** Sections 13–14 contain an older H51 slot recommendation that is withdrawn. H51 artifacts are historical only; the current H53-A experiment is NO-GO / NO SLOT. The values below are local models or historical score claims, not organizer receipts. See the current [README](../../README.md), [H53 results](../../results.html), and [H33 score review](h33-score-review-20261007.md).

Verification labels follow `docs/research/score-model.md`: **[OFFICIAL]** read from an organizer
source, **[MEASURED]** computed here from hash-pinned bytes, **[MODEL]** arithmetic under stated
assumptions, **[INFERENCE]** a conclusion drawn from measurements, **[LIMIT]** a known weakness.
The scores quoted below are **owner-reported historical values recorded in sibling-repository registries**;
file hashes identify local TIFF bytes but do not authenticate a score-to-file link or an organizer receipt.
They are not asserted to be the current leaderboard, and this project does not scrape or poll the board.
Historical values such as `0.3195`, `0.3774`, and `0.3220` remain user/owner-provided snapshots, not live reads.

---

## 1. What is being scored [OFFICIAL]

```
k(d)  = max(1 − d/300 m, 0)                      (the support is 300 m = 3 px at 100 m)
TP_w  = Σ_{g∈G} max_{x} p(x)·k(d(x,g))           credit captured by the prediction
FP_w  = Σ_{x:p>0} p(x)·[1 − max_{g} k(d(x,g))]   unmatched prediction mass
FN_w  = Σ_{g∈G} [1 − max_{x} p(x)·k(d(x,g))]
DTI   = TP_w / (TP_w + 0.2·FP_w + 0.8·FN_w)
```

Two exact consequences drive everything below.

* **Identity.** The same `max` appears in `TP_w` and `FN_w`, so `TP_w + FN_w = |G|` exactly, and
  with binary predictions (`p = 1` on dots, `N` dots, `M = MPw = Σ_dots max_g k`)

  ```
  DTI = T / (0.2·(N − M + T) + 0.8·G)                                         (1)
  ```

* **Marginal-inclusion rule.** A dot that is the unique maximiser for one truth pixel adds `k` to
  `T` and `0.2` to the denominator (net of its own matched mass), so it pays only if its kernel
  credit beats `0.2·s`. At `s ≈ 0.2` that is `0.04` credit per dot — i.e. a dot must sit within
  ~290 m of a *hidden* truth pixel to be worth spending. **[MODEL]**

Known USGS/INGENIOUS faults are masked out of evaluation, so dots on mapped faults are free and
worthless. **[OFFICIAL]** Everything therefore turns on the hidden truth mass `G`.

## 2. Conditional model of hidden truth mass [MODEL; inputs unverified]

The earlier analysis used a sibling-repository record describing `GEMSDOE13` as a spacing-5 px
lattice with `N = 204,504` dots and an owner-quoted `s = 0.0904`. This review does not authenticate
that score, its receipt, or its mapping to the raster. For a unit lattice of spacing `s_px`, the
model assumes every truth pixel has the same *ensemble* kernel credit `c`, with `M = c·G`; under
those assumptions, equation (1) collapses to

```
s = c·G / (0.2·N + 0.8·G)        ⇒        G = 0.2·N·s / (c − 0.8·s)            (2)
```

with `c = 0.37481` the modelled mean kernel credit over the lattice's fundamental cell. If the
recorded inputs and simplifying assumptions are accepted, substitution yields

```
G_model = 0.2 · 204,504 · 0.0904 / (0.37481 − 0.8 · 0.0904) = 12,226 px   (±~1%, cell-integration only)
```

This is a **conditional model output, not a measurement of the private test's truth mass**. It would
correspond to about 0.24% of a 5.1 M-pixel unmasked footprint, or roughly 1,200 km of 100 m-wide
trace, only if its inputs and assumptions held. The older analysis also compared model-derived
credits for other corpus entries and found internal numerical agreement. Those entries share the
same unverified owner/sibling provenance and are not independent organizer receipts, so this is not
external validation of `G_model`.

## 3. What the old model implies about coverage [conditional model]

Solving (1) for the credit `T` a given score would require, under this model and its assumed
`ρ = M/T = 1.188` ratio for dense corridor designs:

```
T_req(s, N) = s·(0.2·N + 0.8·G) / (1 − 0.2·s·(1 − ρ))                        (3)
```

The score-input column is a mixture of a local H51 model output and historical owner/sibling-corpus
records. None of the latter is independently authenticated here; in particular, the pinned H33-2-B2
audit labels its run UNSCORED and reports a projection rather than an organizer receipt. This table
is scenario arithmetic, not an estimate of actual hidden-truth coverage.

| artifact / target | N (dots) | score input (provenance unverified) | model-required `T` | model-required coverage `T/G` |
| --- | ---: | ---: | ---: | ---: |
| GEMSDOE9 placeholder | 343,816 | 0.0107, corpus-recorded | 1,008 | 8 % |
| GEMSDOE4 combined | 264,247 | 0.0343, corpus-recorded | 2,361 | 19 % |
| **H51 candidate** | **30,000** | **0.1684, local model output** | **2,641** | **21.6 %** |
| gems25 dotted h19-5 d2.8 | 44,090 | 0.2600, corpus-recorded | 4,788 | 39.2 % |
| **H33-2-B2 (user-provided score claim; pinned audit says UNSCORED)** | **37,654** | **0.2778, unauthenticated** | **4,759** | **38.9 %** |
| owner-quoted DARD target | 30,000 (assumed) | 0.3195, unverified | 4,982 | 40.7 % |
| owner-provided claimed high score | 42,000 (assumed) | 0.3774, unverified | 6,764 | 55.3 % |

The `N` values in the last two rows are assumptions, and their scores are claims rather than verified
leaderboard values. Within this model only, a higher DTI at fixed truth mass requires either more
credit or a more efficient prediction mass. The calculation does not establish that the actual
hidden test has `G = 12,226` pixels, that the score claims are valid, or that any listed strategy
would achieve its modeled coverage.

**Could pruning explain the user-provided 0.2778 H33-2-B2 claim? [PLAUSIBLE, NOT VERIFIED]** The
pinned sibling audit describes removing 2,545 catalogue-near dots from a 40,199-dot parent, leaving
37,654. Under the binary-dot DTI formula, removing predictions with very low marginal truth credit
can improve the score by reducing denominator mass. That is a plausible mechanism, not a verified
explanation: the 0.2778 itself is unauthenticated, the pinned audit labels the run UNSCORED, the
score-to-TIFF mapping and receipt are missing, and no paired organizer-scored before/after comparison
is available. Removing dots could also discard useful credit. The current caveated analysis is in
[`h33-score-review-20261007.md`](h33-score-review-20261007.md).

**Could a strategy exceed the user-provided 0.3774 high-score claim?** Mathematically, a higher DTI is
possible, but the claim has not been independently verified as the current leaderboard high and this
historical model cannot predict hidden-test performance. The conditional calculations above do not
establish a winning route. H53-A failed its blocked holdout, and no strategy in this repository is
validated as exceeding 0.3774.

## 4. The H51 score instrument and its limits [historical fit]

`registry/h51_score_corpus.json` pins 25 raster artifacts whose hashes match local registry rows
associated with owner-reported score values (recorded range 0.0107 … 0.2600 in sibling/public
repositories). This review did not authenticate organizer receipts or the score-to-TIFF mapping.
For each artifact the metric's fields are computed (`M_a` matched mass, `C_a` credit delivered), a
posterior is formed as `q ∝ Σ_a exp(s_a/τ)·S_a` (`τ = 0.05`), and the instrument fits each recorded
score from `(T, M, N)` under (1) with `q` as the assumed truth density. Leave-one-out:

```
Spearman(corpus-recorded, fitted) = +0.973   (p = 3.7e-16, n = 25)
Pearson                           = +0.949     MAE = 0.0192     RMSE = 0.0248
```

These are internal leave-one-out fit statistics on one corpus, not independent calibration against
verified organizer scores. At most, the instrument summarizes where the historical corpus recorded
its score-associated pixels; because its posterior is a kernel density of where those dots occur:

* **It can price "where the group already looks".** Its optimum over the unrestricted domain is
  `0.2559` at `N = 42,000` — and 94 % of those dots land on pixels a prior artifact already used.
  Optimising it reproduces the corpus; that is its ceiling, and it matches the observed plateau.
* **It cannot price genuinely new territory.** `q ≈ 0` anywhere a prior artifact never dotted, so
  a new fault found in unexplored ground scores zero on the instrument until *after* it has been
  submitted. This is a structural limit, not a fitting failure, and it is why the instrument alone
  cannot certify a hypothesis that is supposed to find something nobody has found.

## 5. What the shipped candidate is, and what it is not [MEASURED]

`downloads/gemsdoe50-h51-corridor-consensus-mix-20261007T0200Z.tif` (SHA-256 in
`evidence/h51_ship.json`), 30,000 dots:

| component | dots | domain | basis |
| --- | ---: | --- | --- |
| core | 24,000 | ≤200 m from a prior dot, on pixels no prior artifact used | H51 consensus posterior (best validated predictor) |
| exploration | 6,000 | >200 m from **every** prior dot, on pixels no prior artifact used | seismicity corridors + TMI magnetic ridges + radiometric-K ridges + hot-spring alignment |

* Frozen format gate: **PASS** (`all_checks_pass`, values exactly {0,1}, NaN only outside the
  published footprint, EPSG:32611, 3292×3730, transform and bounds identical to the template).
* Frozen uniqueness gate (`scripts/check_submission.py`, 200 m-proximity IoU < 0.5):
  **PASS** at `0.422` worst-case against `gems25-dotted-h19-5-d2-8`; **zero pixels shared with any
  of the 26 prior artifacts**; 20 % of dots are >200 m from even the closest prior family.
* Instrument prediction: **0.1684** (`T = 2,641`, `M = 3,138`). The exploration dots are priced at
  ~zero by the instrument by construction (section 4), and they cost ~0.012 of predicted score
  relative to a 24 k-dot exploration-free design (`0.1806`).
* Proxy frames: `sgmc_off` DTI 0.0642, below the matched uniform control 0.0704 — the candidate
  **failed the then-used H51 proxy gate**. That gate was not usable here: on the same
  frame, the proxy's rank correlation with 25 owner/sibling-corpus score records was only
  `ρ = +0.196` (p = 0.35) (`evidence/h51_proxy_ranking_power.json`), and it ranked a 264 k-dot
  artifact at 0.224 against a corpus-recorded 0.034. Neither value is independently authenticated
  as an organizer score. **[LIMIT — recorded, not explained away.]**

Consequences, stated plainly:

* The candidate was **format-checked and pixel-novel under the archived audit**; the old instrument
  selected it as its preferred design. Those are historical artifact-level checks, not evidence of
  competition performance or permission to submit it.
* The legacy instrument's modeled DTI is **≈0.17 (LOO RMSE 0.025)**. This is not an expected
  leaderboard score. It is numerically below the user-provided 0.2778 H33 value and owner-quoted
  0.3195 target, both unauthenticated here and not mapped to a verified organizer receipt. No
  submission was made to test whether the consensus-core placement transfers.
* The old H51 slot recommendation is withdrawn. Its proxy gate did not establish transfer to hidden
  labels, and it is not the current promotion gate. The current experiment is H53-A **NO-GO / NO
  SLOT**; see the current project overview and frozen H53 protocol.

## 6. Historical H51 hypotheses (superseded; not the current ranking)

The rows below are old proposals, not a live ranking or slot recommendation. The current four-way
ranking, with layers, physical signature, novelty, expected DTI direction, cost, source, and licence
needs, is in `docs/research/h53-hypotheses-20261007.md`. Every association and ΔDTI below is
corpus-internal or a historical hypothesis estimate based on unverified score/file records; none is a
current forecast or a validated route to the hidden test.

| rank | hypothesis | why it could raise `T` | expected ΔDTI | cost |
| ---: | --- | --- | ---: | --- |
| 1 | **Magnetic-lineament corridors** on upward-continued TMI + K/Th/U gradients, sensor-height-corrected | the only layer with a positive, robust score association in this corpus (ρ = +0.57, partial +0.53, p = 0.006); the corpus spends only 5 % of its dots there | +0.02 … +0.06 if a strand is hit | medium |
| 2 | **Cross-layer lineament conjunction** (magnetic ∩ radiometric ∩ scarp ridge ∩ spring alignment), scored by conjunction order, not by any single layer | independent evidence for the *same* line raises precision, which is what the marginal rule needs | +0.01 … +0.04 | medium |
| 3 | **Basin-margin relay/step-over geometry**: terminations and overlapping fault tips of *existing* ranges | unmapped transfer faults live at relay zones; catalogue inventories under-map them systematically | +0.005 … +0.03 | low |
| 4 | **1 m LiDAR scarp curvature** (curvature/roughness, not amplitude quantiles) | resolves scarps too short/small for the 30 m DEM products used so far | unknown, unvalidated | high (needs new data) |
| 5 | **InSAR/GNSS strain-rate lineaments** | persistent aseismic creep marks active traces | unknown | high (needs new data) |

## 7. Limitations

1. **No organizer score exists for the shipped file.** Every number here is local. The instrument
   was fitted against 25 owner/sibling-corpus score records; their receipt provenance and mapping to
   the underlying TIFFs were not independently verified in this review (section 4).
2. **`G = 12,226` rests on the uniform-cell assumption** for the blind lattice's mean credit `c`;
   an adversarial spatial arrangement of truth could move it by several percent. It is a working
   constant, not an organizer figure.
3. **The corpus is one group's artifact family**, not a random sample of the competition; its
   mutual agreement may encode shared method bias. The instrument's high LOO score partly measures
   that agreement.
4. **The historical H51 proxy gate was not a valid promotion gate** (section 5). Its results are
   retained for audit only; they neither authorize a slot nor define the current test. H53-A's
   separate preregistered holdout failed, so the current decision remains NO-GO / NO SLOT.
5. **Exploration was unpriced.** The 6,000 exploration dots were a hypothesis, not a validated
   contribution. The original H51 recommendation is withdrawn; do not infer efficacy from it.
6. **Leaderboard values are historical.** No live leaderboard value, rank, or competitor name is
   asserted anywhere in this repository; the DrivenData Terms of Use forbid automated monitoring.

---

## 8. Conditional inversion of the historical corpus [MODEL; inputs unverified]

If the conditional `G_model = 12,226` from §2 and the owner/sibling-reported score values were all
valid, each artifact's implied credit would follow from `T = s·(0.2·N + 0.8·G)`. Applying that
algebra to the 25 hash-verified raster files (`scripts/h51_truth_map.py`,
`evidence/h51_truth_map.json`) gives the table below. The raster hashes do not authenticate organizer
scores or their mapping to those files. `T/N` and `T/G` are therefore model-derived values, not
measured hidden-truth credit or coverage.

| artifact (family) | corpus-recorded score (unverified) | N | model-implied `T` | model `T/N` | model `T/G` |
| --- | ---: | ---: | ---: | ---: | ---: |
| dotted-h19-5 **d2.8** | 0.2600 | 44,090 | **4,836** | **0.1097** | 0.396 |
| dotted-h19-5 d1.5 | 0.2477 | 60,069 | 5,399 | 0.0899 | 0.442 |
| topo-gap-closure on d1.5 | 0.2449 | 61,328 | 5,399 | 0.0880 | 0.442 |
| h19-5 mirror "group-best" | 0.1922 | 121,131 | 6,536 | 0.0540 | 0.535 |
| h19-4 multiline-corroborated | 0.1894 | 123,779 | 6,541 | 0.0528 | 0.535 |
| h16-1 topo-geophys ridges | 0.1855 | 123,939 | 6,413 | 0.0517 | 0.524 |
| h28 dotted-ridge | 0.1839 | 69,281 | 4,347 | 0.0627 | 0.356 |
| dual-union | 0.1560 | 183,642 | **7,255** | 0.0395 | **0.593** |
| blind lattice s5 | 0.0904 | 206,895 | 4,625 | 0.0224 | 0.378 |

These are three conclusions of the *conditional model*, not facts about hidden truth or contest performance.

* **Model-implied corpus maximum credit per dot is 0.1097.** This describes the transformed records
  only, assuming the score/file mappings and `G_model` are correct; it does not show what a new
  submission can achieve.
* **Model-implied maximum coverage is 0.593** for the recorded 183,642-dot row. It does not establish
  that 41% of actual hidden truth is unreachable, nor that 0.3195 is impossible by blending. The old
  posterior has no validated ability to predict new territory.
* **Conditional nested-family arithmetic.** If `d2.8 ⊂ d1.5 ≈ topo-gap ⊂ mirror` and all input scores
  are correct, the *differences* imply `44,090 → 60,069` earns `(5,399 − 4,836)/15,979 = 0.0352`
  per dot, and `44,090 → 121,131` earns `(6,536 − 4,836)/77,041 = 0.0221` per dot. This is below
  the modelled marginal cost `0.2·s = 0.052`; it motivates a pruning hypothesis, but does not prove
  that pruning a specific H33 file caused a verified score change.

## 9. Conditional DTI arithmetic at the historical targets [MODEL, not feasibility]

Under `G_model = 12,226`, the formula `DTI = T/(0.2·N + 0.8·G)` gives the following arithmetic at
`N = 30,000` dots. Targets and historical score inputs are unverified; these calculations do not show
that any value is a real leaderboard score or an achievable prediction:

| hypothetical target / historical model input | model-required `T` | model-required `T/G` |
| --- | ---: | ---: |
| 0.1684 (H51 local instrument output) | 2,657 | 21.7 % |
| 0.2600 (corpus-recorded value; unverified) | 4,103 | 33.6 % |
| 0.2778 (user-provided H33-2-B2 claim; unverified) | 4,384 | 35.9 % |
| **0.3195 (owner-quoted historical target; unverified)** | **5,042** | **41.2 %** |
| 0.3774 (user-provided current-high claim; not independently checked) | 5,955 | 48.7 % |

At the historical champion budget (`N = 44,090`), the same assumptions yield `T = 5,726` for
0.3195 and `T = 6,738` for 0.3774. This is arithmetic conditional on an unverified `G_model`, not
evidence of reachability or a bound on an actual candidate. The earlier conclusion that a particular
score was reachable or unreachable by re-blending is withdrawn; H53-A failed and this corpus model
does not establish a strategy that exceeds 0.3774.

## 10. Internal diagnostics of the historical instrument [same-corpus tests]

Two diagnostics were run against the same unverified owner/sibling score corpus to limit §4's claims.
They do not validate organizer score provenance or prediction outside that corpus.

* **Trivial similarity predictor.** Predict each artifact's score as the IoU-weighted mean of the
  other 24 (`Spearman +0.905`, `RMSE 0.0296`, `MAE 0.0207`) versus the consensus instrument's LOO
  (`+0.973`, `0.0248`, `0.0192`). The median pairwise exact-pixel IoU in the corpus is only
  **0.031**, so this is not near-duplication — but a predictor that uses *no spatial information
  at all* beyond "how similar is this to higher owner-reported-score entries" already reaches ρ = 0.91. **Most of the
  instrument's apparent skill is corpus self-similarity**, and its confident pricing of designs
  outside the corpus's span (e.g. `0.0422` for the repository's own `seislin` artifact) is *not*
  out-of-sample validated.
* **Truth-density inversion.** `scripts/h51_truth_map.py` discretises the domain into 4²…32²
  blocks and solves `T_a = Σ_c R_ac·φ_c` for non-negative `φ` with a Laplacian penalty, then tests
  it leave-one-artifact-out in `evidence/h51_truth_map.json`. On the historical inputs, LOO
  `RMSE(T) = 1,923 … 2,353` versus 1,920 for the corpus-mean baseline; fitted total mass is
  3.2×10⁴ … 3.4×10⁵ versus the conditional `G_model ≈ 1.2×10⁴`. These internally derived targets did
  not localise a stable pattern from the recorded corpus. They do not measure or locate actual hidden
  truth because the score inputs and mapping are unverified.

Historical design implication only: the consensus instrument assigns mass where its corpus has
pixels and has no validated basis for extrapolating to new territory. The H51 exploration layer was
therefore an unvalidated bet; this is one reason the old H51 slot recommendation is withdrawn.

## 11. Two different novelty rules, and why the pixel-level one is not enough [MEASURED]

The project tests novelty twice, and they are not equivalent.

| rule | test | shipped candidate | H52 halo interleave |
| --- | --- | --- | --- |
| pixel-level ("do not copy a prior submission's pixels") | exact-pixel intersection with the 26 prior artifacts | 0 px | 0 px |
| structure-level (frozen uniqueness gate) | max 2 px-proximity IoU, must be < 0.5 | **0.422 PASS** | **0.678 FAIL** |

`scripts/h51_ship_novel.py` builds the strongest design that satisfies the *pixel-level* rule
alone: belief `q`, domain = allowed minus every prior pixel, 42,500 dots, per-dot 2.8 px separation,
`n = 42,500`, `T = 3,598`, instrument `0.1989` — higher than the shipped candidate's 0.1684. It is
**rejected**: 98.3 % of its dots lie within 2 px of the `d2.8` artifact's dots, i.e. it closely
reproduces a structure associated with a higher owner-reported score in the historical corpus. Evidence and the rejection are recorded in
`evidence/h51_ship_novel.json`; the artifact was deleted so that the site offers one download.

## 12. The unresolved instrument conflict (recorded, not resolved) [LIMIT]

On the independent `sgmc_off` frame (a mapped off-catalogue inventory, 62,122 px in that historical
run), the archived `seislin-44709` artifact reaches `DTI 0.1464`, above every corpus-recorded scored
artifact (best recorded value 0.1113) and 2.5× the matched uniform control, while the H51 candidate
reaches 0.0573 — below uniform (0.0593). These score records are not independently authenticated
organizer receipts. The same proxy's association with corpus-recorded scores was only ρ = +0.196
(p = 0.35), so it has no demonstrated power to predict a hidden score. The conflict is unresolved:
**the archived corpus and the local proxy point in opposite directions about where to place dots**.
That uncertainty is a reason not to promote H51 or spend a slot; the H51 recommendation is withdrawn
and the current H53-A decision is NO-GO / NO SLOT.

## 13. Historical decision record (withdrawn; not current slot guidance)

| option | instrument | frozen uniqueness gate | legacy model estimate | current status |
| --- | ---: | --- | --- | --- |
| **archived H51 mix** (24 k consensus core + 6 k evidence exploration) | 0.1684 | PASS (IoU 0.422) | ≈0.17 ± 0.03 | **not slot-eligible; recommendation withdrawn** |
| unconstrained instrument optimum (= corpus re-draw) | 0.2559 | FAIL (98 % on prior pixels) | ≈0.26 | forbidden by the novelty rule |
| H52 pixel-disjoint halo interleave | 0.1989 | FAIL (IoU 0.678) | ≈0.20 | rejected as a shifted copy |
| exploration-free core (24 k, no far dots) | 0.1806 | PASS (IoU ≈0.48, thin margin) | ≈0.19 | dominated on the key axis: no new territory |
| archived `seislin-44709` (incumbent) | 0.0422 | cannot be resubmitted | unknown | comparator only |

The recommendation recorded in the original version of this section is withdrawn. Neither H51 file
is eligible for a current weekly slot: the shared-frame comparison is a local proxy only, the H51
control comparison did not clear its matched control, and the newer H53-A experiment is explicitly
NO-GO / NO SLOT. No upload or score should be inferred from this historical analysis.

The shared-frame measurement added on 2026-10-07 placed the parallel-session
`gems51-scarpradio-offcat` file above the H51 mix on that one local proxy frame. That relative ordering
is preserved below as historical evidence only; it does not authorize a submission.

## 14. Cross-frame adjudication of the two in-repo candidates [MEASURED]

Sections 4–13 compare designs on *different* instruments: the consensus posterior prices an artifact
against the 25 scored artifacts' score history, the off-catalogue `sgmc_off` frame prices coverage of
USGS SGMC fault pixels that the given catalogue does not contain, and the 4-macrofold holdout prices
generalisation. Those currencies are not interchangeable, which is exactly the conflict recorded in
§12. One measurement can adjudicate, because the repository now holds two new candidate GeoTIFFs:

* **A** — `gemsdoe50-h51-corridor-consensus-mix-20261007T0200Z.tif` (this branch; 30,000 dots).
* **B** — `gems51-scarpradio-offcat-35000-20261006-ecf058ea-nan.tif` (parallel session; 35,000 dots).

Both were re-scored on one identical frame with identical code
(`python scripts/h51_validate.py --layers data/external --candidates A B`): unmasked domain of
5,106,385 px; truth = SGMC fault pixels more than 300 m from the given catalogue, 61,664 px
(1.208 %). Result (`evidence/h51_candidate_frame_compare.json`):

| file | dots | `sgmc_off` DTI | credit per dot | tp per dot |
| --- | ---: | ---: | ---: | ---: |
| A · corridor-consensus mix | 30,000 | 0.0566 | 0.00616 | 0.1050 |
| **B · scarp + radiometric lineaments** | 35,000 | **0.1158** | 0.00659 | **0.1889** |
| archived `gems50-seislin-44709` (reference only) | 44,709 | 0.1472 | 0.00879 | 0.1972 |
| matched uniform control at 30 k dots | 30,000 | 0.0592 mean / 0.0617 max | — | — |
| four translations of A | — | 0.0448 mean / 0.0472 max | — | — |

Readings that follow directly, with no extra assumptions:

1. **B is the stronger of the two new files, and A does not clear its own matched control**
   (0.0566 < 0.0592 mean, 0.0617 max). B beats every control on this frame by roughly 1.9×.
2. **The consensus instrument's ordering does not transfer.** It prices A at 0.1684 and the archived
   incumbent at only 0.0422, while on this frame the incumbent is 2.6× A. Combined with §10 (a
   trivial similarity predictor already reaches ρ 0.905 and the truth-density inversion fails), the
   parsimonious explanation is that the instrument prices *resemblance to the corpus*, and the corpus
   optimum is a re-draw of itself (§11) — a property that cannot create new off-catalogue coverage.
3. On this one frame, B scored above A, while A was below the matched uniform control. This
   describes a historical local-proxy ordering only; it does not establish which file is safer or
   better on the hidden expert-labeled test set.
4. **No slot is recommended for either file.** The older 4/4-fold comparison against a random control
   in `evidence/holdout_h51.json` is not the current incumbent-beating gate, does not establish
   organizer performance, and is superseded by the present NO SLOT decision.

Limitations of this adjudication, stated so it is not over-read: it is **one frame** (a single
variant of the SGMC mask at one clearance radius), it compares artifacts at different masses (30 k vs
35 k vs 44.7 k dots), and it cannot rank either file against the 25 scored artifacts, whose scores
come from the hidden expert labels. It is useful for preserving one narrow historical proxy comparison, but is not sufficient to order
current competition submissions or predict a leaderboard number.
