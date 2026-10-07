# H52 diagnosis — why 0.2778 topped the corpus, and what beating 0.3774 actually requires

**Written** 2026-10-07 UTC, before the H52 build. Every number is labelled:
**[OFFICIAL]** read from the organizer's own page, **[MEASURED]** computed here from pinned bytes,
**[MODEL]** arithmetic from the published equations under stated assumptions, **[LIMIT]** a known
weakness. No live leaderboard value is read, polled or published here; `0.2778`, `0.3195` and
`0.3774` are the owner's own reported snapshots, as in `registry/h51_score_corpus.json`.

---

## 1. The metric is a coverage-per-cost ratio, and nothing else

**[OFFICIAL]** (problem description, read 2026-10-07):

```
k(d) = max(1 - d/R, 0),  R = 300 m = 3 px at 100 m
TP_w = sum_{g in G} max_{x: d(x,g)<=R} p(x) k(d(x,g))
FP_w = sum_{x: p(x)>0} p(x) [ 1 - max_{g in G} k(d(x,g)) ]
FN_w = sum_{g in G} [ 1 - max_x p(x) k(d(x,g)) ]
DTI  = TP_w / (TP_w + 0.2 FP_w + 0.8 FN_w + eps)
```

**[MODEL]** For binary predictions with `N` dots at unit height, the same `max` appears in
`TP_w` and `FN_w`, so `TP_w + FN_w = |G|` exactly and `FP_w = N - M` with
`M = sum over dots of k(d to nearest truth)`. Writing `T = TP_w`:

```
DTI = T / (0.2 N + 0.8 G)                                                       (1)
```

**[MODEL]** Two consequences decide every design choice in this repository.

* **A dot is worth its *credit*, not its existence.** Adding one dot changes the denominator by
  `0.2(1 + dT - dc)` where `dT` is the credit it newly captures and `dc` its own matched kernel
  weight; the dot pays iff `dT > 0.2 s (dT + 1 - dc)` with `s` the current DTI. At `s = 0.28` a
  dot must earn about `0.056` of credit — i.e. sit within ~283 m of a *hidden* truth pixel.
* **Coverage is the binding term.** `T <= G`. At `G` fixed, raising the score means raising `T`
  faster than `0.2 N`; a detector whose extra dots earn less than the bar lowers the score.

## 2. Why 0.2778 topped the corpus **[MEASURED + MODEL]**

Using the repository's calibrated hidden mass `G = 12,226 px` (the blind-lattice inversion of
`docs/research/h51-analysis.md` §2) and (1), each owner-quoted score gives an exact credit:

| artifact | score | N | `T = s(0.2N + 0.8G)` | `T/N` |
| --- | ---: | ---: | ---: | ---: |
| `dotted-h19-5 d2.8` | 0.2600 | 44,090 | 4,836 | 0.1097 |
| `dotted-h19-5 d1.5` | 0.2477 | 60,069 | 5,399 | 0.0899 |
| `h33-2-b2` (**repository best**) | 0.2778 | 37,654 | **4,809** | 0.1277 |
| `dual-family-union` | 0.1560 | 183,642 | 7,255 | 0.0395 |

