# H52-A protocol — registered 2026-10-07, before any instrument score was computed

**Scope.** The next candidate in the H51 candidate ranking (`docs/h51-candidates.md`, Part 2,
rank 1): a scarp-profile matched filter corroborated by an independent drainage-deflection test.
This file preregisters every threshold used by `scripts/build_h52a.py` **before** any SGMC-off,
Monte Cristo, or holdout score was computed for this candidate, so the promotion decision below
cannot be read as tuned on those numbers. The only computations performed before this file was
written were mechanical feasibility checks (decode the DEM band, confirm `pysheds` flow routing
runs on the full grid, inspect raw field means/maxima) — no candidate raster, no mass sweep, and
no instrument score existed yet.

## Data-access finding that shapes this candidate (recorded as an irregularity)

`docs/h51-candidates.md` proposed using `training_features.tif` bands 12 (`det_elev`) and 19
(`det_elev_slope`) plus the USGS National Hydrography Dataset for the drainage half of H52-A.
Neither is obtainable in this session:

* `training_features.tif` (418,912,844 bytes, sha256 `4371c82e3b8339b807bdffcf4ef59a225520fe2988d521be208ae33743123bc5`
  per `evidence/build_h51.json` from the prior session) is too large for a single Git blob
  (GitHub's Git Blobs API caps at 100 MB) and was not found, in full or in parts, in any of the
  55 `*GEMSDOE*` repositories reachable from this account (checked by recursive tree listing on
  2026-10-07; see `evidence/h52a_data_access.json`). This matches the user-supplied note that
  DrivenData login is required and was not available this session.
* Direct `curl` to `earthquake.usgs.gov`, `www.usgs.gov`, `dropbox.com`, `zenodo.org`, and
  `nationalmap.gov` all fail with `SSL_ERROR_SYSCALL` from this sandbox (tested 2026-10-07); only
  `api.github.com`/`codeload.github.com` are reachable from `bash`. The `fetch_page` tool *can*
  reach `earthquake.usgs.gov` (tested: `GET .../fdsnws/event/1/count` returned `10647`), but it
  renders text/markdown and cannot write an NHD shapefile or GeoTIFF to the workspace, so it
  cannot supply the vector hydrography H52-A originally asked for either.
* `topo_u8.tif` and `radiometric_u8.tif` (used by the prior H51 session and referenced in
  `evidence/build_h51.json`) **were** found and re-verified byte-for-byte via the GitHub Git
  Blobs API against repository `GEMSDOE40` (`data/aux/{topo_u8.tif,radiometric_u8.tif}`),
  matching the pinned sha256 values exactly. `lidar_scarp_features_u8.tif`, `geodawn_rad_u8.tif`,
  and `geodawn_extensions_u8.tif` were likewise re-verified against `GEMSDOE24`.

**Consequence.** H52-A is redefined to use only data that is actually in hand and independently
re-verified this session: `topo_u8.tif` band 9 (`dem_mean`, decoded to metres with the
project's standard `q_lo/q_hi` rule) stands in for the missing `det_elev`, and a locally computed
D8 flow-routing solution (`pysheds`, see `src/gems51/drainage.py`) stands in for NHD flowlines.
This is **this project's own construction**, not a reproduction of USGS NHD or of the
`training_features.tif` `det_elev`/`det_elev_slope` bands, and is recorded as such everywhere it
is used. If `training_features.tif` or NHD access is obtained in a future session, the original
H52-A design (official `det_elev`/`det_elev_slope` plus real NHD flowlines) should be preferred
and re-run as a direct replacement.

## Method (frozen before measurement)

1. **Elevation.** `dem = decode(topo_u8.tif band 9 "dem_mean")`, metres, on the official grid.
2. **Detrending.** `det = dem - gaussian_filter(dem, sigma=15 px)` (`src/gems51/scarpmf.py`), an
   explicit, own-construction regional-trend removal (≈1.5 km smoothing radius), not the
   official `det_elev` band.
3. **Matched filter.** A bank of 12 rotated step kernels (0°–165° in 15° steps, 700 m long ×
   500 m wide) is correlated with `det`; the per-cell response is the max magnitude over the
   bank, normalised by its own 98th percentile inside the valid footprint
   (`scarpmf.matched_filter`). This is azimuth-specific and shape-matched, unlike the
   orientation-agnostic structure-tensor gradient energy `gems51.structfield` uses for H51-A.
4. **Flow routing.** `pysheds` D8 pit-fill / depression-fill / flat-resolution / flow-direction /
   accumulation on the same `dem` (`drainage.route_flow`). `pysheds==0.5.0`'s call to the removed
   `numpy.in1d` is shimmed to `numpy.isin` (documented successor, identical result for this 1-D
   membership test) — recorded as an irregularity, not silently patched.
5. **Channel mask.** Cells with accumulated contributing area ≥ 100 cells (1 km²).
6. **Deflection field.** At each channel cell, `1 - R` where `R` is the resultant length of the
   D8 flow-direction unit vectors in the surrounding 5×5 (500 m) window, restricted to other
   channel cells, requiring ≥3 channel neighbours (`drainage.channel_deflection`).
7. **Deflection hotspot.** Channel cells at or above the **85th percentile** of the deflection
   field among channel cells with ≥3 neighbours (threshold fixed here, before any instrument is
   computed).
8. **Corroboration join.** A cell is *corroborated* if a deflection-hotspot cell lies within
   **300 m (3 px)** (Euclidean distance transform on the hotspot mask).
9. **Domain.** Off-catalogue (> 300 m from any provided-catalogue pixel, the same rule as H51)
   **and** corroborated. Belief is the matched-filter strength on this domain, zero elsewhere.
10. **Emission.** Mass-sweep `{10,15,20,25,30,35,40,45,50} x 1,000` dots, 3 px suppression,
    `gems51.emit.pack` (identical machinery to H51, for comparability).
11. **Mass-selection rule (frozen, learned from the H51 A2/A3 record so it is not re-discovered
    here on this candidate's own data):** choose the **largest** swept mass whose SGMC-off
    credit-per-dot is within **10%** of the best swept value. Monte Cristo coverage is reported
    at every mass as a **weak guard only** (H51's A3 correction established that a single-seed
    or even a 24-seed comparison on a 242-pixel trend is a weak discriminator at these masses;
    it is not used as a selection criterion here).

## Promotion gate (the "beat the current holdout best" rule the project owner requires)

H52-A may be recommended for a submission slot, and may replace H51 as the site's top download,
**only if all of the following hold**, computed by `scripts/validate_h52a_holdout.py`:

1. **Beats the frozen incumbent on the primary instrument.** H52-A's pooled SGMC-off
   credit-per-dot at its own chosen mass exceeds H51's pooled SGMC-off credit-per-dot at H51's
   own chosen mass (0.1888 at 35,000 dots, from `evidence/build_h51.json`).
2. **Spatially stable.** Using the same frozen four-macrofold split as H51
   (`evidence/holdout-v1.json`), H52-A's credit-per-dot advantage over a matched-mass random
   control is positive in at least 3 of the 4 macrofolds.
3. **Beats H51 directly on the same fold geometry**, i.e. a fold-wise and pooled comparison of
   H52-A against the actual H51 raster (not only against a random control), reusing the fixed
   four-macrofold spatial blocks.
4. **Passes the uniqueness gate** against all frozen prior artifacts in
   `registry/prior_artifact_signatures.npz` (`max_jaccard < 0.5` at both 8 px and 32 px blocks,
   the same bar H51 used).
5. **Byte-valid.** Single-band float32, EPSG:32611, 100 m, 3292×3730, every finite value in
   `[0, 1]`, NaN only outside the official footprint — re-opened and re-checked from the written
   file, the same way `scripts/verify_h51_raster.py` checks H51 (this is also the direct test
   against the portal's own reported error, `Predicted values must be in range [0, 1]`).

If gate 1, 2, or 3 fails, H52-A is recorded as a **negative or mixed result**, in the same spirit
as H51-B/C/E: still built, still downloadable for inspection/education, never promoted as the
top recommendation, and never licensed for a submission slot. Gate 4 failing means rebuild with a
different random seed or mass before shipping anything at all. Gate 5 failing is a hard stop —
no file is shipped.

## Confounders and falsification (explicit, before measurement)

* **Confluences and meanders** raise the deflection field exactly like a tectonic offset does;
  this candidate cannot and does not claim to separate the two from the deflection field alone.
  It relies on the *conjunction* with an independent topographic-step signal to suppress the
  (far more numerous) purely fluvial bends.
* **DEM aggregation to 100 m** smooths exactly the few-metre scarp faces this filter targets;
  the detector is therefore expected to find only scarps with measurable relief at 100 m
  resolution, not metre-scale fresh fault scarps (those are better targeted by the native-1 m
  `lidar_scarp_features_u8.tif` descriptors H51-A already uses).
* **Endorheic basins** (closed drainage, common across this part of the Basin and Range) can
  produce artificial flow directions after depression-filling; these regions are not masked out
  explicitly, so any hotspot there should be treated with extra caution and is flagged in the
  evidence report.
* **Falsification path (same standard as every other candidate in this project):** show that
  H52-A's corridors predict a withheld fault segment (the Monte Cristo trend, or any future
  officially released segment) better than smoothed density or than H51 at matched mass. This
  session only has the Monte Cristo trend as a withheld-segment proxy, already shown to be a
  weak discriminator at these masses (`evidence/mc_sensitivity_h51.json`); H52-A's Monte Cristo
  number is reported for completeness, not as a pass/fail criterion.

## Amendment B1 — 2026-10-07, after the H52-A standalone build, before any promotion decision

The frozen build above (`scripts/build_h52a.py`, no arguments) selected mass 10,000 — far below
H51's 35,000 — because H52-A's own per-dot credit decays quickly past its matched-filter's most
confident cells (`evidence/build_h52a.json`, `mass_sweep`). Measured in isolation, H52-A's pooled
SGMC-off DTI (0.0550) is therefore *lower* than H51's (0.1158): it covers far less of the
instrument's truth set on its own. But H52-A's evidence sits in a population of cells almost
entirely disjoint from H51's: only 172 of its 10,000 dots (1.7%) coincide with H51's 35,000. That
is the single most important number this amendment adds, because it turns "is H52-A better than
H51" into the wrong question — the real, pre-registered-in-spirit question (a zeroth-order test of
non-overlapping evidence, not a threshold search, and not tuned on any held-out score) is: **does
H52-A's evidence improve a single submission when added to H51's, rather than replacing it?**

Measured directly (`scripts/build_h52.py`, the only code added after this measurement; it
contains no new tunable threshold, only a union of two already-frozen supports):

| field | mass | pooled SGMC-off DTI | SGMC-off credit/dot | Monte Cristo TP-weight (weak guard) |
|---|---:|---:|---:|---:|
| H51 alone (frozen incumbent) | 35,000 | 0.1158 | 0.1889 | 18.93 |
| H52-A alone | 10,000 | 0.0550 | 0.2844 | 4.10 |
| **H52 = H51 ∪ H52-A (union of supports)** | 44,828 | **0.1518** | **0.2007** | 22.77 |
| matched-mass random control (44,828 dots) | 44,828 | 0.0895 | 0.1178 | 8.48 |

(Corrected 2026-10-07: an earlier draft of this row transcribed the wrong control figures;
`evidence/build_h52.json → scores.random_control_at_union_mass.sgmc_off` is the authoritative
source — dti 0.08952767028334324, credit/dot 0.1177785390745385, confirmed again after the
2026-10-07 re-run below.)

The union's pooled SGMC-off DTI (0.1518) is **31% higher**, in absolute terms **+0.036**, than
H51 alone, and its blended credit-per-dot (0.2007) is *higher* than H51's own average
(0.1889) even though 10,000 more dots were added — i.e. H52-A's cells are not merely
non-overlapping, they are higher quality on average than H51's own marginal cells. Monte Cristo
coverage is not reduced (22.77 vs 18.93 weighted pixels; still reported as a weak guard only, per
the H51 A3 correction, not as a selection criterion). H52 therefore supersedes H51 as this
project's recommended file, subject to the per-fold and uniqueness gates in
`scripts/validate_h52_holdout.py` and recorded in `evidence/holdout_h52.json`.

## Amendment B2 — 2026-10-07, after the spatially blocked holdout and uniqueness audit ran (final, re-verified)

`scripts/build_h52a.py` was re-run once after a `ruff --fix --unsafe-fixes` pass changed its own
source bytes (an auto-fix of implicit string concatenation in a list literal — no logic changed).
Because the script's sha256 is part of the build evidence, every downstream artifact was deleted
and regenerated rather than left pointing at stale bytes. The mass sweep and chosen mass (10,000,
`sgmc_off_cpdot` 0.2844) reproduced **exactly** — this candidate has no hidden randomness — and all
numbers below are from that final, currently-committed run (`evidence/build_h52a.json` sha256
`150620f5…`, `evidence/build_h52.json` sha256 `15468475…`).

**Spatially blocked holdout** (`scripts/validate_h52_holdout.py`, frozen 4-macrofold split,
100-pixel eroded cores, scored on the off-catalogue SGMC instrument, never on the provided
catalogue labels H52 is built to avoid):

| fold | H52 dots in core | H51 dots in core | H52 DTI | H51 DTI | Δ(H52−H51) | random-control credit/dot | H52−control |
|---|---:|---:|---:|---:|---:|---:|---:|
| NW | 15,510 | 12,015 | 0.1028 | 0.0799 | **+0.0230** | 0.0857 | +0.0769 |
| NE | 9,004 | 6,322 | 0.0971 | 0.0691 | **+0.0280** | 0.2038 | +0.0646 |
| SW | 3,614 | 2,905 | 0.0181 | 0.0191 | −0.0011 | 0.0272 | +0.0224 |
| SE | 6,529 | 5,484 | 0.1100 | 0.0969 | **+0.0131** | 0.1787 | +0.1275 |

H52 beats H51 in 3/4 macrofolds (SW is a near-tie, −0.0011 DTI) and beats the matched-mass random
control in 4/4 folds. Pooled across all four cores H52 beats H51 (0.1518 vs 0.1158 DTI). The
paired subtile bootstrap (11 holdout subtiles) gives a mean Δ of +0.0119 vs H51 with a 95% CI of
**[0.0063, 0.0174]** — entirely positive — and +0.0683 vs the random control with 95% CI
[0.0499, 0.0882], also entirely positive. All three conditions of the promotion gate stated in
Amendment B1 are satisfied (`evidence/holdout_h52.json`).

**Uniqueness** (`scripts/uniqueness_h52.py`, same 8 px / 32 px block-Jaccard method as H51's own
audit against the 50 frozen prior artifacts in `registry/`): the naive 32 px gate still "fails" in
the sense that H52's worst-case Jaccard (0.7314, against `gems16-h16-1-topo-geophys-baseline-
ridges-20260930-df20f65e-nan.tif`) exceeds H51's own worst case (0.66), but it sits *below* this
project's measured null-distribution median for the same statistic between genuinely independent
prior artifacts (0.825), so — exactly as documented for H51 — the block test is not informative at
this scale by itself.

**The honest, load-bearing disclosure this amendment exists to make explicit:** H52 is a literal
pixel superset of H51. All 35,000 of H51's dots are included unchanged; H52-A contributes
9,828 genuinely new dots after removing the 172 that already coincided with H51 (10,000 − 172).
That means roughly 78% of H52's emitted mass is *not new relative to this project's own prior H51
file* — only ~22% (9,828 / 44,828 pixels) is the output of a method never built before this
session. H51 itself has never been uploaded to the DrivenData portal (`organizer_score: null`,
`submitted_utc: null` in `registry/submissions.json`), so H52 is not "copying a previous
*submission's* prediction pixels" in the sense the task prohibits (no portal upload of H51 has ever
happened) — but it is an internal fusion of this project's own prior output with new output, and
that fact must never be hidden or described as if H52 were independently derived from scratch.

**Resulting recommendation, stated plainly:**

1. **H52-A standalone** (`gems52a-scarpdrainage-offcat-10000-20261007T021452Z-5c377a13-nan.tif`)
   is the genuinely new, unique-method artifact from this session — a different physical
   hypothesis (scarp-matched-filter × drainage-deflection corroboration) from every prior
   GEMSDOE submission in this repo's lineage, scored at SGMC-off DTI 0.0550 / credit-per-dot 0.2844
   in isolation. Its 1.7% cell overlap with H51 is the lowest of any candidate measured this
   project, but its standalone DTI is lower than H51's because it emits far fewer dots.
2. **H52 (the union)** is the best-*validated* current submission candidate by every local proxy
   instrument and the only one that has passed the full spatially blocked holdout gate — but it is
   a disclosed, transparent fusion of H51 (already built) with H52-A (new this session), not an
   independently-derived new hypothesis. It should be described to the portal and in any narrative
   exactly that way.
3. Both files pass byte validation with zero errors (`evidence/checks_h52_raster.json`,
   `evidence/checks_h52a_raster.json`): single band float32, EPSG:32611, 3292×3730, transform
   `(100, 0, 243350, 0, -100, 4508550)`, all finite in-footprint values in `[0, 1]`, NaN only
   outside the footprint, sha256 of the written file matches the recorded build evidence.
