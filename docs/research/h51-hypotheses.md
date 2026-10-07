# Historical H51 candidate hypotheses, ranked

> **ARCHIVE ONLY — all H51/H52 rankings, expected-score estimates, and slot language below are superseded.** H51 artifacts are not current submission recommendations; H53-A is **NO-GO / NO SLOT**. The old score-corpus and hidden-truth calculations rely on owner/sibling records that are not authenticated to organizer receipts or TIFFs. They do not validate seismicity, predict the private test, or authorize a slot. See the [current four-hypothesis H53 ranking](h53-hypotheses-20261007.md), [current score review](h33-score-review-20261007.md), and [project overview](../../index.html).

The ranking criterion below is preserved as historical context. Its hidden-truth `T` and expected
score reasoning came from the conditional model in `docs/research/h51-analysis.md`; that model's
inputs and score-to-TIFF mappings are unverified. It is not evidence about actual private-test truth
or a current ordering. The active ranking is the H53 four-way review linked above.

Every hypothesis must answer the same question: *why would this find a fault that the
USGS/INGENIOUS catalogue does not already contain?* The catalogue pixels are masked out of
scoring, so reproducing them is worth exactly nothing.

Historical exploratory starting point (`evidence/h51_residual_alignment.json`,
`evidence/h51_consensus.json`, 25 raster hashes paired with owner-reported score values). The files
are hash-identified, but scores and their organizer receipts/mappings were not independently verified; correlations below are corpus-internal, not predictive validation:

* the fraction of an artifact's dots inside the TMI-lineament mask is the **only** layer alignment
  with a positive, robust association to score: raw `ρ = +0.566` (p = 0.003), partial controlling
  `log10 N` `+0.534` (p = 0.006);
* the corpus spends only ~5 % of its dots there (prevalence 5.0 %), so it is exploiting that
  evidence no more than chance;
* extreme LiDAR-scarp quantiles are **negatively** associated with score in this corpus
  (`ex99`: `ρ = −0.722`, partial −0.620, p = 0.001; `step99`: −0.802) — the group's scarp-quantile
  families are the ones that plateaued at 0.09–0.16;
* the three highest-scoring artifacts are almost identical in all eleven measured alignments,
  i.e. the corpus's top end is **one idea**, not several.

---

## H51-A (rank 1) — Magnetic-lineament corridors on upward-continued TMI, corroborated by K/Th/U gradients

* **Layers.** `data/external/geodawn_extensions_u8.tif` band 4 (`TMI_up150`, the upward-continued
  total magnetic intensity, DOI 10.5066/P93LGLVQ) plus `data/external/geodawn_rad_u8.tif`
  (K, Th, U, total count). Both are official USGS/GeoDAWN products, public domain, already in the
  repository with byte-grid identity to the competition raster.
* **Physical signature.** A fault that juxtaposes rocks of different magnetisation produces a
  *linear gradient* in TMI, not a blob: compute the multi-scale gradient-magnitude geometric mean
  (σ = 1.5, 3.0 px) and subtract a moving median (9 px ridge filter) — an **edge/ridge transform**
  that keeps thin linear gradients and removes the regional field. Corroborate with the same
  transform on K and U; keep only ridges where at least two of the three channels agree.
* **Why it targets unmapped faults.** The TMI ridge is a *physical* lineament observable
  regardless of whether anyone has mapped a fault there; the published catalogue in this area is
  built mainly from geologic mapping and LiDAR morphology, so magnetic lineaments that lack a
  surface scarp are a population it might under-represent. In this historical corpus, ridge overlap
  was associated with owner-reported scores, but the correlation does not establish causation or
  hidden-test transfer.
* **How it differs from everything already implemented.** H47-B's `TMI_up150` test used a
  *persistence* filter on the upward-continued field (a value threshold) and lost to a random
  control; H46 fused radiometrics as a density prior. Neither used the **multi-scale
  gradient-ridge transform with cross-channel corroboration**, and neither combined it with the
  metric-aware dot geometry. The corpus's scarp-quantile families (`ex95/ex99/step95/step99`) are
  a different physical quantity (surface relief), which is precisely the one that shows a
  *negative* association here.
* **Historical expected DTI (unvalidated scenario, superseded).** The old model proposed
  `+0.02 … +0.06` if a long unmapped strand were hit, with a possible negative delta if exploratory
  dots were noise. These figures depend on unverified corpus inputs and are not empirical results,
  current forecasts, or a basis for a slot.
