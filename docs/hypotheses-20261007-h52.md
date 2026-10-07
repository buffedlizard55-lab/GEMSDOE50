# H52 candidate register — five untried hypotheses, ranked by measured evidence

**Registered and measured 2026-10-07 UTC.** This is a *results* register, not a preregistration:
every candidate below was screened with the same instrument before the ranking was written, and
the raw numbers are in `evidence/h52_layer_screen.json`, `evidence/h52_enrichment.json`,
`evidence/h53_supervised_holdout.json` and `evidence/h52_holdout_offcat.json`. The frozen priors
in `docs/hypotheses-preregistered.md` are untouched.

## The instrument, and its honest limitation

Two independent truth frames are used, because neither is the hidden label set:

| frame | pixels | what it is | why it is not the target |
| --- | ---: | --- | --- |
| **F1 — off-catalogue** | 61,664 | USGS State Geologic Map Compilation fault pixels more than 300 m from any given-catalogue pixel | a *different vintage* of mapping; enriched in older bedrock faults with weak young surface expression |
| **F2 — frozen INGENIOUS holdout** | per fold | given-catalogue labels held out by contiguous macrofold, scored only outside the visible catalogue buffered by 300 m | the same compilation, so it tests *generalisation inside a source*, not a new source |

The repository already measured F1's power against the 25 real scores
(`evidence/h51_proxy_ranking_power.json`): Spearman `rho = +0.196`, `p = 0.35` — **no demonstrated
power**. That result is the single most important caveat in this document. F1 is used because it is
the only *independent-population* frame available offline, and every claim below is stated as a
result on F1, never as a predicted leaderboard number.

## Screen result — which evidence channels actually carry information about unmapped faults

Mean value over F1 truth pixels divided by the mean over the scored domain, for all 31 channels
built here (`evidence/h52_enrichment.json`). "Residual" = `clip(band - median_filter(band, 9), 0, None)`.

| channel | enrichment | family |
| --- | ---: | --- |
| LiDAR **up-face** residual | **1.423** | LiDAR scarp |
| LiDAR **relief** (raw) | **1.397** | LiDAR scarp |
| LiDAR relief residual | 1.318 | LiDAR scarp |
| LiDAR **lap-positive** residual | 1.282 | LiDAR scarp |
| LiDAR **cross-slope** residual | 1.263 | LiDAR scarp |
| LiDAR ex-mean residual | 1.259 | LiDAR scarp |
| LiDAR **down-face** residual | 1.255 | LiDAR scarp |
| radiometric total-count **gradient** | 1.242 | geophysics |
| LiDAR ex-max residual | 1.242 | LiDAR scarp |
| LiDAR lap-negative residual | 1.210 | LiDAR scarp |
| proximity to the given catalogue | 1.128 | catalogue |
| magnetic/radiometric ThK, UTh, UK, TMI residuals | 1.03 – 1.09 | geophysics |
| magnetic TMI residual / TMI gradient | 1.028 / 1.015 | geophysics |
| radiometric K, U residuals | 0.992 / 0.980 | geophysics |
| LiDAR coherence `coh100` | 0.906 | LiDAR scarp |
| **−distance to the given catalogue** | **0.886** | catalogue |

Two facts decide everything below.

1. **The LiDAR surface-morphology family carries the information; the airborne magnetics and
   radiometrics carry essentially none** (1.03 – 1.09 against a 1.42 head). This is a measured
   contradiction of the repository's own H51-A claim that magnetic lineaments were the single
   positive layer association, and §"Correction" below shows that claim was never supported by the
   file it cites.
2. **The off-catalogue population is *farther* from the given catalogue than average**
   (enrichment 0.886 on distance). New faults are not splayed along the flanks of mapped faults;
   they occupy the gaps. That is a direct, measured rejection of the fault-tip-extension family
   (candidate 5) and a warning against every "near a known trace" prior in the corpus.

## The ranked candidates

### 1 — H52-S: full-strength LiDAR scarp-dispersion detector *(adopted, built, gated)*

