# H52 decision record — what is shipped, why this budget, and what is still unproven

*Written 2026-10-07 by the Arena session on branch `arena/685c6059-gemsdoe50`. Every number below
is reproduced by a script in this repository; nothing is quoted from a previous session.*

## 1. The artifact

| item | value |
| --- | --- |
| file offered first | `docs/downloads/gems50-h52-coincidence8-80000-20261007T032938Z-nanoutside.tif` |
| SHA-256 | `c8292db9e2c6d16b99a32ceae3d1652eb15019c8faa6f9d8b6d8b052d15dd582` |
| all-finite twin | `docs/downloads/gems50-h52-coincidence8-80000-20261007T032938Z.tif` |
| twin SHA-256 | `a2ed87fac9fdb4b9604ab2850b5f750eefe51fa9795caa6a503fc4739de6475d` |
| zip (single GeoTIFF inside) | `docs/downloads/gems50-h52-coincidence8-80000-20261007T032938Z-nanoutside.zip` |
| predicted pixels | 80,000 isolated cells, ≥3 px (300 m) apart |
| format | GTiff, 1 band, float32, EPSG:32611, 3292 × 3730, 100 m, values in {0, 1}, NaN (or 0.0 in the twin) outside the study footprint, no nodata sentinel |
| builder | `scripts/build_h52_coincidence.py` (input SHA-256s in `evidence/h52_build_80000.json`) |
| receipts | `evidence/h52_validation_80k.json`, `evidence/h52_uniqueness.json`, `evidence/h52_budget_curve.json` |

Reproduction: `scripts/restore_inputs.sh .arena/inputs` (28 s, eight SHA-256 checks) then
`python scripts/build_h52_coincidence.py --inputs .arena/inputs --out-dir .arena/out --budget 80000`
(≈6–13 min). Two independent runs on 2026-10-07 produced byte-identical output for the all-finite
file — the builder is deterministic given the pinned inputs.

## 2. What the artifact is

Eight evidence families, each reduced to a within-family percentile rank and then combined:

| family | source bands | rationale |
| --- | --- | --- |
| T | `training_features.tif` 12, 19 (detrended elevation, detrended slope) | surface expression of a fault scarp or range front |
| S | `topo_u8.tif` 1–9 | multi-scale topographic roughness / curvature discontinuities |
| L | `lidar_scarp_features_u8.tif` 1–12 | USGS 3DEP 1 m DEM scarp descriptors: ground-truth-resolution steps |
| R | `radiometric_u8.tif` 1–7 | K/Th/U and ratios change across fault-bounded lithologies and along fracture-controlled alteration |
| D | `geodawn_rad_u8.tif` 1–4 | an independent GeoDAWN radiometric mosaic, so R and D cannot fail together for a survey-processing reason |
| P | `training_features.tif` potential-field bands | magnetic/gravity gradients respond to structure at depth, where the surface may be concealed |
| G | `training_features.tif` geodetic-strain and conductivity bands | present-day strain accumulation and conductivity contrasts along damage zones |
| Q | `training_features.tif` 10, 16 (ComCat-derived seismicity) | spatial prior from instrumentally recorded earthquakes |

Saliency per band is the multi-scale structure-tensor response (gradient energy × coherence at
σ = 1.5, 3, 6 px), clamped at its own 99th percentile, ranked within itself, and the family field is
the per-cell maximum over its bands. The coincidence score is
`count of families with percentile ≥ 0.90 + 0.5 × mean normalised excess`; the emitter takes cells in
descending score order, accepts a cell only if no accepted cell is within 2 px (Chebyshev), and stops
at the budget. Dots within 300 m of the provided catalogue (200 m buffer + the metric's own kernel
arithmetic) are excluded by construction, because the organizer excludes catalogue pixels from
scoring (DrivenData staff, forum thread 11516; recorded in `README.md`).

## 3. The budget question, stated exactly

Two owner-recorded organizer scores exist for a nested pair of submissions — 44,090 px at 0.2600 and
its 37,654 px strict subset at 0.2778. Because the child is a subset of the parent, its weighted
credit equals the parent's, so the two metric equations

```
s = T / (alpha * n + beta * G)        alpha = 0.2, beta = 0.8
```

solve exactly for the two unknowns: **G = 14,088.75 truth pixels** and **T = 5,223.14 weighted
credit** (re-derived in `scripts/h52_coincidence_budget.py`; unit-tested in `tests/test_h52_coincidence.py`).
The champion therefore reaches only 37 % of the truth mass, and the bar for adding a fresh pixel
follows from the same algebra: a dot is worth adding only if its expected credit exceeds
`bar × (1 − k)`, with `bar = alpha·s/(1 − alpha·s) = 0.0588` at `s = 0.2778`. In distance terms a
fresh pixel must be within ≈283 m of uncredited truth to pay for itself.

That is the whole reason this artifact looks different from the incumbent family: the incumbent has
already spent its 37,654 dots inside the region it can reach, and the remaining truth mass — about
8,866 px — is by definition outside the 300 m reach of any of its dots. A new file has to place dots
where the incumbent has none, which is exactly what the ≥200 m catalogue buffer and the
coincidence-of-independent-families score are for.

