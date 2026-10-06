# GEMSDOE50 — seismicity-first fault prediction for the DOE GEMS Prize

> **Read this README at the start of every session.** It contains the standing brief, the
> current state, the feed, and the rules this repository holds itself to. Core decision
> framework: **Maximize P(Win)** and **Own the Outcome**.

**Submit this file:** [`docs/downloads/gemsdoe50-seis-ridge-v1.tif`](docs/downloads/gemsdoe50-seis-ridge-v1.tif)
(one-click, no login) · zip twin `…-v1.zip` · [how to submit](docs/executive-summary.html) ·
[live site](https://buffedlizard55-lab.github.io/GEMSDOE50/) ·
[evidence receipts](evidence/) · **unique name** `GEMSDOE50-SEIS-RIDGE-V1-5CAD91AC`.

| item | value |
|---|---|
| file | `gemsdoe50-seis-ridge-v1.tif`, 150,672 bytes |
| SHA-256 | `5cad91ac7580db912ebac0cf352cce56d713e99ad53f596a57f714f51636d3c9` |
| format | single band, float32, EPSG:32611, 100 m, 3,730 × 3,292, origin (243350, 4508550), **every cell finite, min 0.0, max 1.0, no nodata tag, no NaN, no sentinel** |
| content | 45,000 cells = 1.0, all > 300 m from the provided catalogue; 12,234,160 cells = 0.0 |
| novelty | max \|Pearson r\| 0.033 and max support Jaccard 0.021 against **118** retrievable prior submission rasters; no prior submission in this family contains any seismicity-derived mass |
| what is *not* verified | any organiser score for this file. All local numbers are instruments with stated biases. |

---

## 1. The standing brief (verbatim intent, condensed into requirements)

**Goal.** Place at the top of the DrivenData **DOE GEMS Prize** leaderboard (competition #306,
GeoDAWN NW Nevada). Submission = a single-band float32 GeoTIFF of fault probabilities in
EPSG:32611 at 100 m. Public test scored by distance-weighted Tversky (α = 0.2, β = 0.8,
R = 300 m); the private/expanded label set re-scores in the Final Prize Round.

**Hard requirements.**

1. **Generate a unique TIF submission.** Never copy a previous submission; copying is allowed
   only for learning. Run a uniqueness gate against every retrievable prior raster before shipping.
2. Beat the group's best (**0.2778**, rank #13) and aim at the board leader
   (**0.3774** at the 2026-10-06 observation; the brief's 0.3195 target is stale by 0.058).
3. **Primary scientific directive: derive seismicity lineations from the earthquake point
   pattern, not from a density band.** Follow Ouillon/Ducorbier/Sornette (JGR 113, 2008,
   doi:10.1029/2007JB005032) inertia-tensor clustering; Ouillon & Sornette (JGR 116, 2011,
   doi:10.1029/2010JB007752) clustered-vs-background separation; the later ACLUD variant
   (arXiv:1304.6912) for location uncertainty. Take epicentres from a public catalogue
   (USGS ComCat) — record its official URL and licence first, and confirm the competition's
   external-data rule permits it. Decluster, remove known injection/mining sequences, compute
   2-D covariance eigenvalues per neighbourhood, keep linear well-sampled neighbourhoods, and
   emit **a corridor along the principal axis whose width follows the catalogue's location
   error**, not a single-pixel trace. Flag the 2-D adaptation of the 3-D tetrahedron test as
   **our own unverified adaptation**.
4. **Hypothesis:** blind faults produce seismic lineations where the mapped catalogue has no
   trace → **score corridors only outside existing-fault buffers** (300 m here). Confounders:
   aftershock swarms, location artefacts, induced seismicity. **Falsify** by showing corridors
   predict withheld fault segments better than smoothed earthquake density.
5. Normalise to [0, 1]; write the required GeoTIFF; **snap the corridor to another layer's
   ridge** in the placement step; run the uniqueness gate.
6. **Explain why/how the incumbents scored what they scored** — line-by-line against official
   sources with links for manual review, no hallucinations, irregularities flagged.
7. **Before implementing anything: 3–5 candidate geological hypotheses not yet tried**, each
   naming (a) the specific layer(s), (b) the physical signature/transform, (c) why it catches a
   fault missing from the catalogue rather than one already in it, (d) how it differs from
   everything already implemented in the GEMSDOE repos; ranked by expected DTI gain and cost;
   validate on a spatially blocked holdout before spending a weekly slot; name the specific
   free official source for any new external data and confirm obtainability first.
8. Find overlooked data sources; be contrarian but grounded; store gathered knowledge from
   official verified sources in the repository.
9. Site: GitHub Pages, clean and simple, with a **one-click downloadable submission TIF at the
   very top**, the unique submission name, note text (≤ 200 chars), an executive-summary subpage
   explaining exactly how to submit, and official verified source links.
10. Fix the portal error `"Predicted values must be in range [0, 1]"` (known causes: the
    −3.4028235e+38 sentinel and NaN encoding) — every shipped TIF must be all-finite in [0, 1]
    with no nodata tag.
11. Work autonomously, no manual input; multiple passes (implement + verify → review edge cases
    and fix → re-check against this brief and improve); then open a PR and merge it to `main`,
    and list the remaining work and limitations for the next session.
12. Keep the Arena Core Values (**Maximize P(Win)**, **Own the Outcome**) as the decision
    framework for every upgrade.

**Explicit constraint.** DrivenData downloads require login and no credentials exist here, so
only free, publicly licensed sources are used (USGS ComCat, USGS 3DEP, USGS GeoDAWN
radiometrics, USGS SGMC), and the competition's external-data rule is checked before use.

## 2. What this submission is, in one paragraph

An OADC-style lineation detector run on the **official USGS ComCat catalogue** (222,939 rows,
public domain): declustered with a 2-D triangle-area adaptation of the Ouillon–Sornette
tetrahedron test plus a rescaled nearest-neighbour control, clustered in (x, y, 3 km/yr·t) with
DBSCAN, split recursively until each cluster's minor-axis σ ≤ Δ = 600 m, kept when
λ₁/λ₂ ≥ 3 at Monte-Carlo p < 0.01, emitted as thin axes + curved spines + 300 m gap bridges, and
**snapped to the ridge of the USGS 3DEP lidar scarp descriptors** within 300 m. Terrain and
GeoDAWN radiometric ridge evidence provide the volume; everything within 300 m of the provided
catalogue is excluded. The metric's own marginal rule (`k > 0.2·DTI`) and the family's 16-anchor
live ledger set the operating mass.

## 3. Current status feed (2026-10-06)

* **Shipped:** `docs/downloads/gemsdoe50-seis-ridge-v1.tif` — format legal, unique, 45,000 cells.
* **Instruments.** Off-catalogue SGMC credit per cell **0.2227** at 45,000 cells vs **0.1434** for
  the owner-reported 0.2778 file at its own mass (**1.55×**); 2020 Monte Cristo rupture trend:
  0.0022 credit/cell and 36 % covered vs 0.0008 / 11 % (incumbent), 0.0006 / 11 % (previous best).
* **Predictive falsification test passed narrowly and honestly:** with only pre-2020 earthquakes
  the corridor detector is the sole field placing mass on the 2020 rupture trend (2.4 % of it);
  smoothed density (σ = 10 and 20 px) and uniform random cover 0 %. On the *mapped* catalogue the
  density fields beat the corridors (0.039–0.052 vs 0.027 credit/cell) — reported as the negative
  half of the test.
* **Hidden-truth size is the open question:** the family's two published estimates are ≈5,667 and
  ≈15,100 cells (57–151 km of fault), disagreeing by 2.7×. The mass decision (45,000) sits at the
  ledger's optimum neighbourhood, not at either estimate's optimum; the full sweep is published.
* **Leaderboard at last observation:** #1 xiaofanhu 0.3774 · #2 alexoktaba 0.3345 ·
  #3 nchuzhoy 0.3262 · #13 extradr19 (this family) 0.2778. No automated monitoring: DrivenData's
  terms of use forbid it.

## 4. Remaining work and limitations (for the next session)

1. **Spend a weekly slot on the shipped file** and record the score in `registry/submissions.json`;
   the two competing hidden-truth-size estimates are separated by exactly that observation.
2. **Bracket the mass** if a second slot is available: rebuild at 37,654 and 60,000 cells
   (`scripts/build_submission.py --mass …`) and compare on the instruments.
3. **Wire the nightly ComCat refresh into the detector** (`.github/workflows/fetch-external-data.yml`
   exists in the sibling branch; this repository's own workflow still needs to be added) so the
   corridor set tracks new sequences.
4. **Cross-strike swath profiling of the 1 m DEM** (hypothesis H50-5) — the strongest untried
   physical signature; blocked by the ≈100 GB raw DEM tile set.
5. **H50-3 (cross-inventory disagreement) is deliberately not shipped** — SGMC/QFaults may be the
   organisers' own label source, so emitting their traces would be indistinguishable from leakage.
6. Known biases: the off-catalogue SGMC instrument rewards dispersion at low mass (uniform random
   beats structured fields below ≈10,000 cells); the Monte Cristo instrument is circular as a
   geometry check; the lidar descriptor layer covers 75 % of the survey; the detector needs
   M ≥ 1.5 / depth ≤ 20 km events, so detection power falls with fault age.

## 5. Reproduce

```bash
pip3 install --break-system-packages numpy scipy pandas pyproj rasterio scikit-learn pytest
cd GEMSDOE50
PYTHONPATH=src python3 -m pytest tests -q                       # metric + grid + format tests
PYTHONPATH=src python3 scripts/falsification_test.py           # the pre-2020 predictive test
PYTHONPATH=src python3 scripts/build_submission.py --name seis-ridge-v1 --mass 45000
PYTHONPATH=src python3 scripts/audit_submission.py docs/downloads/gemsdoe50-seis-ridge-v1.tif
```

## 6. Layout

```
docs/                  GitHub Pages site (index, how-to-submit, hypotheses, analysis, sources)
docs/downloads/        the submission GeoTIFF + zip + checks-*.json receipts
evidence/              every number behind the build, the falsification test, the uniqueness gate
registry/              sources.json, hypotheses.json, submissions.json (ledger), claims.json
src/gems50/            grid, metric, catalog, decluster, lineation, hough, emission
scripts/               fetch/freeze data, run the detector, build, audit
tests/                 metric algebra, grid, format rules
data/external/         the data actually used, with licences and sha256 receipts
```

## 7. Rules this repository holds itself to

* **No hallucinations.** Every number is either recomputable from the repository
  (`evidence/`, `tests/`) or marked `[owner-report]`/`[instrument]` with its bias named.
* **Instruments are not receipts.** A local score never justifies a claim about the organiser's
  hidden set; where an instrument has a measurable bias, the bias is published next to the number.
* **Irregularities are flagged, not smoothed** — see `registry/claims.json`.
* **Unique, all-finite, in-range** — or it does not ship.
