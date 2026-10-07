# H57 three-pass review — every deviation, bug and assumption

Pass 1 builds and verifies; pass 2 hunts bugs, broken assumptions and edge cases;
pass 3 re-checks every requirement in the brief line by line. Corrections are listed
with the evidence that exposed them and with the measurement that closed them.

## Pass 2 — bugs found and fixed

### B1 (major) A quarter of the map was silently receiving no dots

The first H57 builder required **both** evidence families to be finite before a cell
could hold a dot:

```python
field = np.where(np.isfinite(lidar_top7) & np.isfinite(o19g), 0.5 * ..., np.nan)
```

`rank_transform` returns NaN wherever a channel has no data, and the USGS 3DEP LiDAR
scarp stack is undefined on **1,274,189 of the 5,167,373** footprint cells (24.7 %).
Those cells were excluded from the emission pool entirely, and 1,275,818 cells got
no dots at all.

Attribution, not guesswork (`scripts/h57_decompose.py`,
`evidence/h57_decompose.json`), all at N = 180,000 on `S_matched`, same seed:

| field assembly | eligible pool | off-catalogue DTI | truth-side credit |
|---|---|---|---|
| strict intersection (first revision) | 3,886,785 | **0.17990** | 14,239 |
| NaN-aware rank mean (fixed) | 3,886,785 | **0.21812** | 17,362 |

The strict form lost **21 % of the truth-side credit** for a reason that had nothing
to do with geology. Fixed by combining the families with a NaN-aware rank mean, so
the topographic rank stands in where the LiDAR has no data. This also explains the
0.180 → 0.218 jump between the two H57 builds.

### B2 The uniform control was not the control the candidate faced

The candidate is drawn from a pool that excludes the 61-artifact prior union and the
catalogue buffer; the matched-mass uniform control was drawn from the whole study
footprint. Those are different populations, and the difference is worth 0.016 DTI
(0.1670 whole-footprint vs 0.1507 same-pool at N = 180,000). Both are now reported,
the same-pool one is labelled the fair comparison, and the whole-footprint one is
kept as the conservative bound.

### B3 `evaluate()` crashed on an empty-truth tile

The per-subtile block bootstrap evaluates 32 × 32 px windows. A window containing no
truth pixels hit a `DTIParts(...)` branch that referenced `dot_credit` before it was
assigned (`UnboundLocalError`). The branch's arithmetic was also wrong: with no
truth in the window the false-positive mass is the full prediction mass, not zero.
Fixed in `src/gems57/metric.py`, and the value returned by the branch now matches the
general path exactly. Reproduced and closed by the metric self-tests in
`tests/test_h57.py`.

### B4 The blocked-holdout emitter asked for more dots than the lattice had blocks

`scripts/h57_holdout_fields.py` scaled the requested dot count by
`eligible / fold_area` instead of by `fold_area / footprint_area`, so the small NE
fold was asked for 249,964 dots from a lattice of 152,438 blocks. Fixed to an
area-proportional allocation, which is the only allocation that makes the pooled
number a population statistic rather than a density artefact.

### B5 The declared selection rule and the shipped code disagreed

`scripts/h57_field_select.py` used a NaN-aware blend; `scripts/build_h57.py` used the
strict intersection. The screen therefore validated a field that was never built.
This is the same defect as B1 seen from the other side, and it is the reason the
receipt for the superseded build quoted 0.1710 while the same script's screen quoted
0.24.

## Pass 2 — assumptions tested and corrected

### A1 The mass curve is not the proxy's curve (assumption, declared)

The frozen mass comes from the coverage-transfer rule in
`docs/research/h57-proxy-gap.md`, not from the proxy's own optimum. Stated everywhere
the number appears. This is the largest single uncertainty in the artifact.

### A2 The 2 px novelty statistic is not a novelty guarantee

"88.3 % of dots are more than 200 m from any prior dot" sounds strong and is
misleading: the prior union's 2 px neighbourhood already covers **85.2 %** of the
footprint, so a uniform draw of the same mass would score about 15 % "novel" by the
same measure. The site now reports exact-cell overlap (0 by construction) and
block-signature IoU against 50 signature-pinned priors (worst 0.0407 at 800 m,
0.1106 at 3.2 km) as the discriminating statistics, and the proximity figure is
quoted only with its baseline.

### A3 The translation control is not discriminative here

Shifting the whole raster by ±3 px or by (+7, +7) changes `S_matched` DTI only from
0.2181 to 0.2136–0.2209. The field is spatially autocorrelated, so a global shift
preserves performance; the control is reported for completeness and explicitly
labelled as not evidence of localisation. The block bootstrap and the four
macrofolds carry the significance argument instead.

### A4 The catalogue-buffer choice cannot be decided on the matched frame

`S_matched` is *defined* as more than 300 m from the catalogue, so on that frame a
300 m suppression can never lose a truth pixel and always removes false-positive
mass. The measured "buffer 3 px is best" (0.24315 vs 0.23016 for buffer 0 at
N = 250,000) is a **selection artefact of the frame**, not a result. DrivenData
staff ruled that (i) known-fault pixels are excluded from evaluation and do not count
towards penalty terms and (ii) new-fault truth may occur within 300 m of a known
trace; the supplied answers also confirm that a "new fault" may be newly mapped
geometry of an existing fault system. A suppression buffer therefore discards dots
that can still earn credit, and the frozen artifact uses **1 px** — enough to keep
dots off the masked cell and its immediate neighbour, not enough to concede the
100–300 m band. The measured price of that decision on the frame that cannot see
the question is 4.4 % of DTI, and it is stated on the site.

