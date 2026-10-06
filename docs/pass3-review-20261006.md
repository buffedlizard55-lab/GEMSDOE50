# Pass-3 re-check against the original request (2026-10-06 UTC)

This file closes the third review pass. Pass 1 built and verified the H51 candidate, Pass 2 hunted bugs
and edge cases, and Pass 3 re-read the original request line by line and checked every clause against an
artifact in this repository. Anything that could not be satisfied is listed as remaining work or a
limitation, not as a claim.

## 1. Requirement-by-requirement status

| Original requirement | Where it is satisfied | Status |
| --- | --- | --- |
| A unique TIF submission for competition 306, no copied pixels | `docs/downloads/gems51-scarpradio-offcat-35000-20261006-ecf058ea-nan.tif`, sha256 `8f8708d2872b66d71925707e0aede23eebcf217dfd2e57d6e61186f32e686f5d`; `evidence/uniqueness_h51.json` (new hash, 953 px / 2.72 % exact-pixel overlap with the nearest prior artifact, `max_overlap_of_mine` 0.9987 is a *shape* statistic against a lattice reference and is reported, not hidden) | **MET** (unique bytes; no prior raster was read into the belief field) |
| Beat the historical leaderboard context (0.3195; own family best 0.2778) | Not claimed. Local proxy instruments only: sgmc-off credit/dot 0.1889 vs matched random controls 0.112–0.126, 4/4 blocked folds positive, paired mean +0.0583 (CI95 0.0406–0.0785) | **PARTIAL** — no organizer score exists; the step to a leaderboard number is unverified by construction |
| One-click download at the very top of the site | `index.html` top band (`h51_download_band`): GeoTIFF, all-finite twin, zip, unique name, note, sha256, verified on the live Pages site | **MET** |
| Fix `"Predicted values must be in range [0, 1]"` | `scripts/verify_h51_raster.py` re-opens the written bytes: 1 band, float32, EPSG:32611, 3292×3730, transform `(100,0,243350,0,-100,4508550)`, 5,167,373 finite cells all in [0,1], 0 outside, NaN only outside the footprint, 35,000 non-zero | **MET** |
| Unique submission name + short portal note | `GEMSDOE50-H51-SCARPRADIO-OFFCAT`; note in the download band, `submission.html`, README step 5, and `registry/sources.json` | **MET** |
| Executive-summary subpage explaining exactly how to submit | Root `index.html` (executive summary + band), `submission.html` (6-step manual path), `docs/executive-summary.html` and `docs/how-to-submit.html` redirect to the current pages with archive banners | **MET** |
| 3–5 untried geological hypotheses, each naming layers, physical signature, why a catalogued fault can be missed, and the difference from what is implemented | 5 candidates (H52-A…H52-E) in `docs/h51-candidates.md`, the site's `methods.html` table, and a ranked card on the executive-summary page | **MET** |
| Ranked by expected DTI improvement vs implementation cost | Rank + `cost x/5` + `expected gain` columns in the same table; H52-A first (cost 4/5, high gain), H52-B second | **MET** |
| Validate the top candidate on the spatially-blocked holdout before spending a weekly slot | Rule stated in the candidates table and on the site; the shipped H51 file passed it (`evidence/holdout_h51.json`: 4/4 folds, paired mean +0.0583, CI95 [0.0406, 0.0785]) | **MET for H51; open for H52-A** (not yet implemented) |
| Name a specific free official source when new external data is needed | H52-A: USGS 3DEP 1 m DEM + USGS NHD; H52-C: GDR submission 1391 + INGENIOUS (already mirrored); H52-E: USGS ANSS ComCat focal mechanisms; H52-B/H52-D need no new data | **MET** |
| Seismicity lineations from the point pattern, declustered, injection/mining sites removed | H51-B implemented all of it (222,939 → 70,509 ComCat rows, 813 induced-buffer events removed at Steamboat/Dixie/San Emidio/Patua, 9 clusters, 1,008 corridors) and **failed its own test** (solo 0.0972 at 20 k, below the 0.1158 random control; MC 0.0) — so it carries no mass in the shipped file | **NEGATIVE RESULT, published not buried** |
| Corridors scored only outside existing-fault buffers; falsified against smoothed density | `docs/research/earthquake-geometry-review-20261006.md`, `evidence/falsification_test.json`, density controls on `results.html` | **MET** |
| Full prompt in README as the standing brief | `README.md` §Standing project brief (10 numbered items) | **MET** |
| Solve manual checking and keep an up-to-date feed | `scripts/verify_h51_raster.py`, `scripts/uniqueness_h51.py`, `scripts/validate_h51_holdout.py`, `scripts/mc_sensitivity_h51.py` are re-runnable with pinned hashes; `docs/data/feed.json` carries the H51 block and `evidence/build_h51.json` stamps the builder script argv + every input hash | **MET** |
| Multiple passes, PR, merged to `main`, remaining work listed | PR #8 squashed to `main` as `129a66d`; this pass adds PR #9; see §4 below | **MET** |
| No scraping/polling/automated portal access | No portal client exists in the repository; `registry/sources.json` records the DrivenData ToU restriction; the one historical automated leaderboard request is disclosed in README | **MET** |
| No hallucinations — verify against official/trusted sources | Metric transcribed from the official problem page and mirrored in `src/gemsdoe50/metric.py`; every external number in the site links its source; the h_err imputation is labelled as this project's own construction, not from arXiv:1304.6912 | **MET** |

