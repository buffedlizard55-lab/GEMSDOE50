# H59 final analysis

Everything below is measured. Each table names the script that produced it and the
committed evidence file it was read from. Numbers on the site are rendered from those
files, so the pages cannot drift from the measurements.

## 0. The metric, and what it implies

`src/gems59/metric.py` implements the organizers' published definition: a triangular
kernel `k(d) = max(1 − d/R, 0)` with `R = 300 m = 3 px`, and

```
DTI = TP_w / (TP_w + 0.2 · FP_w + 0.8 · FN_w + ε)
TP_w = Σ_g max_x p(x)·k(d(x,g))      FP_w = Σ_x p(x)·(1 − max_g k(d(x,g)))
FN_w = Σ_g (1 − max_x p(x)·k(d(x,g)))    so  TP_w + FN_w = G  exactly
```

For unit-height binary predictions with `P` painted cells and prediction-side credit
`A = Σ_x k(d(x, G))`, this reduces exactly to

```
DTI = T / (0.2·(P − A) + 0.8·G + 0.2·T)
```

Three consequences, all of which were then tested rather than assumed:

1. a painted cell sitting on a truth cell adds nothing to `P − A`, so it is **free**;
2. therefore the metric is recall-dominated and the marginal question is how much
   truth one painted cell buys;
3. but consequence 1 does **not** imply that painting densely along a believed trace
   is best — see §3, where that argument was refuted by experiment.

## 1. Which evidence field? (`evidence/h59_field_select.json`, `h59_holdout_fields.json`)

Frame `S_matched`, N = 250,000 dots, 3 px lattice, matched-mass uniform control drawn
from the same pool, five uniform seeds:

| field | DTI | lift | macrofold DTIs (NW, NE, SW, SE) |
|---|---|---|---|
| `o19` (official layer 19, detrended-elevation slope) | 0.24346 | 1.290 | .2180 .2708 .1362 .2982 |
| `o19grad + lidar7` | 0.24315 | 1.289 | .2165 .2721 .1408 .2974 |
| `o19 + o19grad + lidar7` | 0.24286 | 1.287 | .2162 .2710 .1391 .2986 |
| `o19 + o19grad` | 0.24263 | 1.286 | .2175 .2709 .1362 .2956 |
| `o19 + lidar7` | 0.24078 | 1.276 | .2146 .2680 .1316 .2986 |
| `o19grad` | 0.23991 | 1.272 | .2157 .2667 .1314 .2948 |
| `o12` (detrended elevation) | 0.22426 | 1.189 | .1971 .2538 .1339 .2727 |
| `lidar7` (7 LiDAR scarp bands) | 0.19028 | **1.009** | .1643 .1833 .1281 .2771 |
| uniform control | 0.18866 | 1.000 | — |

Frame `L-holdout` (the catalogue removed inside each fold, scored against that fold's
own labels, mass allocated by fold area):

| field | pooled DTI | per-fold lifts |
|---|---|---|
| `o19grad` | **0.22620** | 1.117 1.202 1.200 1.189 |
| `o19grad + lidar7` | 0.22501 | 1.109 1.204 1.180 1.192 |
| `o19` | 0.22142 | 1.113 1.148 1.155 1.159 |
| `lidar7` | 0.20520 | **0.991 0.991** 1.193 1.174 |
| `o12` | 0.19634 | 1.049 0.971 0.986 0.940 |

The two instruments disagree about the winner by less than their own spread, and
they agree on the two things that matter: the topographic-slope family is the signal,
and the LiDAR scarp family alone is not — it fails to beat a matched-mass uniform
scatter in the two largest folds on the labelled population. `o19grad + lidar7` was
frozen because it is within noise of the best on both instruments and hedges the
single-family risk.

## 2. The field's largest defect was not geological (`evidence/h59_decompose.json`)

The USGS 3DEP LiDAR scarp stack is undefined on 1,274,189 of 5,167,373 footprint
cells (24.7 %). Requiring every family to be finite therefore blanked a quarter of
the map. See pass-2 item B1 in `h59-deviation-log.md`: NaN-aware combination recovered
0.0382 DTI (0.17990 → 0.21812 at N = 180,000).

