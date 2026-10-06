# Legacy candidate hypotheses — historical proxy record, not current ranking

> **Audit correction (2026-10-06):** This is inherited H50-A–E research history. Its local metrics are not the frozen H50-S1 four-macrofold holdout, not organizer scores, and not authenticated score-to-TIFF mappings. H50-B's 2-D ComCat lineation work is already implemented and is not new; source-specific ComCat rights are unresolved, and its triangle-area `keep` mask is not applied by the legacy builder. H50-D depth-resolved lineations were already proposed. The current 3–5-hypothesis review and H50-S1 eligibility decision are in [`hypothesis-ranking-20261006.md`](hypothesis-ranking-20261006.md) and [`earthquake-geometry-review-20261006.md`](earthquake-geometry-review-20261006.md).

The material below is retained to audit what the repository previously proposed and measured. It must not be used as a current ranking or submission claim.

Evidence classes such as `[OFFICIAL]`, `[MEASURED]`, and `[FALSIFIED]` describe the historical authors' labels only; they do not imply a current official score.

---

## H50-A — LiDAR scarp-dipole chains (rank 1 — implemented, validated)

* **Layers.** Owner-derived 12-channel 1 m-DEM scarp descriptor stack
  (`data/external/lidar_scarp_features_u8.tif`), decoded per its documented
  sqrt-quantisation: `ex_max, ex_mean, step_max, lapneg_max, lappos_max, downface_max,
  upface_max, cross_max, relief, coh100, strike, valid`. Derived from USGS 3DEP 1 m DEM
  (public domain).
* **Signature.** `sqrt(step_max · max(upface_max, downface_max)) · sqrt(coh100 · valid)`
  — a *dipole* (a step with a consistent facing direction), then a 9-px, 16-direction
  collinearity vote that keeps only scarps continuing along a line.
* **Why off-catalogue.** At 100 m a sub-metre scarp produces almost no signal, so
  catalogue compilations built from regional maps and 10–30 m DEMs systematically miss
  short, low-relief, en-echelon strands; at 1 m they are the clearest features on the
  landscape. Expert mappers accept a fault exactly when such scarplets are collinear.
* **Novelty.** In the earlier repositories the stack enters as per-pixel channels or as
  a single fused scalar; the *chain* (collinearity) vote on the dipole score is new, and
  so is its use as the dominant term of a metric-calibrated emission.
* **[MEASURED] validation** (equal 44,090-dot budget, SGMC off-catalogue frame, `F2`):
  scarp **0.0345** vs uniform-random control **0.0190** vs smoothed-300 m density
  **0.0043**; at 70,000 dots: **0.0490** vs 0.0266 (random at equal spread) and 0.0084
  (density). **Rank 1.** Cost: minutes, no new data.

## H50-B — Legacy seismicity-lineament corridors from mixed-network ComCat (already implemented; not new)

