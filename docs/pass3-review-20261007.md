# Three-pass acceptance review — H53-A no-go close-out (2026-10-07 UTC)

This is the current acceptance record for the project charter and user request. The older [`pass3-review-20261006.md`](pass3-review-20261006.md) describes an earlier H51-oriented iteration; its H51 promotion statements are superseded and withdrawn.

## Pass 1 — implement and verify

- Ranked four distinct geological hypotheses before implementation in [`research/h53-hypotheses-20261007.md`](research/h53-hypotheses-20261007.md), with feature layers, physical signatures, novelty against USGS/INGENIOUS and sibling work, expected DTI direction, cost, permissions, and official references. Froze H53-A's detector and promotion conditions in [`research/h53-preregistration-20261007.md`](research/h53-preregistration-20261007.md).
- Built a new one-band Float32 GeoTIFF on the official 3292 × 3730 EPSG:32611 grid. Its SHA-256 is `5f2fd91ad46a3602c03802e0f7773fd466b08e47cbfcf40ff796ffc2b956a382`; in-footprint values are finite and in `[0,1]`, with NaN outside the footprint. The frozen detector accepted 0/145 clusters, so every in-footprint value is 0.0. This is a reproducibility artifact, not a useful submission; do not upload it.
- Ran the preregistered blocked validation before any slot decision. H53-A DTI was 0.000000 versus 0.136074 for the frozen comparator; the paired spatial-subtile bootstrap interval was [−0.169861, −0.079791]. It failed incumbent, mass, and control gates: **NO-GO / NO SLOT**. No weekly slot was used and no threshold was loosened post hoc.
- Reviewed the user-provided H33-2-B2 0.2778 claim against a pinned sibling audit: the run is labeled UNSCORED and the 0.274673 value is a projection, not an organizer receipt. Pruning 2,545 catalogue-near points could plausibly reduce low-credit mass, but it is not a verified causal explanation. The 0.3774 high-score claim was not independently checked; this work establishes no strategy that exceeds it.
- Published the research TIFF prominently at the top of the root site, with a unique research identity, identity-only note, hash, no-go explanation, and a separate future-only submission checklist. The name and note are explicitly not approved portal metadata.

## Pass 2 — review and fix

- Re-read H50/H51 analysis, candidates, score records, generator templates, feeds, and registries for stale current-slot language. Withdrew the old H51 slot recommendation; labeled H50/H51 pages, files, metrics, and hypotheses historical; retained them only for audit. Removed H51's old portal-step and all-finite-twin links from the generated results page.
- Corrected H51 score phrasing: archived instrument outputs are modeled/local DTI, not expected leaderboard scores; owner/sibling-corpus values are not authenticated organizer scores. Fixed registry refresh so lower-case H51 names are replaced idempotently, source metadata is archival, and generated feeds do not carry H51 portal instructions.
- The first console-script `pytest` invocation exposed a repository-path issue (`scripts` was not importable). Added the repository root alongside `src` in both pytest configuration files; the direct pytest command now runs the full suite.
- Rebuilt the feed and four root pages. Added guardrails for H53 status, TIFF hash, H33 caveats, hypothesis ranking, source rights, and historical H51 status. Removed the dead H50 metrics helper and unused TIFF CLI argument from the root-site builder; the optional H50-S1 report is explicitly historical. No new live-leaderboard request was made during this H53 close-out; no competition upload occurred.

## Pass 3 — re-check the original acceptance criteria

| Requirement | Re-check |
|---|---|
| Unique GeoTIFF; no copied prediction pixels; correct grid and `[0,1]` bounds | New H53 build artifact and hash are recorded. It contains zero positive cells because the preregistered detector accepted no clusters; it is prominently labeled **NO-GO**, not offered as a candidate for scoring. |
| 3–5 distinct hypotheses ranked before implementation | Four documented and preregistered; only H53-A implemented, and no alternate was promoted after the failure. |
| Blocked holdout against frozen incumbent and controls before a slot | Completed; H53-A lost and failed mass/control gates. **No slot authorized or used.** |
| H33 score explanation and chance of exceeding 0.3774 | Caveated in the score review and README. Neither score claim was independently authenticated; no winning strategy is asserted. |
| External-data rules, permissions, and provenance | Official DrivenData format/rights page and September 2026 DOE/NLR rules are linked. GDR and GeoDAWN local bytes are not independently matched to official assets; conductance per-asset rights and mixed-network ComCat rights remain unresolved. These remain blockers, not assumed permissions. |
| Site download, short note, and submission guide | H53 artifact appears first on the root page, but carries an unmistakable do-not-upload warning. Its name/note identify the research build only; future submission steps require a separately marked SLOT-ELIGIBLE artifact. |
| Three passes, tests, and review fixes | This document records all three passes. Final local checks: `pytest` **94 passed**; `scripts/verify_claims.py` all guardrails passed; Ruff **All checks passed**; Python compilation passed; registry and site generators completed and were byte-idempotent across 12 generated pages/registries. |
| PR and merge | GitHub state must be checked after final validation. Do not report a PR or merge until confirmed; if permissions or CI block it, report the exact blocker. |

## Remaining blockers and next steps

1. Keep H53-A and all H50/H51 artifacts **NO SLOT / historical**. Do not upload the all-zero TIFF.
2. Do not use H53 input mirrors for competition submission until official binary provenance and sponsor-sharing rights are independently resolved. Verify the license on any proposed H53-B assets.
3. Any new experiment requires a distinct preregistered hypothesis, controls, frozen spatial holdout, incumbent comparison, and a fresh review before slot authorization. Do not tune H53-A thresholds after its observed failure.
4. Check remote branch and CI state, open a PR from the fixed Arena branch, and merge only if access and required checks permit. No live leaderboard polling is authorized.
