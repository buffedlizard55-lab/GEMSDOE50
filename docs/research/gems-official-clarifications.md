# Official clarifications, rules and source ledger

Everything in this file was read from the source named beside it on 2026-10-07.
Rows marked **primary** were read directly from the organization that published
them; rows marked **quoted** were read on a DrivenData community page and are
labelled as such because the underlying document is not public.

## 1. Scoring rulings that change what the optimum looks like

| # | ruling | source | status |
|---|---|---|---|
| R1 | The metric is a distance-weighted Tversky index: `k(d)=max(1−d/R,0)`, `R = 300 m`, `α = 0.2`, `β = 0.8`; the worked example scores 0.60 | [competition problem description](https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/) | **primary** |
| R2 | Submission shape: one 32-bit float layer, values between 0 and 1, **same bounds as the training data, and data outside the bounds is null or NaN** | [problem description](https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/) | **primary** |
| R3 | The provided `sample_submission.tif` predicts **total fault absence** | [problem description](https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/) | **primary** |
| R4 | The test set is **new faults** the sponsors' experts manually identified that are **not contained within the current public USGS database**; the GeoDAWN region is chunked into a public and a private test set; the same submission is scored in both prize rounds | [problem description](https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/) | **primary** |
| R5 | "Pixels corresponding to known USGS/INGENIOUS faults are masked / excluded from evaluation, so they do not count towards penalty terms", and re-evaluation will mask them too | [forum 11516, post 2](https://community.drivendata.org/t/scoring-clarification-are-known-usgs-ingenious-faults-masked-when-scoring-and-are-they-in-the-final-round-label-set/11516) | quoted from DrivenData staff |
| R6 | A "new fault" means "any fault pixel not already captured by USGS/INGENIOUS" and **can include newly mapped geometry of an existing fault system** | [forum 11536, post 2](https://community.drivendata.org/t/where-do-you-draw-the-line/11536) | quoted from DrivenData staff |
| R7 | The organizers will not disclose the data sources, fault types or coverage behind the test faults | [forum 11527, post 7](https://community.drivendata.org/t/how-were-the-new-test-faults-identified-data-sources-and-fault-types/11527) | quoted from DrivenData staff |
| R8 | External data must be licensed for use and shareable with the sponsor; generative-AI use must be disclosed | [rules PDF](https://docs.nlr.gov/docs/fy26osti/96647.pdf) | primary document, cited from the competition site |

### What R1–R7 imply for the design

* **R4 + R5** mean the task is *not* to reproduce the catalogue. Predictions on
  catalogue pixels are free of penalty but earn nothing either, so the entire budget
  belongs to unmapped structures.
* **R5** removes the reason for a wide suppression buffer: a dot 1–2 px from a
  catalogue pixel is *not* masked, so if a new strand really does run beside a known
  one that dot can still earn truth-side credit.
* **R6** is the finding with the largest unexploited upside: a mapped continuation or
  an unmapped parallel strand of a known fault system is a legitimate "new fault".
  H57 does not ship a continuation rule because no frame held in this repository can
  score one — see H57-H4 in `docs/hypotheses-20261007-h57.md`.
* **R2** explains the recurring portal error. A plain `min()/max()` range check over
  a raster that contains NaN is false, because `NaN <= 1` is false. The artifact
  therefore writes 0.0 outside the study footprint so that every one of the
  12,279,160 cells is finite.

## 2. Data sources and licences

| dataset | how H57 uses it | licence / rights | source |
|---|---|---|---|
| Competition feature stack, 19 bands at 100 m (GeoDAWN + INGENIOUS layers) | layers 12 and 19 and their derivatives, the core of the H57 field | provided by the organizers for this challenge | competition data tab (login-gated); the repository's copy is a hash-pinned bridge from the team's own public mirror |
| USGS 3DEP 1 m LiDAR bare-earth DEM over the GeoDAWN area | LiDAR scarp descriptor bands 02–08 | US public domain | [GeoDAWN data release](https://www.usgs.gov/data/geodawn-airborne-magnetic-and-radiometric-surveys-northwestern-great-basin-nevada-and), doi:10.5066/P93LGLVQ |
| USGS SGMC fault layer | **proxy truth only**, never an input to the field | US public domain | USGS State Geologic Map Compilation |
| Supplied `labels.tif` / `training_features.tif` | labels for the blocked-holdout instrument; the artifact is steered away from them (R5) | competition data | competition data tab |
| Trugman relocated catalogue (Zenodo 11167510) | tested as the seismicity point-pattern term; **not** in the shipped artifact | CC BY 4.0 | https://doi.org/10.5281/zenodo.11167510 |
| USGS ComCat | not used | contributor-specific rights unresolved | — |

**H57 uses no dataset whose rights are unresolved.** That is the specific reason it
is offered ahead of H56, whose mixed-network ComCat-derived corroboration carries an
open rights question.

## 3. Physical basis

* Most Great Basin hydrothermal systems are fault-controlled, and roughly 39 % of the
  426 catalogued systems are blind — the prize exists because the surface expression
  is missing ([Faulds & Hinz 2015](https://www.osti.gov/servlets/purl/1724082)).
* USGS Quaternary faults can sit up to ~400 m from lidar-based labels, and database
  density varies with the source map ([Hermant et al. 2025](https://pangea.stanford.edu/ERE/db/GeoConf/papers/SGW/2025/Hermant.pdf)).
* Lineament detection from a *point pattern* rather than a smoothed density surface
  follows Ouillon, Ducorbier & Sornette, *JGR* 2008,
  [doi:10.1029/2007JB005032](https://doi.org/10.1029/2007JB005032), and
  [arXiv:1304.6912](https://arxiv.org/abs/1304.6912). The 2-D adaptation of their
  3-D tetrahedron test used here is an approximation of this repository's own
  making and has never been verified against the published algorithm — stated
  because the brief requires unverified steps to be labelled.
* A step edge is the standard topographic signature of a fault scarp, which is why
  the frozen field uses the *gradient* of a slope layer rather than a slope layer
  alone.

## 4. Sources for the repository's own claims

| claim on the site | evidence file |
|---|---|
| off-catalogue proxy DTI 0.21812, per-fold and controls | `evidence/h57_validation.json` |
| format gate and novelty gate | `evidence/h57_check.json` |
| file hashes, frozen constants, portal name and note | `evidence/h57_build.json` |
| field selection and the frame-L holdout | `evidence/h57_field_select.json`, `evidence/h57_holdout_fields.json` |
| emitter comparison | `evidence/h57_emission_shapes.json` |
| mass decision | `evidence/h57_final_select.json` |
| the 24.7 % dead-zone defect | `evidence/h57_decompose.json` |
| the price of the novelty constraint | `evidence/h57_novelty_price.json` |
| single-channel audit of all 61 features | `evidence/h57_feature_audit.json` |