* **Cost.** Medium: the transform is implemented (`h51.gradient_lineament_response`), the layers
  are in-repo, and the only new work is threshold/corroboration calibration on the blocked holdout
  and a slot-sized emission.
* **Data, licence, obtainability.** Official GeoDAWN metadata lists source data as CC0 1.0 (DOI
  10.5066/P93LGLVQ), but the local quantized sibling mirror was not independently rebuilt or byte-
  matched to the official files. The official licence does not settle provenance or sponsor-sharing
  rights for the local derived raster; that remains a blocker. State-map products are historical
  context, not cleared input for this proposal.

## H51-B (rank 2) — Cross-layer lineament conjunction (order-2 and order-3 conjunctions)

* **Layers.** `lidar_scarp_features_u8.tif` (`ex_max`, `step_max`, `lapneg_max`, `downface_max`),
  `geodawn_extensions_u8.tif` (TMI, Th/K), `geodawn_rad_u8.tif` (K), `gdr_wellspring_in_footprint.csv`
  (1,873 hot springs/wells), `derived_sgmc_faults_100m_u8.tif` (for *exclusion*, not for targets).
* **Physical signature.** Not a new transform: a **conjunction statistic**. Score each pixel by the
  *number and ordering* of independent lineament families that pass through it (magnetic ridge,
  radiometric ridge, scarp ridge, spring alignment), then keep only pixels above a conjunction
  order that is rare in the catalogue's own buffer — i.e. lineaments that are independently
  supported but *not* accompanied by a mapped trace.
* **Why it targets unmapped faults.** Single-layer detectors have a high false-positive rate
  (that is why the corpus's scarp families plateaued); requiring two or three independent physical
  signatures to agree is the classical way to raise precision, and precision — not recall — is
  what the marginal-inclusion rule pays for.
* **How it differs.** The corpus's families are single-layer or two-layer *unions* (union raises
  recall, not precision); `h19-4` used "multiline corroboration" but as a *coverage* criterion over
  its own multilines, not as a cross-physics conjunction. GEMSDOE32's H33-E used a seismicity
  band; H47-GSA combined strain × alteration × thermal and lost to controls.
* **Expected DTI.** `+0.01 … +0.04`, mostly by allowing a *smaller* `N` for the same `T`
  (equation 1 rewards fewer dots), plus better tail behaviour than single-layer maps.
* **Cost.** Medium-low: all inputs in-repo; the work is threshold calibration and honest
  control comparison (the conjunction can be gamed, so controls must be conjunction-matched).
* **Data/licence/obtainability.** None new; all USGS public domain, already committed.

## H51-C (rank 3) — Basin-margin relay and step-over zones

* **Layers.** `data/grid/labels.tif` (the published catalogue, used only as *geometry*, never as
  target pixels), `derived_sgmc_faults_100m_u8.tif`, `gdr_qfaults_traces.csv` (1,127 traces),
  LiDAR scarp bands as corroboration.
* **Physical signature.** Structural geometry, not a pixel transform: extract fault-trace
  **terminations and overlapping tips** (endpoints within 2 km of each other, opposing dips or a
  left/right step), and emit a short corridor **between** the tips. This is where transfer faults
  and relay ramps sit, and where a 300 m-wide survey can see them only if it looks.
* **Why it targets unmapped faults.** Inventories systematically under-map short transfer faults
  that connect two long faults; the long faults are in the catalogue (hence masked), the link
  between them usually is not.
* **How it differs.** Nothing in the corpus's lineage models *topology* — all its families are
  pixel-level filters (scarp quantiles, ridges, dotted thinning, topo-gap closure).
* **Expected DTI.** `+0.005 … +0.03`; a low-recall, high-precision hypothesis: few dots, and each
  is placed where a missed fault must exist topologically.
* **Cost.** Low: geometry only, no raster transforms.
* **Data/licence/obtainability.** None new; USGS/state geological survey public domain.

## H51-D (rank 4) — 1 m LiDAR scarp **curvature** (needs new data)

* **Layers.** The competition's published 1 m DEM tiles (`1m_DEM_links.csv` on the competition data
  tab), reduced to a curvature/roughness surface; corroborate with the 12-band
  `lidar_scarp_features_u8.tif`.
* **Physical signature.** Second-derivative (curvature) and local roughness of a 1 m DEM along
  candidate lines, which resolves scarps far below the amplitude threshold of the 10–30 m products
  used by every scarp family so far. The corpus's scarp families all threshold *amplitude
  quantiles* of the pre-computed feature bands, which is why they plateaued.
