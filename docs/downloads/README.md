# Which file should I download — and is it OK to submit?

**Short answer: download and submit exactly one file — the current candidate in the first data row
below.** The ranking quoted here is the measured one on this repository's frozen spatially-blocked
gate, all artifacts scored on identical frames (`evidence/h60_gate_decision.json`). Everything else here is an alternative, a superseded candidate, or an audit/negative-control
file that exists so the reasoning can be checked. Nothing in this directory has been uploaded to the
competition portal, and no organizer score is represented anywhere on this site.

All files are single-band float32 GeoTIFFs on the competition grid (EPSG:32611, 3,730 × 3,292 at
100 m, origin 243350 / 4508550) with values in `[0, 1]`. The `-allfinite.tif` files write `0.0`
outside the study footprint (every cell finite — the direct antidote to the portal error
`Predicted values must be in range [0, 1]`); the `.tif` twins carry `NaN` outside the footprint,
matching the sample-submission convention. Submit the file **as downloaded** — do not re-save,
re-project, re-scale or re-compress it.

| file | cells | status | evidence |
|---|---|---|---|
| `gemsdoe50-h59-sharpened-scarp-scatter-90k-20261007T171954Z-allfinite.tif` | 90,000 | **RECOMMENDED — the repository's current candidate** (frozen gate 0.2125 vs 0.1286 matched uniform, 4/4 folds; pooled off-catalogue F1 0.1255, lift 2.32). Built by the sibling session merged on main; measured here on the same frames as everything else. | `evidence/h60_competitor_holdout.json`, `evidence/h60_competitor_f1.json`, `h59.html` |
| `gemsdoe50-h60-union-d0-75308-20261007T2250Z-allfinite.tif` | 75,308 | Second on the frozen gate (0.2033; pooled F1 0.1018) and **the strictest on the charter rule: 0 of 1,405,451 prior positive cells reused**. Beats the older H57 on both instruments. | `evidence/h60_gate_decision.json`, `evidence/h60_holdout_offcat.json` |
| `gemsdoe50-h57-scarpstep-80000-20261007T1830Z-allfinite.tif` | 80,000 | **History — do not submit as a fresh entry.** 27,248 of its 80,000 dots (34.1 %) sit on cells a prior submission had already marked positive, which the charter forbids. Retained as a comparator. | `evidence/build_h57-scarpstep.json`, `evidence/h60_gate_decision.json` (prior-pixel audit) |
| `gemsdoe50-h60-union-d2-75308-20261007T2250Z-allfinite.tif` | 75,308 | **Negative control — do not submit.** Maximal-novelty arm: loses to a matched uniform control (0.0618 vs 0.0917) in 4/4 folds. It exists to price novelty. | `evidence/h60_holdout_offcat-d2.json` |
| `gemsdoe50-h60-officialstack-50000-20261007T2100Z-allfinite.tif` | 50,000 | Superseded arm (official-stack belief alone; frozen gate 0.1224, far below the incumbent). Record only. | `evidence/h60_holdout_offcat-officialstack.json` |
| `gemsdoe50-h58-seislineage-98598-…-allfinite.tif` | 98,598 | **NO SLOT.** Unique ComCat-lineation corridor artifact; loses the frozen gates and its contributor-rights question is unresolved. **Do not upload** until rights clearance. | `evidence/h58_build.json`, `evidence/h58_holdout.json` |
| `gemsdoe50-h61-updipseis-326-20261007T205554Z-cc1f44da-allfinite.tif` | 326 | **NO SLOT — do not submit.** The owner-mandated seismic-lineation map (ComCat, Zaliapin–Ben-Zion declustering, unverified 2-D triangle screen, up-dip corridors snapped to a ridge): frozen-frame DTI 0.0002, below random dots and below smoothed density on withheld faults; unique (Jaccard ≤ 0.0016) but scientifically falsified, and ComCat rights are unresolved. Also confirms the recommendation above (`evidence/h61_candidates.json`). | `evidence/h61_build.json`, `evidence/h61_uniqueness.json`, `docs/research/h61-verdict-20261007.md` |
| `gemsdoe50-h56-scarpdisperse-90000-allfinite.tif` | 90,000 | **History — do not submit.** 27,914 of 90,000 dots (31.0 %) sit on prior-submission cells, and the mixed-network ComCat rights question is unresolved. | `evidence/h56_build.json`, `evidence/h56_holdout.json` |
| `gemsdoe50-h55-seisgeom-ridgesnap-13591-20261007-bcb60d89-zeros.tif` | 13,591 | Older unique deliverable; frozen decision **NO SLOT** (loses the blocked proxy test to the incumbent). | `evidence/results/h55s1-evaluation-20261007.json` |
| `gemsdoe50-h53-probe-tmi-pointlineation-…tif` | 0 | **Audit-only all-zero file — do not upload.** It records a NO-GO experiment. | `evidence/h53-validation-20261007.json` |
| `gems50-h52-coincidence8-…`, `gems50-h54-corpuscal-…`, `gems51-scarpradio-…`, `gems52-union-…`, `gems52a-scarpdrainage-…`, `gemsdoe50-h51-corridor-consensus-mix-…`, `gems50-seislin-…` | varies | Earlier candidates and comparison artifacts from this project's own sessions. Each has a `checks-*.json` receipt beside it; none is a current recommendation. | local `checks-*.json`, `evidence/` |

Every SHA-256 is printed on the site next to its download button and re-verified from disk before the
page is regenerated (`scripts/build_h60_site.py` refuses to publish a band whose bytes drifted). The
files in `downloads/` mirror a subset of `docs/downloads/` for the top-level site.
