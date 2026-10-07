# H51 analysis — why 0.2778 topped the corpus, and what beating 0.3195 actually requires

Verification labels follow `docs/research/score-model.md`: **[OFFICIAL]** read from an organizer
source, **[MEASURED]** computed here from hash-pinned bytes, **[MODEL]** arithmetic under stated
assumptions, **[INFERENCE]** a conclusion drawn from measurements, **[LIMIT]** a known weakness.
Every score quoted below is an **owner-quoted public-leaderboard value at its own submission
date**, taken from the sibling repositories' registries and hash-matched to a file
(`registry/h51_score_corpus.json`); none of them is asserted to be the current leaderboard, and
this project does not scrape or poll the leaderboard. Historical values quoted in the charter
(`0.3195`, `0.3774`, `0.3220`) remain **owner-quoted historical snapshots**, not live reads.

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

## 2. The hidden truth mass is measurable in closed form [MEASURED + MODEL]

`GEMSDOE13`'s blind lattice artifact is a spacing-5 px lattice with `N = 204,504` dots, zero
structural information, owner-quoted score `s = 0.0904`. For a unit lattice of spacing `s_px`
every truth pixel has the same *ensemble* kernel credit `c`, and `M = c·G` as well, so (1)
collapses to

```
s = c·G / (0.2·N + 0.8·G)        ⇒        G = 0.2·N·s / (c − 0.8·s)            (2)
```

with `c = 0.37481` the mean kernel credit over the lattice's fundamental cell **[MODEL]**.
Substituting the measured values gives

```
G = 0.2 · 204,504 · 0.0904 / (0.37481 − 0.8 · 0.0904) = 12,226 px   (±~1%, cell-integration)
```

**The entire hidden test truth in the scored domain is about 12,200 pixels** — 0.24 % of the
5.1 M-pixel unmasked footprint, roughly 1,200 km of 100 m-wide trace. **[INFERENCE]** Two
independent cross-checks agree: the corpus's best artifact at `N = 44,090` requires `T = 4,788`
for `s = 0.2600` under (1), and the H51 consensus instrument's independent estimate of that same
artifact's `T` is `4,803` — a 0.3 % agreement. Three artefacts of different construction
(`h19-5` at 121 k dots, `h16-1` at 124 k, the lattice at 205 k) all reproduce (2) within 2 %.

## 3. Coverage is the whole game [MEASURED]

Solving (1) for the credit `T` a given score requires, with the measured
`ρ = M/T = 1.188` of dense corridor designs:

```
T_req(s, N) = s·(0.2·N + 0.8·G) / (1 − 0.2·s·(1 − ρ))                        (3)
```

| artifact / target | N (dots) | score | required `T` | required coverage `T/G` |
| --- | ---: | ---: | ---: | ---: |
| GEMSDOE9 placeholder | 343,816 | 0.0107 | 1,008 | 8 % |
| GEMSDOE4 combined | 264,247 | 0.0343 | 2,361 | 19 % |
| **H51 shipped candidate** | **30,000** | **0.1684 (pred)** | **2,641** | **21.6 %** |
| gems25 dotted h19-5 d2.8 | 44,090 | 0.2600 | 4,788 | 39.2 % |
| **gems32 h33-2-b2 (repository best)** | **37,654** | **0.2778** | **4,759** | **38.9 %** |
| owner-quoted DARD target | 30,000 (assumed) | 0.3195 | 4,982 | 40.7 % |
| owner-quoted leaderboard top | 42,000 (assumed) | 0.3774 | 6,764 | 55.3 % |

The `N` values in the last two rows are **assumptions** (those artifacts are not in the corpus);
the coverage column is the assumption-free statement: **every point of score above ~0.26 in this
competition corresponds to capturing a larger fraction of the same 12,226 hidden pixels.**

