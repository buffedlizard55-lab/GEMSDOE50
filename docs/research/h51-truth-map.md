# Historical H51 analysis: can score history map the hidden truth? — No.

> **Archive only.** This negative result and its score-corpus inputs are historical research, not a current submission recommendation or an authenticated leaderboard record. Current status: H53-A NO-GO / NO SLOT; see the [project site](../../index.html).

**Result (negative).** Discretising the scored domain into 4²…32² blocks and solving the linear
system implied by the metric for non-negative truth mass per block *does not* predict a held-out
artifact's score better than predicting the corpus mean. Evidence:
`evidence/h51_truth_map.json`, code: `scripts/h51_truth_map.py`.
Reproduces, with a stricter leave-one-artifact-out protocol, the same negative result recorded in
the sibling `GEMSDOE40` repository's `docs/data/truth-inversion.json`.

## Why one might expect it to work

The organizer metric is *linear in the truth*: with binary dots, `TP_w = Σ_{g∈G} max_x k(d(x,g))`,
so a corpus of scored artifacts with known dot sets gives one linear equation per artifact,

```
T_a = Σ_c R_ac · φ_c ,     R_ac = mean over unmasked pixels x in block c of C_a(x)
```

where `C_a(x) = max over dots of a of k(d)` is the exact credit field, `φ_c` is the hidden truth
mass in block c, and `T_a = s_a·(0.2·N_a + 0.8·G)` is exactly recoverable from the published score
(§8 of `h51-analysis.md`). One measured score therefore *is* one measurement of where credit can
be earned. With 25 hash-verified scored artifacts, the hope is that a coarse, smoothed,
non-negative inversion localises the 12,226 px of hidden truth.

## What was measured

| blocks per side | LOO RMSE(`T`) | LOO Spearman | constant-predictor RMSE(`T`) | fitted total mass |
| ---: | ---: | ---: | ---: | ---: |
| 4 (16 unknowns) | 2,353 | +0.558 | 1,920 | 31,775 |
| 8 (64) | 2,157 | +0.437 | 1,920 | 46,266 |
| 16 (256) | 1,924 | +0.526 | 1,920 | 137,276 |
| 32 (1,024) | 2,099 | +0.432 | 1,920 | 343,112 |

The fitted mass should come out near the calibrated `G ≈ 12,226 px`; instead it grows with the
number of blocks, which is the signature of a fit absorbing noise rather than signal. A
ranks-only view is mildly positive (ρ ≈ +0.5), but on the quantity that matters — the metric —
the inversion is not better than a constant, at any resolution.

## Why it fails, and what it implies

* **The corpus is not a designed experiment.** Its members are nested or method-similar: the
  median pairwise exact-pixel IoU is 0.031, but the *families* share 68–100 % of their dots, so
  most blocks are seen by almost every artifact and are not separately identifiable.
* **Placement differences are small relative to score noise.** Score differences between family
  members are dominated by dot count (ρ = −0.61 against log₁₀N), not geography.
* **Therefore the score history constrains *global efficiency* (credit per dot) and not
  geography.** It can rank structures that already exist in the corpus (the instrument of §4 of
  the analysis does that at ρ = 0.973), and it cannot tell us where the 41 % of truth that no
  corpus artifact reached actually is.

Implication for strategy: any claim to raise coverage above 0.59 must rest on a **new detector**
validated on an independent frame or on a submitted score — never on re-weighting the existing
artifacts. This is why the ranked hypotheses in `h51-hypotheses.md` are framed as *new signal
classes* with named layers and named free sources, and why the shipped candidate is labelled a
measurement rather than a predicted win.
