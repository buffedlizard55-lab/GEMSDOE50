# H55 preregistration — point-pattern seismic lineations and four independent alternatives

**Frozen:** 2026-10-07 UTC, before H55 code was written or any H55 proxy score was computed.  
**Decision criterion:** expected gain in distance-weighted Tversky index (DTI), then implementation
cost, then whether the input is already obtainable with a competition-compatible licence. A proxy
pass is necessary, not sufficient, and is never an organizer score.

## Source and rule gate recorded before implementation

* **Chosen earthquake source:** Trugman (2024), *Relocated Earthquake Catalog for Nevada
  (2008–2023)*, Zenodo record 11167510, DOI
  [10.5281/zenodo.11167510](https://doi.org/10.5281/zenodo.11167510), **CC BY 4.0**. The exact
  `nvreloc_catalog_newmag.txt` bytes are pinned by the record's MD5
  `38fa663f473378b61c74b597c53c416b`; `registry/nvreloc_catalog_receipt.json` records the API
  response, file size, licence identifier, and repository-copy hash. The paper is
  [DOI 10.1785/0220240106](https://doi.org/10.1785/0220240106).
* **Why this replaces ComCat as the geometry input:** the inherited ComCat CSV is a mixed-network
  export. Its official service URL is
  [USGS FDSN Event Web Service](https://earthquake.usgs.gov/fdsnws/event/1/), but this repository
  has not established contributor-specific reuse/shareability rights for all `nc`, `nn`, and
  other network records. It remains an exploratory comparator, not an H55 prediction input.
* **Competition rule:** the official problem page's
  [External datasets](https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/#external-datasets)
  section was previously recorded as requiring a licence that permits challenge use and sharing
  with the sponsor for evaluation. CC BY 4.0 permits sharing and adaptation, including commercial
  use, subject to attribution and change notice. The H55 artifact will disclose both.
* **Important limitation:** the relocated table has no event-specific location covariance. H55
  therefore will **not** claim to implement Wang et al.'s ACLUD or to know a per-event error. The
  corridor-width sensitivity (300/600/1,000 m) is an explicit assumption, and between-year axis
  stability is only an empirical robustness diagnostic. A result that depends on one assumed width
  is not slot-eligible.

## Ranked candidates not previously implemented in this repository

| rank | ID and exact layers | physical signature | why it can find a catalogue omission | difference from existing work | expected DTI / cost |
|---:|---|---|---|---|---|
| **1** | **H55-S1 — recurrent epicentre axes, ridge-snapped.** CC BY 4.0 relocated epicentres (`lat`, `lon`, `otime`, `mag`, `reloc=1`); GDR-1391 hot-well/spring points for a geothermal-activity exclusion; 3DEP scarp bands `step_max`, `lapneg_max`, `relief`, `coh100`; GeoDAWN K/Th/U/TC gradients. | First remove transient multiplicity by one largest-magnitude event per 250 m × 90-day cell. Apply a local-density-normalised **2-D nearest-neighbour triangle-area** background test against random catalogues (explicitly an unverified adaptation of the published 3-D tetrahedron test). Fit each retained, multi-year neighbourhood's full 2-D covariance; retain long, linear, well-sampled axes. Rasterize an uncertainty-sensitivity corridor, then snap its centreline **across**, not along, the axis to the nearest independent scarp/radiometric ridge with a continuity penalty. | A blind or buried active fault can organize hypocentres even when it has no mapped surface trace. Requiring multi-year support rejects a one-off aftershock cloud; independent ridge snapping asks whether the inferred axis has a plausible surface expression while all pixels within 300 m of the supplied catalogue are excluded. | Legacy H50-B computed but did not apply its triangle mask and mixed a global geophysical field into the output. H51-B used ComCat, an uncertainty model, and no ridge snap. H50-S1 fitted 3-D planes and projected them to `z=0`. H55-S1 instead applies the background mask, uses the licence-clean relocated catalogue, fits **2-D epicentre** geometry, tests recurrence and density controls, and uses a dynamic cross-axis ridge snap. | **Prior ΔDTI +0.01…+0.05 if transferable; tail risk high. Cost 3/5.** All inputs are already obtainable; no GPU. |
| **2** | **H55-G1 — magnetic curvature ridge × radiometric-ratio step.** GeoDAWN `TMI_up150` plus Th/K, U/K and U/Th; K/Th/U/TC as controls. | Hessian negative-curvature ridges on TMI after 500 m and 1,500 m numerical continuation, retained only where a radiometric ratio has a co-oriented step within 200 m. | Basement faults can juxtapose magnetic/lithologic domains beneath alluvium without a Quaternary scarp, so their potential-field edge can be absent from the surface-built catalogue. | Earlier H47 used TMI amplitude/persistence and H51 computed generic structure-tensor gradients. No artifact here uses a Hessian ridge at two continuation scales **AND** a co-oriented ratio edge. | **Prior +0.01…+0.04; cost 2/5.** Inputs are pinned USGS derivatives already available from GEMSDOE24. |
| **3** | **H55-B1 — basin-floor displacement edge.** Official feature bands `depth_to_base_surf`, `iso_grav_anom_hg`, `iso_grav_anom_vg`, and `cond_surf`. | Directional step of at least 150 m in modelled basement depth over at most 1 km, requiring a gravity-gradient maximum and conductivity contrast within 500 m. | A range-front or intrabasin fault can offset basement while recent alluvium hides its surface trace. | H51-C tested generic potential-field edges; this candidate uses a discontinuity in a modelled physical interface and an explicit displacement scale. | **Prior +0.005…+0.03; cost 3/5.** No new licence issue, but restoring the 419 MB competition stack is required. The pinned GitHub mirror is obtainable; organizer provenance remains mirror-consistency rather than a fresh authenticated download. |
| **4** | **H55-T1 — thermal-source-to-lineament conduit graph.** GDR 1391 hot springs/wells (`temp_c`, quartz/chalcedony/cation geothermometers), conductivity, and the H55-G1 ridge skeleton. | For each independently hot point, solve a minimum-cost path to the nearest structural ridge; keep straight, low-tortuosity path segments whose azimuth agrees with the regional normal-fault family. | A hot discharge point is direct evidence for permeability; an untraced segment between discharge and a geophysical boundary is a plausible concealed conduit. | H19/H51 used thermal points as a blurred favourability field. No implementation here constructs discrete, auditable conduit paths. | **Prior +0.005…+0.02; cost 3/5.** GDR 1391 is DOI 10.15121/1881483, CC BY 4.0, and the CSV is hash-pinned/obtainable. |
| **5** | **H55-FM1 — focal-mechanism strike Hough field.** USGS ComCat moment-tensor/focal-mechanism products plus relocated epicentres. | Accumulate both nodal-plane strikes in a depth-stratified Hough transform; retain a line only where nearby mechanisms resolve one plane consistently. | Mechanisms directly constrain fault orientation and can expose a blind seismogenic structure without morphology. | Every seismic artifact here uses event positions, not focal-plane solutions. | **Potentially high but presently not viable; cost 5/5.** Coverage in this footprint and contributor-specific product rights have not been established. It must not be promoted or implemented as a submission input until both are verified. |

## Frozen H55-S1 implementation and falsification gates

1. Use only `reloc=1` points inside finite template cells. Remove negative-depth rows and points
   within 2 km of a de-duplicated GDR `Hot` well/spring centre before fitting. Record all counts.
   The hot-feature mask is an incomplete geothermal-operation screen, not a complete injection
   history. A complete, date-matched mine/injection inventory is unavailable in this sandbox and
   remains a disclosed limitation.
2. Decluster by keeping the largest-magnitude event per 250 m cell per 90-day window; then apply
   the normalized 2-D triangle-area test. The 2-D test is this project's adaptation and must be
   labelled **unverified**, never attributed to Ouillon & Sornette as a published 2-D method.
3. Candidate axes require at least 10 retained events, at least three distinct years, covariance
   linearity `(lambda1-lambda2)/(lambda1+lambda2) >= 0.60`, 5th–95th-percentile length at least
   1.5 km, and bootstrap strike p90 at most 30 degrees.
4. Test corridor half-widths 300, 600, and 1,000 m as a **predeclared sensitivity**, not as three
   holdout-tuned models. H55-S1 passes only if the sign of its advantage is positive at all widths.
5. Score only dots more than 300 m from supplied catalogue pixels. Compare at matched mass with
   (a) Gaussian event-density maps at 1 km and 2 km, (b) translations, (c) matched uniform
   placement, and (d) the frozen current holdout incumbent
   `gems51-scarpradio-offcat-35000-20261006-ecf058ea-nan.tif`.
6. Spatial validation uses the frozen NW/NE/SW/SE cores in `evidence/holdout-v1.json` and SGMC fault
   pixels outside the catalogue buffer as the imperfect off-catalogue truth. Promotion requires:
   pooled DTI above the incumbent at matched mass; positive candidate-minus-incumbent credit per
   dot in at least 3/4 macrofolds; positive candidate-minus-density credit per dot in 4/4 folds;
   and a paired subtile bootstrap 95% lower bound above zero. SGMC is a proxy, not hidden truth.
7. Before a weekly slot, the GeoTIFF must be single-band float32, EPSG:32611, 3730×3292 on the exact
   template transform, finite and within `[0,1]` in the footprint, and pass full-resolution
   uniqueness against every retrievable prior submission. No portal upload is performed by code.

If H55-S1 fails any score gate, record the negative result and do not label it slot-eligible. If it
passes the numerical gates but the incomplete mine/injection screen remains, publish the unique
GeoTIFF for reproducible review while explicitly marking the external-confound gate unresolved.