## 3. Which emission geometry? (`evidence/h59_emission_shapes.json`)

Frame `S_matched`, mass matched at 250,000 painted cells where possible, uniform
control matched to the painted count:

| emitter | painted | DTI | lift |
|---|---|---|---|
| field-weighted 3 px lattice (**frozen**) | 250,000 | **0.23991** | 1.272 |
| top-N blob painting | 250,000 | 0.20516 | 1.087 |
| skeleton of the thresholded field | 186,325 | 0.21674 | 1.228 |
| skeleton dilated to 3 px corridors | 838,641 | 0.14640 | 0.940 |

The dense-emission argument of §0 is therefore refuted in practice: blobs and
skeletonised lines both lose to spreading the dots in proportion to the evidence,
because the field ranks *cells*, not *traces*, and its highest cells form blobs.

## 4. Mask handling and lattice (`evidence/h59_final_select.json`)

| catalogue buffer | eligible cells | DTI at N = 250,000 |
|---|---|---|
| 0 px | 5,106,385 | 0.23016 |
| 1 px (**frozen**) | 4,983,788 | 0.23235 |
| 3 px | 4,722,579 | 0.24315 |

This table must **not** be read as "3 px is best". `S_matched` is defined as more
than 300 m from the catalogue, so on this frame a 300 m suppression can never lose a
truth pixel and always removes false-positive mass — the benefit is a selection
artefact of the frame. DrivenData staff ruled that known-fault pixels are excluded
from evaluation and do not count towards penalty terms, and that new-fault truth may
occur within 300 m of a known trace. The frozen buffer is 1 px. See pass-2 item A4.

| lattice | DTI | truth-side credit | false-positive mass |
|---|---|---|---|
| 2 px | 0.22620 | 21,190 | 238,319 |
| 3 px (**frozen**) | 0.23016 | 21,595 | 238,660 |
| 4 px | 0.22030 | 20,676 | 239,709 |

## 5. How many dots? (`evidence/h59_final_select.json`)

Coverage `c(N) = T/G` on `S_matched`, and the model DTI under the stated
coverage-transfer rule `T(N) = c(N)·G`:

| N | c(N) | model DTI at G = 8,000 | G = 16,000 | G = 52,219 |
|---|---|---|---|---|
| 60,000 | 0.1402 | 0.0602 | 0.0889 | 0.1326 |
| 120,000 | 0.2474 | 0.0643 | 0.1053 | 0.1890 |
| **180,000** | 0.3353 | 0.0625 | **0.1076** | 0.2154 |
| 250,000 | 0.4135 | 0.0580 | 0.1032 | 0.2247 |
| 320,000 | 0.4731 | 0.0532 | 0.0966 | 0.2231 |

180,000 minimises both the mean loss and the worst-case regret over the grid of
assumed hidden masses (mean regret 0.0024 DTI, against 0.0082 at 120,000 and 0.0038
at 250,000). The proxy's own optimum is 250,000.

## 6. The delivered artifact (`evidence/h59_build.json`, `h59_validation.json`, `h59_check.json`)

| quantity | value |
|---|---|
| file | `docs/downloads/gemsdoe50-h59-topo-lineament-scatter-180k-*-allfinite.tif` |
| bytes / SHA-256 | 629,906 / `ad9750be86acf6b8c253dcd8f1ee6487c2ea8327a582a8c9e6a765d16037d319` |
| geometry | 1 band float32, EPSG:32611, 3,730 × 3,292, 100 m, transform (243350, 4508550) |
| values | {0.0, 1.0}; 12,279,160 finite cells; 0 NaN; plain min/max in [0, 1] |
| predicted cells | 180,000 |
| cells on the supplied catalogue | 0 |
| cells outside the study footprint | 0 |
| cells shared with the 61-artifact prior union | 0 |
| worst 800 m block IoU vs 50 signature-pinned priors | 0.0407 |
| worst 3.2 km block IoU | 0.1106 |

