# H51 candidate hypotheses, ranked

> ## ⚠ CORRECTION — 2026-10-07 UTC: the magnetic-alignment statistic in this document was never real
>
> This document states four times (lines 16–17, 180, 232, and in the H51-A section) that the
> fraction of an artifact's dots inside the TMI-lineament mask is the only layer alignment with a
> positive, robust association to score, quoting **`ρ = +0.566` (p = 0.003)** raw and
> **`+0.534` (p = 0.006)** after controlling `log10 N`, and citing
> `evidence/h51_residual_alignment.json` as the source. **That file does not contain those
> numbers.** Its measured content, recomputed and re-read on 2026-10-07, is:
>
> | feature in `evidence/h51_residual_alignment.json` | raw `rho` | p | partial `rho` | p |
> | --- | ---: | ---: | ---: | ---: |
> | `f_gmtmi95` (the TMI alignment this document is about) | **+0.125** | 0.552 | **−0.385** | 0.058 |
> | `f_gmK95` (radiometric K) | +0.192 | 0.359 | +0.104 | 0.621 |
> | `f_ex95` (LiDAR excess q95) | +0.097 | 0.644 | **+0.590** | 0.0019 |
> | `f_ex99` | −0.141 | 0.501 | **+0.591** | 0.0019 |
> | `f_step95` | −0.083 | 0.692 | **+0.505** | 0.0099 |
> | `f_step99` | −0.321 | 0.117 | +0.379 | 0.062 |
> | `f_ring0_1` / `f_ring1_2` / `f_ring2_3` | −0.464 / −0.509 / −0.495 | 0.019 / 0.009 / 0.012 | −0.565 / −0.575 / −0.584 | 0.0033 / 0.0027 / 0.0022 |
> | `f_hot10` (thermal-spring proximity) | **−0.527** | 0.007 | −0.382 | 0.059 |
>
> Three further claims in the same paragraphs are also wrong in sign or magnitude:
>
> * "extreme LiDAR-scarp quantiles are **negatively** associated with score (`ex99`: `ρ = −0.722`,
>   partial −0.620, p = 0.001; `step99`: −0.802)" — the file says `f_ex99` raw −0.141 (p = 0.501)
>   and partial **+0.591** (p = 0.0019), and `f_step99` raw −0.321 (p = 0.117), partial **+0.379**.
>   The LiDAR-scarp family is the one family that is *positively* associated with score once mass is
>   controlled, which is the opposite of what this document concludes.
> * "the corpus spends only ~5 % of its dots there" — not reproducible from any file in this
>   repository; no per-artifact TMI coverage table exists here.
> * "the three highest-scoring artifacts are almost identical in all eleven measured alignments" —
>   the file holds eleven features but no per-artifact matrix, so this cannot be checked and should
>   not be cited.
>
> **Where `+0.566` and `+0.534` actually came from.** They are AUC values, not rank correlations,
> and they are not from this repository. `0.5658749925558758` is
> `/references/candidate/primary/fold_aucs[0]` in the sibling repository's
> `docs/data/audit.json`, and `0.534...` values appear there as `null_aucs[4]`, `null_aucs[15]`,
> `null_aucs[30]`, `null_aucs[93]` under `/references/*/shift_diagnostic/`. Inside this repository
> the string also appears once, at `evidence/h51_truth_map.json` key
> `/grids/32/phi[919] = 0.5662404620083589` — a **single spatial block's phi for a single artifact
> grid**, which is not a corpus-wide association statistic either.
>
> **Consequences, applied the same day.** H51-A's rank-1 position rested on this number and is
> withdrawn; the H52 register (`docs/hypotheses-20260707-h52.md`, corrected path
> `docs/hypotheses-20261007-h52.md`) re-ran the full channel screen and measured the magnetic and
> radiometric residual/gradient channels at **1.02 – 1.09 enrichment** against a **1.42** head for
> the LiDAR scarp family, and rejected the magnetic family on that basis. The claims in the body of
> this document are left in place rather than edited, so the record of what was believed and when
> stays intact; the numbers, not the prose, are corrected.
>
> **Process fix.** Every statistic quoted from here on must be reproducible by a command in the
> repository. `scripts/verify_claims.py` is the existing hook for that; a follow-up item is recorded
> in the pull request to extend it to the `docs/research/*.md` citations it does not yet cover.