* **Why it targets unmapped faults.** Short, young, low-relief traces — exactly the ones a
  regional inventory misses — are visible in 1 m curvature and invisible in 30 m products.
* **How it differs.** Amplitude quantile (what the corpus did) vs curvature/roughness of the
  highest-resolution DEM available.
* **Expected DTI.** Unknown; **no local frame validates it**. Note the measured *negative*
  association of scarp-quantile alignment with score in this corpus is a warning that this family
  is the most crowded.
* **Cost.** High: ~hundreds of GB of tiles; per-tile processing; needs a new, verifiable
  acquisition path.
* **Data/licence/obtainability.** USGS 3DEP 1 m DEM via the competition's link list; the links are
  behind hosts that fail TLS **from this sandbox** (Dropbox and `prd-tnm.s3.amazonaws.com` both
  returned SSL errors). **Not currently verified obtainable here.** The documented path is a GitHub
  Actions runner (`workflow_dispatch`), which has full egress but whose dispatch token scope is
  denied to this session (`HTTP 403 Resource not accessible by integration`); the remaining
  verified fallback is an owner-side download. Do not propose this as viable until a fetch is
  demonstrated.

## H51-E (rank 5) — InSAR/GNSS strain-rate lineaments (needs new data)

* **Layers.** OPERA/ARIA surface-displacement or GNSS velocity products, reduced to a
  strain-rate gradient field; corroborate with the seismicity corridors of H50-S1.
* **Physical signature.** Persistent aseismic creep or interseismic strain localises on **active**
  traces: a lineament in the strain-rate gradient, not in topography.
* **Why it targets unmapped faults.** A creeping fault that has never been mapped geologically is
  still a fault; geodesy is independent of the morphological evidence the catalogue is built on.
* **How it differs.** The corpus's entire lineage is surface-morphology or seismicity-density; no
  geodesy has been attempted here.
* **Expected DTI.** Unknown; theoretically strong for creep, but the study area's InSAR coherence
  and the products' spatial resolution (hundreds of metres) are poorly matched to a 300 m kernel.
* **Cost.** High: new data, new processing, new validation.
* **Data/licence/obtainability.** Free and official (NASA OPERA/ARIA, USGS GNSS); **not verified
  obtainable from this sandbox** (the same TLS blocks), same Actions/manual caveat as H51-D.

---

## Historical H51 slot gate — superseded; no authorization

The conditions below were an earlier H51-era proposal, not the current promotion rule. The old
instrument and its proxy were not validated against hidden labels, and the suggested “submit and
learn” path is withdrawn. H51/H52 proposals are not slot-eligible. H53-A is the current experiment
and is **NO-GO / NO SLOT**; see the H53 preregistration and results before considering a distinct,
newly registered study.

---

# Historical H52-era re-ranking (superseded; not current evidence)

This section records the older H52 re-ranking. Its score-derived quantities depend on the
unverified owner/sibling corpus described above; the ranking, expected gains, and slot suggestions
are all superseded by the current H53 four-way review. H51/H52 blocks are retained only to preserve
the former description of the ideas.

* The credit ledger in `h51-analysis.md` is a conditional transformation of unverified score/file
  records; it does not measure private-test coverage or prove a pruning gain.
* The truth-density inversion is an internal fit to the same corpus and did not provide stable
  spatial localization; it does not show where actual hidden faults are.
* Historical seismicity point-pattern/corridor tests were not validated against the hidden labels.
  The local off-catalogue proxy results were level with or below matched controls in the later H51
  analysis; the earlier cross-frame ranking was proxy-dependent, not proof of a validated signal.

| rank | hypothesis | lever | expected ΔDTI | cost | validated locally? |
| ---: | --- | --- | ---: | --- | --- |
| **1** | **P1 — dot-economy pruning of a historical structure** | `T/N` of the *same* structure | old model estimate +0.01 … +0.05; unvalidated | low (CPU) | only a corpus-conditional marginal hypothesis; no verified paired score |
| **2** | **P2 — magnetic-lineament corridors** (H51-A) | potential coverage of a new strand | old model estimate +0.02 … +0.06; unvalidated | medium | association only within a corpus with unverified score provenance |
| **3** | **P3 — seismicity point-pattern geometry** (historical H50/H51 lineage) | possible structural geometry, if independent signal exists | unknown | medium/high | not validated; later off-catalogue event-geometry test was level with or below matched controls, with confounds unresolved |
| **4** | **P4 — relay/step-over bridges between existing fault tips** | new location class, no new data | old hypothesis only; unvalidated | low | not tested under a current frozen protocol |
| **5** | **P5 — 1 m LiDAR scarp curvature** | resolution the 30 m products may not resolve | unknown | high | not tested under a current frozen protocol; obtainability/licence not independently verified |

