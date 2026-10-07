# Archived five-candidate hypothesis inventory

> **Historical prior-work notes only — not the current H50-S1 preregistration, input approval, or submission plan.** This page preserves earlier candidate descriptions and owner-reported local proxy outputs. It has not been independently reproduced in this session; none of the reported values is an organizer score. The H50-A scarp derivative has no explicit repository reuse license and is excluded from current work. The mixed-network ComCat extract has unresolved source-specific rights and unverified `horizontalError` semantics. See [`data-rights-audit-20261006.md`](data-rights-audit-20261006.md) and the current [`hypotheses-preregistered.md`](../hypotheses-preregistered.md).

Every hypothesis below records the **layers**, proposed **physical signature**, rationale, and historical difference from earlier project work. The former ranking by estimated *DTI gain per implementation cost* is an archived judgment, not a current assessment. Earlier terms such as “validated,” “falsified,” and “submission” refer to reported local proxy exercises or legacy builder behavior only; they do not establish scientific validation, organizer scoring, or present eligibility.

Evidence classes in the archived records: `[OFFICIAL]` source information cited by the original notes, `[MEASURED]` local values reported from then-pinned bytes, `[FALSIFIED]` a historical local comparison reported negative, and `[PROPOSED]` not implemented at that time. These labels do not mean this session independently verified the results.

---

## H50-A — LiDAR scarp-dipole chains (archived candidate; excluded from current work)