Ranking criterion, in the order the charter requires: **expected improvement in captured hidden
truth `T`** (section 3 of `docs/research/h51-analysis.md` shows every point of leaderboard score is
a point of coverage of the same ~12,226 hidden pixels), then implementation cost, then whether the
required data is already in the repository and licence-clean.

Every hypothesis must answer the same question: *why would this find a fault that the
USGS/INGENIOUS catalogue does not already contain?* The catalogue pixels are masked out of
scoring, so reproducing them is worth exactly nothing.

Measured starting point (`evidence/h51_residual_alignment.json`, `evidence/h51_consensus.json`,
25 hash-verified artifacts with owner-quoted scores):

* ~~the fraction of an artifact's dots inside the TMI-lineament mask is the **only** layer alignment
  with a positive, robust association to score: raw `ρ = +0.566` (p = 0.003), partial controlling
  `log10 N` `+0.534` (p = 0.006);~~ **[WITHDRAWN 2026-10-07 — the cited file says `f_gmtmi95`
  raw `+0.125` (p = 0.552), partial `−0.385`; see the correction notice at the top of this file.

  What the file *does* support: the LiDAR-scarp excess quantiles `f_ex95`/`f_ex99` are the family
  positively associated with score after controlling `log10 N` (partial +0.590, p = 0.0019), and
  artefacts whose dots sit near thermal springs score lower (`f_hot10` raw −0.527, p = 0.007).]**
* the corpus spends only ~5 % of its dots there (prevalence 5.0 %), so it is exploiting that
  evidence no more than chance;
* extreme LiDAR-scarp quantiles are **negatively** associated with score in this corpus
  (`ex99`: `ρ = −0.722`, partial −0.620, p = 0.001; `step99`: −0.802) — the group's scarp-quantile
  families are the ones that plateaued at 0.09–0.16;
* ~~the three highest-scoring artifacts are almost identical in all eleven measured alignments,
  i.e. the corpus's top end is **one idea**, not several.~~ **[WITHDRAWN 2026-10-07: the file holds
  no per-artifact alignment matrix, so this is unverifiable here.]**

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
  surface scarp are exactly the population it under-represents. The score data agrees: artifacts
  that happened to concentrate on TMI ridges scored ~0.03–0.04 above what their dot geography
  predicts.
* **How it differs from everything already implemented.** H47-B's `TMI_up150` test used a
  *persistence* filter on the upward-continued field (a value threshold) and lost to a random
  control; H46 fused radiometrics as a density prior. Neither used the **multi-scale
  gradient-ridge transform with cross-channel corroboration**, and neither combined it with the
  metric-aware dot geometry. The corpus's scarp-quantile families (`ex95/ex99/step95/step99`) are
  a different physical quantity (surface relief), which is precisely the one that shows a
  *negative* association here.
* **Expected DTI.** `+0.02 … +0.06` if a single previously unmapped strand of ≥40 km is hit
  (`T` rises by ~1,000–1,400 of the 12,226 available, which is the whole 0.26 → 0.32 gap at
  `N ≈ 30–40 k`); `−0.01` if the layers are noise, because 6–10 k exploratory dots cost
  `0.2·ΔN/(0.2N + 0.8G)`.
* **Cost.** Medium: the transform is implemented (`h51.gradient_lineament_response`), the layers
  are in-repo, and the only new work is threshold/corroboration calibration on the blocked holdout
  and a slot-sized emission.
* **Data, licence, obtainability.** No new data. USGS public domain; DOI 10.5066/P93LGLVQ and the
  state-map products are linked in `docs/sources.html`. Obtainable today: already committed.

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

## What must be true before any of these spends a slot

1. The frozen format and uniqueness gates pass (`scripts/check_submission.py`).
2. The candidate beats the incumbent in the **instrument's** LOO-calibrated prediction, and the
   repository replaces the current pre-registered proxy gate, which cannot rank the corpus
   (`ρ = +0.196`, p = 0.35, `evidence/h51_proxy_ranking_power.json`).
3. A geopolitically independent check is recorded: for any hypothesis whose evidence lies in
   territory no prior artifact touched, **no local instrument can price it** (section 4 of the
   analysis). The honest options are (a) submit and learn, with the score pre-registered here as a
   prediction, or (b) hold the slot. This repository's rule is (b) unless the owner overrides it.

---

# H52 update — re-ranking after the credit ledger, the blind inversion and the proxy audit

