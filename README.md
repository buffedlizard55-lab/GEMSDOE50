# GEMSDOE50 — seismic-geometry research for the DOE GEMS Prize

**Project aim:** maximize the probability of a strong result in the [DOE Geologic Enhanced Mapping System (GEMS) Prize Challenge, DrivenData competition 306](https://www.drivendata.org/competitions/306/competition-doe-gems/), by finding defensible, previously unmapped fault traces in the GeoDAWN study area. Core values: **Maximize P(Win)** and **Own the Outcome**.

> **Read this charter before each work session.** It is the standing project purpose and the acceptance criteria for every experiment and deliverable.

## Standing project brief

1. **Deliver a new, unique GeoTIFF prediction.** Generate it from this repository's documented method and pinned inputs. Never copy a previous submission's prediction pixels; earlier artifacts may be inspected only for education, controls, or comparison. The intended download must be a single-band float32 GeoTIFF on the actual competition grid, EPSG:32611, 100 m resolution, with the official shape, transform, and bounds. Predictions must be finite and within `[0, 1]` wherever data are valid; outside-footprint handling must follow the official sample/template and be tested against the reported portal error `Predicted values must be in range [0, 1]`.
2. **Make the artifact easy to find and download.** Put a one-click download and a concise executive summary at the top of the site. Include a clear, numbered “how to submit” page, a unique submission name, and a short distinguishing note for the competition's optional note field. Do not imply portal acceptance when no upload receipt exists.
3. **Do the science before implementation.** Before writing a detector, list and rank 3–5 genuinely distinct geological hypotheses. Each must state the exact layers/data, physical signature, why it could detect a fault missing from USGS/INGENIOUS, how it differs from prior GEMSDOE work, expected DTI direction/impact, implementation cost, and data/license requirements. Preserve the ranking in [`docs/hypotheses-preregistered.md`](docs/hypotheses-preregistered.md); exact implementation choices and controls are frozen in [`docs/h50s1-protocol-addendum.md`](docs/h50s1-protocol-addendum.md).
4. **Protect the weekly submission budget.** Validate the leading hypothesis on a spatially blocked holdout against a frozen, same-fold incumbent and appropriate controls before using any of the competition's three weekly scoring slots. A hypothesis that does not beat the holdout incumbent is not slot-eligible. A local proxy score is not an organizer score or a prediction of private-test performance.
5. **Use compliant, traceable evidence.** Prefer official and peer-reviewed primary sources; link sources directly, state evidence and license status, pin file hashes, and disclose attribution/changes. External data may be used only where the competition permits it, the license permits commercial use, and the data can be shared with the organizers for independent verification. Do not use the scratch mixed-network USGS ComCat extract until its source-specific rights and location uncertainty are resolved.
6. **Do not overstate the literature.** The project tests a 2-D raster adaptation of earthquake lineament methods cited by the user—Ouillon et al. (2008), Ouillon & Sornette (2011), and Wang et al. (2013, arXiv:1304.6912). These papers reconstruct 3-D fault networks from seismicity; the Nevada catalog lacks per-event location probability distributions. A 2-D adaptation is a hypothesis, not a validated transfer of those methods.
7. **Work autonomously and auditably.** Review rules, data, sources, prior attempts, and limitations; record every material decision and irregularity; run multiple implementation/review passes; fix defects found; and maintain a concise next-steps list. Do not ask the owner to do research or resolve issues the agent can verify independently.
8. **Keep the score context honest.** The owner-quoted `0.3195` is historical, not the live leader. Prior sibling-repository notes contain conflicting historical leaderboard values and are not a fresh independent official check; do not repeat them as current official scores or map any score to a TIFF without organizer-verified provenance. DrivenData's Terms of Use prohibit automated monitoring/copying and manual monitoring/copying without prior written consent. This repository links to the official board but does not scrape, poll, or publish leaderboard snapshots.
9. **Follow the prize rules.** The September 2026 NLR/DOE rules require an AI-use disclosure in the narrative, permit up to three feedback submissions per week, and require selection of one final submission for both prize rounds. Finalists must provide reproducible code/assets and documentation. The competition ends December 3, 2026 at 23:59 UTC (verify the official page before any deadline-dependent action).
10. **Create and merge a PR when practical.** Keep all work on Arena's fixed branch `arena/5e2ce8c3-gemsdoe50`. Run tests and review the PR before merging. Do not switch branches or push elsewhere.

## Current evidence and decision (2026-10-07 UTC)

**Where the project actually stands.** The H50-S1 seismicity branch has run; the H51/H52 branch
that followed is the current state of the art here. Read this section as the starting point of
every session, then read [`docs/research/h51-analysis.md`](docs/research/h51-analysis.md) (why the
best prior artifact scored what it did, and what beating 0.3195 requires),
[`docs/research/h51-hypotheses.md`](docs/research/h51-hypotheses.md) (ranked hypotheses with their
fields), and [`docs/research/h51-truth-map.md`](docs/research/h51-truth-map.md) (a negative result
that closes a whole line of attack).

- **The metric, exactly.** With binary dots the official distance-weighted Tversky index collapses
  to `DTI = T / (0.2·N + 0.8·G)`, where `N` is the predicted pixel count, `T` the credit captured
  inside the 300 m kernel, and `G` the hidden truth mass in the scored domain. Inverting the pinned
  blind-lattice artifact gives **`G ≈ 12,226 px`** (±~1 %). Two consequences drive every decision
  below: a dot pays only if it earns more than `0.2·s ≈ 0.05` credit, and coverage — not dot
  count — is the binding term.
- **Every scored artifact inverted.** The 25 hash-verified artifacts of
  `registry/h51_score_corpus.json` were converted to credit pixels (`scripts/h51_truth_map.py`).
  The corpus's best credit per dot is **0.1097** (`gems25-dotted-h19-5-d2-8`, owner-quoted 0.2600)
  and its best coverage is **59.3 %** (a 183,642-dot blanket at 0.0395 credit/dot). **The whole
  group's detector family cannot reach ≈41 % of the hidden truth.** 0.3195 needs `T = 5,042` at
  `N = 30,000` (41.2 % coverage) — reachable in principle, never reached in practice.
- **Instrument, and its honest limit.** The consensus instrument (posterior over the 25 scored
  artifacts) predicts a held-out artifact's real score at leave-one-out Spearman **0.973**
  (`evidence/h51_consensus.json`), but a *trivial* predictor that uses only how similar an artifact
  is to the winners already reaches **0.905**. Most of the instrument's skill is corpus
  self-similarity, its optimum is literally a re-draw of the corpus (98 % of dots on prior pixels),
  and a block-grid **truth-density inversion fails leave-one-out** at every resolution tested
  (`evidence/h51_truth_map.json`). The score history constrains *efficiency*, not geography.
- **Shipped candidate (one click on the site).**
  `downloads/gemsdoe50-h51-corridor-consensus-mix-20261007T0200Z.tif` — 24,000 consensus-core dots
  (every one on a pixel no prior artifact used) plus 6,000 evidence-only exploration dots
  (seismicity-lineament corridors, TMI/radiometric ridges, thermal springs) more than 200 m from
  every prior dot. Format-clean float32 on the official grid, values in `[0, 1]`, NaN outside the
  footprint; **0 pixels shared with any of the 26 prior artifacts**; frozen uniqueness gate
  **PASS** (`max 2 px-proximity IoU 0.4219 < 0.5`, `min_novel_fraction_at_2px 0.2003`). Instrument
  prediction **0.1684** (LOO RMSE 0.025).
- **It is a measurement, not a win, and the README says so before the download.** 0.1684 is below
  the repository's best delivered artifact (owner-quoted 0.2778 for `GEMSDOE32`'s `h33-2-b2`) and
  below the owner-quoted 0.3195 target. It also **fails the pre-registered `sgmc_off` proxy gate**
  (0.0573 vs matched uniform 0.0593) — and that proxy has no demonstrated power to predict a live
  score (ρ = +0.196, p = 0.35 over 25 real scores, `evidence/h51_proxy_ranking_power.json`), so the
  failure is recorded as a limitation rather than explained away. The archived `seislin-44709`
  artifact is the opposite case: priced at 0.0422 by the instrument but 2.5× the uniform control on
  the independent `sgmc_off` frame. The two evidence lines conflict; §12 of the analysis records it
  instead of hiding it.
