# H51 candidate hypotheses

Written 2026-10-06 for the DOE GEMS Prize (DrivenData #306). Two parts:

* **Part 1** — the H51 candidates that have already been *measured* in this session, with their
  outcomes, so nothing here is proposed twice.
* **Part 2** — five candidate geological hypotheses that have **not** been tried, ranked by
  expected DTI improvement per unit of implementation cost.

The competition metric is the distance-weighted Tversky index
`DTI = TP_w / (TP_w + 0.2·FP_w + 0.8·FN_w)` with a 300 m triangular kernel, so a candidate is
only useful if it puts mass where *newly mapped* faults are, not where the provided catalogue
already is: catalogue pixels are masked out of the scored truth, and a prediction near a known
trace but far from new truth is fully penalised. Every candidate below is therefore also judged
on **how far from the given catalogue its evidence can sit**.

## Part 1 — already measured this session (do not repeat)

| id | one-line statement | outcome |
|---|---|---|
| H51-A | Corroborated LiDAR-scarp + radiometric lineaments (structure tensor), emitted only >300 m from the catalogue | **Shipped.** Best of the session on both independent instruments. |
| H51-B | Seismicity event-geometry corridors with a calibrated location-uncertainty width | Level with a matched random control on the off-catalogue instrument; not given mass. |
| H51-C | Depth-edge potential-field lineaments (tilt angle, vertical gradients, depth-to-base) | Below the random control on the off-catalogue instrument; not given mass. |
| H51-D | Thermal spring / well conduit anchoring (GDR 1391, INGENIOUS) | *Not measured* — carried forward as H52-C below. |
| H51-E | Orientation-concordance gate across all families | Reduced both instruments' scores; kept as a diagnostic only. |

## Part 2 — candidate hypotheses not yet tried

Ranking is expected DTI gain ÷ implementation cost. "Cost" is engineering time in this
repository: 1 = a few hours, 5 = a multi-day build with new external data.

### H52-A — Scarp-profile matched filter with drainage-deflection corroboration ★ top pick
* **Layers.** `lidar_scarp_features` bands 3 (`step_max`), 4 (`lapneg_max`), 9 (`relief`);
  `topo_u8` bands 2, 5, 6, 8; `training_features` band 12 (`det_elev`) and band 19
  (`det_elev_slope`) used to extract a drainage network.
* **Physical signature.** A *signed, azimuth-specific matched filter*: convolve detrended
  elevation with a bank of scarp cross-section templates (a step of 1–3 m over 5–30 m width,
  rotated through 180°), then require an independent hydrologic test — a stream channel that
  crosses the same azimuth line within 300 m and shows a lateral deflection or a knickpoint in
  `det_elev_slope`.
* **Why it catches a fault the catalogue misses.** The given catalogue is dominated by
  LiDAR-scarp picks and field mapping. A low-relief or degraded trace with no free face can fail
  a scarp-picking threshold while still deflecting every channel that crosses it; the *conjunction*
  of a weak-but-real topographic step and a hydrologic offset is exactly the evidence geologists
  use to map a fault that a scarp-only inventory omits.
* **Difference from what is implemented.** H51-A applies an orientation-agnostic structure-tensor
  gradient magnitude (a generic edge detector) and takes the max over layers. This candidate
  instead (i) matches the *expected scarp shape* rather than generic gradient energy,
  (ii) is azimuth-specific by construction rather than by a tensor azimuth, and (iii) requires a
  second, independent physical quantity (channel geometry) to agree — an AND that no GEMSDOE
  artifact implements.
* **Source if new data is wanted.** USGS 3DEP 1 m DEM and the USGS National Hydrography Dataset
  (both U.S. public domain, https://www.usgs.gov/3d-elevation-program and
  https://www.usgs.gov/national-hydrography). The 10 m products are already inside the official
  stack, so the candidate can be built with **no new data at all**; a 1 m run would need the 3DEP
  download, which is currently egress-blocked in this sandbox.

**Result (2026-10-07, implemented and validated — see `docs/h52a-protocol.md` Amendments B1/B2 for
full numbers): IMPLEMENTED.** `training_features.tif` turned out to be permanently unobtainable
this session (see "Errors & dead ends" discipline in the protocol doc), so the drainage half was
built from `topo_u8.tif`'s detrended elevation and `pysheds` D8 flow routing instead of the
originally proposed `det_elev`/`det_elev_slope` bands — a substitution, not a scope change. Built
as `scripts/build_h52a.py` / `src/gems51/scarpmf.py` + `src/gems51/drainage.py` (8 passing unit
tests in `tests/test_gems51_scarpmf.py` and `tests/test_gems51_drainage.py`). Standalone SGMC-off
DTI 0.0550 at mass 10,000 (lower than H51 alone because far fewer dots are emitted), but only 1.7%
of its cells overlap H51's — the lowest overlap of any candidate measured in this project. Unioned
with H51 (`scripts/build_h52.py`, no new tunable threshold) it raises pooled SGMC-off DTI from
0.1158 to **0.1518** (+31%), beats H51 in 3/4 spatially blocked macrofolds and the matched random
control in 4/4, with a paired bootstrap 95% CI entirely above zero. **Disclosure:** the union (H52)
is therefore a pixel superset of H51, ~78% of whose mass is H51's own prior output; H52-A alone is
the genuinely new, independently-scored artifact. See Amendment B2 for the full honest accounting
before treating either file as a submission candidate.

### H52-B — Basement-depth step (basin-margin) lineaments
* **Layers.** `depth_to_base_surf` (band 15), `cond_surf` (band 17), `iso_grav_anom` (band 13)
  with `iso_grav_anom_vg`/`hg` (bands 11, 18).
* **Physical signature.** Directional derivative of the *depth-to-basement surface* along azimuth
  θ, requiring a step of ≥150 m over ≤1 km; corroborated by a gravity horizontal-gradient
  maximum within 500 m.
* **Why it catches a missing fault.** Basin margins in the Basin and Range are fault-controlled,
  and a fault that has no Quaternary surface expression still offsets the basin floor — a step
  that appears in a depth-to-basement model but not in a scarp inventory.
* **Difference.** H51-C tested generic potential-field anomaly *edges*; this uses a *modelled
  physical interface* and a slip-magnitude criterion, which is a different quantity (depth
  discontinuity, not anomaly gradient) and is only valid inside the basins, where H51-A's scarp
  evidence is weakest.
* **Source.** None — every layer is in the official stack.

### H52-C — Spring / well conduit segments (carried from H51-D)
* **Layers.** `data/external/gdr_wellspring_in_footprint.csv` (GDR submission 1391), the INGENIOUS
  2 m temperature-probe and paleo-geothermal grids, `cond_surf` (band 17).
* **Physical signature.** Straight-line conduit between each thermal spring/well and the nearest
  mapped structure, kept only where its azimuth agrees within 20° with a topographic or
  radiometric lineament and where it lies >300 m from the catalogue.
* **Why it catches a missing fault.** Springs are hard evidence of a plumbing system; the part of
  a conduit that no map shows is the best available hypothesis for a concealed fault.
* **Difference.** H19-4/H19-5 used the GDR thermal evidence as one term of a favourability
  *field*; this inverts it into discrete conduit *segments* anchored on the nearest structure,
  which changes both the geometry and the failure mode (it can be wrong per spring).
* **Source.** Geothermal Data Repository submission 1391 and the INGENIOUS project (free to
  redistribute with attribution; both already mirrored under `data/external/`).

### H52-D — Coincident DEM slope break + radiometric ratio step
* **Layers.** `radiometric_u8` bands 1–7 (K, Th, U, TC and the Th/K, U/K, U/Th ratios),
  `geodawn_rad_u8` bands 1–4, `topo_u8` slope/curvature bands, `geodawn_extensions_u8`.
* **Physical signature.** An AND of two independent edges at the same azimuth: a slope/curvature
  break in the DEM **and** a step in a radiometric ratio (Th/K or U/K) within 200 m.
* **Why it catches a missing fault.** Alluvial-covered faults express themselves as a subtle
  topographic break plus a change in the exposed lithology/soil radionuclide budget; the ratio
  bands normalise out the gross lithology so the step is more specific than a raw count edge.
* **Difference.** H51-A ORs the families together (a max/weighted sum); this candidate requires the
  two to coincide, which suppresses the pattern-matching false positives that H51-A's `radiometric`
  family can emit on its own.
* **Source.** None — the radiometric extensions are already in the official stack.

### H52-E — Focal-mechanism nodal-plane lineaments
* **Layers.** USGS ComCat `moment-tensor` / `focal-mechanism` products for events in the
  footprint (the local CSV is the same FDSN event service the project already uses).
* **Physical signature.** Hough accumulation over nodal-plane strikes (two planes per mechanism,
  weighted by the mechanism's quality and magnitude), split by depth band, keeping peaks where
  the two planes of one mechanism cancel to a single strike.
* **Why it catches a missing fault.** A mechanism gives the fault's *orientation* directly, and a
  blind fault with mechanisms but no surface trace is precisely a catalogue omission.
* **Difference.** H51-B used epicentre geometry only (locations, no orientations); nodal planes
  carry information that is not in any epicentre pattern.
* **Source.** USGS ANSS Comprehensive Earthquake Catalog (public domain,
  https://earthquake.usgs.gov/fdsnws/event/1/). Caveat to measure first: most events in this
  footprint may not have a published mechanism, in which case the candidate is not viable.

## Part 3 — forward-looking H53+ candidates (2026-10-07, from the geothermal-vent research pass, NOT YET PREREGISTERED OR IMPLEMENTED)

These two candidates came out of the deep-research pass in
[`docs/research/geothermal-vents-20261007.md`](docs/research/geothermal-vents-20261007.md). Neither
has an instrument score, a preregistration, or a holdout result. Both are blocked on fetching free,
officially licensed data this sandbox could not reach this session (confirmed `SSL_ERROR_SYSCALL` to
`gdr.openei.org`/`sciencebase.gov`, same ceiling as `training_features.tif`) — list them here rather
than implement on faith so a future session (or the human owner, from a normal network) can fetch the
named files first.

### H53-A — Paleo-geothermal-feature / vent corroboration gate
* **Layers.** A new candidate corridor/dot field from any already-implemented family (H51-A scarp,
  H51-B radiometric, H52-A scarp+drainage), corroborated by INGENIOUS's **Quaternary Volcanics**
  (vent points, `great_basin_q_volcanics.zip`) and **Paleo Geothermal Features** (tufa/sinter,
  `paleo_geothermal_regional.zip`) point layers from GDR submission 1391 (CC BY 4.0).
* **Physical signature.** A candidate dot is up-weighted (not created from scratch) if it falls
  within a calibrated radius of a mapped Quaternary volcanic vent or paleo-spring deposit, on the
  reasoning in Faulds et al.'s Astor Pass case study that these features mark buried fault
  intersections directly (`docs/research/geothermal-vents-20261007.md` §1, §3).
* **Why it catches a fault the catalogue misses.** A vent or tufa tower with no currently mapped
  fault beneath it is itself a missed-fault indicator independent of this project's topographic or
  radiometric physics — a genuinely different evidence class.
* **Difference from what is implemented.** Every current family (H51-A/B/C, H52-A) derives evidence
  from continuous raster physics (gradients, matched filters, flow routing). This is the first
  candidate in this project's history to use discrete, independently mapped point features as a
  corroboration gate.
* **Source and obtainability.** GDR submission 1391 (CC BY 4.0, DOI 10.15121/1881483),
  <https://gdr.openei.org/submissions/1391>; direct files
  `https://gdr.openei.org/files/1391/great_basin_q_volcanics.zip` and
  `https://gdr.openei.org/files/1391/paleo_geothermal_regional.zip`. Confirmed free and license-
  compatible; **not fetchable from this sandbox** (network egress blocked to this host this
  session) — must be downloaded by a session/host with normal internet access.
* **Expected gain / cost.** Low-to-medium expected gain (corroboration gates have historically
  moved this project's metrics by single-digit percent, cf. H51-E), low cost once the two shapefiles
  are in the workspace (a point-in-radius join, no new model).

### H53-B — Substituted basement/potential-field bands for the blocked H52-B candidate
* **Layers.** USGS data releases **"Elevation Trend and Detrended Elevation"**
  (<https://doi.org/10.5066/P9MQRCBY>) and **"Geophysical Maps — Gravity and Magnetics"**
  (<https://doi.org/10.5066/P9Z6SA1Z>), both produced for the same INGENIOUS/Great Basin study area.
* **Physical signature.** Identical to the already-preregistered H52-B (basement-depth step
  corroborated by a gravity horizontal-gradient maximum) and the originally proposed H52-A drainage
  half — the only change is the *source* of the `det_elev`/`det_elev_slope`-equivalent and
  magnetic/gravity bands, substituting these two independently published USGS data releases for the
  unobtainable `training_features.tif`.
* **Why it catches a missing fault.** Unchanged from H52-B's original rationale: basin margins are
  fault-controlled even where there is no Quaternary surface scarp.
* **Difference from what is implemented.** This is not a new physical hypothesis; it is a *data-access
  unblock* for an already-ranked, not-yet-implementable candidate. Recorded separately so the
  distinction between "new idea" and "old idea, new data path" stays auditable.
* **Source and obtainability.** Both are USGS ScienceBase data releases (U.S. public domain).
  Confirmed to exist and be correctly described via `fetch_page` this session; **not fetchable from
  this sandbox** (same `sciencebase.gov` SSL block as every other non-GitHub host tested). Must be
  downloaded by a session/host with normal internet access before this candidate can move past
  "named and confirmed obtainable."
* **Expected gain / cost.** Unknown until measured — H52-B's own ranking already estimated this as
  the second-highest-expected-gain untried candidate; cost is medium (new band ingestion, reuse of
  the already-written `scarpmf.py`-style matched-filter and gradient code).

## Rule before spending a weekly slot

No candidate may be submitted on instrument scores alone. The top candidate must first pass the
same spatially blocked validation the shipped file did
(`scripts/validate_h51_holdout.py`, `evidence/holdout_h51.json`): its advantage over a
matched-mass random control must be positive in every frozen macrofold and the paired subtile
bootstrap lower bound must clear zero. A candidate that fails is recorded as a negative result
and the slot is not spent.