**Answer to the first question — why did 0.2778 score highest? [INFERENCE]** Because it captured
*the same* hidden truth as the 0.2600 artifact (`T = 4,759` vs `4,788`, a 0.6 % difference —
inside the metric's own discretisation) while spending **6,436 fewer dots**. From (1) the
denominator difference is `0.2 · 6,436 = 1,287`, which is exactly the observed score gap. Its win
was therefore **not geological**: it was dot economy — pruning redundant dots that sat inside the
300 m support of neighbours (its 2-px-pruned predecessor) without giving up credit. The same
mechanism explains the whole corpus's shape: the artifacts that reach 0.24–0.26 all capture 33–39 %
of the hidden truth, and their ordering follows `N` almost exactly (`Spearman(score, log10 N) =
−0.52`, p = 0.008).

**Answer to the second question — is a score above 0.3195 achievable? [INFERENCE]** Yes in
principle and no by any route in this repository's current evidence:

* The barrier is **+1,200–1,400 credit pixels** — i.e. one unmapped fault strand of ~40–60 km
  inside the scored domain, on top of everything the corpus already covers. It is not a tuning
  problem: the corpus's 25 artifacts already exhaust the blending space, and the H51 instrument's
  own optimum (a literal replica of the prior family) is `0.2559`.
* It is *not* a truth-availability problem: the lattice inversion shows 12,226 px exist, the best
  known capture is 39 %, and the owner-quoted top artifact implies ~50–55 % is reachable. Those
  pixels are findable; nobody in this corpus found them.
* The route is therefore **a genuinely different detector**, not a better-blended one. Section 6
  lists the five candidates, ranked.

## 4. The H51 score instrument and what it can and cannot price [MEASURED]

`registry/h51_score_corpus.json` pins 25 artifacts whose SHA-256 matches a registry row's
owner-quoted score (scores 0.0107 … 0.2600, all in `buffedlizard55-lab/*` public repos). For each
artifact the metric's own fields are computed (`M_a` matched mass, `C_a` credit delivered), a
posterior is formed as `q ∝ Σ_a exp(s_a/τ)·S_a` (`τ = 0.05`), and the instrument predicts each
artifact's score from `(T, M, N)` under (1) with `q` as the truth density. Leave-one-out:

```
Spearman(actual, predicted) = +0.973   (p = 3.7e-16, n = 25)
Pearson                    = +0.949     MAE = 0.0192     RMSE = 0.0248
```

**[INFERENCE]** The instrument is a calibrated *ranking* device — but its posterior is a kernel
density of where credit-earning dots have historically been, so:

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
  **fails the repository's pre-registered proxy gate**. That gate is not usable here: on the same
  frame, the proxy's rank correlation with the 25 real scores is only `ρ = +0.196` (p = 0.35)
  (`evidence/h51_proxy_ranking_power.json`), and it ranks a 264 k-dot artifact at 0.224 for an
  actual 0.034. **[LIMIT — recorded, not explained away.]**

Consequences, stated plainly:

* The candidate is **format-clean, pixel-novel, and the best-scoring design the validated
  instrument admits** — not a copy of anything, and the first H51 artifact to pass the frozen
  uniqueness gate.
* Its expected leaderboard score is **≈0.17 (LOO RMSE 0.025)**, i.e. **below** the repository's best
  delivered artifact (0.2778) and below the owner-quoted target (0.3195). It should be treated as a
  *measurement*, not as a competitive score: a submitted score would add a 26th row to the corpus
  and would test whether the consensus-core placement transfers.
* Because it fails the frozen proxy gate, the repository's own rule ("a hypothesis that does not
  beat the holdout incumbent is not slot-eligible") says **do not spend a weekly slot on it** until
  the owner decides otherwise. The site states this in the same place as the download.

## 6. Ranked hypotheses that could actually raise coverage

Full fields (layers, physical signature, off-catalogue argument, difference from prior work,
expected DTI, cost, source, licence, obtainability) are in `docs/research/h51-hypotheses.md`.

| rank | hypothesis | why it could raise `T` | expected ΔDTI | cost |
| ---: | --- | --- | ---: | --- |
| 1 | **Magnetic-lineament corridors** on upward-continued TMI + K/Th/U gradients, sensor-height-corrected | the only layer with a positive, robust score association in this corpus (ρ = +0.57, partial +0.53, p = 0.006); the corpus spends only 5 % of its dots there | +0.02 … +0.06 if a strand is hit | medium |
| 2 | **Cross-layer lineament conjunction** (magnetic ∩ radiometric ∩ scarp ridge ∩ spring alignment), scored by conjunction order, not by any single layer | independent evidence for the *same* line raises precision, which is what the marginal rule needs | +0.01 … +0.04 | medium |
| 3 | **Basin-margin relay/step-over geometry**: terminations and overlapping fault tips of *existing* ranges | unmapped transfer faults live at relay zones; catalogue inventories under-map them systematically | +0.005 … +0.03 | low |
| 4 | **1 m LiDAR scarp curvature** (curvature/roughness, not amplitude quantiles) | resolves scarps too short/small for the 30 m DEM products used so far | unknown, unvalidated | high (needs new data) |
| 5 | **InSAR/GNSS strain-rate lineaments** | persistent aseismic creep marks active traces | unknown | high (needs new data) |

## 7. Limitations

1. **No organizer score exists for the shipped file.** Every number here is local. The instrument
   is validated against 25 real public scores, but it is corpus-conditional (section 4).
2. **`G = 12,226` rests on the uniform-cell assumption** for the blind lattice's mean credit `c`;
   an adversarial spatial arrangement of truth could move it by several percent. It is a working
   constant, not an organizer figure.
3. **The corpus is one group's artifact family**, not a random sample of the competition; its
   mutual agreement may encode shared method bias. The instrument's high LOO score partly measures
   that agreement.
4. **The pre-registered proxy gate is unusable** (section 5). The repository needs a new gate: a
   candidate that beats the corpus's best on the instrument *and* survives a real submitted score.
5. **Exploration is unpriced.** The 6,000 exploration dots are a deliberate, documented bet on the
   corridor evidence; nothing local can validate them. This is stated on the site, not hidden.
6. **Leaderboard values are historical.** No live leaderboard value, rank, or competitor name is
   asserted anywhere in this repository; the DrivenData Terms of Use forbid automated monitoring.

---

## 8. The corpus ledger: every scored artifact inverted to credit pixels [MEASURED]

With `G = 12,226` (§2), each scored artifact's credit mass follows from its score alone:
`T = s·(0.2·N + 0.8·G)`. Inverting the 25 hash-verified artifacts
(`scripts/h51_truth_map.py`, `evidence/h51_truth_map.json`) gives the table below. `T/N` is the
**credit per dot** — the quantity the marginal rule of §1 prices at `0.2·s ≈ 0.05` — and `T/G` is
the fraction of the whole hidden truth the artifact reached.

| artifact (family) | score | N | T (credit px) | T/N | T/G |
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

Three facts follow, and they decide the whole strategy.

* **The corpus's maximum credit per dot is 0.1097.** No artifact in the group's history converts
  more than ~0.11 credit per predicted pixel, and the blind lattice converts 0.0224. A submission
  earns a prize-contending score only by pushing this number up, not by pushing `N` up.
* **The corpus's maximum coverage is 0.593** — reached only with 183,642 dots, at a credit per dot
  barely above blind. **Faults that this group's entire detector family cannot reach are ≈41 % of
  the hidden truth**, and they are the reason 0.3195 is not reachable by blending.
* **Nested-family marginal rates.** Because `d2.8 ⊂ d1.5 ≈ topo-gap ⊂ mirror` at the pixel level,
  the *differences* price the marginal dots: `44,090 → 60,069` earns
  `(5,399 − 4,836)/15,979 = 0.0352` per dot, and `44,090 → 121,131` earns
  `(6,536 − 4,836)/77,041 = 0.0221` per dot. Both are **below the marginal cost `0.2·s = 0.052`**
  (`∂DTI/∂N < 0` at the champion). The 0.2600 lattice is therefore already *past* its own
  family's optimum: a correctly pruned subset of the same structure should score higher. Nothing
  in the corpus scores a subset of `d2.8`, so the size of that gain is **not measurable locally**
  (§10, hypothesis P1).

## 9. What a 0.3195 submission requires, in credit pixels [MODEL]

`DTI = T/(0.2·N + 0.8·G)`, so at `N = 30,000` dots:

| target score | required `T` | required coverage `T/G` |
| ---: | ---: | ---: |
| 0.1684 (shipped candidate, instrument) | 2,657 | 21.7 % |
| 0.2600 (best scored artifact) | 4,103 | 33.6 % |
| 0.2778 (repository best) | 4,384 | 35.9 % |
| **0.3195 (owner-quoted target)** | **5,042** | **41.2 %** |
| 0.3774 (top of the recorded snapshot) | 5,955 | 48.7 % |

At the champion's own budget (`N = 44,090`) 0.3195 needs `T = 5,726`, i.e. **+19 % over the
champion's 4,836**, and 0.3774 needs `T = 6,738` (+39 %). Since the *whole corpus* tops out at
`T = 7,255` (with 4.2× the dots), the honest statement is:

> 0.3195 is reachable in principle — it needs about **1,200 credit pixels more than anything the
> group has measured**, roughly one 40–60 km unmapped strand inside the 300 m kernel — but it is
> **not reachable by re-blending, re-spacing or pruning the existing corpus**, because every
> design in that space is bounded by coverage 0.59 and credit/dot 0.11.

## 10. Instrument honesty: how much of the corpus actually constrains anything [MEASURED]

Two tests were run against the corpus to keep §4 from over-claiming.

* **Trivial similarity predictor.** Predict each artifact's score as the IoU-weighted mean of the
  other 24 (`Spearman +0.905`, `RMSE 0.0296`, `MAE 0.0207`) versus the consensus instrument's LOO
  (`+0.973`, `0.0248`, `0.0192`). The median pairwise exact-pixel IoU in the corpus is only
  **0.031**, so this is not near-duplication — but a predictor that uses *no spatial information
  at all* beyond "how similar is this to the winners" already reaches ρ = 0.91. **Most of the
  instrument's apparent skill is corpus self-similarity**, and its confident pricing of designs
  outside the corpus's span (e.g. `0.0422` for the repository's own `seislin` artifact) is *not*
  out-of-sample validated.
