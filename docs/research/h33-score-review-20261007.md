# H33-2-B2 score review and H53-A no-go

**Review date:** 2026-10-07 UTC. **Purpose:** evaluate the user-provided `0.2778` H33-2-B2 score claim, assess whether the user-provided `0.3774` high-score claim is plausibly beatable, and document the preregistered H53-A test. No competition submission slot was used.

## Executive conclusion

The `0.2778` score is **not independently tied to the downloaded H33-2-B2 TIFF by an organizer receipt in the reviewed record**. In the exact pinned GEMSDOE32 snapshot (`b983924b57781edd29b8e249c4923bf33d9902f6`), the H33-2-B2 audit names the 37,654-dot file and its SHA-256, but its submission note explicitly says **UNSCORED** and gives a *modelled* `predicted_leaderboard_dti` of `0.274673`, not an organizer score. The same snapshot's score ledger has no H33-2-B2 / `0.2778` row. The downloaded TIFF's bytes do match that audit SHA exactly; that proves file identity, not a score-to-file link.

The H33-2-B2 recipe was not a new H33 geological detector. The pinned audit describes it as the existing owner-reported 0.2708 base with all dots within 2 pixels (200 m) of the public catalogue deleted: 40,199 → 37,654 dots, removing 2,545 predictions. Fewer weak/near-catalogue dots while retaining most estimated weighted credit is a plausible way for a distance-weighted Tversky score to rise without demonstrating new fault discovery. The sibling's own model estimated a modest gain; it did not verify the quoted score.

The leading new candidate, H53-A, failed before promotion: the frozen probe/TMI rule accepted 0 of 145 thermal clusters, emitted 0 cells, scored DTI 0.0000 on the local blocked proxy, and lost to the frozen incumbent and controls. **Do not submit the linked all-zero GeoTIFF or spend a slot.** There is no validated result here supporting a strategy that exceeds 0.3774. It is possible in principle, but that claim is currently unproven and should not be presented as likely.

## What the H33-2-B2 artifact actually is