- **Rejected designs are recorded with their numbers** so no future session re-litigates them: the
  instrument optimum that re-draws the corpus (0.2559, forbidden by the originality rule); a
  pixel-disjoint halo interleave that satisfies the letter of "no copied pixels" but is a one-pixel
  translation of the group's own structure (0.1989, rejected on the 2 px-proximity gate,
  `evidence/h51_ship_novel.json`); an exploration-free core (0.1806, gate-passing, but no new
  territory); and every spacing/thinning variant (recorded in the frontier files).
- **Decision rule for the next slot.** A candidate must (a) pass `scripts/check_submission.py` with
  `GEMS50_CORPUS` mounted (`verdict_unique: true`), (b) beat the frozen incumbent on the consensus
  instrument, and (c) not be a translation of prior structure. No candidate yet beats the
  repository's best delivered score under those rules; the shipped file is the best gate-clean
  measurement available and is the intended use of a slot **only if the owner chooses to spend
  one**.
- **Data reality in this sandbox.** `data/grid/{labels,sample_submission}.tif` are present and
  hash-consistent with the bridge manifest. The 19-band competition feature stack is **not**
  available here and its Dropbox mirrors are network-blocked (as are Zenodo, USGS ScienceBase,
  EarthExplorer, and `raw.githubusercontent.com`); reachable hosts are `github.com`,
  `api.github.com`, `codeload.github.com`, `pypi.org`, and `files.pythonhosted.org`. Staged
  geophysical layers (TMI, K, radiometric, LiDAR scarp features) live in the public sibling
  repository `GEMSDOE24` and are re-clonable from GitHub. The ComCat extract under
  `data/external/` is a mixed-network product whose source-specific rights are unresolved, so it is
  used for exploration only, never as a submission input.

