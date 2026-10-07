# Historical three-pass acceptance review — H53-A no-go close-out (2026-10-07 UTC)

> **SUPERSEDED; historical record only.** This review predates the later H56 emitter-spacing and metric-algebra audits, the H57/H58 rights and NO-SLOT decisions, and the explicit H59 withdrawal. Its statements that H56 is the current candidate or that any H56 portal guide remains active are obsolete. Current project status, authorized-name policy, and no-go decision are maintained in [`README.md`](../README.md) and [`submission.html`](../submission.html). Nothing in this historical review authorizes a download for submission, portal name/note, upload, or weekly slot.

This is the original acceptance record for the H53-A work from this Arena branch. The remote `main` advanced during that session and then contained later H55/H56 work; H53-A is a separate, archived no-go experiment (not the repository's other H53 TMI-conjunction artifact). The older [`pass3-review-20261006.md`](pass3-review-20261006.md) describes an earlier H51-oriented iteration; its H51 promotion statements are superseded and withdrawn.

## Pass 1 — implement and verify

- Ranked four distinct geological hypotheses before implementation in [`research/h53-hypotheses-20261007.md`](research/h53-hypotheses-20261007.md), with feature layers, physical signatures, novelty against USGS/INGENIOUS and sibling work, expected DTI direction, cost, permissions, and official references. Froze H53-A's detector and promotion conditions in [`research/h53-preregistration-20261007.md`](research/h53-preregistration-20261007.md).
- Built a new one-band Float32 GeoTIFF on the official 3292 × 3730 EPSG:32611 grid. Its SHA-256 is `5f2fd91ad46a3602c03802e0f7773fd466b08e47cbfcf40ff796ffc2b956a382`; in-footprint values are finite and in `[0,1]`, with NaN outside the footprint. The frozen detector accepted 0/145 clusters, so every in-footprint value is 0.0. This is a reproducibility artifact, not a useful submission; do not upload it.
- Ran the preregistered blocked validation before any slot decision. H53-A DTI was 0.000000 versus 0.136074 for the frozen comparator; the paired spatial-subtile bootstrap interval was [−0.169861, −0.079791]. It failed incumbent, mass, and control gates: **NO-GO / NO SLOT**. No weekly slot was used and no threshold was loosened post hoc.
- Reviewed the user-provided H33-2-B2 0.2778 claim against a pinned sibling audit: the run is labeled UNSCORED and the 0.274673 value is a projection, not an organizer receipt. Pruning 2,545 catalogue-near points could plausibly reduce low-credit mass, but it is not a verified causal explanation. The user-provided 0.3774 claim was not independently checked. Separate H56 work has a 0.386 transfer-model estimate after positive local holdout results, but that is not an organizer score and its ComCat-rights gate remains unresolved.
- The initial branch site placed the H53-A research TIFF at the top; after integrating the newer main history, kept H56 as the current site's primary one-click candidate and retained H53-A only as an audit-only no-go. Its unique research identity, hash, do-not-upload status, and separate H56 submission guide are explicit; the H53-A name/note are not approved portal metadata.

## Pass 2 — review and fix

- Re-read H50/H51 analysis, candidates, score records, generator templates, feeds, and registries for stale current-slot language. Withdrew the old H51 slot recommendation; labeled H50/H51 pages, files, metrics, and hypotheses historical; retained them only for audit. Removed H51's old portal-step and all-finite-twin links from the generated results page.
- Corrected H51 score phrasing: archived instrument outputs are modeled/local DTI, not expected leaderboard scores; owner/sibling-corpus values are not authenticated organizer scores. Fixed registry refresh so lower-case H51 names are replaced idempotently, source metadata is archival, and generated feeds do not carry H51 portal instructions.
- Final source review found the H53 baseline re-audit could overwrite its hash-pinned incumbent evidence by default. Made `--output` mandatory for re-audits, documented the frozen-report hash workflow, and added a regression test that verifies omission cannot change the committed baseline. Re-ran the incumbent audit to `/tmp`; all baseline fields match the frozen report exactly except `built_utc`, and the frozen file remains unchanged.
- The first console-script `pytest` invocation exposed a repository-path issue (`scripts` was not importable). Added the repository root alongside `src` in both pytest configuration files; the direct pytest command now runs the full suite.
- Rebuilt the feed and four root pages. Added guardrails for H53 status, TIFF hash, H33 caveats, hypothesis ranking, source rights, and historical H51 status. Removed the dead H50 metrics helper and unused TIFF CLI argument from the root-site builder; the optional H50-S1 report is explicitly historical. No new live-leaderboard request was made during this H53 close-out; no competition upload occurred.

## Pass 3 — re-check the original acceptance criteria

| Requirement | Re-check |
|---|---|
| Unique GeoTIFF; no copied prediction pixels; correct grid and `[0,1]` bounds | New H53 build artifact and hash are recorded. It contains zero positive cells because the preregistered detector accepted no clusters; it is prominently labeled **NO-GO**, not offered as a candidate for scoring. |
| 3–5 distinct hypotheses ranked before implementation | Four documented and preregistered; only H53-A implemented, and no alternate was promoted after the failure. |
| Blocked holdout against frozen incumbent and controls before a slot | Completed; H53-A lost and failed mass/control gates. **No slot authorized or used.** |
| H33 score explanation and chance of exceeding 0.3774 | H33 score-to-TIFF mapping and 0.3774 claim remain unauthenticated. H56's 0.386 is a conditional transfer-model estimate, not an organizer score; unresolved ComCat rights block upload. |
| External-data rules, permissions, and provenance | Official DrivenData format/rights page and September 2026 DOE/NLR rules are linked. GDR and GeoDAWN local bytes are not independently matched to official assets; conductance per-asset rights and mixed-network ComCat rights remain unresolved. These remain blockers, not assumed permissions. |
| Site download, short note, and submission guide | H56 remains the current root-page one-click candidate and numbered guide. H53-A is retained as a separate audit-only, do-not-upload no-go record; its research name/note are not portal metadata. |
| Three passes, tests, and review fixes | This document records all three passes. Final integrated checks: `pytest` **174 passed, 2 skipped** (both optional flow-routing/`pysheds` tests); scoped Ruff **All checks passed**; `scripts/verify_claims.py` all guardrails passed; Python compilation, `git diff --check`, and H53 frozen-baseline re-audit passed. The five H56/H55/H53-A root-site outputs were byte-idempotent. |
| PR and merge | [PR #20](https://github.com/buffedlizard55-lab/GEMSDOE50/pull/20) was merged to `main` on 2026-10-07 after `checks-and-site`, `pytest`, and `tests-and-artifacts` all passed. Merge commit: `0f2f7e8d0603fb7eef28df0abb0de2d715ff3662`. The repository merge does not authorize a competition upload or slot. |

## Remaining blockers and next steps

1. Keep H53-A and all H50/H51 artifacts **NO SLOT / historical**. Do not upload the all-zero TIFF.
2. Do not submit H53-A: it is all-zero and its GDR/GeoDAWN mirrors are not byte-matched to official assets. H56 remains blocked from a slot until mixed-network ComCat contributor rights and sponsor-sharing eligibility are cleared; verify rights for every source used by any future candidate.
3. Any new experiment requires a distinct preregistered hypothesis, controls, frozen spatial holdout, incumbent comparison, and a fresh review before slot authorization. Do not tune H53-A thresholds after its observed failure.
4. PR #20 merged the code and research record only; it does not authorize spending a competition slot. No live leaderboard polling or competition upload was performed.