Pinned audit source: [GEMSDOE32 audit at commit `b983924`](https://github.com/buffedlizard55-lab/GEMSDOE32/blob/b983924b57781edd29b8e249c4923bf33d9902f6/docs/downloads/gemsdoe32-h33-h33-2-b2-20261004T220000Z-e5eb6e7e-audit.json). The raw audit downloaded in this review has SHA-256 `e4db14f2e369b1db37870d8d1a31035f730512309a88810d99ff705782e28212`.

| item | reviewed value | evidence class |
|---|---:|---|
| File name in the pinned audit | `gemsdoe32-h33-h33-2-b2-20261004T220000Z-e5eb6e7e-nan.tif` | pinned sibling record |
| TIFF SHA-256 | `baeae3219bba6a19bc8cfe79224e28555c50184b7c1ca65c2a822f54807c77dd` | independently recomputed from downloaded bytes; matches audit |
| Grid | 3,292 × 3,730, EPSG:32611, 100 m | audit and local raster inspection |
| Positive pixels | 37,654 binary dots | audit and local raster inspection |
| Audit description | “0.2708 base with every dot at d(catalogue) <= 2 px deleted” | owner-authored artifact audit |
| Dots deleted | 2,545 | sibling's removal-rule evidence |
| Dots within 100/200 m of catalogue after prune | 0 / 0 | sibling's audit, for that radius only |
| Dots within 300 m in this review | 2,171 | locally measured; 2–3 pixel annulus is not covered by “within 200 m” |
| Submission note status | `UNSCORED` | pinned audit text |
| Modelled `predicted_leaderboard_dti` | 0.274673 | explicitly a model, not a score |
| Actual organizer receipt / submission ID linking 0.2778 to this hash | **not found** | unresolved |

The TIFF hash in the audit is strong evidence that the compared artifact is the one GEMSDOE32 recorded. It is **not** evidence that DrivenData scored this exact TIFF at 0.2778. The pinned `docs/score-ledger.csv` (SHA-256 `8eba2f703360d3826ff16f64086c1e7411a9abe74f6094eabd909f9c593c28f2`) contains no H33-2-B2 / 0.2778 row; the H33 audit calls the artifact `UNSCORED`. A later score may exist outside that pinned snapshot, but the score-to-file provenance remains unresolved.

## Why a score near 0.2778 could be high — without claiming that it was verified

The official metric is distance-weighted Tversky: `DTI = TPw / (TPw + 0.2·FPw + 0.8·FNw)` with a triangular 300 m kernel. Thus extra false-positive mass is penalized, but less heavily than missed truth. If removing 2,545 predictions removes mostly unsupported/low-credit dots while leaving the useful weighted TP largely intact, the ratio can rise. The sibling audit's own removal calculation reports `d_credit = 65.09`, `d_tp_g = 55.29`, a safety factor of 2.08, and a projected DTI of 0.2747. Those values are **model-derived from that project's local instrument**, not organizer measurements.

The route to the higher score is therefore plausibly **mass pruning / dot economy**, not evidence that the “H33” name introduced a superior new geological signal. That reading is also consistent with the build record: H33-2-B2 is a catalogue-flank deletion applied to the previous 0.2708 base. It does not use the 2 m probe, chemistry, paleo-deposit, or multi-physics H33 candidate fields. Its deletion distance is measured from the public catalogue, which is a heuristic; it does not establish that a removed pixel was false on the private test or that a retained pixel is a newly confirmed fault.

This review does **not** assert the following as facts: that the organizer score was 0.2778; that the H33-B2 hash received that score; that the projected 0.2747 was observed live; that every removed dot was a false positive; or that the map identified faults. All are unverified or model-based. The archived `docs/research/score-model.md` and `docs/research/h51-analysis.md` use different hidden-truth inversion assumptions, so their implied truth/credit counts are estimates and are not a stable target for the new model.

## Blocked comparison in this checkout

The H53 preregistration ranked four physical hypotheses before implementation. H53-A was the only one advanced; its exact rules and source receipts are in [`h53-preregistration-20261007.md`](h53-preregistration-20261007.md). The H33 TIFF was used solely as an incumbent-set comparison; no old raster pixels were read into the H53 builder.

The candidate-independent baseline audit froze the best pooled local comparator as **H50 prior seismicity**, not H33-2-B2. This is a narrowly scoped screening result on one local SGMC-off proxy, **not** a validation of seismicity as a novel strategy. H51-B already tested seismic event geometry; its controls and injection/mining/location-uncertainty confounds are unresolved, so the H50 file is shown only as a comparator.

| fixed artifact | total dots | local blocked DTI on four frozen cores |
|---|---:|---:|
| H50 prior seismicity — comparator only | 44,709 | **0.136074** |
| H51-A scarp/radiometric | 35,000 | 0.108799 |
| GEMSDOE32 H33-2-B2 — downloaded for comparison only | 37,654 | 0.095759 |
| H51 corridor consensus | 30,000 | 0.058137 |

H53-A's frozen rules detected 2,782 in-footprint probe records, collapsed 80 duplicate area/cell rows, selected 714 positive within-Area upper-quartile marks, and tested 145 connected clusters. The 145 were rejected as: 113 below five points, 24 with <50% qualifying TMI alignment, and 8 below the PCA-axis ratio. **Accepted clusters: 0.** This is a fail under the precommitted detector, not permission to lower thresholds after looking at holdout results.

| H53-A local blocked result | result |
|---|---:|
| Candidate cells / requested full-grid incumbent budget | 0 / 44,709 |
| Candidate pooled DTI | 0.000000 |
| Frozen incumbent | H50 prior seismicity, comparator only |
| Incumbent pooled DTI | 0.136074 |
| Incumbent fold DTI (NW / NE / SW / SE) | 0.102588 / 0.096115 / 0.074476 / 0.264573 |
| Candidate fold DTI | 0 / 0 / 0 / 0 |
| 95% paired spatial-subtile bootstrap interval, candidate − incumbent | [−0.169861, −0.079791] |
| Highest of five matched uniform control DTI | 0.082992 |
| 500 m warm-probe density control DTI / mass achieved of 31,819 requested | 0.023235 / 20,857 |
| 1 km warm-probe density control DTI / mass achieved | 0.032984 / 28,219 |
| TMI-only ridge control DTI / mass achieved | 0.040004 / 19,090 |
| Decision | **NO SLOT** |

The smoothed-density and TMI-only controls could not emit the full incumbent-matched mass under the frozen 3-pixel suppression rule; their scores are diagnostic, not equal-mass head-to-head results. The five uniform controls did reach the 31,819 in-core target; all scored below the 0.136074 local incumbent. The candidate itself could not produce any dots, so there is no positive evidence to promote.

This DTI uses the 2026-10-06 frozen NW/NE/SW/SE cores and **SGMC mapped faults >300 m from the provided catalogue** as a proxy. It is not the expert-labelled private test set, not the public leaderboard, and not directly comparable numerically to 0.2778 or 0.3774.

## Can a strategy exceed the user-provided 0.3774?

- **In principle:** yes. The score is not capped at 0.3774. A better predictor could find more previously unmapped faults while avoiding unsupported predictions.
- **What this run establishes:** nothing in H53-A supports that outcome. It failed the geometry gate before mass emission and scored zero on the proxy. The incumbent/control values are local screens, not a reason to submit H50 or any other map.
- **What is needed to claim a route:** an independently verified current score-to-file receipt for the claimed 0.3774; a new geological signal; permission-cleared source data; a preregistered, spatially separated validation against the frozen best and matched controls; and an improvement that survives the registered uncertainty test. The depth-profile conductance and chemistry ideas remain future hypotheses, not results.
- **No numeric hidden-truth inversion is treated as truth.** A single reported DTI and dot count do not identify the hidden truth size, weighted TP, and FP without additional assumptions. Old repo inversions disagree; use them only as sensitivity analyses, never to promise 0.3774+.

The only local public-board snapshot recorded in this repository is dated 2026-10-03 and is not current. The user's 0.3774 claim is therefore preserved as **user-provided/unverified**; this review did not monitor or scrape the live leaderboard.

## Competition rules, data permissions, and unresolved issues

- [DrivenData problem page — external datasets](https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/): additional sources are allowed only if the participant possesses a licence permitting use in the challenge **and sharing with the sponsor for evaluation**. The same page specifies a one-band float32 GeoTIFF on EPSG:32611 at 100 m, same bounds, finite predictions from 0 to 1, and null/NaN outside bounds. The H53 no-go file conforms to the raster structure/value rule; its all-zero prediction is not useful and is not eligible for a slot.
- [GDR INGENIOUS submission 1391, DOI 10.15121/1881483](https://gdr.openei.org/submissions/1391): page marks the compilation CC BY 4.0 and permits redistribution with attribution. The local 2 m ZIP's SHA-256 matches a pinned sibling mirror, but direct official-binary comparison failed (the official asset endpoint returned HTTP 500). Source-byte provenance therefore remains unresolved for competition use.
- [USGS GeoDAWN, DOI 10.5066/P93LGLVQ](https://www.usgs.gov/data/geodawn-airborne-magnetic-and-radiometric-surveys-northwestern-great-basin-nevada-and): official metadata marks the source CC0 1.0. The 100 m `TMI_up150` raster used here is a sibling-mirrored, quantized derived feature, not raw TMI in nT; no independent rebuild from official GeoDAWN source files was done.
- [USGS Great Basin conductance maps, DOI 10.5066/P9TWT2LU](https://doi.org/10.5066/P9TWT2LU): provides five depth ranges from 2 to 200 km. The reviewed page did not expose a sufficiently precise per-asset licence statement, so H53-B is not implemented until terms are verified.
- [September 2026 DOE/NLR GEMS Prize Official Rules](https://docs.nlr.gov/docs/fy26osti/96647.pdf): sections 3.2–3.5 require one 100 m single-layer GeoTIFF, note up to three scoring submissions per week, require a single final choice for both prize rounds, and require generative-AI use to be disclosed in the narrative. The competitor remains responsible for truthfulness, accuracy, authorship, and rights.
- [DrivenData Terms of Use](https://www.drivendata.org/termsofuse/): no automated leaderboard polling or copying was performed; the terms restrict robots/automatic devices for monitoring/copying. The claimed live score was not re-queried.

**Operational/legal hard stop:** the GDR and derived GeoDAWN source bytes are from hash-pinned sibling mirrors, not matched to official binary downloads. In addition, no official receipt links the owner-provided 0.2778 to the TIFF. No score slot should be spent until both issues are resolved.

## Reproducibility and outputs

- Hypothesis ranking: [`h53-hypotheses-20261007.md`](h53-hypotheses-20261007.md)
- Frozen protocol: [`h53-preregistration-20261007.md`](h53-preregistration-20261007.md)
- Baseline-only record: `evidence/h53-baseline-20261007.json`
- Build record: `evidence/h53-build-20261007.json`
- Blocked validation: `evidence/h53-validation-20261007.json`
- New research-only artifact (not for the portal): `docs/downloads/gemsdoe50-h53-probe-tmi-pointlineation-20261007-44afc05b.tif`
- Source fetcher (retrieves pinned sibling mirrors only): `scripts/fetch_h53_inputs.sh`

For any future real submission, use a truthful AI disclosure describing assistance with source synthesis, code authoring, documentation, and review, and manually verify every source citation, licence, and result before signing the DOE/NLR certification. This H53 artifact is **not a competition submission recommendation**.