## Executive summary and submission instructions

The site is generated and CI-verified. Root pages come from
[`scripts/build_h50_site.py`](scripts/build_h50_site.py) (`index.html`, `results.html`,
`methods.html`, `submission.html`) and the data feed from [`scripts/build_site.py`](scripts/build_site.py)
(`docs/data/*.json`). The H51 candidate panel on `index.html` is rendered directly from
`evidence/h51_ship.json` and `evidence/h51_check_submission.json`, so the numbers on the site cannot
drift from the evidence. `.github/workflows/h50s1-site-and-checks.yml` and `site.yml` regenerate the
four root pages and fail the build if the committed bytes differ.

**One-click download (top of the site):**
`downloads/gemsdoe50-h51-corridor-consensus-mix-20261007T0200Z.tif` — SHA-256
`a26055834f8e6cc57cc33e96a4a5a26a1adeaafbeec490135af84c6ccd4d1da0`, 339,039 bytes, 30,000
predicted pixels, values `0` / `1`, `float32`, EPSG:32611, 3730×3292, NaN outside the published
footprint, all in-footprint values finite and inside `[0, 1]`. An `-allfinite.tif` sibling sets
`0` outside the footprint for portals that reject non-finite values, so the historical error
`Predicted values must be in range [0, 1]` cannot recur. A `.zip` of the same GeoTIFF is also
offered.