* **Truth-density inversion.** `scripts/h51_truth_map.py` discretises the scored domain into
  4²…32² blocks and solves `T_a = Σ_c R_ac·φ_c` for non-negative truth mass `φ` with a Laplacian
  penalty, then tests it leave-one-artifact-out in `evidence/h51_truth_map.json`. Result: LOO
  `RMSE(T) = 1,923 … 2,353` versus **1,920 for predicting every artifact with the corpus mean**,
  and fitted total mass 3.2×10⁴ … 3.4×10⁵ against the calibrated `G = 1.2×10⁴`. **The score
  history does not localise the hidden truth**; it constrains global efficiency (credit per dot),
  not geography. (This reproduces, with a stricter protocol, the negative result recorded in the
  sibling `GEMSDOE40` truth-inversion.)

Consequence for shipping: a candidate can be *placed* by the consensus instrument only where the
corpus already has dots; everywhere else the instrument is blind by construction. That is exactly
the 6,000-dot exploration layer of the shipped file, and it is why that layer is a documented bet
rather than a validated prediction.

## 11. Two different novelty rules, and why the pixel-level one is not enough [MEASURED]

The project tests novelty twice, and they are not equivalent.

| rule | test | shipped candidate | H52 halo interleave |
| --- | --- | --- | --- |
| pixel-level ("do not copy a prior submission's pixels") | exact-pixel intersection with the 26 prior artifacts | 0 px | 0 px |
| structure-level (frozen uniqueness gate) | max 2 px-proximity IoU, must be < 0.5 | **0.422 PASS** | **0.678 FAIL** |

