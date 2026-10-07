# H59 — preregistration (frozen before any H59 code was run)

Date: 2026-10-07 (UTC). Branch `arena/5550c3e4-gemsdoe50`, parent commit `09fdee9`.
Everything in this file was written **before** `src/gemsdoe50/h59.py` or
`scripts/build_h59.py` existed. Edits after the run are only allowed in the
"Post-run" section at the bottom and must be marked as such.

## 0. What is being decided

The holdout best is still **H57 scarpstep 80k**
(`docs/downloads/gemsdoe50-h57-scarpstep-80000-20261007T1830Z-allfinite.tif`,
SHA-256 `8027c4e9…`). The standing rule is: **do not spend a weekly slot on an
idea that has not beaten the current holdout best.** H59 decides, under
frozen rules, whether (a) the mandated seismic-lineation method, (b) a hybrid
of it with H57, or (c) a metric-algebra-motivated change of H57's emission
spacing beats H57 on the same frozen holdout.

## 1. Corrections that motivate H59 (verified numerically this session)

1. **The repo's metric collapse is wrong.** `docs/research/h56-diagnosis.md`
   eq. 1 and several docstrings state that, for dots spaced ≥ 3 px, the
   official score reduces *exactly* to `DTI = T / (0.2 N + 0.8 G)`. Running the
   repository's own `distance_weighted_tversky` on synthetic cases gives
   `DTI = T / (0.2 N + 0.8 G + 0.2 (T − M))`, where `M = N − FP` (the number of
   prediction cells with any truth within range): on-line dots at 3 px spacing
   score 0.6462, the "exact" formula says 0.6972. Equivalent and easier to
   use: `1/DTI = 0.2 + (0.2·FP + 0.8·G)/T`.
2. **"Spacing ≥ 3 px ⇒ no two dots compete" is false.** Two dots compete for
   a truth pixel whenever both are within 3 px of it, i.e. for spacing < 6 px.
   Per-dot credit on a straight truth line at spacing *s* px is
   1.0 / 1.667 / 2.333 / 2.667 / 3.0 / 3.0 for s = 1…6. Dots *on* truth cost no
   false-positive weight at any spacing, so the best spacing depends on how
   certain the placement is — which is exactly what H59-M tests.

Neither correction changes a frozen holdout number already reported (those
were computed with the official-equivalent implementation); they change the
*analytic* "required credit" tables and the design rationale.

## 2. Hypotheses, ranked by expected DTI gain per unit cost

| Rank | ID | Hypothesis | Expected Δ vs H57 on frozen holdout | P(beat H57) | Cost |
|---|---|---|---|---|---|
| 1 | **H59-M** | H57's own field, emitted with Chebyshev spacing 4 or 5 px instead of 3 (same 80k mass). Motivated by correction 2: a high-precision ridge chain wastes credit at 3 px. | +0.000 … +0.010 | 0.25 | very low (re-emission only) |
| 2 | **H59-H** | Hybrid: corridor-snapped seismic dots replace the *lowest-ranked* H57 dots at the same 80k mass. Wins iff seismic-corridor dots are more precise than H57's marginal dots. | −0.005 … +0.005 | 0.15 | low |
| 3 | **H59-S** | Mandated method, standalone: published nearest-neighbour declustering, location-error-deconvolved 2-D covariance lineations, epicentral **and up-dip-projected** corridors, ridge snap inside the corridor. | −0.10 … −0.02 (prior: H55, H58-S1 both lost) | 0.05 | medium |
| 4 | H59-T | Hydrothermal-proximity gate on H57 (experts may map preferentially near geothermal systems; fault-controlled upflow). Needs an official hot-spring/geothermal-feature inventory with coordinates (NOAA/USGS/GDR). | unknown | 0.15 | medium (data provenance) |
| 5 | H59-D | Step-over / fault-termination prior (Faulds & Hinz favourable structural settings) built from the supplied catalogue's fault tips. | unknown | 0.10 | medium |

H59-T and H59-D are **not run** in this session (recorded as next work).

### Why each could catch faults the catalogue misses, and how it differs from the repo
* **H59-M** — no new physics; it removes self-competition among H57's dots so
  the same evidence covers more distinct truth length. The repo never tested
  spacing because it believed 3 px was competition-free.