## 2. Pass 1 — build and verify

- `scripts/build_h51.py` (deterministic; second clean run reproduced the identical sha256 in 147 s).
- Belief `0.75 x topographic scarp + 0.55 x radiometric` on the official 19-band stack, all dots >300 m
  from the provided catalogue, metric-matched sparse emission, mass 35,000 chosen by the published sweep.
- `evidence/build_h51.json` carries the builder stamp (script sha256, argv including `--mass`, per-input
  sha256/bytes), the mass sweep, the instrument table, the holdout block and the uniqueness verdict.

## 3. Pass 2 + Pass 3 — defects found and fixed

| Pass | Defect | Fix |
| --- | --- | --- |
| 2 | `KeyError 'qc'`, `NameError candidates_html`, `IsADirectoryError`, `metric_cards` crash on `evaluation: null` | guarded loaders and pre-defined blocks in `scripts/build_h50_site.py` |
| 2 | 4 `F841` unused locals + unformatted H51 modules; `ruff` missing from the venv | removed locals, `ruff --fix`, ruff installed; CI-scoped ruff green |
| 2 | Site test asserted a bare phrase that also appears in the nav | assert against the `<h2>Executive summary</h2>` heading |
| 2 | Dead subtile loop in `validate_h51_holdout.py`; unclosed template handle in `verify_h51_raster.py` | removed; context manager |
| 2 | A1 mass was still shipped after the A2 mass rule | A1 artifacts deleted, download band repointed |
| 3 | **Merge left literal conflict markers in `README.md`** (the naive two-block resolution only handled the first conflict) and the merge had dropped main's provenance bullets, which broke `scripts/verify_claims.py`'s two guardrails | README unioned by hand (both sides kept), and `verify_claims.py` now has a new guardrail that fails on any `<<<<<<<`/`>>>>>>>`/`=======` marker in the hand-merged files |
| 3 | The executive-summary page still said "No download until data and byte checks pass" *below* a live download band, and its status line described only the unrun H50-S1 hypothesis | the hero tag and the summary card now name the shipped H51 deliverable, its mass, and its non-organizer-scored status, and keep H50-S1 explicitly separate |
| 3 | The 5 ranked untried hypotheses were only in `methods.html` | a compact ranked card (rank, id, name, cost, expected gain, slot rule) now sits on the executive-summary page |
| 3 | `docs/` archive stubs still said "no new H50-S1 GeoTIFF has been produced" | reworded to point at the H51 download; both stubs redirect to the current pages |

## 4. Remaining work

1. **Owner decision + manual upload** of the H51 GeoTIFF (the repository never uploads). Record the
   returned score and portal receipt next to the pinned sha256; until then every number here is a proxy.
2. **H52-A** (scarp-profile matched filter + drainage-deflection corroboration) is ranked first but is not
   implemented. It must pass its own preregistration and the same blocked holdout before a slot.
3. **H50-S1** remains unimplemented because the Nevada catalog cannot be fetched from this sandbox
   (dispatch returns HTTP 403). The frozen split and protocol stay valid for a future run.
4. **H51-B seismicity** should only be revisited if relocated catalogs with per-event covariance become
   available; as measured, epicentre geometry did not beat smoothed density.

## 5. Limitations (do not overstate the result)

- No organizer score, upload receipt, or leaderboard verification exists for any file in this repository.
- The instruments are local proxies: the given-catalogue raster cannot score H51 (H51 emits nothing near
  it by design), the SGMC and Monte-Cristo frames are external products of unknown completeness, and the
  mass-transfer factor (0.28) comes from one owner-quoted artifact pair.
- The block-Jaccard 0.5 uniqueness gate failed at 35,000 px, and the prior-vs-prior null shows the
  threshold is unusable (independent priors reach a 0.825 median at 32 px); the audit therefore reports
  overlap statistics instead of a pass/fail novelty certificate.
- The Monte-Carlo control is a weak guard only (percentiles 75/71/96), and the A3 amendment says so.
- The location-uncertainty model is this project's own regression; the catalog has no per-event covariance.
- H51's advantage is per-dot credit and fold consistency, not a higher total score at equal mass; against
  the `gems50-seislin` incumbent, H51 scores lower on the same frame (0.1158 vs 0.1468 SGMC-off DTI).
- Existing USGS/INGENIOUS labels are an imperfect proxy for the hidden expert set, and a lineament is not
  evidence of geothermal productivity.
- Re-check the official submission contract before uploading; the portal specification can change and this
  repository does not monitor it automatically.
