# H59 preregistration — frozen protocol

**Written before the H59 build ran. Every constant below is copied verbatim from
`scripts/build_h59.py`; nothing was changed after the numbers came back except where
an entry in `docs/research/h59-deviation-log.md` says so and why.**

## Question

Which *evidence family* and which *emission geometry* maximise the official
distance-weighted Tversky index (DTI) against faults that the public USGS /
INGENIOUS catalogue does not contain, and how many dots should be spent?

## Instruments (frozen before selection)

| instrument | definition | why |
|---|---|---|
| frame `S_matched` | USGS SGMC fault pixels, inside the study footprint, more than 300 m from the supplied catalogue, and in an 8-connected component smaller than 500 px (52,219 px) | the only truth in this repository that is *not* the thing being predicted |
| frame `S_raw` | the same without the component filter (61,664 px) | comparability with earlier artifacts |
| frame `L` | the supplied catalogue itself | negative control only; the artifact is deliberately steered away from it |
| frame `L-holdout` | for each spatial macrofold, the catalogue is removed in that fold only and the field is emitted into that fold and scored against that fold's own labels | measures the field against the fault population that is actually labelled |
| control | uniform scatter of the *same* dot count drawn from the *same* eligible pool, five seeds | matched-mass; the only fair baseline |
| uncertainty | paired block bootstrap over 32 × 32 px subtiles, 400 replicates | the map is spatially autocorrelated, so a per-dot bootstrap would be an overstatement |

## Frozen constants (H59 final build)

| constant | value | where it came from |
|---|---|---|
| field | rank-mean of the rank transforms of official layer 19 *gradient magnitude* and the rank-mean of LiDAR scarp bands 02–08, combined NaN-aware | `evidence/h59_field_select.json`, `evidence/h59_holdout_fields.json` |
| emitter | field-weighted scatter on a 3 × 3 px lattice, one dot per chosen block, dot on the strongest eligible cell of the block, sampling weight ∝ block maximum + 1e-6 floor | `evidence/h59_emission_shapes.json` |
| mass | 180,000 dots | `evidence/h59_final_select.json` (coverage-transfer regret rule) |
| catalogue buffer | 1 px | staff ruling, `docs/research/gems-official-clarifications.md` |
| novelty | never on a registered prior-artifact positive cell | standing brief |
| RNG seed | 20261007 | fixed |
| raster | float32, 1 band, EPSG:32611, 3,730 × 3,292, 100 m, transform (100, 0, 243350, 0, −100, 4508550), values {0, 1}, **every cell finite** | portal safety |

## Selection rule stated in advance

1. Among a declared list of field candidates, take the one with the highest DTI on
   frame `S_matched` at a single mass, *provided* it also beats the matched-mass
   uniform control in 4/4 macrofolds on frame `L-holdout`.
2. Among a declared list of emitter families at matched painted-cell count, take
   the best DTI on frame `S_matched`.
3. Choose the mass by minimising the mean regret over a grid of plausible hidden
   masses under a stated coverage-transfer assumption, **not** the frame's own
   optimum.

## What success would look like, stated in advance

* the artifact beats the matched-mass uniform control in 4/4 macrofolds on
  `S_matched` **and** on `L-holdout`;
* the paired bootstrap interval on `S_matched` excludes zero;
* zero cells on the supplied catalogue and zero shared cells with the prior union;
* the plain `min()/max()` range check passes on the delivered bytes.

## What was declared out of scope

* Any use of the organizers' hidden labels (none exist in this repository).
* Any claim that a proxy number transfers to the leaderboard. The coverage-transfer
  assumption is stated as an assumption everywhere it is used.
* Any external dataset whose licence or challenge-use rights are unresolved. H59
  uses the competition's own feature stack and public-domain USGS 3DEP products
  only, which is why it is preferred over H56 (whose mixed-network ComCat geometry
  carries unresolved contributor rights).

---

## Amendment 1 — declared post-hoc, 2026-10-07 (after the first build's numbers were seen)

Two changes to the frozen design were made **after** the first build was measured, and are labelled
post-hoc here rather than presented as preregistered:

1. **Sharpening exponent ^16 on the field.** The frozen field was the plain NaN-aware rank mean.
   A screen run after the first build (`scripts/h59_field_power_screen.py` →
   `evidence/h59_field_power_screen.json`) showed the sharpened form beating it at every mass by 21–34 %
   of off-catalogue DTI, and a dedicated sweep (`scripts/h59_sharpen_sweep.py`,
   `scripts/h59_sharpen_ext.py`) located the turnover at ^32. ^16 was frozen at that point.
2. **Mass 180,000 → 90,000.** The original mass came from a coverage-transfer regret rule evaluated on
   frame `S_matched`. That rule is frame-relative: because the proxy's truth (52,219 px) is far denser
   than the hidden target (~12,226 px), the proxy's own optimum sits at ~250,000 dots. The shipped
   revision uses the repository's *hidden-scale* transfer model instead
   (`docs/research/h56-diagnosis.md` §§5–6), which saturates at 90,000 for the sharpened field.

What is **not** changed: the frames, the emitter family, the 3 px lattice, the 1 px catalogue buffer,
the prior-union exclusion, the seed, the raster format, and the comparison instrument (matched-mass
uniform control on the same pool). The amendment is a change of two numeric parameters on measured
evidence, it is disclosed on the site and in the README, and both revisions' files are retained so the
two can be compared directly. The proxy result of the first revision (0.21812) and of the second
(0.23028 on the delivered bytes) are both reported.

**Why this is not presented as preregistration.** A preregistered protocol that is edited after seeing
results is no longer preregistration. The honest description is: the protocol was preregistered, then
amended once, and the amendment is disclosed with the evidence that motivated it and with the
measurement that could have falsified it (the exponent sweep turns over; the mass curve is reported at
every transfer factor from 0.30 to 1.00).