* **Layers.** A historical ComCat export with events from multiple contributing networks (222,939 rows in and around the
  footprint; `data/external/usgs_comcat_earthquakes.csv.gz`). Contributor-specific rights and
  competition shareability remain unresolved; this export is not cleared as an external competition input. Joined to the
  grid in EPSG:32611. The competition's own seismicity bands are unusable for this
  (`ieq_n100a15` has autocorrelation 0.9935 at 3 km: constant at the metric's scale).
* **Signature.** Ouillon–Ducorbier–Sornette (2008): cluster epicentres, then use each
  cluster's **full 2-D inertia tensor** to keep only linear, well-sampled clusters and to
  orient a corridor along the principal axis, with a width set by the catalogue's own
  location error. Background/clustered separation follows Ouillon & Sornette (2011): the
  nearest-neighbour distance distribution is compared with a Poisson null of the same
  event count in the same rectangle (`r_c = 1.61 km` [MEASURED]); the 2-D **triangle
  area** of an event with its two nearest neighbours is the dimensional analogue of the
  3-D tetrahedron-volume statistic — **this adaptation is ours and unverified**.
* **Why off-catalogue.** Instrumental seismicity is a *dynamic* inventory: a blind,
  low-slip fault lights up seismically while leaving no scarp (the 2020 M6.5 Monte
  Cristo Range rupture is the regional example).
* **Novelty correction.** The historical claim that this was the first implementation is withdrawn: the same 2-D ComCat covariance/lineation family and triangle-area code are already present in the repository, and H50-D depth-resolved lineations were already proposed. This is not a new detector.
* **Historical local proxy comparison (not the frozen H50-S1 holdout).** At equal dot
  budget on the legacy catalogue-fold frame the corridors score 0.0014/0.0036/0.0036 at
  5,000/20,000/44,090 dots against the smoothed-density baseline's
  0.0001/0.0041/0.0112; on the off-catalogue frame 0.0015/0.0034/0.0034 against
  0.0016/0.0023/0.0043. The corridor predictor therefore **does not beat smoothed
  earthquake density** on either available frame (it ties at best).
  Two structural reasons are recorded rather than hidden: (i) epicentre clusters are
  dominated by aftershock swarms, and (ii) the off-catalogue frame selects faults
  *far from the active catalogue*, which is precisely where instrumental seismicity is
  weakest — the frame is biased against this hypothesis by construction.
  The old artifact retained a low-weight corridor component (0.25) as a historical hedge. That choice is not a current recommendation, and the artifact is not a submission candidate.

## H50-C — Multi-physics oriented-lineament consensus (rank 3 — implemented, best on the catalogue frame)

* **Layers.** Official bands `tmi` (14), `rtp` (2), `mag_anom` (1), `iso_grav_anom`
  (13), `cond_surf` (17), `depth_to_base_surf` (15), `det_elev` (12), `tilt_angle` (6).
* **Signature.** A scale-normalised Hessian line response (Sato-style eigenvalue
  difference, both polarities, σ = 1.2 and 2.5 px) per physics, multiplied by the
  second-order **orientation order parameter** `R = |Σ_p w_p e^{2iθ_p}|/Σ_p w_p` across
  physics: a pixel scores only if independent fields agree that a line exists *and which
  way it runs*.
* **Why off-catalogue.** The catalogue is dominated by faults that were mappable in one
  dataset; requiring multi-physics strike agreement selects exactly the class that
  single-dataset mapping under-represents.
* **Novelty.** Earlier repositories contain per-band ridge responses and pixel-wise
  products; none requires independent physics to agree on an *orientation*.
* **[MEASURED]** Best field on the catalogue-fold frame (0.0217 at 44,090 dots vs 0.0209
  random, 0.0112 density) but weak off-catalogue (0.0087 vs scarp's 0.0345). Carried at
  weight 0.6 as the second term: it is the only component that improves the
  catalogue-frame score without changing the off-catalogue score materially.

## H50-D — Depth-resolved seismicity lineations (rank 4 — PROPOSED, data in hand)

* **Layers.** The same ComCat catalogue, but using hypocentral **depth** and magnitude,
  not just the epicentre.
* **Signature.** For each candidate corridor, take the events inside it, project them
  onto the vertical plane containing the corridor axis, and test (a) that the
  along-strike length exceeds the across-strike width in map view, **and** (b) that the
  depth distribution forms a plane (or a dipping line) rather than a diffuse cloud —
  i.e. the 3-D inertia tensor's smallest eigenvalue is close to the location-error
  variance.
* **Why off-catalogue.** It removes the dominant confounder of H50-B: swarms and
  aftershock clouds are diffuse in depth, whereas a fault plane is a plane. The 2-D
  epicentre test cannot make that distinction; the 3-D test can, and the catalogue has
  depth for every event (median 5.0 km, p90 10.4 km [MEASURED]).
* **Novelty.** No earlier repository used earthquake *depths*; H33-E and H45 were
  epicentre-only or depth-clustered without the inertia-tensor plane test.
* **Cost.** Low (data already fetched). **Expected gain.** Moderate — it is the
  best-justified repair of a falsified method, and its own falsification test is
  pre-specified: it must beat both the epicentre-only corridors *and* smoothed density
  at equal dot budget on the SGMC off-catalogue frame.

## H50-E — Fluid-path alignment (rank 5 — PROPOSED, data in hand)

* **Layers.** GDR 1391 (DOI 10.15121/1881483, CC BY 4.0) well/spring temperatures and
  chemistry (`gdr_wellspring_in_footprint.csv`), paleo-geothermal sinter/tufa
  (`derived_gdr_paleo_100m_u8.tif`), Quaternary volcanic vents
  (`derived_gdr_volcanics_100m_u8.tif`), plus `depth_to_base_surf` and `cond_surf`.
* **Signature.** Point-pattern alignment: fit straight lines through chains of thermal
  features (not a kernel density of them), and require the chain to coincide with a
  gradient ridge of the conductive-basement surface.
* **Why off-catalogue.** Faults are the permeability conduits of the Great Basin;
  a line of springs that follows a basement step is a structural trace even where no
  scarp survives. The catalogue records surface expression, not subsurface permeability.
* **Novelty.** Earlier repositories tested vent *corridors* as density and
  basement-edge holdouts separately (H32-01, H32-05); the *alignment* of thermal points
  with a basement gradient ridge is a relational feature, and the well/spring chemistry
  table has never been used as a point pattern.
* **Cost.** Low (all data on disk). **Expected gain.** Low-to-moderate; the falsification
  test is the same equal-budget one used above.

---

## Ranked decision table

| rank | hypothesis | layers | signature | off-catalogue reason | novelty | cost | validation |
| ---: | --- | --- | --- | --- | --- | --- | --- |
| 1 | **H50-A** scarp-dipole chains | 12-ch scarp stack | dipole × 16-direction chain vote | sub-100 m strands invisible to regional mapping | chain vote on the dipole score | minutes | historical local proxy; not current holdout |
| 2 | **H50-B** seismicity corridors | mixed-network ComCat, rights unresolved | 2-D inertia tensor + Poisson crossover | active blind faults are seismic | already implemented; not new | minutes | historical local density comparison; not frozen holdout |
| 3 | **H50-C** multi-physics lineaments | 8 official bands | Hessian line × orientation order parameter | single-dataset mapping misses what only multiple fields agree on | orientation agreement across physics | minutes | validated on catalogue frame only |
| 4 | **H50-D** depth-resolved lineations | ComCat + depth | 3-D inertia tensor plane test | kills the swarm confounder of H50-B | first use of hypocentral depth | minutes | pre-specified, not run |
| 5 | **H50-E** fluid-path alignment | GDR thermal + basement | line fit through thermal points × basement ridge | faults are the permeability conduits | thermal points used as a point pattern | minutes | pre-specified, not run |
