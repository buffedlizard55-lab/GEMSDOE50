# H53 analysis — TMI-conjunction emission, seismic falsification split, tip near-miss

Labels: **[OFFICIAL]** organizer/agency source, **[MEASURED]** computed here from pinned
bytes, **[OWNER-QUOTED]** the owner's leaderboard report, **[MODEL]** arithmetic,
**[INFERENCE]** conclusion, **[LIMIT]** weakness. All measurements 2026-10-07 unless noted.

Session question (owner brief): why did `h33-h33-2-b2` score highest (owner-quoted 0.2778),
and can this repository generate a unique submission that scores higher? The first half is
answered byte-verbatim in `docs/research/h33-02778-study-20261007.md`: the file is the
0.2600 file minus its 6,436 near-catalogue dots — dot economy, not geology. Beating it
requires credit/dot above 0.1097 or coverage beyond the corpus blanket, i.e. a detector on
new ground. This note records what the H53 slate (`docs/research/h53-hypotheses.md`) found.

## 1. What shipped [MEASURED]

`downloads/gemsdoe50-h53-tmiconj-20261007T0345Z.tif` (mirrored at
`docs/downloads/`), SHA-256 `3c22da583d53…`, 159,966 bytes, 23,598 dots, values {0, 1},
float32, EPSG:32611, 3730×3292, NaN only outside the published footprint; an `-allfinite`
twin (0.0 outside, SHA-256 `90026224ed74…`) and a one-file `.zip` accompany it.

- Content: H53-C TMI_up150 × radiometric-K/U gradient-ridge conjunction (order ≥ 2 of 3
  families), packed with 3 px suppression on the off-catalogue domain minus every pixel any
  of 27 prior artifacts used.
- Format gate: **PASS** (`evidence/h53_check_submission.json`, `all_checks_pass`).
- Uniqueness gate vs 27 priors (24 GEMSDOE32 files incl. `h33-2-b2`, plus seislin, the H51
  mix and scarpradio): **PASS** — 0 shared pixels with any prior, worst 2 px-proximity IoU
  **0.0767** (threshold 0.5), 82.3 % of dots >200 m from every prior dot.
- Shared `sgmc_off` frame (61,664 truth px, same code as §14 of `h51-analysis.md`):
  **DTI 0.0565, tp/dot 0.1303**, vs matched uniform max 0.0495 and translation max 0.0397
  (5 draws each), 4/4 quadrants positive vs own translation control
  (`evidence/h53_validation_final.json`). The MODEL mapping of that proxy credit through
  the metric identity at G = 12,226 is 0.2121 — a MODEL, not a leaderboard prediction.
- Determinism: rebuilt from scratch with identical bytes (same SHA-256 across runs).

## 2. The shared frame now orders three in-repo candidates [MEASURED]

| file | dots | shared-frame DTI | tp/dot | shared px w/ priors |
|---|---|---:|---:|---:|
| B · H51 scarp + radiometric | 35,000 | **0.1158** | 0.1889 | not 0 (see `evidence/uniqueness_h51.json`) |
| **H53 TMI conjunction (new)** | 23,598 | 0.0565 | 0.1303 | **0** |
| A · H51 corridor-consensus mix | 30,000 | 0.0566 | 0.1050 | 0 |
| archived seislin-44709 (reference) | 44,709 | 0.1472 | 0.1972 | — (cannot resubmit) |
| matched uniform (per-row mass) | — | 0.047–0.059 | — | — |

Readings: H53 ≈ A on DTI with 21 % fewer dots and 24 % more credit per dot; B remains the
strongest in-repo file on this frame by ~2×. H53 is the only file besides A with zero
shared pixels, and at 82 % far-dots it is the most off-prior file the repository has built.
**Slot recommendation is unchanged: B first, H53 second, A third** — and no slot is spent
by this repository under any reading; the owner decides.

## 3. H53-B seismicity: falsification PASSES, proxy gate FAILS [MEASURED]

The owner's method ran in two routes on the background-separated set (triangle keep-mask
**applied** — the seislin defect fix; 13,000 of ~20,430 cut events kept; Gardner-Knopoff
and Baiesi-Paczuski/Zaliapin agreement recorded as side diagnostics):

- Route 1 (DBSCAN-in-spacetime OADC-style): 22 clusters from 13,000 events — the
  t×3000 m/yr metric fragments everything but swarm sequences, which sit on mapped faults.
  Off-catalogue pack: 284 dots, DTI 0.0002. **Rejected**, kept as the documented negative
  control.
- Route 2 (the brief's literal method — per-neighbourhood 2-D covariance, λ1/(λ1+λ2) ≥
  0.80, ≥8 events in 5 km, ≥2 km long, width from catalog `horizontalError`, 500
  corridors, snapped ≤3 px to the TMI gradient ridge): n = 17,928, DTI 0.0390,
  tp/dot 0.1158, 3/4 quadrants, beats translation max (0.0335), and **beats both
  smoothed-density controls 2.8× (0.0147 / 0.0135)** — the brief's falsification test
  **passes**: geometry beats density.
- But it does not beat the matched uniform max (0.0412), so the preregistered proxy gate
  **fails** and H53-B is **not shipped**.

[INFERENCE] Cleaned seismicity lineations carry real geometry (they beat their own density
by 2.8×) but land no better than chance on SGMC's off-catalogue faults: the lineations
trace the known (masked) fault system, and SGMC's extra faults are elsewhere. This is a
split result, not a burial: the hypothesis survives its falsification test yet earns no
mass. [LIMIT] The proxy itself ranks live scores at ρ = +0.196 (p = 0.35), so this frame
cannot certify or kill the hypothesis for the hidden truth either.

## 4. H53-A tip-relay bridges: near-miss [MEASURED]

6,938 catalogue-tip endpoints → strike-compatible bridges (≤3 km, ±60°) plus singleton-tip
horsetail projections, snapped ≤5 px to the TMI ridge: n = 20,631, DTI 0.0441 vs uniform
max 0.0453 — fails `beats_uniform` by 3 % — but beats translation and is positive in 4/4
quadrants. Recorded as a near-miss; a follow-up with preregistered tighter strike
tolerance may re-test it, but post-hoc tuning on this frame is not done here.

## 5. Why H53-C passed where the corpus plateaued [INFERENCE]

The corpus spends ~5 % of its dots on TMI lineaments while TMI occupancy is the only
positive robust score correlate (ρ = +0.566). H53-C spends 100 % of its 23,598 dots on
TMI×K/U conjunction ground with zero prior pixels — the largest unspent physical layer in
the evidence stack. Its tp/dot (0.1303) exceeds every H51-line file except B on the shared
frame. Whether SGMC-off credit transfers to the hidden expert labels is unproven ([LIMIT],
same proxy caveat as §3); what is proven is format, novelty, and a like-for-like proxy
gain over chance with 4/4 spatial folds.

## 6. Limitations carried forward

1. No organizer score exists for the H53 file; every number here is local.
2. The `sgmc_off` proxy has no demonstrated power to predict live scores (ρ = +0.196).
3. Injection/mining removal is by ComCat `type` only (545 rows); no site inventory exists
   here (see `docs/research/comcat-license-review-20261007.md` §5).
4. The 2-D triangle reduction of the 3-D tetrahedron test is unverified; H53-B is not ACLUD
   (scalar errors, no covariances, no focal mechanisms).
5. H53 sits 82 % on ground no prior artifact touched — exactly where no score-history
   instrument can price it. Its live score, if the owner spends a slot, would be the first
   prospective test of TMI-conjunction ground.
