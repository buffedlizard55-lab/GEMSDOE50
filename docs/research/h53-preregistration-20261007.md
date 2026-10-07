# H53-A preregistration — probe-point/TMI lineation

**Frozen:** 2026-10-07 UTC, before H53 implementation and before any H53 DTI. This protocol follows the candidate ranking in [`h53-hypotheses-20261007.md`](h53-hypotheses-20261007.md). Any result, including a failure, must be appended to a separate results report; do not retune these constants after viewing holdout metrics.

## Question and scope

Do positive, survey-normalized 2 m temperature-probe anomalies form *linear point patterns* that are co-located and parallel with an independent GeoDAWN upward-continued TMI lineament, and does that combined signal recover SGMC fault traces that the current catalogue omits in the frozen spatial cores? This is a local proxy experiment. SGMC is not the private expert-labelled test set, and a proxy pass is not an organizer score.

## Pinned inputs and current provenance

| input | intended source / SHA-256 | status |
|---|---|---|
| 2 m temperature-probe archive | GDR submission 1391, `2m_temperature_probe_INGENIOUS_regional_data.zip`; `1301f70d230058e616ea5d34d1c7a32fabf7d49198172f376c59c89bd652eca3` (1,080,530 bytes) | Retrieved from pinned `GEMSDOE24` mirror commit `07345ea0604953d7efb858d9cfbc21e20c7aca0b`; official GDR page lists the same asset and ~1.03 MB size, but direct byte-for-byte comparison to the official binary download is not available here. The shapefile is NAD83 geographic; attributes include `F2mDAB`, described in the archive README as 2 m temperature normalized to the area background. Exact units/measurement uncertainty are not specified in the inspected README. |
| GeoDAWN TMI extension | `geodawn_extensions_u8.tif`; `a35a9c6d2a14786f4dab85481ee59769213072f5dab5b2535ea82ae4d9bb7d9b` (27,132,925 bytes) | Retrieved from the same pinned sibling mirror. Local raster is 3292×3730, EPSG:32611, 100 m, band 4 `TMI_up150`; values are quantized uint8 ranks (0 nodata), not physical units. Official GeoDAWN release is CC0 1.0, but this derived raster's byte/grid transformation has not been independently rebuilt from official source files. |
| local sample grid / known catalogue | `data/grid/sample_submission.tif` SHA-256 `2176d08e485aa2cd2860ce8df539db4faf4d76163b38a4dd8c30a40454d35cbc`; `data/grid/labels.tif` SHA-256 `7ba308ccdc4418b31a178f4f1ef21aaa6e152e4028f2f6f64b01f7eb25ae4093` | Hashes pinned by `evidence/holdout-v1.json`. This is the repository's source-bridge/sample grid; direct authenticated download from the competition account was not performed. |
| off-catalogue proxy labels | `data/external/derived_sgmc_faults_100m_u8.tif` | Existing local derivative; used only as independent *proxy* truth after a 3-pixel visible-catalogue exclusion. Not the hidden labels and not used to build predictor scores. |

Official external-data wording: the DrivenData problem page allows additional data if participants have a licence to use it in the challenge and share it with the sponsor for evaluation. GDR 1391 is explicitly CC BY 4.0 and says the data may be redistributed with attribution; GeoDAWN is explicitly CC0 1.0. The mirror/provenance caveat above remains a hard stop for any submission slot until resolved. Attribution must remain in code, the site, and the final narrative.

## Frozen detector (one configuration)

1. Read only the official-source-named shapefile inside the GDR archive. Transform its NAD83 geographic point geometry to EPSG:32611 and then to the pinned 100 m grid. Do not consume the sibling-derived `gdr_wellspring_in_footprint.csv`, its `dist_known_fault` field, any SGMC geometry, any hidden labels, or any prior submission pixels.
2. Use `F2mDAB` and survey `Area` only. For each `Area` with at least 12 finite, unique projected probe locations, define the warm marks as `F2mDAB > 0` and at or above that area's 75th percentile. This uses the source's own area-normalized field and prevents one survey's raw scale from dominating. Areas with fewer than 12 usable points do not contribute. Duplicate grid cells within an `Area` are reduced to the median `F2mDAB` before thresholding.
3. Within each `Area`, join warm marks into connected components using a fixed 1,500 m maximum neighbor distance. Retain a component only if it contains at least five unique locations, has a major/minor PCA eigenvalue ratio ≥3, and spans 0.8–20 km along its first principal axis. PCA is used for point-pattern geometry; point density alone is not a candidate feature. Use the 5th–95th percentiles of first-axis projections for segment endpoints so a single edge point does not set the corridor length.
4. Compute TMI lineament strength, angle, and coherence from GeoDAWN band 4 using the existing H51 structure-tensor function at scales (2, 5, 10) pixels with coherence smoothing 3 pixels. A qualifying TMI ridge is at or above the 95th percentile of valid-footprint strength and has coherence ≥0.25. Quantized values are used only for relative gradients/orientation, never interpreted in nT.
5. Sample each PCA axis every 100 m. Retain a component only if at least 50% of the samples have a qualifying TMI ridge within 500 m and the axial lineament-angle difference is ≤30°. No axis is shifted to the nearest fault label. Burn the accepted axis as a Gaussian corridor with σ=1.5 pixels, truncated at 3σ; its weight is the product of the component's median within-area anomaly rank and its TMI-alignment fraction. Overlapping components combine by maximum, not sum.
6. For the final candidate and all holdout/control emitters, allow predictions only in the valid sample footprint and farther than 3 pixels (300 m) from the full provided catalogue. This is an exclusion, not a fault target. The score-map builder itself receives no SGMC truth and no prior raster.