**[INFERENCE]** `h33-2-b2` captured *the same* hidden truth as `d2.8` (4,809 vs 4,836, a 0.6 %
difference, inside the metric's own discretisation) while spending **6,436 fewer dots**. From (1)
the denominator difference is `0.2 x 6,436 = 1,287`, which is the entire score gap. **Its win was
dot economy, not geology.** Confirmed independently this session: re-downloading eight of the
hash-pinned artifacts and scoring them on an independent frame reproduces the same ordering by
dot count, not by detector.

**[MEASURED]** The winning *geometry* is measurable from the bytes. The best off-catalogue
performer in the group's history, `gems50-seislin-44709` (44,709 dots):

* **every dot is 8-connected-isolated** (44,709 components of size 1);
* nearest-neighbour separation is **3.0 px at the 10th, 50th and 90th percentiles** — exactly the
  metric's own support `R = 3 px`;
* the dots occupy **44 % of the map's 128 x 128 blocks**.

`R` is the metric's optimum separation: it is the coarsest spacing at which two dots never compete
for the same truth pixel, so no dot is charged `0.2` for credit another dot already earned.

## 3. The corpus's structural flaw: spatial over-concentration **[MEASURED]**

On the independent off-catalogue frame (USGS SGMC fault pixels > 300 m from the given catalogue,
61,664 px in a 5,106,385 px domain), selecting the **top 30,000 pixels** of a single evidence
layer and emitting them scores *worse than 30,000 uniformly scattered dots*:

| emission at N = 30,000 | off-catalogue DTI |
| --- | ---: |
| top 30,000 of `TMI_up150` gradient | 0.0144 |
| top 30,000 of radiometric-K ridge | 0.0331 |
| top 30,000 of LiDAR `step_max` ridge | 0.0235 |
| top 30,000 of radiometric-Th ridge | 0.0288 |
| **uniform random scatter (matched mass)** | **0.0578 - 0.0622** |
| archived `seislin-44709` (44,709 dots) | 0.1468 |
| **H52 at 90,000 dots** | **0.1874** |

**[INFERENCE]** Ranking by "strongest anomaly" is self-defeating here. `TP_w` is a `max` over
dots, so the 5th dot on the same fault adds almost nothing while `0.2 N` grows by 0.2 every time;
and the strongest anomalies are rich in non-fault edges (lithologic contacts, fan margins, roads,
mine benches). The corpus's whole family — scarp quantiles, ridge persistence, multilines,
topo-gap closure — uses this geometry, which is why 25 artifacts over five weeks plateaued between
0.15 and 0.28 and why the blind lattice at 0.0904 needed 206,895 dots to get there.

## 4. What 0.3774 requires, in credit pixels **[MODEL]**

From (1), and with `G = 12,226`:

| target | N | required `T` | required coverage `T/G` | required `T/N` |
| ---: | ---: | ---: | ---: | ---: |
| 0.2778 (repository best) | 37,654 | 4,384 | 35.9 % | 0.116 |
| 0.3774 (owner-quoted top) | 30,000 | 5,955 | 48.7 % | **0.199** |
| 0.3774 | 44,090 | 6,931 | 56.7 % | 0.157 |
| 0.3774 | 108,000 | 12,020 | 98.3 % | 0.111 |

**[INFERENCE]** The corpus's best *measured* `T/N` on the hidden frame is **0.1277** (`h33-2-b2`
itself). Every point of score above ~0.28 therefore needs either a detector roughly 1.6x more
precise at the same mass, or **the same precision sustained to ~98 % coverage**. Those are the only
two routes, and the repository has already proved that re-blending, re-spacing and pruning the
existing corpus cannot take either: its coverage ceiling is 0.593 and its `T/N` ceiling is 0.1097.

## 5. The proxy is not the target — and that is measurable **[MEASURED]**

The repository's own `evidence/h51_proxy_ranking_power.json` shows the off-catalogue instrument
ranks the 25 real scores at only `rho = +0.196` (p = 0.35): **no demonstrated power.** This session
quantifies the gap instead of guessing it. For the eight hash-pinned artifacts that could be
re-downloaded through the GitHub Contents API, compare

* their hidden credit-per-dot, from the owner-quoted score and (1), against
* their credit-per-dot on the off-catalogue frame, measured here with identical code,

and divide by the pure truth-density ratio `G_hidden / G_sgmc = 12,226 / 61,664 = 0.1983`:

| artifact | score | N | hidden `T/N` | off-catalogue `T/N` | transfer |
| --- | ---: | ---: | ---: | ---: | ---: |
| `dotted-h19-5 d2.8` | 0.2600 | 44,090 | 0.10968 | 0.1236 | 4.48 |
| `dotted-h19-5 d1.5` | 0.2477 | 60,069 | 0.08987 | 0.1014 | 4.47 |
| `topo-gap-closure-t-v2` | 0.2449 | 61,328 | 0.08804 | 0.1010 | 4.40 |
| `h19-5 mirror group-best` | 0.1922 | 121,131 | 0.05396 | 0.0592 | 4.59 |
| `h19-4 multiline-corroborated` | 0.1894 | 123,779 | 0.05285 | 0.0620 | 4.30 |
| `h16-1 topo-geophys ridges` | 0.1855 | 123,939 | 0.05174 | 0.0658 | 3.97 |
| `lidarscarp-ridge-top2pct` | 0.1461 | 76,859 | 0.04781 | 0.0546 | 4.41 |
| **blind lattice s5 (control)** | 0.0904 | 206,895 | 0.02235 | 0.1122 | **1.00** |
| `7GEMSDOE submission.tif` (dense) | 0.1563 | 1,828,699 | 0.03210 | 0.0120 | 13.45 |

