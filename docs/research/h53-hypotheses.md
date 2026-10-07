# H53 candidate hypotheses, ranked — 2026-10-07

Charter rule: no detector code before this ranking exists. Each hypothesis names its exact
layers, physical signature, why it targets faults the USGS/INGENIOUS catalogue lacks, how it
differs from everything already implemented, expected DTI direction, implementation cost, and
the free official source plus obtainability. Ranking criterion: expected captured hidden
truth `T` per the H51 credit arithmetic (`G ≈ 12,226 px`), then cost, then license cleanliness.

Starting facts carried forward (see `docs/research/h51-analysis.md` and
`docs/research/h33-02778-study-20261007.md`):

- The repository-best file (`h33-h33-2-b2`, owner-quoted 0.2778) is **byte-identical to the
  0.2600 file minus its 6,436 dots within 2 px of the catalogue** — a dot-economy win, not a
  geological one. Beating it requires higher credit per dot (`T/N > 0.11`) or new coverage,
  not re-blending.
- The only layer with a positive robust score association in the 25-artifact corpus is
  TMI-lineament occupancy (ρ = +0.566, partial +0.534, p = 0.006); the corpus spends only ~5 %
  of its dots there.
- The archived seismicity-lineament artifact is the best independent-frame result in the
  project (`sgmc_off` DTI 0.1472, 2.5× uniform) — but its builder computed the background
  keep-mask and never applied it (documented defect), and it snapped corridors to the
  *terrain* ridge only.

---

## H53-C (rank 1) — TMI gradient-ridge × radiometric-K/U conjunction corridors

- **Layers.** `geodawn_extensions_u8.tif` band 4 (`TMI_up150`) + `geodawn_rad_u8.tif` bands
  K/Th/U/TC (USGS GeoDAWN, DOI 10.5066/P93LGLVQ, public domain). Bytes verified 2026-10-07
  against the pinned hashes (`c22420f7…` rad, `a35a9c6d…` extensions) from public sibling
  repository GEMSDOE24 commit `07345ea0` (GitHub, reachable from this sandbox).
- **Physical signature.** Faults juxtaposing rocks of different magnetisation/alteration
  produce *linear gradients*, not blobs: multi-scale gradient-magnitude geometric mean
  (σ = 1.5, 3.0 px) minus a 9 px moving-median ridge filter (edge/ridge transform), then a
  **conjunction statistic** keeping pixels where ≥2 of {TMI ridge, K ridge, U ridge} agree.
- **Why it catches a fault the catalogue misses.** The catalogue in this area is built from
  geologic mapping + LiDAR morphology; a steep basement fabric or alteration halo with no
  Quaternary scarp appears only in magnetics/radiometrics. The corpus's top end is one
  DEM/radiometric-ridge idea — this is the largest *unspent* physical layer.
- **Difference from prior work.** H47-B's TMI test thresholded upward-continued *amplitude*
  and lost to a random control; H46 fused radiometrics as a density prior; seislin used
  radiometric gradients only as an un-conjoined volume term. None used gradient-ridge +
  cross-channel conjunction. Never emitted.
- **Expected ΔDTI.** +0.02 … +0.06 if a ≥40 km unmapped strand is hit (≈1,000–1,400 credit
  px, the whole 0.26 → 0.32 gap at N ≈ 30–40 k); −0.01 if noise (exploratory dots cost
  `0.2·ΔN/(0.2N + 0.8G)`).
- **Cost.** Medium-low: `h51.gradient_lineament_response` exists; work is threshold
  calibration + slot-sized emission.
- **Source/license/obtainability.** USGS public domain, DOI 10.5066/P93LGLVQ; already fetched
  and hash-verified in this session. Viable.

## H53-B (rank 2) — Fixed declustered-seismicity corridors snapped to the TMI ridge

- **Layers.** ComCat origin parameters (license reviewed in
  `docs/research/comcat-license-review-20261007.md`: public-domain determination with
  attribution) + `TMI_up150` gradient ridge for the placement snap.
