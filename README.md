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
8. **Keep the score context honest.** The owner-quoted `0.3195` is a historical benchmark, not the live leader. A prior project captured a higher public-board value on 2026-10-06, but DrivenData's Terms of Use prohibit automated monitoring/copying and manual monitoring/copying without prior written consent. This repository therefore links to the official board and does not scrape, poll, or publish a refreshed leaderboard snapshot. A public score also does not identify a raster file without an organizer receipt.
9. **Follow the prize rules.** The September 2026 NLR/DOE rules require an AI-use disclosure in the narrative, permit up to three feedback submissions per week, and require selection of one final submission for both prize rounds. Finalists must provide reproducible code/assets and documentation. The competition ends December 3, 2026 at 23:59 UTC (verify the official page before any deadline-dependent action).
10. **Create and merge a PR when practical.** Keep all work on Arena's fixed branch `arena/c6060a3e-gemsdoe50`. Run tests and review the PR before merging. Do not switch branches or push elsewhere.

## Current evidence and decision (2026-10-06 UTC)

- This checkout began as a clean, single-title README repository. The earlier charter, prior-work audit, and ranked hypotheses are already committed on the fixed Arena branch.
- The local ignored `.arena/cache/` bridge contains the competition feature, label, and template rasters. The assembled 19-band feature raster is 418,912,844 bytes with SHA-256 `4371c82e3b8339b807bdffcf4ef59a225520fe2988d521be208ae33743123bc5`; the label and example-submission rasters also match the bridge manifest. **Provenance caveat:** the bridge manifest points to the official data tab and public Dropbox mirrors, but this session did not authenticate to DrivenData and independently re-download the official bytes. Matching hashes establish consistency with the bridge manifest, not organizer provenance.
- The ranked lead remains **H50-S1**, a research hypothesis about waveform-relocated Nevada hypocenter planes and plausible z=0 trace projections. The catalog is public, 2008–2023, 183,002 rows, 103,976 waveform-relocated in the paper, CC BY 4.0, and has Zenodo MD5 `38fa663f473378b61c74b597c53c416b` (13,833,354 bytes). It does not provide per-event location covariance. The data file has **not yet been downloaded into this sandbox**: direct Zenodo `curl` fails TLS here. A manually dispatched GitHub Actions workflow now provides a pinned, auditable acquisition path; it has not yet been run.
- Three prior-work rasters were retrieved via GitHub Contents API into ignored `.arena/cache/prior/` for comparison only. Their source commits/blob IDs and file hashes are pinned in the experiment code. These rasters are not copied into the candidate output.
- The implementation now includes a format-checked catalog parser, robust local 3-D plane/lineament geometry, the official distance-weighted Tversky computation, frozen spatial-mask reconstruction, same-grid comparisons, translation/time-shuffle controls, and byte-level GeoTIFF validation. The unit suite currently passes **13 tests**. The real Nevada-catalog experiment has not run; **no DTI, result report, candidate TIFF, organizer score, portal upload, or weekly slot use is claimed**.
- The exact 3292 × 3730 four-macrofold split and 10 km/300 m mask rules are in [`evidence/holdout-v1.json`](evidence/holdout-v1.json). The realized valid, truth, and per-fold mask hashes are in [`evidence/holdout-realized-v1.json`](evidence/holdout-realized-v1.json). These were created and hash-pinned before any DTI computation. Split-spec SHA-256: `78b6692155c6c6d5f9f19ccee6d595167c2065f1f25eb8d08636d1d9b285ff16`; realized-mask report SHA-256: `981b42e6d0310bf77f79c7c7662a0569c8d2e79514ef4e4a3624a5b07583ae3f`.
- The method remains unvalidated against the hidden expert-labeled set. Existing mapped fault labels are an imperfect spatial proxy; catalog location error may exceed the 300 m metric support. No submission slot will be used unless the preregistered gate passes and an owner manually reviews the data provenance, method, and downloaded TIFF bytes.
- The scratch mixed-network ComCat extract is not used. Its rights and location uncertainty remain unresolved. The project also does not scrape, poll, or copy DrivenData leaderboard rows; a historical `0.3195` is not called the current lead and no score is mapped to a TIFF without verified provenance.

## Executive summary and submission instructions

Static site pages are generated at repository root by [`scripts/build_site.py`](scripts/build_site.py): [`index.html`](index.html), [`results.html`](results.html), [`methods.html`](methods.html), and [`submission.html`](submission.html). When the fixed branch is merged to `main`, the repository's existing GitHub Pages configuration serves the root site at [buffedlizard55-lab.github.io/GEMSDOE50](https://buffedlizard55-lab.github.io/GEMSDOE50/). The site labels the output **research-only** unless every gate passes, and even a local pass is only eligible for manual owner review—not an organizer score or upload receipt.

If (and only if) the protocol passes and the owner approves the artifact, `submission.html` provides a numbered manual portal checklist. The planned unique filename is `gemsdoe50-h50s1-relocated-planes-20261006-research.tif`; the short optional note is “Relocated Nevada event-plane lineaments; 300 m known-fault exclusion; research proxy, not organizer-scored.” The name is only a plan until the verified run produces the TIFF. Re-check the current portal specification and the report's on-disk SHA-256 before any manual upload. No automated portal access is used.

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
| Prior GEMSDOE experiments | Educational evidence only; prior outputs are never copied into this project's deliverable | [GEMSDOE32](https://github.com/buffedlizard55-lab/GEMSDOE32) · [GEMSDOE47](https://github.com/buffedlizard55-lab/GEMSDOE47) · [GEMSDOE48](https://github.com/buffedlizard55-lab/GEMSDOE48) |

## Reproduction

Raw and large inputs belong in ignored `.arena/` or documented external storage, not Git. Final small deliverables, source/license notes, code, tests, and evidence reports belong in the repository.

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
python scripts/build_site.py
```

The manually dispatched [H50-S1 research workflow](.github/workflows/h50s1-research.yml) runs on `arena/c6060a3e-gemsdoe50` only. It verifies tests and the already-frozen masks before scoring, downloads no hidden labels, does not use the feature stack for H50-S1, and commits only the result report/site/research-only TIFF back to this fixed branch. If sandbox egress is still blocked there, the workflow fails visibly and the limitation remains recorded; no raw data are committed.

## Open gates / next actions

1. Run the fixed-branch `H50-S1 preregistered research run` workflow to retrieve and verify the catalog and input rasters from public sources.
2. Review the complete event-count, depth/magnitude irregularity, and spatial-coverage audit; stop if the relocated points do not overlap the valid footprint adequately.
3. Compute the frozen fold-wise DTI, 16-block bootstrap, same-fold incumbent, and matched translation/year-shuffle controls. If the promotion gate fails, do not spend a slot.
4. Re-open and byte-validate the generated unique GeoTIFF, update the static executive-summary/results/submission pages, and review licensing, attribution, limitations, and AI disclosure.
5. Open a PR from the fixed branch, run the full implementation/review passes, and merge only if the report, artifact, site, and evidence agree. No upload is performed by this repository.