**[INFERENCE]** The one *structureless* artifact transfers at **exactly 1.00** — the mathematical
expectation for a detector carrying no information, and a clean sanity check on the method. Every
*structured* artifact transfers at **3.97 - 4.59**, i.e. topography-based detectors are about
**4.4x more effective against the hidden (young, surface-expressed) fault population than against
the older bedrock faults that dominate the SGMC.** That is the quantitative statement of the proxy
mismatch, and it is why optimising on the off-catalogue frame alone is the wrong objective.

**The transfer factor is the single largest uncertainty in this repository's forward predictions.**
It is measured on the group's own detector family; applying it to a *new* detector assumes
comparable specificity. That assumption is unverified and is stated as such everywhere the number
is used. The conservatively rounded value used by the H52 build is **4.2** (band 3.97 - 4.59).

## 6. H52 — the detector and the emitter this diagnosis implies

Two changes follow directly from §2-§4.

**(a) Emission geometry.** Because `R = 3 px` is the metric's own optimum separation, H52 emits
with `h52.emit_blue_noise`: at most one dot per 3 x 3 block, the block chosen with probability
proportional to its belief mass, and the position inside the block at the highest-belief allowed
pixel. This is a variable-density blue-noise sample at exactly `R`. It cannot pile dots one pixel
deep on a ridge, and it cannot waste `0.2` on a dot whose credit a neighbour already earned.

**(b) The mass is chosen by the metric's own stopping rule, not by taste.** The build sweeps
30,000 - 220,000 dots and selects the mass maximising the transfer-calibrated modelled hidden DTI,
with the physical cap `T <= G`.

**Detector content.** The belief field combines