`scripts/h51_ship_novel.py` builds the strongest design that satisfies the *pixel-level* rule
alone: belief `q`, domain = allowed minus every prior pixel, 42,500 dots, per-dot 2.8 px separation,
`n = 42,500`, `T = 3,598`, instrument `0.1989` — higher than the shipped candidate's 0.1684. It is
**rejected**: 98.3 % of its dots lie within 2 px of the `d2.8` artifact's dots, i.e. it is the
group's own winning structure translated by one pixel. Evidence and the rejection are recorded in
`evidence/h51_ship_novel.json`; the artifact was deleted so that the site offers one download.

## 12. The unresolved instrument conflict (recorded, not resolved) [LIMIT]

On the independent `sgmc_off` frame (a real off-catalogue fault inventory, 62,122 px in this run)
the repository's archived `seislin-44709` artifact reaches `DTI 0.1464`, above **every** scored
artifact in the corpus (best 0.1113) and 2.5× the matched uniform control, while the shipped
candidate reaches 0.0573 — *below* uniform (0.0593). The same proxy ranks the corpus's live scores
at ρ = +0.196 (p = 0.35), so it has no demonstrated power to predict a live score; but the conflict
is real and is not explained away here. It means: **the two independent bodies of evidence in this
repository point in opposite directions about where to place dots**, and the only clean way to
settle it is a submitted score (§13).

