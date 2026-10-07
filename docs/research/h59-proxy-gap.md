# The H59 proxy gap, and the mass instrument it forced us to replace

Two irregularities were found in H59 and both changed a design decision. They are
recorded here because the numbers on the site depend on them.

## 1. The off-catalogue proxy is geometrically unlike the supplied catalogue

The repository's standard instrument is the USGS *State Geologic Map Compilation*
fault layer, filtered to pixels that are inside the study footprint and more than
300 m from the supplied catalogue. That construction was carried over from earlier
sessions without ever being compared, shape for shape, with the labels it stands in
for. It does not match.

| measure | supplied catalogue (`labels.tif`) | SGMC proxy, raw |
|---|---|---|
| fault pixels in footprint | 60,988 | 61,664 |
| 8-connected components | 3,199 | 2,077 |
| median component | 12 px | 13 px |
| 90th percentile component | 39 px | 59 px |
| 99th percentile component | 128 px | 356 px |
| components ≥ 200 px | 10 | 40 |
| **components ≥ 500 px** | **0** | **12** |
| share of pixels in components ≥ 200 px | 4.4 % | 29.4 % |
| largest component | 253 px | 4,882 px |

The proxy contains a long-traced bedrock-fault population that the supplied
catalogue does not: 12 components of 500 px or more carrying 29.4 % of the proxy's
pixels, against *none* of that size anywhere in the labels. A field that is good at
following a 2 km bedrock trace is therefore rewarded on the proxy in a way the
labels would never repay, and a field that is good at short, discontinuous surface
traces is penalised.

**Repair.** `S_matched` drops every 8-connected component of 500 px or more:
2,077 → 2,065 components, 61,664 → 52,219 px, largest component 4,882 → 494 px,
share of pixels in components ≥ 200 px 29.4 % → 16.6 %. The component filter is
deliberately coarse — a size cut cannot fix a population mismatch, it can only stop
the proxy rewarding the wrong thing — and the caveat is carried into every page that
quotes a `S_matched` number.

Script and evidence: `scripts/h59_frame_geometry.py`,
`evidence/h59_frame_geometry.json`.

## 2. The mass-calibration instrument was measuring the wrong thing

The dot count is the single most consequential free parameter: with unit-height
binary predictions the metric is
`DTI = T / (0.2(P − A) + 0.8G + 0.2T)`, so every extra dot costs 0.2 of
false-positive mass whether or not it earns anything.

The first H59 mass calibration drew a *random subsample of the proxy's fault
pixels* down to the calibrated hidden mass (≈ 12,226 px) and then swept the dot
count. Random subsampling **cuts continuous traces into isolated specks**. A speck
is trivially covered by any nearby dot, so the optimum is pulled upward and the
whole curve is inflated: at |G| = 12,226 the subsample instrument reported
**0.0957** at 120,000 dots.

**Replacement.** `scripts/h59_calibrate_mass2.py` selects *whole connected
components* until the target pixel count is reached, so line connectivity survives.
Its frame is 12,236 px in 440 components (mean 27.8 px, the same size class as the
supplied catalogue). Result:

| dots | component-preserving truth | random-pixel subsample |
|---|---|---|
| 30,000 | 0.0473 | — |
| 50,000 | 0.0605 | — |
| 80,000 | 0.0695 | — |
| **120,000** | **0.0719** | 0.0957 |
| 180,000 | 0.0689 | — |
| 250,000 | 0.0618 | — |

The correct instrument puts the optimum at 120,000 with a flat top over
80,000–250,000; the broken one put it at the same place but 33 % too high. The
*ranking* was right and the *level* was wrong, which is exactly the kind of error
that makes a proxy number look like a leaderboard score.

Evidence: `evidence/h59_mass_calibration_components.json`,
`evidence/h59_mass_calibration.json`.

## 3. What replaced the calibration: a stated transfer rule

Because frame `S_matched` has 52,219 truth pixels and the hidden set does not, the
frozen mass is not taken from the proxy's own optimum. The field's coverage fraction
`c(N) = T(N)/G` is measured on `S_matched` at seven masses and then re-scored over a
grid of plausible hidden masses from 4,000 to 52,219 px under one explicit
assumption:

> **Coverage transfer.** The field covers the same *fraction* of whatever the truth
> is, so `T(N) = c(N) · G` for the hidden `G`.

That gives a model DTI for every (N, G) pair. 180,000 dots minimise both the mean
loss and the worst-case regret over the grid; the proxy's own optimum, 250,000, is
4 % better there but 30 % worse if the hidden truth turns out to be small. The
assumption is an assumption. It is stated on the site next to every number that
depends on it, and it is the largest single uncertainty in the artifact.

Script and evidence: `scripts/h59_final_select.py`,
`evidence/h59_final_select.json`.