* **H59-H / H59-S** — blind or young faults that have not broken the surface
  still localise micro-seismicity at 2–15 km depth. On a dipping normal fault
  the surface trace sits `Δ = z / tan δ` up-dip of the hypocentral lineation
  (≈ 2.9 km for z = 5 km, δ = 60°), outside every epicentral corridor the repo
  has built (H55, H58-S1 used epicentres only — a likely reason both failed).
  The ridge snap then puts dots where a scarp or slope break exists inside the
  projected corridor.

## 3. H59-S construction (frozen constants)

Input: `data/external/usgs_comcat_earthquakes.csv.gz` (SHA-256 `19e726c8…`;
USGS ComCat via FDSN event service, https://earthquake.usgs.gov/fdsnws/event/1/).

1. **Event screen.** `type == "earthquake"`; magnitude ≥ 1.5; depth in
   (0.5, 20] km (depth ≤ 0.5 km is unconstrained or fixed); `horizontalError`
   ≤ 5 km, missing values imputed as 2.0 km (H58 precedent); `depthError`
   missing → 3.0 km. ComCat defines `horizontalError` as "the length of the
   largest projection of the three principal errors on a horizontal plane"
   (https://earthquake.usgs.gov/data/comcat/index.php#horizontalError) — a
   conservative scalar, *not* a covariance.
2. **Anthropogenic screen.** 3 km exclusion around every ComCat event typed
   as an explosion / quarry blast / mining-related event / induced event
   (H58 rule). Known limitation: no official injection-well or geothermal
   plant inventory is available offline, so the inventory is incomplete.
3. **Declustering — Zaliapin & Ben-Zion (2013), doi:10.1002/jgrb.50179.**
   Nearest-neighbour proximity `η_ij = t_ij · r_ij^df · 10^(−b·m_i)` for
   earlier events *i*, with `df = 1.6`, `b = 1.0`, times in years, distances in
   km; candidate parents = the 64 nearest epicentres plus every event with
   M ≥ 5. A two-component Gaussian mixture on `log10 η` sets the threshold at
   the density crossing; events with `η ≥ η₀` (no strong parent) form the
   declustered catalogue.
4. **Spatial background screen — 2-D triangle test, unverified adaptation of
   Ouillon & Sornette (2011), doi:10.1029/2010JB007752.** For each event, the
   area of the triangle formed with its two nearest neighbours; the reference
   is the same statistic on a catalogue whose x and y coordinates are
   independently permuted (keeps both marginals, destroys 2-D correlation).
   An event is *clustered* if its area is below the reference 5th percentile.
   (H58-S1 used "below the 95th percentile of a uniform-in-box reference",
   which kept 96.5 % of events — a test that rejects almost nothing.)
   **The 2-D adaptation of the 3-D tetrahedron test is mine and unverified.**
5. **Lineations.** For each kept event, its 12 nearest kept neighbours;
   inverse-variance-weighted 2-D covariance; location-error deconvolution
   `λ' = λ − σ̄²`, where σ̄² is the weighted mean squared horizontal error
   (2-D analogue of the Ouillon et al. 2008 planarity criterion λ₃ < Δ²,
   doi:10.1029/2007JB005032). Keep if: ≥ 8 events within 5 km;
   `λ2_obs ≤ 2.25 σ̄²` (thickness explained by location error at 1.5σ);
   `sqrt(λ1') ≥ 1.0 km`; elongation `sqrt(λ1/λ2) ≥ 3`. Lineations whose
   centroids are within 1 km and azimuths within 15° are merged.
6. **Corridors.** Along the principal axis for ±2·sqrt(λ1') (capped 10 km):
   * epicentral corridor (vertical-fault hypothesis), half-width
     `w_e = clip(σ̄, 0.2, 1.0) km`;
   * two up-dip corridors offset `Δ = z̃ / tan 60°` to either side
     (z̃ = median depth of the neighbourhood), half-width
     `w_u = clip(sqrt(σ̄² + (σ_z / tan 60°)² + (z̃ · 0.1745 / sin² 60°)²), 0.2, 2.0) km`
     (depth error and a ±10° dip uncertainty propagated).
7. **Placement (ridge snap).** Every 300 m along each corridor axis, the
   dot goes to the arg-max of the H57 belief field across the corridor
   (± half-width, 100 m steps) among eligible cells. Candidates are ranked by
   ridge value and accepted greedily with Chebyshev spacing ≥ 3 px, capped
   at **40,000** dots.
8. **Eligible cells.** Valid footprint, > 300 m from the supplied catalogue,
   not in the frozen prior-positive union (`registry/prior_positive_union.npz`,
   61 artifacts) **and** not on any positive pixel of the H56/H57/H58 files in
   `docs/downloads/` — zero exact overlap by construction.

## 4. Controls and frames (frozen)

Truth frame A (primary, as H57/H58): SGMC-off proxy, four frozen macrofold
cores from `evidence/holdout-v1.json`. Frame B (the prompt's "withheld
faults" test, seismic arms only): per macrofold, truth = supplied-catalogue
pixels inside the core; predictions may not use the in-fold catalogue
(exclusion buffer from the out-of-fold catalogue only).

All arms are scored with the repository's `distance_weighted_tversky`
(official-equivalent) at matched mass `M` = H59-S's realised dot count:
* **density control** — same declustered events, Gaussian density σ = 1 and
  2 km; the top-density eligible cells with the *same area* as the corridor
  union, then the same H57-ridge emission inside that support;
* **corridor-shaped random** — the corridor union translated by
  (±100, 0) and (0, ±100) px, same ridge emission;
* **H57 at matched mass** — `metric_emit(H57 belief, eligible, M)`;
* **H57 incumbent** — the shipped 80k file, as is.

## 5. Decision rule (frozen)

A candidate is **SLOT-ELIGIBLE** only if all hold on frame A:
1. pooled DTI > H57 incumbent pooled DTI (the current holdout best);
2. fold DTI > H57 incumbent in ≥ 3 of 4 macrofolds;
3. 95 % percentile CI (16 frozen subtiles, 5,000 paired bootstrap replicates,
   seed 55,007) of candidate − incumbent subtile DTI has a positive lower bound;
4. seismic arms only: pooled DTI above the best density control and above
   every corridor-shaped random translation; frame B DTI above density;
5. uniqueness: zero exact overlap with the prior union; for every prior raster
   in the full corpus, block IoU < 0.5 and novel-at-2 px fraction > 0.5 —
   except overlap with the never-submitted H57 file, which a superseding
   H57-derived candidate may share (reported, not gated);
6. compliance: ComCat-derived files additionally need the ComCat contributor
   rights question resolved (it is **not** resolved; see
   `docs/research/comcat-license-review-20261007.md` and README) — so H59-S
   and H59-H cannot be slot-eligible this session even if 1–5 pass.

If no candidate is slot-eligible: **NO SLOT**; H57 remains the recommended
file, and the H59-S file is shipped as a clearly labelled *do-not-submit*
research artifact (it is the mandated deliverable and is unique).

## 6. Post-run

*Added after the frozen run (2026-10-07). Nothing above this heading was changed.*

* **Outcome: NO SLOT.** Every arm fails gates 1–3 against the H57 incumbent
  (frame-A pooled DTI 0.2178): H59-S 0.0002 (326 dots), H59-H 0.2088,
  spacing 4 → 0.1866, spacing 5 → 0.1786. H59-S also loses to density on frame B
  (0.0007 vs 0.0093). Full table: `docs/research/h59-verdict-20261007.md`.
* **Deviation 1 (instrument).** Scoring used a vectorised re-implementation of
  `distance_weighted_tversky`; every pooled score was asserted equal to the
  original to 1e-9 (and a unit test covers masked folds).
* **Deviation 2 (uniqueness gate).** The strict 2-px rule of §5.5 fails for
  every file, including the 326-dot seismic file against dense priors, because
  it measures chance coverage. A chance-corrected refinement (containment and
  excess proximity) was added *after* seeing this; both versions are reported.
* **Design flaw found.** The frozen lineation rules (k = 12, deconvolved
  half-length ≥ 1 km) reject dense linear sequences by construction (2,008 of
  2,307 neighbourhoods failed on length). A post-hoc lenient variant
  (`evidence/h59_sensitivity.json`) removes it; the conclusion is unchanged.
* **Determinism.** Two rebuilds with `--stamp 20261007T205554Z` reproduce the
  TIFs and the zip byte for byte.
* **Citation note.** The `index.php#horizontalError` URL in §3 no longer reaches the
  field definition (the page is now a landing page; the CSV format page's own
  `data-eventterms.php#horizontalError` link redirects to the GeoJSON feed page).
  See flag F9 in `docs/research/h59-verdict-20261007.md`.