## 4. The emission budget: one measurement, one extrapolation

`scripts/h52_coincidence_budget.py` emits the same field at ten budgets and reports, for each, the
*measured* instrument credit per dot, the metric evaluated with the proxy inventory standing in for
the truth, and the model implied by the single transfer constant
`r = 0.8510 = T_champion / (instrument credit per dot × dots)` at the anchor
(G = 14,088.7, T = 5,223.1):

| dots | instrument credit/dot (measured) | instrument DTI (measured) | model T | model DTI (extrapolated) |
| --- | --- | --- | --- | --- |
| 20,000 | 0.1583 | 0.0534 | 2,693.9 | 0.1764 |
| 30,000 | 0.1575 | 0.0769 | 4,019.8 | 0.2328 |
| 37,654 | 0.1568 | 0.0936 | 5,022.9 | 0.2672 |
| 40,000 | 0.1569 | 0.0987 | 5,342.5 | 0.2772 |
| 50,000 | 0.1550 | 0.1179 | 6,597.0 | 0.3101 |
| 60,000 | 0.1509 | 0.1334 | 7,704.2 | 0.3311 |
| 80,000 | 0.1446 | 0.1604 | 9,843.8 | 0.3610 |
| 100,000 | 0.1381 | 0.1808 | 11,748.3 | 0.3757 |
| 120,000 | 0.1347 | 0.2006 | 13,759.7 | 0.3901 |
| 160,000 | 0.1262 | 0.2269 | 14,088.7 | 0.3256 |

Two things are visible and they point in opposite directions.

* The **measured** columns improve monotonically with mass: credit per dot decays slowly
  (0.1583 → 0.1262 from 20k to 160k) while the denominator only grows by `alpha × dots`, so total
  credit wins. On the proxy inventory alone, more dots are better at every budget tested.
* The **model** peaks at 120,000 dots (0.3901) and then collapses, because the
  model caps the numerator at the total truth mass G: at 160k the modelled credit saturates at
  G = 14,088.7 while the false-positive tax `alpha × n` keeps growing.

The cap is an artifact of the model, not a measurement, so the optimum it produces must not be read
as "120,000 dots is the right answer". The defensible statement is narrower:

1. The measured proxy curve says that adding dots has not yet become counter-productive at these
   masses.
2. The model's own optimum is produced by a saturation assumption that the data cannot verify.
3. The shipped file is therefore placed **inside the plateau, below the model optimum**: 80,000 dots
   with a modelled 0.3610 against the model's 0.3901 ceiling — a deliberate
   7% give-up in modelled value in exchange for not betting the file on an
   untested extrapolation.

If a slot is spent, the returned score plus that file's instrument credit pins `r` at a second budget
and turns this single-anchor extrapolation into a two-point measurement — the first item in the list
of remaining work.

## 5. What is *not* established

* **No organizer score exists for this file.** Every number here is a local proxy on the same grid.
* **The instrument is a proxy inventory, not the hidden labels.** It orders known artifacts
  correctly (Spearman ρ = 0.805, p = 0.005, n = 10) but an SGMC-family submission scored 0.0512 on
  the hidden labels — below matched random. A passing calibration is not a score prediction, and the
  per-dot instrument quality of H52 (0.1446) is below every incumbent-family artifact measured
  (0.1573–0.1704).
* **The budget model is an extrapolation from one anchor.** It assumes the proxy-to-hidden credit
  ratio is budget-independent. Nothing available here tests that assumption.
* **Novelty is not correctness.** 87.8 % of the dots are outside the union of every prior support
  and 57.2 % are ≥300 m from any prior dot; a novel dot can still be wrong.
* **The blocked holdout is a weak instrument by construction.** It uses the same proxy inventory, so
  the four positive folds show that placement beats matched-mass random *on that inventory*; they do
  not show that the hidden labels agree.

## 6. Remaining work for the next session

1. **External validation with a genuinely different inventory** — e.g. an independent Quaternary
   fault compilation not used in the field (the Nevada Bureau of Mines and Geology has one), or the
   organizer's own revealed labels once the round closes. Until then the proxy ordering is the only
   calibrated evidence.
2. **Re-run the budget curve with a measured follow-up.** If a submission slot is spent, the
   returned score plus the instrument credit of that file pins `r` at a second budget and turns the
   extrapolation into a two-point measurement.
3. **Rebuild the corroboration field for a different τ** (0.85 / 0.95) and check whether the
   instrument quality curve is flat or peaked; the current τ = 0.90 is a single unexamined choice.
4. **Test the derived marginal rule directly**: emit 200,000 dots and measure whether the per-dot
   credit curve actually decays as the model assumes, which the same script already reports.
5. **Await the organizer's format confirmation** for NaN-outside files before spending the final
   selection; the all-finite twin exists precisely because the earlier portal rejection was a range
   error caused by a nodata sentinel.
