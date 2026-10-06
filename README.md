# GEMSDOE50 — seismic-geometry research for the DOE GEMS Prize

**Project aim:** maximize the probability of a strong result in the [DOE Geologic Enhanced Mapping System (GEMS) Prize Challenge, DrivenData competition 306](https://www.drivendata.org/competitions/306/competition-doe-gems/), by finding defensible, previously unmapped fault traces in the GeoDAWN study area. Core values: **Maximize P(Win)** and **Own the Outcome**.

> **Read this charter before each work session.** It is the standing project purpose and the acceptance criteria for every experiment and deliverable.

## Standing project brief

1. **Deliver a new, unique GeoTIFF prediction.** Generate it from this repository's documented method and pinned inputs. Never copy a previous submission's prediction pixels; earlier artifacts may be inspected only for education, controls, or comparison. The intended download must be a single-band float32 GeoTIFF on the actual competition grid, EPSG:32611, 100 m resolution, with the official shape, transform, and bounds. Predictions must be finite and within `[0, 1]` wherever data are valid; outside-footprint handling must follow the official sample/template and be tested against the reported portal error `Predicted values must be in range [0, 1]`.
2. **Make the artifact easy to find and download.** Put a one-click download and a concise executive summary at the top of the site. Include a clear, numbered “how to submit” page, a unique submission name, and a short distinguishing note for the competition's optional note field. Do not imply portal acceptance when no upload receipt exists.
3. **Do the science before implementation.** Before writing a detector, list and rank 3–5 genuinely distinct geological hypotheses. Each must state the exact layers/data, physical signature, why it could detect a fault missing from USGS/INGENIOUS, how it differs from prior GEMSDOE work, expected DTI direction/impact, implementation cost, and data/license requirements. Preserve this preregistration in [`docs/hypotheses-preregistered.md`](docs/hypotheses-preregistered.md).
4. **Protect the weekly submission budget.** Validate the leading hypothesis on a spatially blocked holdout against a frozen, same-fold incumbent and appropriate controls before using any of the competition's three weekly scoring slots. A hypothesis that does not beat the holdout incumbent is not slot-eligible. A local proxy score is not an organizer score or a prediction of private-test performance.
5. **Use compliant, traceable evidence.** Prefer official and peer-reviewed primary sources; link sources directly, state evidence and license status, pin file hashes, and disclose attribution/changes. External data may be used only where the competition permits it, the license permits commercial use, and the data can be shared with the organizers for independent verification. Do not use the scratch mixed-network USGS ComCat extract until its source-specific rights and location uncertainty are resolved.
6. **Do not overstate the literature.** The project tests a 2-D raster adaptation of earthquake lineament methods cited by the user—Ouillon et al. (2008), Ouillon & Sornette (2011), and Wang et al. (2013, arXiv:1304.6912). These papers reconstruct 3-D fault networks from seismicity; the Nevada catalog lacks per-event location probability distributions. A 2-D adaptation is a hypothesis, not a validated transfer of those methods.
7. **Work autonomously and auditably.** Review rules, data, sources, prior attempts, and limitations; record every material decision and irregularity; run multiple implementation/review passes; fix defects found; and maintain a concise next-steps list. Do not ask the owner to do research or resolve issues the agent can verify independently.
8. **Keep the score context honest.** The owner-quoted `0.3195` is a historical benchmark, not the live leader. A prior project captured a higher public-board value on 2026-10-06, but DrivenData's Terms of Use prohibit automated monitoring/copying and manual monitoring/copying without prior written consent. This repository therefore links to the official board and does not scrape, poll, or publish a refreshed leaderboard snapshot. A public score also does not identify a raster file without an organizer receipt.
9. **Follow the prize rules.** The September 2026 NLR/DOE rules require an AI-use disclosure in the narrative, permit up to three feedback submissions per week, and require selection of one final submission for both prize rounds. Finalists must provide reproducible code/assets and documentation. The competition ends December 3, 2026 at 23:59 UTC (verify the official page before any deadline-dependent action).
10. **Create and merge a PR when practical.** Keep all work on Arena's fixed branch `arena/c6060a3e-gemsdoe50`. Run tests and review the PR before merging. Do not switch branches or push elsewhere.

## Current evidence and decision (2026-10-06 UTC)

- This checkout began at the single-title README commit. It had no committed code, site, holdout report, or submission. This is a clean project, not a continuation of an uncommitted prediction.
- A local, ignored competition-data bridge is present under `.arena/cache/`. The assembled 19-band feature raster is 418,912,844 bytes with SHA-256 `4371c82e3b8339b807bdffcf4ef59a225520fe2988d521be208ae33743123bc5`; the label and example-submission rasters also match the bridge manifest. **Provenance caveat:** the bridge manifest points to the official data tab and Dropbox files, but this session did not authenticate to DrivenData and independently re-download those official bytes. Hash agreement proves local consistency with the bridge manifest, not organizer provenance.
- A viable seismicity source has now been identified: Trugman's Nevada relocated catalog on Zenodo, exact file `nvreloc_catalog_newmag.txt`, open and marked CC BY 4.0, with an explicit downloadable file and checksum. It covers 2008–2023 and provides a binary waveform-relocation flag. It does **not** publish event-specific location-error distributions. The catalog is promising but does not yet justify a submission.
- The scratch ComCat extract is not used. Earlier coverage analysis found most Nevada-network events have no reported `horizontalError`; the meaning/calibration of that field and the rights in mixed-network records were not established.
- Prior-project evidence is mixed: old scalar earthquake density was too spatially smooth; multiple magnetic/strain/thermal and geophysical fusion ideas have failed controls or holdout tests; a recent geomorphic candidate passed controls but is not yet cross-fitted-LATI validated. See [`docs/prior-work.md`](docs/prior-work.md) and the preregistered hypotheses.
- No DrivenData login/session is available in this workspace, so this agent cannot use a submission slot, read private scores, or confirm portal acceptance. No slot has been used.
- **Current gate:** H50-S1 (relocated seismicity geometry) is the leading research hypothesis. It must pass the frozen spatial holdout and controls before a candidate can be described as slot-eligible. No submission TIFF or leaderboard score is claimed at this stage.

## Verified project references

| Source | Verified use | Link |
|---|---|---|
| Challenge overview and current deadline | Prize structure; external data is encouraged only with appropriate license and shareability to organizers | [Competition page](https://www.drivendata.org/competitions/306/competition-doe-gems/) |
| Problem, data, metric, and TIFF contract | EPSG:32611, 100 m, single float32 band, `[0,1]`, null/NaN outside; DTI uses 300 m support, α=0.2, β=0.8 | [Problem description](https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/) |
| Prize rules | AI disclosure, 3 weekly feedback submissions, one final selection across both rounds, reproducible finalist package | [September 2026 official rules PDF](https://docs.nlr.gov/docs/fy26osti/96647.pdf) |
| Competition-specific rules entry | Points to the NLR/DOE rules | [DrivenData rules page](https://www.drivendata.org/competitions/306/competition-doe-gems/rules/) |
| Restrictions on leaderboard monitoring | No robot/automatic access for monitoring or copying; no manual monitoring/copying without written consent | [DrivenData Terms of Use](https://www.drivendata.org/termsofuse/) |
| Nevada relocated earthquake catalog | Trugman (2024), CC BY 4.0; metadata and exact downloadable file | [Zenodo record](https://zenodo.org/records/11167510) · [record API/file metadata](https://zenodo.org/api/records/11167510) |
| Catalog paper | 183,002 3-D-model locations; 103,976 additionally waveform-relocated; location quality depends on the regional velocity model | [Trugman (2024), DOI 10.1785/0220240106](https://doi.org/10.1785/0220240106) |
| Seismicity-to-fault literature | 3-D anisotropic clustering, spatial clustering/segmentation, and explicit location-uncertainty methods | [Ouillon et al. 2008](https://doi.org/10.1029/2007JB005032) · [Ouillon & Sornette 2011](https://doi.org/10.1029/2010JB007752) · [Wang et al. 2013](https://arxiv.org/abs/1304.6912) |
| Prior GEMSDOE experiments | Educational evidence only; prior outputs are never copied into this project's deliverable | [GEMSDOE32](https://github.com/buffedlizard55-lab/GEMSDOE32) · [GEMSDOE47](https://github.com/buffedlizard55-lab/GEMSDOE47) · [GEMSDOE48](https://github.com/buffedlizard55-lab/GEMSDOE48) |

## Reproduction and publication

Raw and large inputs belong in ignored `.arena/` or documented external storage, not Git. Final small deliverables, source/license notes, code, tests, and evidence reports belong in the repository. Use the site as the project executive summary; keep the README as the standing charter and index to the evidence. Never automate access to DrivenData's leaderboard or bypass its authentication.

## Open gates / next actions

1. Download the exact CC BY 4.0 Nevada catalog into ignored scratch storage; verify MD5/SHA-256 and attribution before processing.
2. Implement the preregistered, event-level lineament extractor and matched spatial/random/time-shuffle controls. Do not substitute the smoothed `ieq_n100a15` feature for event geometry.
3. Rebuild the same spatial holdout for the leading prior candidates and H50-S1; publish fold-wise DTI and block-bootstrap uncertainty. If H50-S1 fails, do not spend a slot.
4. Only after a pass, generate and byte-reopen-validate a unique TIFF; build the executive-summary site and reproducibility instructions. Keep the status “research only” unless every gate passes.
5. Create the PR, run the full review/test passes, and merge only after the evidence and artifact agree.
