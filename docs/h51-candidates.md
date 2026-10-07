# Historical H51 candidate hypotheses

> **Superseded — do not treat the files or slot language below as current advice.** H51 outputs are archived; H53-A is NO-GO / NO SLOT. The current ranked proposals are in [`docs/research/h53-hypotheses-20261007.md`](research/h53-hypotheses-20261007.md). Historical local measurements are not organizer scores.

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
* **Source / rights.** The official GDR submission 1391 page lists CC BY 4.0, requiring attribution.
  The local files are sibling mirrors not byte-matched to the official assets, so their provenance
  and shareability for this challenge remain unresolved; do not use them until independently cleared.

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
* **Source / rights.** USGS ANSS Comprehensive Earthquake Catalog, https://earthquake.usgs.gov/fdsnws/event/1/.
  Public access does not resolve contributor-specific rights for this mixed-network extract; rights
  for challenge use and sponsor sharing remain unverified. Mechanism coverage also needs measurement.
  Do not use the staged extract until both data-rights and scientific gates are resolved.

## Historical H51 slot gate (superseded; not current authorization)

This paragraph records an earlier H51-era proxy rule only. Its four-fold comparison against a
matched random control did not establish transfer to the hidden competition labels and is not the
current promotion gate. Neither H51 file is slot-eligible. The current experiment, H53-A, is
**NO-GO / NO SLOT**; use the frozen H53 protocol and results—not this historical rule—to evaluate any
future experiment.