Everything below supersedes the ranking of H51-A…E; the H51 blocks are kept because their
"layers / signature / why off-catalogue / difference / ΔDTI / cost" fields are still the reference
description of each idea. The new evidence that moves the ranking:

* the credit ledger (§8 of `h51-analysis.md`): the corpus converts at most **0.1097 credit/dot**,
  covers at most **59.3 %** of the hidden truth, and the champion `d2.8` is **past its own family's
  optimum** (`∂DTI/∂N < 0`, marginal dot worth 0.035 vs a 0.052 cost);
* the truth-density inversion **fails leave-one-out** (§10) — the score history constrains
  *efficiency*, not geography, so no hypothesis below can be selected by localising hidden truth;
* the proxy audit (§12): the only independent geological frame in the repository ranks the
  *archived seismicity-lineament artifact* far above every scored artifact, while ranking the live
  scores at ρ = +0.196.

| rank | hypothesis | lever | expected ΔDTI | cost | validated locally? |
| ---: | --- | --- | ---: | --- | --- |
| **1** | **P1 — dot-economy pruning of the champion structure** | `T/N` of the *same* structure | **+0.01 … +0.05** | **low (CPU, hours)** | marginal inequality measured; the gain itself is *not* measurable without a slot |
| ~~**2**~~ | ~~**P2 — magnetic-lineament corridors** (H51-A)~~ **WITHDRAWN 2026-10-07** | — | — | — | the cited alignment statistic does not exist; the channel screen measures magnetics at 1.02–1.09 enrichment vs 1.42 for the LiDAR scarp family. See `docs/hypotheses-20261007-h52.md`. |
| **3** | **P3 — seismicity-lineament corridors** (H50-S1/H51 lineage, the owner's own method) | coverage on the 41 % the corpus misses | unknown, tail-heavy | medium | **best independent-frame result in the project** (sgmc_off 0.1464, 2.5× uniform; Monte Cristo hit with the density control beaten) |
| **4** | **P4 — relay/step-over bridges between existing fault tips** (H51-C) | new location class, no new data | +0.005 … +0.03 | low | not yet run |
| **5** | **P5 — 1 m LiDAR scarp curvature** (H51-D) | resolution the 30 m products cannot reach | unknown | high | not yet run; data obtainability verified below |

## P1 — dot-economy pruning of the champion structure (rank 1)

* **Layers**: none — this is an operation on the *existing* champion emission (`dotted-h19-5-d2.8`,
  44,090 dots, live 0.2600). If a field is needed for the prune ranking, the consensus posterior
  `q` of `evidence/h51_consensus.json` and the per-dot credit `qC = q ⊛ k`.
* **Physical signature**: none (a *sparsity* transform, not a signal transform). The prune keeps
  the dots whose 300 m kernel neighbourhood carries the most post-corpus credit and deletes the
  rest; the emitted geometry stays a 2.8 px Poisson-disk lattice.
* **Why it catches a fault the catalogue misses**: it does not. It raises the score by *spending
  fewer false-positive pixels for the same credit* — the only term of the metric that the corpus
  demonstrably allows us to improve.
* **Difference from everything implemented**: every prior experiment chose a *field* or a
  *spacing*; P1 keeps the field and the spacing of the live-best artifact and changes only the
  *subset*, which the corpus shows is where the remaining score is (`d1.5` is a superset of `d2.8`
  and scores 0.0123 lower *because of 15,979 extra dots*).
* **Expected ΔDTI**: removing dots whose credit is below `0.2·s ≈ 0.052` raises `DTI`; at the
  measured marginal rates (0.022–0.035) the champion is above its optimum, so the sign is known
  and the magnitude is bounded by the number of dots whose credit is below 0.052 — plausibly
  10–20 k dots, i.e. **+0.01 … +0.05**.
* **Cost**: low. One CPU-day (the fields are already computed; a sweep over prune thresholds ×
  budget × 4 holdout folds).
* **Falsification test**: prune the champion to `k ∈ {10, 20, 30, 40} k` dots by `qC` and check
  that the *sgmc_off* and *CatBlocked* proxy DTIs rise while the 2 px-proximity IoU stays < 0.5;
  a prune that lowers both proxies is rejected. The decisive test is a slot (the corpus has no
  scored subset of `d2.8`).
* **Source/licence/obtainability**: no new data; the champion artifact is public in the sibling
  `GEMSDOE25` repository and hash-pinned in `registry/h51_score_corpus.json` (SHA-256
  `91eae1ca…`, verified this session).

## P2 — magnetic-lineament corridors on upward-continued TMI (rank 2)

* **Layers**: airborne TMI (band 4 of the staged `geodawn_extensions_u8.tif`) after 500 m and
  1,500 m upward continuation; radiometric K (band 1 of `geodawn_rad_u8.tif`) and Th/U as
  secondary; DEM ridge skeleton as the topographic control.
* **Physical signature**: second-derivative ridge detection (`ridge = 0` of the Hessian of the
  continued field, i.e. a *curvature* transform), then the same per-neighbourhood 2-D covariance /
  eigenvalue-ratio test already implemented for seismicity, applied to the lineament skeleton.
* **Why it catches an unmapped fault**: the catalogue is built from *surface* expression and
  published mapping; a steep basement fabric with no Quaternary scarp appears only in the
  magnetics. The corpus's dots accumulate on DEM/radiometric ridges and avoid the TMI lineaments
  (only ~5 % of corpus dots fall in the TMI-lineament mask), so this is the largest *unspent*
  layer in the whole evidence stack.
* **Difference from everything implemented**: H51-A, never emitted; every prior emission used DEM
  or radiometric geometry, and the previous session's TMI attempt (`TMI_up150`) lost to a random
  control at the wrong scale — this version uses 500/1,500 m continuation and a ridge (not
  amplitude) transform.
* **Expected ΔDTI**: ~~+0.02 … +0.06 if a strand is hit; the measured association is
  ρ = +0.566 (p = 0.003) raw and +0.534 (p = 0.006) after controlling log₁₀N.~~
  **WITHDRAWN 2026-10-07**: the association is not in the cited evidence file; the measured
  TMI alignment is `+0.125` raw (p = 0.552) and `−0.385` partial. The channel screen independently
  finds the magnetic family uninformative about unmapped faults (1.02–1.09 vs 1.42).
* **Data source, licence, obtainability**: GeoDAWN/DOE airborne geophysics via the sibling
  `GEMSDOE24` repository's committed raster (`data/external/geodawn_extensions_u8.tif`, 26 MB,
  public GitHub). **Verified present in this environment**; the upstream USGS/DOE ScienceBase
  hosts are network-blocked here, so the committed copy is the working source.