| frame | truth px | DTI | per macrofold |
|---|---|---|---|
| `S_matched` | 52,219 | **0.21812** | 0.1945 / 0.2420 / 0.1224 / 0.2650 |
| `S_raw` | 61,664 | 0.23575 | 0.2105 / 0.2694 / 0.1224 / 0.2707 |
| `L` | 60,988 | 0.09327 | 0.0948 / 0.0845 / 0.1034 / 0.0918 |

Controls, all at matched mass 180,000: uniform over the whole footprint
0.16700 ± 0.0021 (lift 1.306); uniform over the artifact's own eligible pool
0.15072 ± 0.0019 (lift 1.447); paired 32 × 32 px block bootstrap candidate − uniform
mean **+0.0502**, 95 % interval **[+0.0418, +0.0576]**, positive in 400/400
replicates. Translations: +3 px 0.2197, −3 px 0.2202, +3 px across 0.2203,
−3 px across 0.2209, (+7,+7) 0.2136 — reported and explicitly marked
non-discriminative (§A3 of the deviation log).

## 7. The price of novelty (`evidence/h59_novelty_price.json`)

Same field, same mass, same seed, differing only in whether the registered
prior-artifact positive union is excluded from the emission pool:

| pool | eligible cells | DTI | cells that would have landed on a prior artifact |
|---|---|---|---|
| without the exclusion | 4,983,788 | 0.21917 | 51,114 |
| with the exclusion (**frozen**) | 3,886,785 | 0.21812 | 0 |

The uniqueness guarantee costs **0.5 % of the proxy DTI** — 51,114 dots moved off
prior-artifact cells for 0.00105 of DTI. That is the single cheapest novelty
constraint measured in this repository.

## 8. Comparison with the repository's earlier artifacts on one instrument

All rows measured with the same script and the same frame, matched-mass
whole-footprint uniform control:

| artifact | dots | `S_matched` DTI | uniform | lift |
|---|---|---|---|---|
| **H59 (this session)** | 180,000 | **0.21812** | 0.16700 | 1.306 |
| H56 scarp dispersion | 90,000 | 0.18647 | 0.12384 | **1.506** |
| H52-C eight-family coincidence | 80,000 | 0.14875 | 0.11522 | 1.291 |
| H51 scarp + radiometric | 35,000 | 0.11614 | 0.06414 | **1.811** |
| H55 seis-geometry ridge-snap | 13,591 | 0.02091 | 0.02762 | 0.757 |

Two readings of this table are both true and they disagree, so both are stated. In
*absolute* proxy DTI at its own validated operating point, H59 is the strongest
artifact in the repository. In *lift over a matched-mass control*, H56 and H51 are
higher — but lift falls steeply with mass for every field here, so a lift measured at
35,000 dots is not comparable with a lift measured at 180,000. The mass of H59 was
chosen by the regret rule in §5 precisely so that this comparison is not decided by
an arbitrary operating point.

## 9. What would falsify H59

* `S_matched` or `L-holdout` lift falling to ≤ 1.0 in a majority of macrofolds once
  the LiDAR stack's NaN region is handled honestly (already tested: it rises).
* The coverage-transfer rule failing: if the hidden truth is concentrated in a way
  the proxy is not, the 180,000-dot optimum is wrong and the artifact is over-spent.
  The remedy is the mass curve in §5, which can be re-read for any assumed `G`.
* The emission geometry being wrong for the hidden population: a truth set of long
  continuous traces would favour the skeleton emitter that lost here.

---

## Revision 2 (delivered): the sharpening screen, and the delivered file's own ceiling

Sections 1–8 above describe **revision 1** (unsharpened field, 180,000 dots, 0.21812 on
`S_matched`). It was superseded in the same session; the tables below are the delivered revision and
every number on the site is rendered from these files, so the two cannot be confused in the artifact.

### 9. A rank mean compresses the peaks (`evidence/h59_field_power_screen.json`)

