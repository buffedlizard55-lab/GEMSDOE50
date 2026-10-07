# Which file should I download — and is it OK to submit?

**Short answer: download and submit exactly one file — the recommended artifact in the first row
below.** Everything else here is an alternative, a superseded candidate, or an audit/negative-control
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
| `gemsdoe50-h57-scarpstep-80000-20261007T1830Z-allfinite.tif` | 80,000 | **RECOMMENDED — you may download and submit this one.** Freely-built from public layers, no unresolved rights; strongest artifact on the repository's frozen spatially-blocked gate (0.2025 vs 0.1053 matched uniform, 4/4 folds). | `evidence/build_h57-scarpstep.json`, `evidence/h57_holdout_80k.json`, `evidence/h57_validation.json` |
| `gemsdoe50-h60-union-d0-75308-20261007T2250Z-allfinite.tif` | 75,308 | Alternative, **statistically tied** with H57 (frozen gate 0.2033 vs 0.2025, difference inside instrument noise). Safe and unique — zero prior submission pixels reused — but not the repository's recommendation. | `evidence/h60_gate_decision.json`, `evidence/h60_holdout_offcat.json` |
| `gemsdoe50-h60-union-d2-75308-20261007T2250Z-allfinite.tif` | 75,308 | **Negative control — do not submit.** Maximal-novelty arm: loses to a matched uniform control (0.0618 vs 0.0917) in 4/4 folds. It exists to price novelty. | `evidence/h60_holdout_offcat-d2.json` |
| `gemsdoe50-h60-officialstack-50000-20261007T2100Z-allfinite.tif` | 50,000 | Superseded arm (official-stack belief alone; frozen gate 0.1224, far below the incumbent). Record only. | `evidence/h60_holdout_offcat-officialstack.json` |
| `gemsdoe50-h58-seislineage-98598-…-allfinite.tif` | 98,598 | **NO SLOT.** Unique ComCat-lineation corridor artifact; loses the frozen gates and its contributor-rights question is unresolved. **Do not upload** until rights clearance. | `evidence/h58_build.json`, `evidence/h58_holdout.json` |
| `gemsdoe50-h56-scarpdisperse-90000-allfinite.tif` | 90,000 | Superseded candidate. Blocked on the mixed-network ComCat rights/shareability question — **do not upload** without clearance. | `evidence/h56_build.json`, `evidence/h56_holdout.json` |
| `gemsdoe50-h55-seisgeom-ridgesnap-13591-20261007-bcb60d89-zeros.tif` | 13,591 | Older unique deliverable; frozen decision **NO SLOT** (loses the blocked proxy test to the incumbent). | `evidence/results/h55s1-evaluation-20261007.json` |
| `gemsdoe50-h53-probe-tmi-pointlineation-…tif` | 0 | **Audit-only all-zero file — do not upload.** It records a NO-GO experiment. | `evidence/h53-validation-20261007.json` |
| `gems50-h52-coincidence8-…`, `gems50-h54-corpuscal-…`, `gems51-scarpradio-…`, `gems52-union-…`, `gems52a-scarpdrainage-…`, `gemsdoe50-h51-corridor-consensus-mix-…`, `gems50-seislin-…` | varies | Earlier candidates and comparison artifacts from this project's own sessions. Each has a `checks-*.json` receipt beside it; none is a current recommendation. | local `checks-*.json`, `evidence/` |

Every SHA-256 is printed on the site next to its download button and re-verified from disk before the
page is regenerated (`scripts/build_h60_site.py` refuses to publish a band whose bytes drifted). The
files in `downloads/` mirror a subset of `docs/downloads/` for the top-level site.