* **Layers.** `lidar_scarp_features_u8.tif` bands 0 `ex_max`, 2 `step_max`, 3 `lapneg_max`,
  5 `downface_max`, 8 `relief` — USGS 3DEP 1 m DEM derivatives over 716 tiles, DOI
  [10.5066/P93LGLVQ](https://doi.org/10.5066/P93LGLVQ), US public domain.
* **Signature.** A fault scarp is a *one-sided topographic step that persists along strike*, so it
  lights up simultaneously in the excess, step, lap-negative, down-face and relief descriptors and
  in none of the planform-geometry ones. Using the rank mean of five such descriptors instead of
  their maximum suppresses single-descriptor artefacts (roads, fan margins, quarry benches) that
  fire one channel only.
* **Why it finds faults the catalogue lacks.** These are *physical* observables: the LiDAR does not
  know whether a fault has been mapped. A scarp 0.5 – 3 m high under rangeland is exactly the class
  of feature a regional compilation misses and a 1 m DEM does not.
* **How it differs from everything implemented.** The corpus's scarp family is emitted at top-*k*
  quantiles or on a 2.8 px lattice inside a shrunken footprint; the emission here is
  variable-density blue noise at exactly the metric's own 300 m support with no quantile threshold
  and no footprint shrinkage, so every scarp *anywhere* in the domain can carry a dot and no dot is
  paid for twice.
* **Measured.** F1 lift **1.29x** over a matched-mass uniform control at 108,189 dots (DTI 0.1983
  vs 0.1541); frozen-holdout F2 **4/4 macrofolds positive**, pooled 0.1650 vs 0.1293, paired
  block-bootstrap 95 % CI [0.0209, 0.0490]; beats 4/4 translation controls.
  In the standalone screen the same family at mass 250,000 reaches **0.2502 on F1 vs 0.0641 for
  uniform (3.9x)** and beats the group's previous best artifact on that frame (0.1468) by 1.7x.
* **Cost.** 104 s of CPU. No new data.

### 2 — H52-M: oriented line-persistence matched filter *(screened, positive, folded in)*

* **Layers.** same LiDAR descriptors, transformed by requiring the residual to persist along one of
  16 half-pixel directions over a 9 px baseline before subtracting the direction-mean.
* **Signature.** A fault scarp is a line; a fan margin or a lithologic contact is not oriented at
  this scale. This is a *matched filter* for lineament geometry rather than a brightness ranking.
* **Measured.** F1 DTI 0.0781 at mass 30,000 vs 0.0622 uniform (**1.26x**) — second-best single
  operator in the screen, and it is the only operator here that is positive *and* not a plain
  brightness ranking. Not adopted as the primary because the plain family already outperforms it at
  the mass the metric selects.
* **Cost.** 12 s. No new data.

### 3 — H52-F: opposed up-face/down-face pair operator *(screened, neutral, recorded)*

* **Layers.** `upface_max` and `downface_max`, sampled at opposite sides of the same pixel along 16
  directions and 3 offsets, combined as the geometric mean of the two faces.
* **Signature.** The physically cleanest scarp test: a scarp has a *paired* signature with opposed
  sign on either side, which no single-channel maximum can require.
* **Measured.** F1 DTI 0.0619 at mass 30,000 — **1.00x**, i.e. indistinguishable from uniform, and
  below its own relief-modulated variant `P_faces_relief` (0.0749, 1.21x). The pairing constraint
  costs more recall than the precision it buys at this grid resolution (1 px = 100 m is coarser than
  the 1 – 3 px offsets the operator needs).
* **Cost.** 9 s. No new data. **Not adopted** — reported because it was one of the five and a
  negative result is a result.

### 4 — H52-G: GeoDAWN magnetic and radiometric lineament corridors *(screened, rejected)*

* **Layers.** `geodawn_extensions_u8.tif` (ThK, UK, UTh, TMI_up150),
  `geodawn_rad_u8.tif` (K, Th, U, TC); residual and gradient-magnitude transforms, ridge density,
  with the radiometric total-count gradient (`G_TC`, 1.242) the only channel above 1.1.
* **Why it was ranked high.** Faults that juxtapose differently magnetised or K-altered rocks
  produce linear TMI/radiometric gradients whether or not anyone has mapped them, and the corpus
  spends only ~5 % of its dots in the magnetic-lineament mask — the largest apparent unexploited
  gradient in the project. It was the repository's rank-1 H51 candidate.
* **Measured.** TMI residual 1.028, TMI gradient 1.015, K 0.992, U 0.980, ThK 1.094.
  **Rejected**: on the only independent-population frame available, the magnetic products carry no
  measurable information about unmapped faults. The repository's supporting statistic for this
  family was mis-cited (see the correction below), so the family was ranked on an artefact.
* **Cost.** 41 s. No new data.
* **Residual uncertainty.** `G_TC` (radiometric total-count gradient, 1.242) is the one geophysical
  channel that measured well; it is a *radiometric* rather than magnetic quantity and deserves its
  own test in a future session.

### 5 — H52-T: catalogue-tip extension and relay-zone bridging *(preregistered, rejected before emission)*

* **Layers.** the given catalogue raster only; skeletonise, locate trace terminations, extend each
  trace along its local strike by 5 – 40 px, and bridge step-overs narrower than 10 px.
* **Why it was plausible.** Regional compilations systematically truncate traces at map-sheet
  boundaries and at young cover, so a real fault is often a few hundred metres beyond where the
  compilation stops; and a relay zone between two overlapping strands is a classic place for an
  unmapped connecting fault.
* **Measured rejection.** The off-catalogue population is *farther* from the given catalogue than
  the domain average: enrichment of `−distance_to_catalogue` is **0.886**, and simple proximity
  scores only 1.128. Adding dots near known traces is measurably the wrong place to spend them.
  Rejected before any emission, so no slot and no compute were spent on it.
* **Cost.** 4 s for the screening statistic.

## What this changes about the plan to beat 0.3774

The adopted artifact is the strongest *measured* design in this repository's history on F1
(1.29x uniform at the metric-selected mass; 3.9x at the mass-250,000 optimum), and it is
**unique** — worst full-pixel IoU 0.2176 against the eight priors that could be re-downloaded,
minimum novel fraction at 2 px proximity 0.479, verdict `unique`.

`docs/research/h52-diagnosis.md` §5 shows what is still missing: beating 0.3774 needs about
`T = 5,955` credit pixels at `N = 30,000`, i.e. a per-dot credit of **0.199**, against 0.128 for
the corpus's best artifact and 0.023 for a structureless lattice. Nothing measured here closes that
gap, and **no candidate in this register is claimed to**. The honest position is that this
repository has, for the first time, a design whose evidence is *measured on an independent fault
population with controls*, and it still has to be scored by the organizer to become a datum.