Frame `S_matched`, one emitter, one seed, nested mass prefixes, 1 px catalogue buffer, eligible pool
4,930,382 cells. Rank-mean of the LiDAR scarp stack and the official band-19 gradient, at 90,000 dots:

| field assembly | 60k | 90k | 120k | 180k | credit/dot at 90k |
|---|---:|---:|---:|---:|---:|
| `rank-mean(lidar7, o19grad)` — revision 1 | 0.13415 | 0.17142 | 0.19515 | 0.22244 | 0.1162 |
| same, `^4` | 0.17529 | 0.21730 | 0.24463 | 0.27002 | 0.1479 |
| `o19_raw` alone | 0.13772 | 0.17449 | 0.19865 | 0.22533 | 0.1183 |
| `lidar_rankmean` alone | 0.09211 | 0.12076 | 0.14169 | 0.17181 | 0.0814 |

### 10. Where the exponent stops paying (`evidence/h59_sharpen_sweep.json`, `h59_sharpen_ext.json`)

| exponent | 60k | 90k | 120k | lift at 90k |
|---|---:|---:|---:|---:|
| `^2` | 0.15746 | 0.19790 | 0.22403 | 1.538 |
| `^4` | 0.17529 | 0.21730 | 0.24292 | 1.689 |
| `^6` | 0.18595 | 0.22942 | 0.25453 | 1.783 |
| `^8` | 0.18951 | 0.23066 | 0.25471 | 1.792 |
| **`^16` (frozen)** | — | **0.23406** | 0.25691 | **1.835** |
| `^32` | — | 0.22755 | 0.25323 | 1.784 |

The response is monotone to ^8, plateaus at ^16 and turns over by ^32, so the frozen value is the
plateau rather than the largest number tried. The proxy DTI keeps rising with mass to 250,000
(0.27864 at ^16 / 180,000) because the proxy's truth is four times denser than the hidden target and
therefore keeps repaying dots; the transfer model is what says where to stop, and it saturates at
90,000 for this field. Both readings are on the site.

### 11. The delivered bytes, measured directly (`evidence/h59_delivered_metrics.json`)

| quantity | value |
|---|---|
| painted cells | 90,000 |
| `S_matched` DTI | **0.23028** (folds 0.2072 / 0.2450 / 0.1394 / 0.2762) |
| `S_raw` DTI | 0.24917 |
| `L` DTI (negative control) | 0.03892 |
| truth-side credit `T` on `S_matched` | 14,090.4 |
| false-positive mass `FP_w` | 82,971.3 |
| coverage of the frame's truth | 26.98 % |
| matched-mass uniform controls | 0.12383 whole footprint (lift **1.86×**), 0.11134 same pool (lift **2.07×**) |
| paired block bootstrap | **+0.1041**, 95 % **[+0.0948, +0.1141]**, 400/400 positive |
| score at this coverage with zero false-positive mass | **0.31598** (the file realises 73 % of it) |
| coverage a perfect-precision 0.3774 needs | **32.66 %** |

The last two rows are the honest statement of the remaining gap. On this frame the file's ceiling at
its own coverage is below the 0.3774 target, so the target cannot be reached by precision alone: it
needs about 2,966 more proxy-truth pixels covered at no extra false-positive mass, which means a field
that finds fault pixels this one does not — not a re-spending of this one's dots.

### 12. The price of novelty, re-measured (`evidence/h59_novelty_price.json`)

| emission pool | eligible cells | DTI | lift | dots that would have hit a prior artifact |
|---|---:|---:|---:|---:|
| without the prior-union exclusion | 4,930,382 | 0.23184 | 1.842 | 28,811 |
| **with the exclusion (frozen)** | 3,854,609 | **0.22842** | 1.814 | **0** |

Cost of the uniqueness guarantee: **0.00343** DTI (**1.48 %**) for 28,811 of 90,000 dots moved off
prior-artifact cells — under two percent of the proxy score for a guarantee that is the standing
brief's first requirement.