## P1 — dot-economy pruning of the champion structure (rank 1)

* **Layers**: none — this was a proposed operation on a historical `dotted-h19-5-d2.8` raster
  (44,090 dots; its associated 0.2600 score is not authenticated here). The old proposal used
  `evidence/h51_consensus.json` and per-dot credit `qC = q ⊛ k`.
* **Physical signature**: none (a sparsity transform, not a geological signal). The historical
  proposal would keep dots with higher modelled 300 m kernel credit and remove the rest.
* **Why it might affect score**: under the DTI formula, reducing low-credit prediction mass can
  improve the ratio. This does not identify which H33/H51 dots were false positives or prove that a
  particular deletion caused an organizer-score increase.
* **Difference from earlier work**: it would change the subset of an existing raster, not add a new
  fault-detection signal. The claimed score relation between nested historical rasters is unverified.
* **Expected ΔDTI**: the old `+0.01 … +0.05` estimate is an unvalidated model scenario based on
  unverified score/file records. No sign or magnitude is established for a real held-out or private
  test candidate.
* **Cost**: historically estimated low CPU cost; this does not authorize a new run or slot.
* **Historical falsification proposal**: compare preregistered pruning levels on blocked, spatially
  separated holdout cores against a frozen incumbent and matched controls. No weekly slot is the
  “decisive test” for this archive; a slot could only be considered for a distinct candidate after
  all current gates and rights checks pass.
* **Source/licence/obtainability**: the raster is hash-identified in a sibling repository; that
  hash does not authenticate its owner-reported score or the score-to-file receipt.

## P2 — magnetic-lineament corridors on upward-continued TMI (rank 2)

* **Layers**: airborne TMI (band 4 of the staged `geodawn_extensions_u8.tif`) after 500 m and
  1,500 m upward continuation; radiometric K (band 1 of `geodawn_rad_u8.tif`) and Th/U as
  secondary; DEM ridge skeleton as the topographic control.
* **Physical signature**: second-derivative ridge detection (`ridge = 0` of the Hessian of the
  continued field, i.e. a *curvature* transform), then the same per-neighbourhood 2-D covariance /
  eigenvalue-ratio test already implemented for seismicity, applied to the lineament skeleton.
* **Why it might catch an unmapped fault**: a steep basement fabric without a Quaternary scarp
  could still produce a magnetic lineament. The older corpus recorded a low share of dots near one
  TMI-lineament mask, but score provenance and that association are not independently verified; it
  does not establish a current unspent advantage.
* **Difference from everything implemented**: H51-A, never emitted; every prior emission used DEM
  or radiometric geometry, and the previous session's TMI attempt (`TMI_up150`) lost to a random
  control at the wrong scale — this version uses 500/1,500 m continuation and a ridge (not
  amplitude) transform.
* **Expected ΔDTI**: the old `+0.02 … +0.06` is a historical scenario estimate, not a measured
  gain. The reported ρ values are same-corpus associations against unverified score records and do
  not establish causal or hidden-test performance.
* **Data source, licence, obtainability**: official GeoDAWN metadata lists CC0 1.0 (DOI
  10.5066/P93LGLVQ), but the local quantized sibling raster was not independently rebuilt or
  byte-matched to official files. Its provenance and sponsor-sharing basis remain blockers; a
  public GitHub mirror is not, by itself, permission or source verification.

## P3 — seismicity point-pattern geometry (historical, unvalidated)

* **Layers**: earlier drafts used relocated seismicity and/or a mixed-network ComCat extract,
  sometimes with springs or potential-field ridges as corroboration. The ComCat extract's
  contributor-specific rights are unresolved and it was not reused in H53-A.
* **Physical signature**: an older method proposed local 2-D epicentre geometry and corridors along
  principal axes. Its 2-D adaptation of a 3-D tetrahedron statistic is unverified. Point-pattern
  geometry—not smoothed density alone—would need formal space-time declustering, location-uncertainty
  handling, screening for injection/mining confounds, exclusion buffers around known faults, and
  matched 1 km/2 km smoothed-density controls before any new test could be interpreted.
* **Why it might detect an unmapped fault**: a coherent event pattern could reflect a structure with
  no mapped surface trace, but it can also reflect aftershocks, induced seismicity, catalogue
  completeness, and location error. The mechanism remains a hypothesis, not a demonstrated finding.
