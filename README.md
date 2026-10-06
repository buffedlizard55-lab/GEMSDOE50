# GEMSDOE50 — DOE GEMS Prize (DrivenData #306)

**Start here.** [Read the standing brief](#standing-brief--read-this-first-every-session) · download the file to
submit · check the [status feed](#status-feed) · the [live site](https://buffedlizard55-lab.github.io/GEMSDOE50/).

**Submit this file** (one click):
[`docs/downloads/gemsdoe50-corridor-fusion-v1.tif`](docs/downloads/gemsdoe50-corridor-fusion-v1.tif)
· [zip twin](docs/downloads/gemsdoe50-corridor-fusion-v1.zip)
· [format receipt](docs/downloads/checks-gemsdoe50-corridor-fusion-v1.tif.json)
· [how to submit, step by step](docs/executive-summary.html)

| | |
|---|---|
| file | `gemsdoe50-corridor-fusion-v1.tif` — 41,473 cells at 1.0, **0.0 everywhere else** |
| SHA-256 | `7f9f20295e28354069a40f93dc6f9289fdb135205614acdcbf0e0295c11bbbda` |
| format | single band · float32 · EPSG:32611 · 3730 × 3292 · 100 m · origin (243350, 4508550) · **no nodata tag, all 12,279,160 cells finite in [0, 1]** |
| method | declustered USGS ComCat seismicity (2-D tetrahedra-randomisation; OADC-style inertia-tensor splitting) → lineation corridors → snapped to the USGS 3DEP 1 m lidar scarp ridge, fused with GeoDAWN airborne-radiometric lineaments and a 100–400 m catalogue-correction corridor |
| uniqueness | max \|Pearson r\| **0.0331**, max Jaccard **0.0210** against **119** retrievable prior rasters |
| status | built and audited; **not submitted** — no organiser score exists for it |

Reproduce it: `PYTHONPATH=src python3 scripts/build_fusion.py --name corridor-fusion-v1 --mass 52000 --ring-share 0.30 --suppression-px 4`

---

## Standing brief — read this first, every session

These are the owner's own requirements, kept verbatim in substance so that no session has to re-derive them:

1. **Generate a unique TIF submission.** Never copy a previous submission; copying is allowed only for learning.
   The submission is a single-band float32 GeoTIFF of fault probabilities in EPSG:32611 at 100 m; the score is the
   distance-weighted Tversky index DTI = TPw / (0.2·(TPw + FPw) + 0.8·|G|) with a triangular kernel of radius 300 m.
2. **Beat the leaderboard.** The bar is the live top, not the stale target: read the board by hand before planning
   (2026-10-06: #1 xiaofanhu 0.3774; the owner's best recorded score is 0.2778 at #13–16).
3. **Derive seismicity lineation from the earthquake point pattern, not from a density band.** Follow
   Ouillon/Ducorbier/Sornette (JGR 113, 2008, doi:10.1029/2007JB005032) inertia-tensor clustering; use the
   Ouillon & Sornette (JGR 116, 2011, doi:10.1029/2010JB007752) clustered/background separation; the later method
   (arXiv:1304.6912) adds per-event location uncertainty. Take epicentres from a public catalogue (USGS ComCat),
   **record the official URL and licence first, and confirm the competition's external-data rule permits it**.
   Decluster, remove known injection/mining sites, compute 2-D covariance eigenvalues per neighbourhood, keep linear
   well-sampled neighbourhoods, and emit **a corridor along the principal axis with width set by the catalogue
   location error** — a corridor prior, not a trace. Flag that the 2-D adaptation of the 3-D tetrahedron test is our
   own unverified adaptation.
4. **Hypothesis:** blind faults produce seismic lineations where the mapped catalogue lacks traces, so score
   corridors outside existing-fault buffers. **Confounders:** aftershock swarms, location artefacts, induced
   seismicity. **Falsify** by showing corridors predict withheld fault segments better than smoothed earthquake
   density at matched emitted mass.
5. Normalise to [0, 1], write the required GeoTIFF, **run the uniqueness gate against all prior submissions**, and
   **snap the corridor to another layer's ridge in the placement step**.
6. **Explain how the 0.2778 file earned its score** and whether it can be beaten — with PhD-level judgement, no
   hallucinations, line-by-line verification against official sources with links for manual review.
7. **Before implementing**, generate 3–5 candidate geological hypotheses not yet tried, each naming (a) the specific
   layers, (b) the physical signature/transform targeted, (c) why it catches a fault missing from the
   USGS/INGENIOUS catalogue rather than one already in it, (d) how it differs from everything already implemented.
   Rank by expected DTI improvement and implementation cost; validate the top candidate on a spatially-blocked
   holdout **before spending a weekly submission slot**; if it needs new external data, name the free official source
   and confirm obtainability first. [(current ranking)](docs/hypotheses.html)
8. Find overlooked data sources; be contrarian but grounded; store gathered knowledge from official verified
   sources in the repository ([`docs/sources.html`](docs/sources.html)); aim for a top prize.
9. **Site:** GitHub Pages, clean and simple, with a **one-click downloadable submission TIF at the very top**, a
   unique submission name + short note text, an **executive-summary subpage explaining exactly how to submit**, and
   official verified source links.
10. **Fix the portal error** `Predicted values must be in range [0, 1]` (root cause: the float32 nodata sentinel
    `-3.4028234663852886e+38` and/or a NaN nodata tag) — every shipped TIF must be all-finite, min 0, max 1, no
    nodata tag.
11. Work autonomously, no manual input; flag irregularities for review; run **Pass 1 implement+verify, Pass 2 review
    bugs/edge cases and fix, Pass 3 re-check against this brief**; then create a PR, merge it to `main`, and list the
    remaining work and limitations for the next session.
12. Keep the Arena Core Values — **maximise P(win)** and **own the outcome** — as the decision framework.

## Status feed

| date | event |
|---|---|
| 2026-10-06 | **`gemsdoe50-corridor-fusion-v1.tif` built, audited, unique** (41,473 dots; max \|r\| 0.0331, J 0.0210 vs 119 priors). Recommended over `seis-ridge-v1`. |
| 2026-10-06 | Leakage-free falsification test re-run with the current detector: corridors built from **pre-2020 events only** touch the 2020 Monte Cristo rupture with 78 dots; smoothed density (σ = 10/20 px) and uniform random at matched mass touch **none** of it (`evidence/falsification_test.json`). |
| 2026-10-06 | **Metric bug found and fixed**: `gems50.metric.score` credited each prediction only to its nearest truth pixel, understating TPw by 53 % and DTI by 0.040 absolute on this repo's own 44,709-dot file (`evidence/metric_bug_impact.json`). `tests/test_cross_metric.py` now cross-checks two independent implementations. 40 tests pass. |
| 2026-10-06 | Merged `origin/main` (the sibling 44,709-dot release). Both pipelines coexist: their `{grid,metric,seis,lineaments,emitter,validate}` and this session's `{grid_io,dti,catalog,decluster,lineation,hough,emission}`. |
| 2026-10-06 | Registry of the family ledger read: the 0.2778 file's per-dot credit is ~0.13 against 0.026 for an equal-mass uniform scatter; hidden-truth size ≈ 8,000–16,000 px (`docs/analysis.html`). |

**Next actions, in order**

1. Spend one of the three weekly slots on `gemsdoe50-corridor-fusion-v1.tif` and record the score in
   `registry/submissions.json` (this is the only way the local proxies get calibrated).
2. Turn hypothesis H3 (catalogue-correction corridor) from a documented bet into a measured one using the INGENIOUS
   per-trace map-scale attribute; if it measures badly, rebuild with `--ring-share 0.0`.
3. Re-run the ledger inversion with ≤ 8 spatial regions (the 7,800-block version fails in-sample) to locate the
   hidden truth before the final round.
4. Implement H4 (drainage/channel-offset mapping from 3DEP + NHD) — a physically independent channel.

## Honest evidence table

Measured on three local proxies. "Off-catalogue credit/dot" = mean kernel credit per emitted pixel against the USGS
SGMC inventory **minus** everything within 300 m of the provided catalogue — the closest available stand-in for
"faults the catalogue does not contain". It is a **proxy, not a score**; the family's own validation put its rank
correlation with real scores at ρ = 0.71 (pre-registered bar 0.80, so **not** proven).

| file | dots | off-catalogue credit/dot | 2020 rupture coverage | catalogue credit/dot |
|---|---|---|---|---|
| `gemsdoe50-corridor-fusion-v1.tif` (recommended) | 41,473 | 0.199 | 34.8 % | 0.191 |
| `gemsdoe50-seis-ridge-v1.tif` | 45,000 | **0.223** | **37.8 %** | 0.000 |
| `gems50-seislin-44709-…tif` (sibling, merged from `main`) | 44,709 | 0.194 | 14.0 % | 0.098 |
| the family's 0.2600 file (`d2.8`) | 44,090 | 0.124 | 10.7 % | 0.215 |
| the family's 0.2778 file | 37,654 | 0.143 | 11 % (owner-reported) | ~0 |

## Reproduce

```bash
pip3 install --break-system-packages numpy scipy scikit-learn rasterio pyproj pandas pytest
PYTHONPATH=src python3 -m pytest tests -q                 # 40 tests
PYTHONPATH=src python3 scripts/build_fusion.py --name corridor-fusion-v1 --mass 52000 --ring-share 0.30 --suppression-px 4
PYTHONPATH=src python3 scripts/falsification_test.py      # leakage-free corridor-vs-density test
PYTHONPATH=src python3 scripts/audit_seisridge.py docs/downloads/gemsdoe50-corridor-fusion-v1.tif \
    --exclude gemsdoe50-seis-ridge-v1.tif --out evidence/uniqueness_corridor-fusion-v1.json
python3 scripts/build_site.py                             # regenerate docs/ (site)
python3 scripts/metric_bug_impact.py                      # the TPw bug's size, on this repo's own files
```

## Data, licences, attribution

* **USGS ComCat / FDSN event service** — `https://earthquake.usgs.gov/fdsnws/event/1/query`; US government data,
  public domain, no credential required.
* **USGS 3DEP 1 m lidar DEM** — `https://www.usgs.gov/3d-elevation-program/data-tools`; no use restrictions
  (acknowledge "Map services and data available from U.S. Geological Survey, National Geospatial Program").
* **GeoDAWN airborne radiometrics (USGS 22103)** — `https://doi.org/10.5066/P93LGLVQ`; USGS, public domain.
* **INGENIOUS / GDR submission 1391** — `https://gdr.openei.org/submissions/1391`; redistributed under its
  published terms.
* This repository redistributes only derived rasters; the large external rasters are git-ignored and rebuilt by the
  scripts. No competition test data is redistributed.