## P3 — seismicity-lineament corridors (rank 3, the owner's own method)

* **Layers**: declustered relocated seismicity (ComCat extract already staged, 20,430 events),
  thermal springs (1,873 in the footprint), magnetic/radiometric ridges as corroboration.
* **Physical signature**: per-neighbourhood 2-D covariance eigenvalues on epicentres; keep
  linear, well-sampled neighbourhoods; emit a corridor along the principal axis with width from
  the catalog location error; the 3-D tetrahedron NN-volume test is the owner's 2-D adaptation.
* **Why it catches an unmapped fault**: it requires *no* surface expression, only a
  co-seismic alignment; the catalogue-only detectors used by the rest of the field cannot see it.
* **Difference from everything implemented**: this is the repository's original H50-S1 line and
  the archived `seislin-44709` artifact, not the corpus-consensus line.
* **Evidence**: the *only* method in the project with a positive result on an independent
  off-catalogue frame: `sgmc_off DTI 0.1464` vs uniform 0.0593 and vs its own translation control
  0.0447, i.e. 2.5× the matched random baseline, and the Monte Cristo corridor hit that beat its
  smoothed-density control. Against that, the consensus instrument prices the same artifact at
  0.0422 — the unresolved conflict recorded in §12 of the analysis.
* **Expected ΔDTI**: unknown and tail-heavy. This is the only hypothesis whose upside reaches the
  §9 arithmetic (a corridor that lands on one 40–60 km unmapped strand adds 1,200+ credit px).
* **Cost**: medium (the pipeline exists; the work is parameter selection under the frozen gate).
* **Source/licence/obtainability**: the relocated Nevada catalog is CC-BY-4.0 (Zenodo DOI
  `10.5281/zenodo.11167510`) — **network-blocked in this sandbox**; the ComCat extract used in
  `data/external/` is a mixed-network USGS product whose source-specific rights are **not** yet
  cleared for competition use (`data/external/README.md` de-authorises it), so a submission that
  depends on it needs the rules question resolved first.

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
