# GEMSDOE50 — audit-first fault mapping for the DOE GEMS Prize

**Project aim:** maximize the probability of a strong result in the [DOE Geologic Enhanced Mapping System (GEMS) Prize Challenge, DrivenData competition 306](https://www.drivendata.org/competitions/306/competition-doe-gems/), by finding defensible, previously unmapped fault traces in the GeoDAWN study area. Core values: **Maximize P(Win)** and **Own the Outcome**.

> **Current decision (2026-10-07 UTC): H53-A is NO-GO / NO SLOT.** The H53-A GeoTIFF is an all-zero research artifact. Do not upload it or spend a weekly scoring slot. Older H51 files are preserved as historical evidence, not current submission recommendations.

## Standing project brief

Read this charter before each work session. It defines the acceptance criteria for every experiment and deliverable.

1. **Generate a unique GeoTIFF from a documented method.** Never copy previous submission pixels into a new candidate; earlier artifacts may be inspected only for education, controls, or comparison. The official format is one-band float32 on the specified grid (EPSG:32611, 100 m, same shape, transform, and bounds), with finite values in `[0,1]` in the valid footprint and null/NaN outside. Reopen and validate the bytes written to disk.
2. **Make the artifact easy to find, without implying it is safe to submit.** Put the direct download at the top of the site, alongside an executive summary and a clearly numbered submission guide. Every artifact has a unique research name and a short optional note. Say explicitly when it is not slot-eligible; never imply portal acceptance without an organizer receipt.
3. **Do the science before implementation.** Rank 3–5 distinct geological hypotheses before writing a detector. State the layers, physical signature, why it could find faults missing from USGS/INGENIOUS, differences from repo/sibling work, expected DTI direction, cost, and data/license needs. Re-check existing work before calling a method new. The current H53 ranking is [`docs/research/h53-hypotheses-20261007.md`](docs/research/h53-hypotheses-20261007.md); the frozen leading test is [`docs/research/h53-preregistration-20261007.md`](docs/research/h53-preregistration-20261007.md).
4. **Protect the weekly submission budget.** Validate the leading candidate on a spatially blocked holdout against a frozen incumbent, mass-matched controls, and uncertainty bounds before using a weekly scoring slot. The candidate must beat the frozen holdout best and clear data, provenance, and raster-format gates. A local proxy is neither an organizer score nor a promise of private-test performance.
5. **Use compliant, traceable evidence.** Prefer official and peer-reviewed sources; link sources directly, state evidence and license status, pin hashes, and disclose attribution and transformations. External data may be used only when the participant has rights for challenge use **and** to share the data with the sponsor for evaluation. Do not use the mixed-network USGS ComCat extract until source-specific rights and location uncertainty are resolved.
6. **Do not overstate the literature or the science.** The 3-D local plane-fitting work and the legacy 2-D ComCat lineation adaptation are not validated transfers of cited methods. The 2-D triangle-area analogue to a 3-D tetrahedron statistic is unverified, and the legacy builder does not apply its computed `keep` mask. See the cautionary review and sources in the archived research record; neither seismicity approach is claimed as validated here.
7. **Work autonomously and auditably.** Review rules, data, prior attempts, and limitations; record material decisions and irregularities; run implementation, review/fix, and re-check passes. Do not ask the owner to perform research or resolve issues that can be verified independently.
8. **Keep score context honest.** The user-provided `0.2778` H33-2-B2 score and `0.3774` current-high-score claim are not independently authenticated. No score is mapped to a TIFF without organizer-verified provenance. DrivenData's Terms of Use restrict automated leaderboard monitoring/copying and manual monitoring/copying without prior written consent; this repository does not poll, scrape, or publish a live leaderboard.
9. **Follow prize rules.** The [September 2026 NLR/DOE official rules](https://docs.nlr.gov/docs/fy26osti/96647.pdf) require an AI-use disclosure in the narrative, permit up to three feedback submissions per week, and require one final selection across both prize rounds. Verify the official page before any deadline-dependent action.
10. **Use the session branch and attempt a PR when practical.** Work stays on `arena/d284137f-gemsdoe50`; do not switch branches. Run tests and review all generated output before any PR/merge.

## Current experiment: H53-A — NO-GO / NO SLOT

H53-A tested whether anisotropic clusters of shallow 2 m temperature-probe measurements align with independent GeoDAWN magnetic lineaments. The registered point-pattern geometry accepted **0 of 145 clusters** and emitted **0 positive pixels**. No threshold was loosened after seeing the result.

| Item | Current H53-A record |
|---|---|
| Decision | **NO SLOT — do not submit or spend a weekly scoring slot** |
| Research TIFF | [`docs/downloads/gemsdoe50-h53-probe-tmi-pointlineation-20261007-44afc05b.tif`](docs/downloads/gemsdoe50-h53-probe-tmi-pointlineation-20261007-44afc05b.tif) |
| Unique research name | `GEMSDOE50-H53-PROBE-TMI-POINTLINEATION-20261007` — identity only, **not an approved portal name** |
| Optional note | `Survey-normalized 2 m probe point-pattern lineations concordant with GeoDAWN TMI_up150; 300 m known-catalogue exclusion; research proxy only, not organizer-scored.` — identity only; do not paste for a submission |
| SHA-256 | `5f2fd91ad46a3602c03802e0f7773fd466b08e47cbfcf40ff796ffc2b956a382` |
| Format | Float32, one band, EPSG:32611, 3292 × 3730, 100 m; finite `[0,1]` values inside the valid footprint; NaN outside |
| Predictions | 0 nonzero cells; all in-footprint values are 0.0; all-zero is not useful for competition submission |
| Reports | [`evidence/h53-build-20261007.json`](evidence/h53-build-20261007.json) · [`evidence/h53-validation-20261007.json`](evidence/h53-validation-20261007.json) |

The download is intentionally prominent at the top of the [project site](index.html) so the artifact and its failure are easy to inspect. **Do not mistake prominence for a recommendation:** the root page, results, and submission guide all label it NO-GO.

### Blocked holdout and controls

All numbers below are local proxy instruments on frozen spatial cores using SGMC fault pixels more than 300 m from the supplied catalogue as truth—not hidden expert labels and not competition/leaderboard scores.

- H53-A native pooled DTI: **0.000000**. The frozen H50-prior seismicity raster scored **0.136074** on this proxy; it is a comparator only, not a novel validated strategy.
- Candidate-minus-incumbent spatial-subtile bootstrap mean: **−0.123304**; 95% interval **[−0.169861, −0.079791]**. H53-A was below the incumbent in all four macrofolds: NW −0.102588, NE −0.096115, SW −0.074476, SE −0.264573.
- Requested incumbent-matched budget was 44,709 full-grid cells (31,819 across the four valid fold cores). H53-A emitted zero; its mass gate failed.
- Controls: 500 m probe density DTI 0.023235 (20,857/31,819 cells); 1 km probe density 0.032984 (28,219/31,819); TMI-only 0.040004 (19,090/31,819). These are **not equal-mass** comparisons because they fell short of budget. Five mass-matched uniform controls scored 0.077347–0.082992, each at 31,819 cells. None rescues H53-A.
- The TIFF format was rechecked after correcting outside-footprint values to NaN. In-footprint values are finite and within `[0,1]`; there are no finite pixels outside the valid footprint. The raster validator and reports record the current hash above.

See [`results.html`](results.html) for the generated tables and [`docs/research/h53-preregistration-20261007.md`](docs/research/h53-preregistration-20261007.md) for the frozen protocol.

## Ranked geological hypotheses (before implementation)

Four distinct candidates were ranked before H53-A was implemented. Only H53-A was advanced; H53-B through H53-D remain unimplemented proposals, and none was promoted after the leading candidate failed.

| Rank | Hypothesis | Distinguishing signature | Status / principal blocker |
|---:|---|---|---|
| 1 | **H53-A — probe-temperature point geometry + TMI alignment** | Anisotropic clusters of positive 2 m probe anomalies, retained only when their PCA axis aligns with an independent GeoDAWN magnetic ridge | Implemented once; 0 accepted clusters; **NO-GO**; local source bytes not matched to official downloads |
| 2 | **H53-B — depth-progressive MT conductance boundaries** | A lateral conductance edge that persists or changes coherently through five depth ranges | Not implemented; per-asset licence wording needs verification |
| 3 | **H53-C — deep-circulation chemistry fingerprints** | Quality-screened silica/Na-K chemistry patterns, with a structural orientation prior | Not implemented; official raw geochemistry and columns not audited |
| 4 | **H53-D — fossil hydrothermal-deposit corridors** | Sinter/tufa/travertine spatial corridors, tested with terrain and geophysical context | Not implemented; mirrored records not byte-matched to GDR source |

The full ranking spells out layers, signatures, why each might reveal a fault absent from USGS/INGENIOUS, how it differs from this repo and sibling work, expected DTI direction, cost, permissions, and official links. It also states why seismicity-lineation adaptation is **not** treated as novel or validated: [`docs/research/h53-hypotheses-20261007.md`](docs/research/h53-hypotheses-20261007.md).

## H33-2-B2 score review and the `0.3774` claim

The user-provided GEMSDOE32 `h33-h33-2-b2` score of **0.2778 is unauthenticated** in the available record. At the pinned sibling snapshot (`b983924b57781edd29b8e249c4923bf33d9902f6`), the audit labels the run **UNSCORED** and reports a projected DTI of **0.274673**. No matching organizer score receipt or score-ledger row was found. Do not describe the projected number as an official score.

The pinned audit describes pruning **2,545 catalogue-near dots** from a 40,199-dot parent, leaving 37,654 dots. That could plausibly improve DTI if the removed dots had little or no credit against the scored truth: under the binary-dot form `DTI = T / (0.2·N + 0.8·G)`, removing a dot improves the score only when its marginal truth credit is below approximately `0.2 × current DTI` (about 0.0556 at 0.2778). This is a metric-based mechanism, not a verified explanation: the score itself, the score-to-file mapping, which removed pixels were penalized, and any simultaneous changes in the experiment remain unconfirmed. Pruning could also remove useful credit and lower DTI.

The user-provided **0.3774 current-high-score claim is also unverified** here; we did not independently check the live board. A better strategy could in principle exceed it, but this review has not established one. H53-A failed; the older local proxy, historical sibling scores, and any score-inversion model cannot validate a route above 0.3774. No current strategy is endorsed as exceeding that claim.

Full review, evidence hashes, alternative explanations, official rules, and unresolved source/receipt issues: [`docs/research/h33-score-review-20261007.md`](docs/research/h33-score-review-20261007.md). No live leaderboard was queried in this review.

## Submission instructions

**Current status: do not submit the linked H53-A TIFF.** It is all zero, has failed the spatial promotion gate, and has unresolved source-binary provenance. No weekly feedback slot has been used by this project.

For a future build only after it is explicitly marked **SLOT-ELIGIBLE**:

1. Download only the TIFF labeled `SLOT-ELIGIBLE`; the current H53-A download is not eligible.
2. Verify its displayed SHA-256 and inspect the raster-byte validation report.
3. Re-read the [official format page](https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/): same EPSG:32611 100 m grid and bounds, float32, one band, finite `[0,1]` predictions inside the valid footprint, null/NaN outside.
4. Confirm each external input is licensed for challenge use and sharable with the sponsor; retain attribution and include the rules-required AI-use disclosure.
5. Sign in to DrivenData manually. Spend a weekly feedback slot only after the spatial holdout beats the frozen incumbent and controls and the owner approves.
6. Upload the exact validated file without resaving or reprojecting. Save the portal receipt and associate any score with the exact file hash before reporting it.

The live [`submission.html`](submission.html) page repeats this checklist and the current NO SLOT warning. The `docs/` copies redirect users to current pages; no automatic portal access or upload is used.

## Provenance, legal, scientific, and operational blockers

- **External-data rule:** the [official DrivenData problem/data page](https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/) requires suitable rights both to use external data in the challenge and share it with the sponsor for evaluation. This is not a claim of legal advice; unclear rights remain a blocker.
- **GDR INGENIOUS source:** [submission 1391, DOI 10.15121/1881483](https://gdr.openei.org/submissions/1391) lists CC BY 4.0. The local probe ZIP is a pinned sibling-repository mirror, not byte-matched to the official binary; direct official download previously failed. Attribution alone does not resolve binary provenance.
- **GeoDAWN:** [USGS release, DOI 10.5066/P93LGLVQ](https://www.usgs.gov/data/geodawn-airborne-magnetic-and-radiometric-surveys-northwestern-great-basin-nevada-and) identifies CC0 1.0. The local quantized TMI extension was not independently rebuilt from official source files.
- **Conductance fallback:** the [USGS Great Basin conductance release, DOI 10.5066/P9TWT2LU](https://www.sciencebase.gov/catalog/item/62979746d34ec53d276c113b) is a possible H53-B source, but the per-asset licence was not verified; it remains blocked.
- **Scientific limitations:** shallow temperature/probe anomalies may reflect groundwater, season, survey footprint, lithology, or known prospect bias rather than fault-controlled flow. The mapped-fault proxy is imperfect and does not represent the hidden expert test labels.
- **Seismicity confounds:** the older event-pattern branch is not a fallback recommendation. Any future experiment would need point-pattern geometry (not density alone), formal declustering, injection/mining confound screening, location uncertainty, known-fault buffer exclusion, and matched 1 km/2 km smoothed-density controls. Mixed-network ComCat rights are unresolved.
- **Leaderboard operations:** [DrivenData Terms of Use](https://www.drivendata.org/termsofuse/) restrict leaderboard monitoring and copying. One unintended automated request to the public page occurred in earlier research; no rows/scores were saved or used, and no further automated access is made. No live board was queried for this review; no current leaderboard value is asserted. Prior sibling-repository notes are not a fresh independent official check.
- **AI rules:** the [DOE/NLR official rules (September 2026)](https://docs.nlr.gov/docs/fy26osti/96647.pdf) require generative-AI disclosure in the competition narrative and reproducible finalist assets.

## Historical H50/H51 record — retained, not recommended

Previous H51 artifacts and analyses are kept for auditability and education. They are **not current submissions** and should not be uploaded based on their historical format or uniqueness checks.

- H51 corridor-consensus mix (30,000 dots) scored 0.056553 on the shared local off-catalogue frame, below the matched uniform mean 0.059235; its consensus instrument estimate 0.1684 is not an organizer score.
- H51 scarp + radiometric file (35,000 dots) scored 0.115822 on its local off-catalogue instrument versus 0.116079 for the matched random control. Its archived positive-fold comparison is not organizer-scored and is not a current slot gate.
- H50 prior seismicity map is the frozen H53 comparator at 0.136074 on the same local proxy. It is only a baseline, not a novel strategy or recommendation.
- Original H51 reports, hashes, methods, and TIFFs remain under [`evidence/`](evidence/), [`docs/downloads/`](docs/downloads/), and [`docs/research/h51-analysis.md`](docs/research/h51-analysis.md). The current site exposes them only inside the clearly labeled historical H51 results section, not as the top download.
- The separate H50-S1 dispatch-only workflow was previously blocked by HTTP 403 `Resource not accessible by integration`; no job ran and no data was fetched by that attempt. This does not describe the H53-A mirror-based research run.

## Site, build, and validation

The current three-pass acceptance review is [`docs/pass3-review-20261007.md`](docs/pass3-review-20261007.md). The earlier `docs/pass3-review-20261006.md` is explicitly historical and its H51 promotion statements are withdrawn.

GitHub Pages is configured to serve the repository root. The root pages are built by [`scripts/build_h50_site.py`](scripts/build_h50_site.py); the H53 download band reads the committed build/validation records and the TIFF hash. Rebuild with:

```bash
.venv/bin/python scripts/build_h50_site.py
```

The H53 pipeline is reproducible from hash-pinned inputs mirrored into ignored scratch storage; it does not write those large inputs into Git:

```bash
scripts/fetch_h53_inputs.sh
.venv/bin/python scripts/h53_build.py
.venv/bin/python scripts/h53_validate.py
```

The last full validation produced the NO SLOT metrics above. It is intentionally not presented as a winning candidate.

Run the repository checks before any merge:

```bash
.venv/bin/ruff check .
.venv/bin/pytest -q
.venv/bin/python scripts/verify_claims.py
```

## Immediate next steps

1. Keep H53-A and every older H51 artifact marked **NO SLOT / historical**.
2. Resolve official-binary matching and shareability for the GDR and GeoDAWN inputs before any competition use; check per-asset rights before considering H53-B.
3. Do not tune H53-A after the failed holdout. Any new detector requires a fresh, frozen hypothesis/protocol and a blocked test against the best frozen comparator and matched controls.
4. Do not spend a weekly slot unless the candidate beats the incumbent on its holdout best and passes provenance, license, and byte-level format gates.
5. Preserve any official organizer receipt before making score-to-file claims. No score or leaderboard claim in this README is a substitute for that receipt.