| component | role | measured | source | licence |
| --- | --- | --- | --- | --- |
| 3DEP LiDAR scarp descriptors `ex_max`, `step_max`, `lapneg_max`, `downface_max`, `relief`, rank-averaged then sharpened to the fourth power | the detector | enrichment 1.21-1.42 on the independent frame, the only family above 1.1 | USGS 3DEP 1 m DEM, 716 tiles | US public domain |
| declustered ComCat epicentre lineaments: 2-D covariance eigen-fit of each event's k-nearest neighbourhood, linearity gate, corridor half-width = the catalogue's own epicentral uncertainty | multiplicative corroboration, `belief *= (1 + 0.25 * corridor)` | 1,466 lineations from 91,394 declustered events; the multiplicative form lifts the modelled hidden score from 0.379 to 0.386 | USGS ANSS ComCat | USGS public domain; see §8 |
| GeoDAWN `TMI_up150` + K/Th/U ridge density | diagnostic only | enrichment 1.02-1.09: **no measurable information** | DOI [10.5066/P93LGLVQ](https://doi.org/10.5066/P93LGLVQ) | US public domain |

The seismicity corridor enters **multiplicatively as corroboration**, never as an additive
mixture, because the channel screen measures additive mixtures as strictly worse than either
component. Then the required **placement step**: each dot is offered to three independent ridge
targets -- the belief ridge, the GeoDAWN geophysical ridge, and the fused ridge -- and the
identity placement is kept when no snap improves the metric's own instrument. It did not:
unsnapped 0.1874, belief ridge 0.1629, geophysics ridge 0.1777, fused ridge 0.1660. The step is
executed and measured on every build; the numbers, not a preference, decide.

## 7. Results **[MEASURED]**

| quantity | value |
| --- | ---: |
| dots | **90,000** |
| off-catalogue DTI at that mass | **0.1874** |
| matched uniform control at the same mass (3 seeds) | 0.1401 |
| **lift over uniform** | **1.34x** (1.59x at 30,000 dots, 1.52x at 45,000) |
| archived `seislin-44709` (the previous best artifact on this frame) | 0.1468 |
| lift over the archived incumbent at matched mass | 1.28x |
| frozen macrofold holdout, off-catalogue truth | 0.1733 vs 0.1184 uniform; **4/4** macrofolds positive; paired block-bootstrap 95 % CI **[0.0261, 0.0854]** |
| beats translation controls | 4/4 folds |
| modelled hidden DTI (transfer 4.2, cap applied) | **0.386** |
| format gate | `all_checks_pass: true`; 12,279,160 / 12,279,160 cells finite and in `[0, 1]` |
| uniqueness gate | PASS — worst full-pixel IoU **0.0154** against every prior artifact on disk, minimum novel fraction at 2 px 0.4805, no SHA match |

**[LIMIT]** The modelled 0.379 is **not an organizer score and must not be read as one.** It is
`min(T, G)/(0.2 N + 0.8 G)` with `T` from a proxy measurement multiplied by an assumed transfer.
A 20 % error in the transfer moves the modelled value from 0.30 to 0.45; if the transfer were only
1.0 (the blind-lattice value) the model gives 0.12. The honest statement is: **the design is the
best-measured in this repository on the only independent frame available, and whether that
translates into a competitive leaderboard number is untested.**

## 8. Honest negative results recorded by this session

* **Seismicity lineaments do not measurably beat uniform on this frame.** Three parameterisations
  of the covariance-lineament detector (strict 325 lineations, mid 1,582, loose 5,510), emitted at
  110,000 dots, give off-catalogue DTI **0.1491 / 0.1518 / 0.1498** against a uniform control of
  0.1541 — i.e. `lift 0.96 - 0.99`. Under the *same* emitter, a plain rank-average of five LiDAR
  scarp descriptors gives 0.1969. The seismicity component is therefore kept at weight 0.20 in the
  shipped belief field as a documented physical-diversity bet, **not** because it measured well.
  The exact 2-D covariance geometry is used and is not the reason for the shortfall; the point
  pattern itself is neutral against this truth set. The owner's method is implemented, measured,
  and reported, which is the only honest way to record it.
* **Gardner & Knopoff declustering is unusable at this catalogue's magnitudes.** Its M1.5 window is
  `R = 14.8 km`, `T = 611 d`; applied to 214,438 events it removes **214,385 (99.98 %)**. The
  number is recorded in the build evidence rather than hidden, and the triangle-area test
  (2-D adaptation of the Ouillon-Sornette 2011 tetrahedron test, which keeps 97.0 %) is the
  declusterer actually used.
* **The strongest single-layer predictors are anti-correlated with the truth.** Rank-mean
  enrichment of the top 1 % of each layer against off-catalogue truth: `step_max` 3.13x,
  `ex_max` 3.13x, `relief` 2.30x, `inv_dist_to_catalogue` 1.71x, `TMI_up150` 0.72x,
  `U` 0.22x, **seismicity count 0.41x**, **seismicity density (10 px) 0.30x**. The competition's
  own "density of earthquakes" band is the *worst* single predictor tested, which is exactly why
  the owner's instruction to work from the point pattern rather than the density band is right in
  principle — even though the point-pattern geometry also came out neutral here.

## 9. What would actually be needed to beat 0.3774, stated plainly

1. **A trained model on the 19-band feature stack.** The competition ships surface conductivity,
   depth to conductive base, detrended elevation and its slope, GNSS strain-rate invariants,
   isostatic gravity and its slope, five magnetic products, a magnetic source-depth estimate and
   earthquake density at 100 m. **None of those are in this sandbox**: the DrivenData data tab is
   login-gated and its mirrors are network-blocked here. A U-Net trained with the official
   Tversky loss on that stack, emitted through the H52 geometry, is the most likely route to the
   *sustained* 98 % coverage that (1) requires.
2. **Precision at the 1-px scale.** `seislin` earns `k` at 1 px from truth 2.93x more often than
   chance while being *depleted* at 3 px. Since `k(0)=1`, `k(1)=0.67`, `k(2)=0.33`, the metric
   pays roughly 3x more for a 1-px-accurate prediction than for a 2-px one. Any future detector
   should be judged on 1-px enrichment, not on buffer coverage.
3. **A real submitted score.** One upload of the H52 file would convert the whole transfer-factor
   assumption into a measurement and add a 26th hash-pinned row to the corpus. That is the single
   highest-information action available to the owner, and it is the owner's decision, not this
   repository's.