**How to submit (manual, by the owner, never by this repository):** (1) download the `.tif` and
verify the SHA-256 shown on the page; (2) open
[the competition page](https://www.drivendata.org/competitions/306/competition-doe-gems/) and sign
in; (3) upload the single-band GeoTIFF without re-saving, re-projecting or re-compressing it;
(4) use the unique name and the short optional note printed on the page; (5) record the portal
receipt in this repository before claiming any score. `submission.html` carries the same checklist
with the portal's own warnings.

**Status of the artifact.** Format gate PASS and frozen uniqueness gate PASS (worst 2 px-proximity
IoU 0.4219 against 26 prior artifacts, 0 pixels shared with any of them). Instrument prediction
**0.1684** — *below* this repository's best delivered artifact (owner-quoted 0.2778) and below the
owner-quoted 0.3195 target — and the pre-registered `sgmc_off` proxy gate FAILS. It is published as
a measurement the owner may choose to spend one slot on, not as a predicted win; the page says so
above the download.

## Verified project references

| Source | Verified use | Link |
|---|---|---|
| Challenge overview and current deadline | Prize structure; external data must be appropriately licensed and shareable with organizers | [Competition page](https://www.drivendata.org/competitions/306/competition-doe-gems/) |
| Problem, data, metric, and TIFF contract | EPSG:32611, 100 m, single float32 band, `[0,1]`, null/NaN outside; DTI uses 300 m support, α=0.2, β=0.8 | [Problem description](https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/) |
| Prize rules | AI disclosure, 3 weekly feedback submissions, one final selection across both rounds, reproducible finalist package | [September 2026 official rules PDF](https://docs.nlr.gov/docs/fy26osti/96647.pdf) |
| Competition-specific rules entry | Points to the NLR/DOE rules | [DrivenData rules page](https://www.drivendata.org/competitions/306/competition-doe-gems/rules/) |
| Restrictions on leaderboard monitoring | No robot/automatic access for monitoring or copying; no manual monitoring/copying without written consent | [DrivenData Terms of Use](https://www.drivendata.org/termsofuse/) |
| Nevada relocated earthquake catalog | Trugman (2024), CC BY 4.0; metadata and exact downloadable file/checksum | [Zenodo record](https://zenodo.org/records/11167510) · [record API/file metadata](https://zenodo.org/api/records/11167510) |
| Catalog paper | 183,002 3-D-model locations; 103,976 additionally waveform-relocated; location quality depends on the regional velocity model | [Trugman (2024), DOI 10.1785/0220240106](https://doi.org/10.1785/0220240106) |
| Seismicity-to-fault literature | 3-D anisotropic clustering, spatial clustering/segmentation, and explicit location-uncertainty methods | [Ouillon et al. 2008](https://doi.org/10.1029/2007JB005032) · [Ouillon & Sornette 2011](https://doi.org/10.1029/2010JB007752) · [Wang et al. 2013](https://arxiv.org/abs/1304.6912) |
| Reference-solution notebook | Reviewed 2026-10-06: uses a Tversky training loss with α=0.2/β=0.8, but does not implement the official distance-weighted scoring evaluator; scoring authority is the problem-description page above. | [DrivenData reference solution](https://github.com/drivendataorg/gems-prize-reference-solution/blob/main/unet-mc-cv-reference-solution.ipynb) |
| Prior GEMSDOE experiments | Educational evidence only; prior outputs are never copied into this project's deliverable | [GEMSDOE32](https://github.com/buffedlizard55-lab/GEMSDOE32) · [GEMSDOE47](https://github.com/buffedlizard55-lab/GEMSDOE47) · [GEMSDOE48](https://github.com/buffedlizard55-lab/GEMSDOE48) |

## Reproduction

New H50-S1 raw and large inputs belong in ignored `.arena/` or documented external storage, not Git. The inherited `main` history also contains legacy external/derived data and a prior submission; H50-S1 does not consume those files except the pinned prior raster as a same-fold comparator. New deliverables, source/license notes, code, tests, and evidence reports belong in the repository.

```bash
python -m pip install -e '.[test]'
python -m pytest -q

# Public raster mirrors and the CC BY 4.0 catalog; all input hashes are checked.
scripts/download_inputs.sh .arena/run/inputs

# Prior maps are retrieved through GitHub Contents API and checked against pinned commits/hashes.
GH_TOKEN="$(gh auth token)" scripts/fetch_comparators.sh .arena/run/prior

# Optional no-score reconstruction; write to scratch and compare with the committed freeze.
python scripts/freeze_holdout.py \
  --template .arena/run/inputs/example_submission.tif \
  --labels .arena/run/inputs/existing_faults.tif \
  --output .arena/run/recomputed-holdout.json

# Reads the committed split and realized-mask hashes, then runs H50-S1, 20 time shuffles,
# 32 translations, same-fold baselines, and byte-level GeoTIFF checks.
python scripts/run_experiment.py \
  --catalog .arena/run/inputs/nvreloc_catalog_newmag.txt \
  --template .arena/run/inputs/example_submission.tif \
  --labels .arena/run/inputs/existing_faults.tif \
  --prior-dir .arena/run/prior
python scripts/build_h50_site.py

# H51/H52 research pipeline (needs the staged corpus in .arena/work/h51; see scripts/h51_consensus.py)
python scripts/h51_consensus.py            # score instrument + leave-one-out validation
python scripts/h51_truth_map.py            # credit ledger + block-grid truth inversion (negative)
python scripts/h51_validate.py --candidates downloads/*.tif --incumbent downloads/gems50-seislin-*.tif
GEMS50_CORPUS=.arena/work/h51 python scripts/check_submission.py --submission downloads/gemsdoe50-h51-*.tif
python scripts/h51_ship_novel.py           # reproduces the rejected pixel-disjoint H52 design
```

The manually dispatched [H50-S1 research workflow](.github/workflows/h50s1-research.yml) runs on `arena/5e2ce8c3-gemsdoe50` only. It verifies tests and the already-frozen masks before scoring, downloads no hidden labels, does not use the feature stack for H50-S1, and commits only the result report/site/research-only TIFF back to this fixed branch. If sandbox egress is still blocked there, the workflow fails visibly and the limitation remains recorded; no raw data are committed.

## Open gates / next actions

1. **Decide the slot.** The shipped candidate is gate-clean and pixel-novel but predicted below the
   repository's best delivered score; the decision to spend one of the three weekly feedback slots
   belongs to the owner. If spent, it prospectively calibrates the consensus instrument and adds a
   26th hash-verified row to the corpus.
2. **Settle the instrument conflict** (§12 of the analysis). Either submit a corpus-consensus design
   and a seismicity-lineament design in different weeks, or accept the conflict and pick a side with
   a stated rationale. Do not silently average them.
3. **Test hypothesis P1 (dot-economy pruning)**, the only lever with a *measured* sign: the champion
   artifact is past its own family's optimum (`∂DTI/∂N < 0` at 0.2600). Sweep prune thresholds on
   the frozen holdout and both independent frames.
4. **Build a new detector for the missing 41 %** (P2 magnetic-lineament corridors first, then P4
   relay bridges). No amount of re-blending can reach it; analysis §9 and the failed truth inversion
   are the proof.
5. **Fix the acquisition path.** Replace the unusable pre-registered proxy gate with one that has
   demonstrated power against real scores, and re-enable an auditable fetch route for the
   network-blocked official sources (`gh workflow run` currently returns 403 in this environment,
   and `fetch-external-data.yml` is a disabled stub).
6. Keep the site, feed, and evidence in sync with any new artifact; CI enforces byte-identical
   regeneration of the four pages.
