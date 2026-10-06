# H50-S1 implementation protocol addendum

**Frozen:** 2026-10-06 UTC, before any H50-S1 DTI calculation. The comparator policy was amended later the same day, still before any H50-S1 DTI, after code review found that selecting the highest-scoring baseline on the holdout would leak holdout labels; no H50-S1 holdout scores were viewed. This addendum makes the implementation choices and control counts executable and auditable; it does not revise the ranked scientific hypotheses or their promotion thresholds in [`hypotheses-preregistered.md`](hypotheses-preregistered.md).

**Pre-run amendment v1.1 (2026-10-06 UTC):** Before the first DTI, add 1 km and 2 km Gaussian-smoothed relocated-event-density comparators and enforce additional scientific slot gates for aftershock declustering, mining/injection-site screening, and event-location uncertainty. This is stricter than the original numeric gate and cannot promote an otherwise failing candidate. H50-S1 may be run for research only while any additional gate is unresolved. The reason and source audit are recorded in [`research/earthquake-geometry-review-20261006.md`](research/earthquake-geometry-review-20261006.md); no scores were used to choose these additions.

## Fixed candidate construction

| Parameter | Frozen value |
|---|---:|
| Catalog rows admitted | Only `reloc = 1`, retained only when the projected event falls in a finite template cell |
| Local neighborhood radius | 2,500 m |
| Fit-seed spacing | One occupied 500 m cell |
| Event de-duplication | One observation per 250 m cell per origin year |
| Minimum neighborhood support | 10 de-duplicated events across at least 2 distinct years |
| Horizontal geometry | PCA linearity ≥ 0.70; 4σ minor-axis width ≤ 1,200 m; 5th–95th percentile trace length ≥ 1,500 m |
| Robust plane fit | Up to 3 orthogonal-residual trimming iterations using median + 3 × (1.4826 × MAD); at least 10 inliers must remain |
| 3-D geometry | Planarity ≥ 0.45; plane normal's horizontal norm ≥ 0.20; projected strike alignment with horizontal event axis ≥ 0.65 |
| Surface plausibility | Median event depth ≤ 20 km and absolute plane-to-z=0 extrapolation ≤ 10 km |
| Stability | 24 event-bootstrap resamples; 90th-percentile projected-strike angle ≤ 35° |
| Rasterization | Sample fitted z=0 intersection every 50 m; one-pixel halo with 100 m Gaussian sigma; maximum confidence per pixel |
| Final prediction | Rank positive candidate cells, exclude all known labels buffered by 300 m, emit up to 37,612 cells at `p=1`, other valid cells `p=0`, outside-template cells NaN |

These are label-blind engineering constants, not optimized on the holdout. The method projects a local hypocenter-plane fit to its `z=0` intersection; it is not asserted to recover the actual geological surface trace. Event-location covariance is unavailable, so the result remains a proxy.

## Frozen scoring and controls

- Read the hash-pinned `evidence/holdout-v1.json` and its realized mask hashes in `evidence/holdout-realized-v1.json`; the runner must compare them before computing any DTI.
- Use 100 m pixels, 300 m triangular support, α=0.2, β=0.8, and ε=1e-9. For each method, select the same total of 37,612 binary-probability cells, allocated to macrofolds in proportion to eligible valid pixels with largest-remainder rounding. Ties use deterministic seeded random selection. If a method has fewer positive cells, do not pad it with unsupported pixels.
- The frozen same-grid comparison set is H50-prior (the pre-existing repository candidate) plus H32-D, H47-S3, and H48-DS. File SHA-256 values, Git blob IDs, and source commit IDs are pinned in `scripts/run_experiment.py` and `scripts/fetch_comparators.sh`. **H50-prior is the fixed primary incumbent**, chosen by chronology before this holdout is scored. H32-D, H47-S3, and H48-DS are secondary descriptive comparators only; their holdout DTI values must never select the incumbent or affect the promotion gate. This prevents holdout-based comparator selection. H50-prior's byte/hash and local artifact metadata are used only for same-fold benchmarking and uniqueness review; no leaderboard score is mapped to that TIFF.
- Use 32 no-wrap translations of the candidate score field by randomly selected 5–20 km offsets (seed 505006), preserving line geometry while disrupting map alignment. Use 20 time-shuffle controls: permute origin-year labels among relocated in-grid events (seed 505011), then refit the identical candidate pipeline. Both control families use the same folds and prediction budget. The candidate must exceed the 95th percentile of each control family.
- For uncertainty, compare candidate and frozen incumbent DTI in the 16 registered 2 × 2 macrofold subtiles, using a 3-pixel metric halo so cross-subtile matches are available without double-counting. Bootstrap the 16 paired subtile deltas 5,000 times (seed 505007), percentile 95% interval.
- Promotion remains exactly as preregistered: pooled absolute improvement ≥0.005; positive deltas in ≥3/4 macrofolds; bootstrap lower bound >0; and superiority to both matched control families. A fail means **NO SLOT**.

## Pre-run amendment v1.1 — added seismicity and scientific-safety gates

- Add two baseline maps from the exact `reloc=1` catalog events used by H50-S1: isotropic Gaussian event-count surfaces with σ = **1,000 m** and **2,000 m** on the 100 m grid. Normalize each map to its own maximum after smoothing and set outside-template cells to zero. These are density-only controls, not new candidates and not a replacement for H50-prior.
- Score each density map with the same four spatial macrofolds, 37,612 total-cell budget, equal-mass allocation, DTI kernel, and seeded tie-breaking as every other raster. H50-S1 must strictly beat **both** density controls in pooled held-out DTI. Their scores are descriptive controls and cannot be selected post hoc.
- In addition to the numerical gate above, slot eligibility requires: (a) an explicit, reproducible aftershock/sequence-declustering screen; (b) documented mine/injection-site screening with source dates, licenses, buffers, and known coverage gaps; and (c) event-location uncertainty that informs emitted corridor width or is integrated into the predictions. The present catalog/run does not meet those three conditions, so a numerical pass alone remains **NO SLOT**. The 300 m visible-label buffer remains mandatory and does not substitute for any of these controls.
- The density controls use the same relocated events as the candidate; they do **not** solve aftershock or induced-seismicity confounding. No event covariance is imputed from coordinate precision, and event-bootstrap orientation stability is not a location-uncertainty estimate.

## Inputs, permissions, and audit pins

- Nevada catalog: `nvreloc_catalog_newmag.txt`, Zenodo DOI `10.5281/zenodo.11167510`, CC BY 4.0; expected size 13,833,354 bytes, Zenodo MD5 `38fa663f473378b61c74b597c53c416b`. Attribute Trugman (2024), link the DOI and license, and disclose processing changes. This license permits commercial sharing/adaptation, subject to attribution; the official competition page requires external inputs to be licensable and shareable with the sponsor.
- Competition template and label rasters are pinned by SHA-256 in the split file. They are fetched through public Dropbox mirrors whose hashes were recorded in the local source bridge manifest; this confirms byte consistency but does not independently authenticate those mirrors as official originals.
- Raw catalog and raster data stay in ignored `.arena/` scratch. The report records raw-input hashes, code commit, exact fold masks, source artifacts, and output GeoTIFF byte validation.
- No organizer score, hidden labels, portal upload, or current leaderboard reading is used in this experiment.