* **Difference from earlier work**: event geometry is already represented in the H50/H51 lineage; it
  is not a novel method in this repository. The current H53 ranking does not promote it as a
  validated candidate.
* **Evidence**: the earlier `seislin-44709` and H51 event-geometry outputs used different local
  instruments. Later H51 event-geometry tests were level with or below matched controls, and no
  hidden-label or organizer-score validation exists. The older 0.1464 proxy figure is frame- and
  protocol-specific and is not evidence that this method beats a fair matched-density control.
* **Expected ΔDTI**: unknown; no expected gain is supported by a current preregistered validation.
* **Cost**: medium/high: a new, rights-cleared catalogue and explicit declustering, uncertainty,
  confound, and control pipelines would be required.
* **Source/licence/obtainability**: the relocated Nevada catalog is listed CC BY 4.0 (Zenodo DOI
  `10.5281/zenodo.11167510`) but was network-blocked in the earlier sandbox. The staged ComCat
  extract has unresolved record/contributor-level rights and is **not cleared** for challenge use
  or sponsor sharing; do not use it unless that review is resolved.
## P4 — relay and step-over bridges between existing fault tips (rank 4)

* **Layers**: existing catalogue fault traces (masked from scoring, usable as *geometry*), DEM
  lineament skeleton, magnetic lineaments as corroboration.
* **Physical signature**: tip detection on the fault-trace skeleton (curvature/endpoint
  transform), then a *bridge* prior between overlapping or en-echelon tips within 1–3 km;
  scoring by bridge length and angular consistency.
* **Why it catches an unmapped fault**: transfer faults at relay zones are systematically
  under-mapped in regional inventories because they are short, oblique, and rarely offset
  Quaternary surfaces; the catalogue's own terminations are the best available prior for where
  they are.
* **Difference from everything implemented**: the group's scarp/ridge detectors are *tonal* (they
  fire on ridges); `h16-1` is a global continuation; nothing in the corpus is *anchored to
  catalogue tip geometry*.
* **Expected ΔDTI**: +0.005 … +0.03 (the bridges are short, so the credit per dot is high but the
  total available credit is limited).
* **Cost**: low, no new data.
* **Falsification**: bridge-only dots must beat their own translation control on the frozen
  holdout's off-catalogue frame, and must not simply re-draw the catalogue (max 2 px IoU < 0.5).

## P5 — 1 m LiDAR scarp curvature (rank 5)

* **Layers**: 1 m DEM / LiDAR point clouds over the GeoDAWN area; DEM-derived curvature of the
  *scarp*, not of the ridge; springs and magnetic lineaments as corroboration.
* **Physical signature**: curvature (Laplacian-of-Gaussian at 2–5 m) plus roughness change across
  the scarp, then the covariance/eigenvalue lineament test at 1 m scale, coarsened to the 100 m
  scoring grid.
* **Why it catches an unmapped fault**: the 30 m products used so far cannot resolve scarps below
  ~300 m length; the hidden faults are exactly the short, low-displacement ones.
* **Difference from everything implemented**: `r7-nms3-dem10-scarp` used 10 m DEM quantiles, i.e.
  amplitude, at 100 m support; this is curvature at 1 m resolution.
* **Expected ΔDTI**: unknown; the ceiling is the same 41 % of truth no local detector reaches.
* **Source/licence/obtainability**: USGS 3DEP / OpenTopography LiDAR are free and public, but
  `earthexplorer.usgs.gov`, `prd-tnm.s3.amazonaws.com` and `storage.googleapis.com` are
  **network-blocked in this sandbox**; the sibling `GEMSDOE24` repository commits a derived
  `lidar_scarp_features_u8.tif` (36 MB) which is present and usable, and a GitHub-Actions fetch
  job would be the compliant route to the upstream tiles (workflow dispatch is currently
  unavailable here — `gh workflow run` returns 403).

## What must be true before any of these spends a slot

1. The candidate passes `scripts/check_submission.py` with the corpus mounted (format + 2 px
   proximity uniqueness, `verdict_unique: true`) — this is a hard rule of the repository.
2. It beats the frozen incumbent on **both** the consensus instrument *and* at least one
   independent frame (§12) — no current candidate does, which is why the shipped file is
   labelled a measurement, not a win.
3. Its `T/N` exceeds 0.1097 (the corpus's best) or its prune-adjusted `T/(0.2N+0.8G)` exceeds
   0.2600 — otherwise it is only a reshuffle of known information.
