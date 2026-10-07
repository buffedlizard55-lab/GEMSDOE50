# Archived dotted-file metric analysis (not an organizer score report)

> Legacy research context only. Numeric scores below originated in prior project records and are not independently authenticated organizer results or mapped to a TIFF by H50-S1. Prior sibling-repository leaderboard notes conflict; no current official score or rank is asserted here. See the current project status in [`../../README.md`](../../README.md).

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
pays iff `k > 0.2·s`. For an illustrative hypothetical `s = 0.5`, the kernel threshold
is `0.1`, corresponding to a distance below 270 m. This is algebra only, not a
leaderboard target or score assertion.

**Corollary 3 — coverage arithmetic.** With `x = T/G` and `ρ = F/G`,
`x = s·(0.2ρ + 0.8)/(1 − 0.2s)`. This relation is kept symbolic; no current or
organizer-reported leaderboard value is used as a target.

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

## 5. Leaderboard provenance — no current claim

Earlier sibling-repository notes contain historical leaderboard assertions, but they
conflict and were not freshly independently checked by GEMSDOE50. The current project
makes no claim about the official leader, rank, or score, and no score is mapped to a
TIFF without an organizer receipt. DrivenData's Terms of Use prohibit automated
monitoring/copying and manual monitoring/copying without prior written consent; this
repository links to the official page but does not poll, scrape, or publish leaderboard
rows.

## 6. Ceiling

Under the stated legacy model assumptions (`G = 13,833`, perfect knowledge, and dots
every ≈3 px along hidden traces), `T ≈ 0.8G`, `F ≈ 4,200`, hence DTI ≈ 0.78. This
is a model ceiling, not a forecast, current score, or independently verified leaderboard
comparison. Any gap analysis is conditional on these owner-reported assumptions.

## Closed-form use of the recorded scores (added 2026-10-07)

Two owner-recorded organizer scores for a **nested** pair of submissions turn the metric into two
equations in two unknowns. With `s = T / (alpha*n + beta*G)`, `alpha = 0.2`, `beta = 0.8`, and the
child a strict pixel subset of the parent (so `T_child = T_parent`):

```
44,090 px @ 0.2600  and  37,654 px @ 0.2778   ->   G = 14,088.75 px,  T = 5,223.14 px
```

The solve is implemented and unit-tested in `scripts/h52_budget_curve.py` and
`tests/test_h52_emission.py`. Two consequences are used in the H52 decision record
(`docs/h52-decision.md`):

* **the marginal-value rule** — at score `s` a further pixel pays for itself only if its expected
  credit exceeds `bar * (1 - k)` with `bar = alpha*s/(1 - alpha*s)` (bar = 0.0588 at s = 0.2778), so a
  fresh pixel must be within about 283 m of uncredited truth;
* **the reachable-mass argument** — the 37,654-px artifact reaches only 5,223 of the 14,088.75 truth
  pixels, so ~8,866 px of truth lie outside the 300 m reach of any of its dots. Off-catalogue
  placement is therefore the only way to add credit; this is the quantitative reason the H52 artifact
  looks different from the incumbent family.

The same two constants anchor the single transfer constant `r = 0.851` used by the budget model. That
model is an **extrapolation** from one anchor and is labelled as such everywhere it appears.

Reconciliation with §6 above: the older ceiling model assumed `G = 13,833`; the closed-form solve of
the recorded nested pair gives `G = 14,088.75`, which reproduces the sibling sessions' published
`|G| = 14,088.7` to five significant figures. The closed-form value supersedes the assumed one and the
ceiling in §6 is therefore about 2% low.