* **Layers.** Owner-derived 12-channel 1 m-DEM scarp descriptor stack
  (`data/external/lidar_scarp_features_u8.tif`), decoded per its documented
  sqrt-quantisation: `ex_max, ex_mean, step_max, lapneg_max, lappos_max, downface_max,
  upface_max, cross_max, relief, coh100, strike, valid`. Derived from USGS 3DEP 1 m DEM
  (raw 3DEP products are public domain per USGS, but the derivative's license is not established; excluded from current H50-S1 work).
* **Signature.** `sqrt(step_max · max(upface_max, downface_max)) · sqrt(coh100 · valid)`
  — a *dipole* (a step with a consistent facing direction), then a 9-px, 16-direction
  collinearity vote that keeps only scarps continuing along a line.
* **Why it was proposed.** High-resolution terrain can preserve landforms much smaller
  than a 100 m competition pixel, so aligned scarp-like features might identify strands
  that regional compilations omit. Roads, channels, terraces, and other non-fault terrain
  breaks are important competing explanations; collinearity alone does not establish a fault.
* **Novelty.** In the earlier repositories the stack enters as per-pixel channels or as
  a single fused scalar; the *chain* (collinearity) vote on the dipole score is new, and
  so is its use as the dominant term of a metric-calibrated emission.
* **Archived local proxy report (not reproduced here).** Earlier repository notes
  reported, on an equal 44,090-dot SGMC frame, values of **0.0345** for scarp features,
  **0.0190** for uniform random, and **0.0043** for smoothed-300 m density; a separate
  70,000-dot comparison reported 0.0490, 0.0266, and 0.0084. These are local historical
  values, not competition scores or verified evidence of fault discovery. The input
  derivative's reuse rights are unresolved, so this candidate is not ranked or used by
  current H50-S1.

## H50-B — Mixed-source ComCat seismicity corridors (archived candidate; not approved for reuse)

* **Layers.** Legacy mixed-network USGS ComCat export (222,939 rows in and around the
  footprint, fetched through a GitHub-hosted runner; `data/external/usgs_comcat_earthquakes.csv.gz`).
  It contains multiple preferred contributors; source-specific rights and `horizontalError`
  units/statistical semantics are unresolved, so it is not approved for current H50-S1 use. Joined to the
  grid in EPSG:32611. The competition's own seismicity bands are unusable for this
  (`ieq_n100a15` has autocorrelation 0.9935 at 3 km: constant at the metric's scale).
* **Archived signature.** The legacy implementation clustered epicentres, then used each
  cluster's **full 2-D inertia tensor** to select linear groups and orient a corridor along
  its principal axis. It set corridor width using a converted `horizontalError` value whose
  units and statistical meaning are unresolved, so this is not calibrated uncertainty
  weighting. Background/clustered separation was attributed to Ouillon & Sornette (2011): the
  nearest-neighbour distance distribution is compared with a Poisson null of the same
  event count in the same rectangle (`r_c = 1.61 km` [MEASURED]); the 2-D **triangle
  area** of an event with its two nearest neighbours is the dimensional analogue of the
  3-D tetrahedron-volume statistic — **this adaptation is ours and unverified**.
* **Why it was proposed.** A fault without a clear surface scarp might still leave a
  clustered seismicity pattern. Whether the Monte Cristo sequence is an independent
  example of that mechanism requires a primary-source and geological review; the archived
  analogy is not validation of a predictive fault map.
* **Historical novelty claim.** Earlier repository notes described this as a first
  implementation in the project and referenced H33-E as data-blocked; that comparison has
  not been re-audited for this archived page.
* **Archived local comparison (not reproduced here).** Historical notes report that,
  at equal dot budgets, the corridors scored 0.0014/0.0036/0.0036 on a catalogue-fold
  frame and 0.0015/0.0034/0.0034 on an off-catalogue frame, versus the listed smoothed-
  density values. Those records described no consistent win over density, but are not
  organizer scores and are not independently re-run in this session. The archive proposed
  two possible explanations—aftershock-dominated clusters and a test frame far from active
  seismicity—neither of which is established by those numbers alone. A legacy builder once
  assigned a 0.25 weight to this field; that unlicensed, historical build is not the current
  submission and no such layer is used by H50-S1.

## H50-C — Multi-physics oriented-lineament consensus (archived candidate; not current H50-S1)

* **Layers.** Official bands `tmi` (14), `rtp` (2), `mag_anom` (1), `iso_grav_anom`
  (13), `cond_surf` (17), `depth_to_base_surf` (15), `det_elev` (12), `tilt_angle` (6).
* **Signature.** A scale-normalised Hessian line response (Sato-style eigenvalue
  difference, both polarities, σ = 1.2 and 2.5 px) per physics, multiplied by the
  second-order **orientation order parameter** `R = |Σ_p w_p e^{2iθ_p}|/Σ_p w_p` across
  physics: a pixel scores only if independent fields agree that a line exists *and which
  way it runs*.
* **Proposed rationale.** Independent geophysical layers may preserve complementary
  structural signatures; agreement in line orientation could help prioritize features
  not obvious in one layer. The assumption requires controls for correlated acquisition,
  processing artifacts, and terrain effects.
* **Novelty.** Earlier repositories contain per-band ridge responses and pixel-wise
  products; none requires independent physics to agree on an *orientation*.
* **Archived local proxy values (not reproduced here).** The old report described a
  catalogue-fold value of 0.0217 at 44,090 dots versus 0.0209 for random and 0.0112 for
  density, with an off-catalogue value of 0.0087 versus 0.0345 for scarp. The old fusion
  assigned a weight of 0.6. These comparisons are not competition scores, were not
  independently rerun here, and do not authorize use of the legacy scarp input.

## H50-D — Depth-resolved seismicity lineations (archived proposal; input rights unresolved)

* **Layers.** The archived mixed-source ComCat export, with hypocentral **depth** and
  magnitude; its reuse rights, field semantics, and completeness are unresolved, so it is
  not an approved data source for this proposed work.
* **Signature.** For each candidate corridor, take the events inside it, project them
  onto the vertical plane containing the corridor axis, and test (a) that the
  along-strike length exceeds the across-strike width in map view, **and** (b) that the
  depth distribution forms a plane (or a dipping line) rather than a diffuse cloud —
  i.e. the 3-D inertia tensor's smallest eigenvalue is close to the location-error
  variance.
* **Proposed rationale.** Depth might help distinguish some planar sequences from diffuse
  clusters, but aftershocks can themselves occupy planes, and catalog depths carry error.
  A 3-D fit would not eliminate the swarm confounder without declustering and uncertainty
  analysis.
* **Historical novelty claim.** Earlier notes stated that H33-E and H45 did not use this
  exact plane test; that prior-work comparison has not been re-audited here.
* **Archived cost estimate and expected gain.** Earlier notes called implementation low
  cost and expected a moderate gain, with a proposed equal-budget comparison against
  epicentre corridors and smoothed density. Those estimates are unverified; the required
  input is not approved for reuse, and the test has not been run under the current protocol.

## H50-E — Fluid-path alignment (archived proposal; dataset rights need review)

* **Layers.** Earlier notes proposed GDR 1391 (DOI 10.15121/1881483, reported there as
  CC BY 4.0) well/spring temperatures and chemistry, plus derived paleo-geothermal and
  volcanic rasters and competition feature bands. The item-level terms and provenance of
  those derived files have not been re-audited for this work; they are not current H50-S1
  inputs.
* **Signature.** Point-pattern alignment: fit straight lines through chains of thermal
  features (not a kernel density of them), and require the chain to coincide with a
  gradient ridge of the conductive-basement surface.
* **Proposed rationale.** Faults can provide permeability pathways in geothermal
  settings. A spatially coherent spring chain near a basement gradient could motivate a
  structural hypothesis, but would require independent geological review and controls;
  proximity alone does not identify a fault or establish productivity.
* **Novelty.** Earlier repositories tested vent *corridors* as density and
  basement-edge holdouts separately (H32-01, H32-05); the *alignment* of thermal points
  with a basement gradient ridge is a relational feature, and the well/spring chemistry
  table has never been used as a point pattern.
* **Archived cost estimate.** Described as low because prior notes claimed the files
  were present; availability and reuse rights have not been verified in this audit.
  **Expected gain.** Qualitative low-to-moderate proposal only; no test was run.

---

## Archived comparison table — not the current preregistered ranking

| archived rank | candidate | proposed inputs | physical rationale | historical novelty claim | historical cost / impact estimate | evidence in old notes |
| ---: | --- | --- | --- | --- | --- | --- |
| 1 | H50-A scarp-dipole chains | 12-band GEMSDOE24 scarp derivative | Aligned terrain breaks may flag small geomorphic lineaments | Chain vote on a dipole score | Low / moderate | Local proxy values reported, but not reproduced; reuse rights unresolved; excluded |
| 2 | H50-B seismicity corridors | Mixed-source ComCat extract | Seismicity may mark structures with weak surface expression | Earlier notes called it a first project implementation | Low / uncertain | Old proxy notes reported no consistent advantage over density; not re-run; rights unresolved |
| 3 | H50-C multi-physics lineaments | Eight competition feature bands | Multiple layers may carry complementary orientation evidence | Orientation agreement across layers | Low / uncertain | Historical local proxy values only; not re-run; not a current submission component |
| 4 | H50-D depth-resolved lineations | ComCat plus depth | Hypocenter depth may help characterize 3-D clusters | Prior notes described a new plane test | Low / speculative | Proposed only; not run under current protocol; data rights unresolved |
| 5 | H50-E fluid-path alignment | GDR spring data, derived rasters, feature bands | Spring chains near basement gradients may motivate structural review | Thermal point alignment with a gradient ridge | Low / speculative | Proposed only; data availability and item-level rights not re-audited |

The **current** three-candidate ranking is in [`hypotheses-preregistered.md`](../hypotheses-preregistered.md). None of the archived candidates above is an authorized H50-S1 input unless its data-rights, scientific, and source-provenance gates are independently resolved.