- **Physical signature.** Gardner–Knopoff declustering **plus the triangle-area keep-mask
  actually applied** (the seislin defect fix), per-neighborhood 2-D covariance eigen-ratio
  ≥ 9 with ≥12 events inside 3 km, corridor half-width from catalog `horizontalError`
  (median 0.36 km ≈ 3.6 px — a corridor prior, not a trace), centerline snapped ≤3 px to the
  TMI gradient ridge. The 2-D triangle reduction of the 3-D tetrahedron test
  ([Ouillon & Sornette 2011](https://doi.org/10.1029/2010JB007752)) stays explicitly
  **unverified**; the method is **not** ACLUD ([Wang et al. 2013](https://arxiv.org/abs/1304.6912)).
- **Why it catches a fault the catalogue misses.** Requires no surface expression, only a
  co-seismic alignment; background separation removes the Poisson scatter seislin kept, so
  far-from-catalogue corridors are cleaner.
- **Difference from prior work.** Seislin never applied its keep-mask, added Hough spans,
  and snapped to the terrain ridge. H53-B applies the mask, drops Hough, snaps to magnetics.
  New bytes by construction.
- **Expected ΔDTI.** Unknown, tail-heavy: the only line whose upside reaches the §9
  arithmetic (one 40–60 km strand = +1,200 credit px).
- **Cost.** Medium: pipeline exists (`gems50.catalog/decluster/lineation/emission`); work is
  the decluster fix + TMI snap + validation.
- **Source/license/obtainability.** ComCat FDSN service + TMI as above; both viable today.
  Known injection/mining sites removed by ComCat `type` (545 rows); no separate site
  inventory is obtainable here — recorded limit.

## H53-A (rank 3) — Fault-tip relay/stepover bridges snapped to TMI ridges

- **Layers.** `data/grid/labels.tif` (catalogue *geometry* only — its pixels are masked from
  scoring) + `TMI_up150` gradient ridge for corroboration/snap + SGMC only for exclusion.
- **Physical signature.** Structural topology, not a pixel filter: skeletonize catalogue
  traces → endpoints (tips) → bridge corridors between tips ≤2 km apart with compatible
  strike (±60°), extended ±750 m along the bridge axis, snapped ≤5 px to the TMI ridge.
- **Why it catches a fault the catalogue misses.** Regional inventories systematically
  under-map short transfer faults linking two long faults; the long faults are masked, the
  link is not. Grounding: Faulds et al.'s Great Basin structural inventory finds step-overs
  / relay ramps the most favorable setting (~32 % of ~250 systems) and terminations a top
  setting, explicitly including blind/hidden systems
  ([OSTI dataset 1148722](https://www.osti.gov/dataexplorer/biblio/dataset/1148722)).
- **Difference from prior work.** Nothing in any corpus family models *topology*; all are
  pixel filters, continuations, or thinning rules. Never implemented.
- **Expected ΔDTI.** +0.005 … +0.03 (low recall, high precision: few dots where a missed
  fault must exist topologically).
- **Cost.** Low: geometry only, CPU minutes.
- **Source/license/obtainability.** Competition data + USGS public domain. Viable.

## H53-D (rank 4) — Fault-bend dilatational-jog corridors

- **Layers.** `labels.tif` + scarp `step_max`/`lapneg_max` + `TMI_up150`.
- **Physical signature.** Along-trace curvature/deflection detector (bends >15° over <2 km
  on the skeletonized catalogue) → corridors on the extensional side of the bend (dilational
  jogs ⇒ fracture density ⇒ geothermal upflow; same Faulds inventory: "fault bends" a named
  favorable setting, [OSTI 1148722](https://www.osti.gov/dataexplorer/biblio/dataset/1148722)).
- **Why it catches a fault the catalogue misses.** Bend damage zones and horsetail splays
  extend hundreds of metres beyond the mapped single trace.
- **Difference from prior work.** No bend-geometry detector exists in the corpus lineage.
- **Expected ΔDTI.** +0.005 … +0.02. **Cost.** Low-medium.
- **Source/license/obtainability.** Same as H53-A. Viable. Ranked below H53-A because jog
  polarity (which side is extensional) needs slip-sense data we do not have, so half the
  emitted dots would sit on the compressional side.

## H53-E (rank 5, preregistered negative control) — QFaults-minus-catalogue discrepancy segments

- **Layers.** USGS Quaternary Faults (public domain) vs `labels.tif`, corroborated by
  TMI/scarp ridges within 300 m.
- **Physical signature.** QFault segments >300 m from the catalogue, kept only if a magnetic
  or scarp ridge corroborates them.
- **Why it would catch a missed fault.** By construction. **But** GEMSDOE32 already measured
  the newest public compilation as 59,065 px of which all but one lie within 300 m of the
  given catalogue — the discrepancy set is ~empty. Included as the control that should fail.
- **Expected ΔDTI.** ≈ 0. **Cost.** Low. **Viable** (QFaults public domain) but expected to
  stay unbuilt unless H53-A–D all fail their gates.

---

## Validation contract (frozen before implementation)

A hypothesis may only enter the fused H53 emission if, on the frozen `sgmc_off` frame
(SGMC fault pixels >300 m from the catalogue, unmasked domain, `scripts/h51_validate.py`
with `--layers data/external`):

1. its component dots beat the matched-count uniform control max **and** the translation
   control max (5 draws each);
2. on the 4-quadrant SGMCBlocked holdout (grid split into quadrants; each quadrant's
   `sgmc_off` pixels are proxy truth, scored with the official DTI at 300 m) it is positive
   in ≥3/4 folds against its own translation control;
   *(amended 2026-10-07 before any ship: the as-written CatBlocked version scored
   off-catalogue dots against catalogue truth, which is vacuous by construction — kernel
   range 3 px < 3 px clearance renders every fold DTI identically 0. The sgmc_off
   version tests whether off-catalogue coverage generalises across spatial blocks.)*;
3. (H53-B only, the prompt's falsification test) its corridors beat **both**
   smoothed-density controls (σ = 1 km, 2 km Gaussian on the same declustered events) on
   `sgmc_off` — geometry must beat density or the hypothesis is rejected.

The fused file must additionally pass `scripts/check_submission.py` (format ALL PASS +
`verdict_unique: true` against the full mounted corpus) with **zero shared pixels** against
every prior artifact as the target. No weekly slot is spent on any file that fails any gate;
a local proxy score is not an organizer score.