## Incumbent, blocks, metrics, and controls

### Baseline-only freeze

Before H53 DTI, re-score this fixed list on the same `evidence/holdout-v1.json` spatial cores against the same `SGMC_off` proxy (`SGMC` pixels >300 m from the provided catalogue):

- H51-A scarp + radiometric artifact: SHA-256 `8f8708d2872b66d71925707e0aede23eebcf217dfd2e57d6e61186f32e686f5d`;
- H50 prior seismicity artifact: SHA-256 `79e260ae223d7dfd96413da28a9c6fed30107285ab843795181a5c9e5dff7262`;
- H51 corridor-consensus artifact: SHA-256 `a26055834f8e6cc57cc33e96a4a5a26a1adeaafbeec490135af84c6ccd4d1da0`;
- the user's owner-reported best file, GEMSDOE32 H33-2-B2: SHA-256 `baeae3219bba6a19bc8cfe79224e28555c50184b7c1ca65c2a822f54807c77dd`, 37,654 binary dots, downloaded for **comparison only** from pinned `GEMSDOE32` commit `b983924b57781edd29b8e249c4923bf33d9902f6`.

The baseline audit, not a candidate result, chooses the incumbent with the greatest pooled DTI over the union of the four frozen eroded cores. Its identity, hash, per-fold counts, and scores were frozen in the committed `evidence/h53-baseline-20261007.json` before H53 implementation; SHA-256 `acd05c2a55d4d5a64a297075907bd53b5c0d52a78f655ddf3d34bc1d4d85f7bb`. The build and validation scripts require that exact baseline hash. A fresh audit, if desired, must write to a separate path (for example `/tmp/h53-baseline-recheck.json`) and must not overwrite the frozen evidence; changing it would be a new experiment requiring a new preregistration. If any comparator is missing or hash-mismatched, stop rather than silently substitute. The H33 pixels are used for comparison only and never as predictor features, masks, or fill material.

### Frozen spatial protocol

- Use exactly the four NW/NE/SW/SE half-open macrofolds and 100-pixel (10 km) eroded cores in `evidence/holdout-v1.json`; verify the split and valid-mask hashes before scoring. Use only the core's `SGMC_off` cells as that fold's truth. Predictions and truth are both zeroed outside that core for each fold's official 300 m triangular distance-weighted Tversky calculation (α=0.2, β=0.8).
- Exclude the full-catalogue 300 m buffer from both candidate eligibility and `SGMC_off` truth. Keep the off-catalogue scoring domain otherwise unchanged. No holdout truth is read by the detector.
- Freeze the per-fold candidate/control budget to the corresponding incumbent's number of positive cells in that core. Use the same 3-pixel suppression rule for all newly emitted maps. If the candidate score surface cannot produce that mass, do not add filler; record a gate failure. Report the final full-map native-mass result separately from this matched-mass rank-map comparison.
- Controls: (i) Gaussian-smoothed warm-probe intensity with σ=5 pixels (500 m), (ii) σ=10 pixels (1 km), (iii) TMI-only ridge strength, and (iv) five seeded uniform spatial maps, all at the matched per-fold mass. Also report 16-subtile paired deltas and a 5,000-draw subtile bootstrap. The smoothed controls preserve the warm-probe mark weights but intentionally remove PCA line geometry; they are not treated as seismicity-density controls.
- Report fold-wise and pooled DTI, TP/FP/FN weights, candidate mass, exact pixel overlap with the frozen incumbent, and a no-wrap spatial translation check. No hidden/private labels or live leaderboard access are used.

### Promotion / slot gate

H53-A is **not** eligible for any weekly scoring slot unless every condition passes:

1. Inputs, official grid, licenses, and source attribution are verified; no unresolved mirror/provenance issue remains.
2. The equal-mass H53 lineation map beats the frozen incumbent in pooled DTI by at least +0.005, is positive in all four macrofold paired DTI deltas, and has a 95% subtile-bootstrap lower bound above zero.
3. It beats both smoothed-probe controls, TMI-only, and the maximum of the five matched-uniform draws on the same folds. The emitted candidate's native-mass blocked DTI must also beat the incumbent's native-mass blocked DTI.
4. Raster format and value-range tests pass; the new file is built only from the H53 evidence field, has a fresh hash, and a uniqueness audit finds no exact hash match. Any incidental exact-dot overlap is disclosed; no prior prediction pixels are read into the builder.

Failure on any item means **NO SLOT**. A local proxy pass, even if achieved, is not an organizer score, a leaderboard forecast, or proof of a geological fault. There is no authorization to spend a weekly slot in this protocol.

## Intended artifact identity (only if a build is produced)

- Candidate filename stem: `gemsdoe50-h53-probe-tmi-pointlineation-20261007` plus a content-derived short hash.
- Portal submission name: `GEMSDOE50-H53-PROBE-TMI-POINTLINEATION-20261007`.
- Optional note: “Survey-normalized 2 m probe point-pattern lineations concordant with GeoDAWN TMI_up150; 300 m known-catalogue exclusion; research proxy only, not organizer-scored.”

These identifiers do not imply that the candidate passed or should be submitted. The portal artifact must be a single-band float32 GeoTIFF on the exact EPSG:32611, 100 m sample grid, with every finite prediction inside the valid study footprint in [0,1] and NaN/null outside the official bounds. This follows the current [DrivenData submission-format specification](https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/); the range validator must test the in-footprint values rather than treating the required outside-bounds NaNs as scores.