## 13. Decision record for the next slot

| option | instrument | frozen uniqueness gate | expected live score | verdict |
| --- | ---: | --- | --- | --- |
| **shipped H51 mix** (24 k consensus core + 6 k evidence exploration) | 0.1684 | PASS (IoU 0.422) | ≈0.17 ± 0.03 | recommended measurement |
| unconstrained instrument optimum (= corpus re-draw) | 0.2559 | FAIL (98 % on prior pixels) | ≈0.26 | forbidden by the novelty rule |
| H52 pixel-disjoint halo interleave | 0.1989 | FAIL (IoU 0.678) | ≈0.20 | rejected as a shifted copy |
| exploration-free core (24 k, no far dots) | 0.1806 | PASS (IoU ≈0.48, thin margin) | ≈0.19 | dominated on the key axis: no new territory |
| archived `seislin-44709` (incumbent) | 0.0422 | cannot be resubmitted | unknown | comparator only |

If the owner spends one slot, the shipped file is the intended measurement: it is the only design
that is simultaneously gate-clean, pixel-novel, and above the incumbent on the validated
instrument. Its live score would (a) prospectively calibrate the consensus instrument, (b) settle
the §12 conflict in the direction of whichever family it agrees with, and (c) add a 26th
hash-verified row to the corpus used by every future design.

**Superseded in part by §14.** The shared-frame measurement added on 2026-10-07 puts the
parallel-session `gems51-scarpradio-offcat` file ahead of this candidate on the only frame where both
were scored identically. Read §14 before acting on this table.

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
3. **§12's conflict is therefore resolved in favour of the seismicity/geophysics evidence line** on
   the only frame that can adjudicate, at least for the purpose of choosing a file to submit. The
   consensus posterior remains useful as a *prior over where dot-efficiency has historically paid*,
   not as a predictor of new-territory value.
4. **A slot, if the owner spends one, should carry B first.** B additionally has 4/4 positive
   macrofolds on the frozen holdout (paired subtile CI `[0.0406, 0.0785]`,
   `evidence/holdout_h51.json`), a line of evidence A never had.

Limitations of this adjudication, stated so it is not over-read: it is **one frame** (a single
variant of the SGMC mask at one clearance radius), it compares artifacts at different masses (30 k vs
35 k vs 44.7 k dots), and it cannot rank either file against the 25 scored artifacts, whose scores
come from the hidden expert labels. It is strong enough to order two *in-repo* candidates for the
purpose of spending a slot, and not strong enough to predict a leaderboard number.
