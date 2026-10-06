# Why the dotted file scored 0.2778, and what it would take to beat it

**Verification status of every number is labelled** — `[OFFICIAL]` read from an
organizer source, `[MEASURED]` computed here from hash-pinned bytes,
`[MODEL]` arithmetic under stated assumptions, `[PROJECT]` the owner's own pages.

---

## 1. The metric, exactly [OFFICIAL]

The problem description (<https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/>)
defines a triangular kernel with 300 m support and α = 0.2, β = 0.8:

```
k(d)   = max(1 - d/300 m, 0)                       (3 pixels at 100 m)

TP_w   = Σ_{g∈G}  max_{x : d(x,g) ≤ R}  p(x)·k(d(x,g))
FP_w   = Σ_{x : p(x) > 0}  p(x)·[1 − max_{g∈G} k(d(x,g))]
FN_w   = Σ_{g∈G}  [1 − max_{x : d(x,g) ≤ R} p(x)·k(d(x,g))]
DTI    = TP_w / (TP_w + 0.2·FP_w + 0.8·FN_w + ε)
```

`tests/test_metric.py::test_official_scoring_example` reproduces the page's own worked
example (TP_w = 3.00, FP_w = 1.89, FN_w = 2.00 → 0.60) to 1e-12.

**Exact identity.** The same `max` appears in `TP_w` and `FN_w`, so
`TP_w + FN_w = |G|` exactly. Hence

```
DTI = T / (0.8·G + 0.2·T + 0.2·F)          (T = TP_w, F = FP_w, G = |truth|)
```

verified numerically in `tests/test_metric.py::test_coverage_inversion_matches_forward_metric`.

**Corollary 1 — binary beats graded.** Scaling a support by λ gives
`DTI(λ) = λT / (0.2λ(T+F) + 0.8G)`, whose derivative in λ is
`0.8·T·G / (0.2λ(T+F)+0.8G)² > 0`: every graded map is dominated by its own
thresholded support. All competitive artifacts are binary.

**Corollary 2 — the marginal-inclusion rule.** A dot that is the unique maximiser for
one truth pixel raises `T` by `k` and the denominator by exactly `0.2`. It therefore
pays iff `k > 0.2·s`. At the current best public score of 0.2778 the bar is 0.0556
(within 283 m); at the 2026-10-06 leader's 0.3774 it is 0.0755 (within 277 m).

**Corollary 3 — coverage arithmetic.** With `x = T/G` and `ρ = F/G`,
`x = s·(0.2ρ + 0.8)/(1 − 0.2s)`. Reaching s = 0.3774 requires 32.7 % weighted
coverage of the hidden truth at zero false-positive mass, 40.8 % at ρ = 1.

## 2. What the highest-scoring artifact actually is [MEASURED]

`gems24-h25-1-dotted-h19-5-d2-8-…-nan.tif` (owner's 0.2600 artifact) and its
2-px-pruned variant `gemsdoe32-h33-h33-2-b2-…-nan.tif` (owner-reported 0.2778):

| property | D2.8 | H33-2-B2 |
| --- | ---: | ---: |
| positive pixels | 44,090 | 37,654 |
| unique positive value | {1.0} | {1.0} |
| nearest-neighbour spacing (median / p10) | 3.0 / 2.83 px | 3.0 / 2.83 px |
| 100-px blocks occupied | 43.9 % | — |
| mean dots per occupied block | 80.2 | — |
| footprint within 300 m of a dot | 17.19 % | — |
| area-weighted kernel credit over the footprint | 0.0679 | — |
| dots within 300 m of the catalogue | 19.52 % | 0 (by construction) |

So the record artifact is a sparse binary dot lattice at *the metric's own spacing*
(2.83–3.0 px ≈ the 300 m kernel radius), not a density map and not a better model.

## 3. A three-point model of the hidden truth [MODEL]

Three artifacts with reported scores are (nearly) nested, so their scores constrain the
unknown hidden-truth mass `G` and credit `T`:

| artifact | dots N | reported score |
| --- | ---: | ---: |
| `d28-poisson300m-offcat-44090` | 44,090 | 0.2600 |
| `h27-4-r1-solo-d2-8` | 40,199 | 0.2708 |
| `h33-h33-2-b2` (pruned 2 px) | 37,654 | 0.2778 |

Solving `s = T/(0.8G + 0.2T + 0.2N)` for the first two with `T` held fixed gives
`0.8G + 0.2T ≈ 12,160` and `T ≈ 5,460`; the third then predicts 0.2600 for N = 44,090,
which is the value reported. **`G ≈ 13,800` hidden-truth pixels and `T ≈ 5,460`
weighted credit — i.e. ≈ 40 % weighted coverage with 37–44 k dots, and ≈ 0.12 credit
per emitted dot.**

This is a model, not a measurement: the three scores are owner-reported, the nesting is
approximate, and the identity assumes the dots are unique maximisers. It is used here
only to (a) explain the shape of the winning files and (b) set the scale of the belief
field for the emitter (`G_est = 13,833`).

## 4. Why this is not a model-quality story

The dotted family's score rises as dots are *removed* (121,131 → 0.1922, 60,069 →
0.2477, 44,090 → 0.2600, 37,654 → 0.2778 [PROJECT]). Under the metric algebra that is
exactly what thinning a support at the metric's own spacing should do: coverage
saturates at ~3 px spacing, while every dot keeps costing 0.2. The pruning step that
produced 0.2778 from 0.2708 removed 2,545 dots that lay within 200 m of the published
catalogue, i.e. **dots that could not earn credit because the scored truth is a
different inventory from the catalogue** — the metric's own definition of the test set.

The practical consequence is the whole strategy of this project: the binding constraint
is *coverage of faults the catalogue does not contain*, and the only lever that can
move it is evidence that is independent of the catalogue.

## 5. What the live board says now

[OFFICIAL, fetched 2026-10-06] The public leaderboard's best score is **0.3774**
(xiaofanhu, 11 submissions); then 0.3345, 0.3262, 0.3222, 0.3220, 0.3218, 0.3195 …
The task instruction's target of "> 0.3195" is therefore already the **seventh** place.
Any claim that a file "scores higher than 0.3195" must be checked against 0.3774.

## 6. Ceiling

With `G = 13,833`, perfect knowledge and dots every ≈ 3 px along the hidden traces would
give `T ≈ 0.8G`, `F ≈ 4,200`, hence DTI ≈ 0.78. The gap between 0.28 and 0.38 is
therefore a *coverage* gap of roughly 25–50 % relative, not an emission-quality gap.