## Pass 2 — hypotheses tested and rejected

* **Dense emission.** The theoretical argument that a painted cell on a truth cell
  is free, and therefore that densely painting predicted traces must beat 3 px
  spacing, is **wrong in practice**: at matched painted-cell count, top-N blob
  painting and skeletonised lines both lose to field-weighted spreading on every
  field tested (`evidence/h57_emission_shapes.json`). The reason is that the field
  ranks *cells*, not *traces*: the highest cells form blobs around field maxima, so
  concentrating the budget there spends it on the same trace repeatedly.
* **Seismicity corridors.** Measured at or below chance on both frames. Rejected,
  documented, and excluded from the artifact.
* **The eight-family coincidence vote** (H52-C) and **magnetic / radiometric
  families**: re-measured, still negative on these frames.

## Pass 2b — the two corrections that produced the delivered revision

### B6 (major) A rank *mean* was flattening the field

The frozen field combined two families with a rank mean. A mean compresses the top of the
distribution, and the emitter samples in proportion to the field, so the compression was applied
exactly where the decision is made. Raising the blend to a power, with emitter, seed, lattice, buffer
and pool all frozen, moved the off-catalogue DTI at 90,000 dots from **0.17142 to 0.23406** (+37 %) and
the lift over a matched-mass uniform control from 1.33× to **1.84×**
(`evidence/h57_sharpen_sweep.json`, `evidence/h57_sharpen_ext.json`). The exponent sweep is monotone to
^8, plateaus at ^16 and turns over by ^32; ^16 is frozen. Declared post-hoc in
`docs/research/h57-preregistration.md` § "Amendment 1".

### B7 (major) The dot count was sized for a frame that is not the target

Revision 1 spent 180,000 dots on a regret rule evaluated on `S_matched`. That rule is frame-relative,
and `S_matched` has 52,219 truth pixels on 4.93 M eligible cells against an estimated hidden mass of
about 12,226 px: the proxy's truth is roughly four times denser on the ground, so it keeps repaying
dots that the hidden scoring would not. The delivered revision uses the repository's hidden-scale
transfer model instead, which for the sharpened field saturates at **90,000**. The consequence is not
cosmetic: at 90,000 the proxy reads 0.23406 and the model 0.440; at 180,000 the proxy reads 0.27864 and
the model 0.267, and at 250,000 the model has fallen to 0.204. Choosing the proxy's optimum costs about
0.17 of modelled hidden score, i.e. it is a worse decision than the one shipped by a wide margin under
the model — and better under the proxy. Both readings are published so the choice can be re-opened
rather than assumed settled.

### A5 (assumption, restated) What the 0.3774 number would take

A prediction with unit-height binary dots and **zero** false-positive mass scores `c/(0.8+0.2c)` where
`c` is its coverage of the hidden truth; 0.3774 therefore needs **32.66 %** coverage, not 100 % and not
merely "more dots". The delivered file covers 26.98 % of the proxy truth with 82,971 of
false-positive mass, so its ceiling at its own coverage on that frame is **0.31598** — below the
target. The gap is coverage, and the only admissible routes to coverage that this repository has
identified are (i) a field that finds fault pixels the current one misses and (ii) the
continuation/splay geometry that staff ruling R6 makes admissible and that no frame held here can
score. Both are stated on the site as the recommended next work.

## Pass 3 — requirement recheck

| brief requirement | where it is satisfied |
|---|---|
| a *new* artifact, never a copy of a prior submission | `scripts/build_h57.py` draws every dot from a pool that excludes the registered prior union; `evidence/h57_check.json` shows 0 exact shared cells and worst 800 m block IoU 0.0419 across 50 priors, and `evidence/h57_novelty_price.json` prices that guarantee at 1.48 % of proxy DTI |
| uniqueness gate run against all prior submissions | `scripts/check_h57_submission.py` |
| portal error `Predicted values must be in range [0, 1]` fixed | all-finite raster, verified by re-reading the delivered bytes; `plain_minmax_in_range = true`, `nan_cells = 0` |
| obvious whether the file is OK to download and submit | `h57.html` opens with a "safe to download and safe to submit" statement backed by the format gate; the root page carries a one-click banner as its very first element |
| easy one-click download | three download buttons at the top of `h57.html` and one in the root banner |
| unique submission name and short note | `GEMSDOE50-H57-TOPO-LINEAMENT-SCATTER-180K` plus the receipt's `portal_note` |
| seismicity from the point pattern, not the density band | implemented (`docs/hypotheses-20261007-h57.md` H57-H2), measured at chance, excluded from the artifact, and reported as a negative |
| record the official catalogue URL and licence before use | `docs/research/gems-official-clarifications.md`; H57 uses no such dataset |
| preregister 3–5 hypotheses, ranked, before implementation | `docs/hypotheses-20261007-h57.md`, `docs/research/h57-preregistration.md` (including declared **Amendment 1**, which is post-hoc and labelled as such) |
| do not spend a slot on an unvalidated idea | H57-H1 selected on measurement; H57-H2 rejected on measurement; H57-H4 recorded as unvalidated and **not** shipped |
| line-by-line sourcing with links | `docs/research/gems-official-clarifications.md` |
| store the research in the repository | `docs/research/` |
| three passes | this file |
| pull request merged to `main` | see the branch's pull request |
| core values focal | README charter, and the "Maximize P(Win) · Own the Outcome" footer on every page |
