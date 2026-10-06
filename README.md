# GEMSDOE50 — GEMS Prize (DrivenData #306)

**Submission:** [`downloads/gems50-seislin-44709-20261006T2041Z-79e260ae.tif`](downloads/gems50-seislin-44709-20261006T2041Z-79e260ae.tif)
(single-band float32 GeoTIFF, EPSG:32611, 100 m, values exactly {0, 1}, NaN outside the
study footprint; a `.zip` containing the identical file is provided for the form's
alternative upload path). **Format checks: 15/15 pass. Uniqueness gate: pass** against
all 50 known prior artifacts (no identical hash, ≤ 0.36 IoU, ≥ 47 % of dots novel at
200 m); CI re-runs the gate at coarse 32× signature level from
`registry/prior_artifact_signatures.npz`. See [`registry/submission_checks.json`](registry/submission_checks.json).

**Paste-in note (one line for the submission form):**

> GEMSDOE50 — 44,709 binary dots placed on the marginal-credit support of a
> LiDAR-scarp-chain field with a falsified seismicity-corridor hedge; identical GeoTIFF
> also in the .zip. Format, range and uniqueness verified in
> registry/submission_checks.json.

---

## Standing project prompt (the owner's words)

> Deliver in repo `GEMSDOE50` (fork-free, must become a new public GitHub repo + Pages site):
>
> * **A unique .tif submission for DrivenData DOE GEMS Prize (#306), easy one-click
>   download, one file, zero range violations**, named uniquely with a short paste-in
>   note. Must NOT duplicate any prior GEMSDOE artifact (uniqueness gate required).
> * Answer, with PhD-level reasoning, why `GEMSDOE32/h33-h33-2-b2` scored 0.2778 and
>   whether a higher score is achievable (current public leaderboard best ≈0.3195 per
>   user — **updated: the live board reads 0.3774 as of 2026-10-06**).
> * Before implementing: generate **3–5 candidate geological hypotheses not yet tried**,
>   each naming the specific layer(s), the physical signature/transform targeted
>   (edge/curvature etc.), why it should catch a fault missing from USGS/INGENIOUS
>   catalogues rather than one already in them, and how it differs from everything
>   already in the repo; rank by expected DTI improvement vs implementation cost;
>   **validate the top candidate on the spatially-blocked holdout before spending a
>   weekly submission slot**; if a candidate needs new external data, name specific free
>   official sources and verify obtainability.
> * Put the user's full project prompt into the repo README and treat it as the standing
>   starting point (re-read each session); keep "**Maximize P(Win)**" and
>   "**Own the Outcome**" as focal decision values.
> * Site: clean, simple, user-friendly GitHub Pages with official verified source links,
>   executive-summary subpage explaining exactly how to submit, and the report/utilities
>   the user asked for (automatic no-manual-check workflow, current feed, CSV preview).

**Focal decision values (kept in view at every step):** *Maximize P(Win)* — spend effort
where it changes the probability of winning the prize, not where it produces tidy
artifacts; *Own the Outcome* — every number here is produced, checked and reported by
this repository, including the result that failed.

**Standing rules honoured by this repository:** read the whole prompt each session;
work line by line; verify from official sources with links for manual review; no
hallucinations; flag irregularities for review; **no manual input** — everything below
is produced by scripts in this repository.

---

## What was delivered

| deliverable | path |
| --- | --- |
| submission GeoTIFF (one click) | `downloads/gems50-seislin-44709-20261006T2041Z-79e260ae.tif` |
| submission as a .zip (form's alternative) | `downloads/gems50-seislin-44709-20261006T2041Z-79e260ae.zip` |
| format + uniqueness evidence | `registry/submission_checks.json` |
| both-frame validation of the exact file | `registry/submission_validation.json` |
| build diagnostics | `registry/submission_build.json` |
| hypothesis ranking (5) | `docs/research/hypotheses.md` |
| metric / 0.2778 analysis | `docs/research/score-model.md` |
| data provenance receipts | `registry/sources.json` |
| site | `docs/` (GitHub Pages) |

## Headline numbers [MEASURED]

Equal-dot-budget comparison on two frames, 44,090 dots (details in
`registry/field_validation.json`, `registry/fusion_experiment.json`):

| field | catalogue-fold frame (F1) | off-catalogue SGMC frame (F2) |
| --- | ---: | ---: |
| LiDAR scarp-dipole chains | 0.0113 | **0.0345** |
| multi-physics lineaments | **0.0217** | 0.0087 |
| seismicity corridors | 0.0073 | 0.0066 |
| smoothed 300 m quake density | 0.0112 | 0.0043 |
| uniform random | 0.0209 | 0.0190 |

The shipped file, scored on the same frames, reaches **F1 = 0.0416 mean / F2 = 0.0670**
(2.2–5.7× the matched random control, `registry/submission_validation.json`) — the
fusion uses scarp as the leading term (0.60) with the falsified corridor field at 0.25
and the multi-physics consensus at 0.35, because the off-catalogue frame, not the
catalogue frame, is the one that resembles the private test set.

**The honest falsification.** The owner's seismicity-lineament hypothesis (H50-B) was
implemented and **failed its registered test** on both available frames: the corridors do
not beat smoothed earthquake density at equal dot budget. It is retained at low weight as
a diversity hedge only, and the failure is reported everywhere the score is reported.
See `docs/research/hypotheses.md` § H50-B.

## Reproduce

```bash
python3 -m pytest tests/ -q                       # 13 tests, metric identity included
python3 scripts/fetch_external_data.py            # ComCat fetch (needs network/GH runner)
python3 scripts/build_field.py                    # components -> /tmp/gems50/cache
python3 scripts/validate_fields.py                # two-frame equal-budget table
python3 scripts/fuse_experiment.py                # fusion variants (slow, ~9 min)
python3 scripts/build_submission.py               # writes the GeoTIFF
python3 scripts/check_submission.py               # 15 format checks + uniqueness gate
python3 scripts/validate_submission.py            # scores the exact file on both frames
```

## Official sources

* Problem + scoring: <https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/>
* Competition rules: <https://www.drivendata.org/competitions/306/competition-doe-gems/page/964/>
* Leaderboard (read 2026-10-06): <https://www.drivendata.org/competitions/306/competition-doe-gems/leaderboard/>
* Reference solution: <https://github.com/drivendataorg/gems-prize-reference-solution>
* USGS ComCat (public domain): <https://earthquake.usgs.gov/fdsnws/event/1/>
* USGS SGMC / GDR 1391 (public domain / CC BY 4.0): receipts in `registry/sources.json`

---

*Every quantitative statement here is reproduced by a script committed in this
repository; nothing relies on manual inspection. Scores on the private leaderboard are
unknown to this project, and none of the numbers above is presented as a leaderboard
score.*
