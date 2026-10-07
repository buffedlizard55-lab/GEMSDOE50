# H55 final analysis: the reported 0.2778, the 0.3195 barrier, and seismic geometry

Evidence labels: **OFFICIAL** = organizer/source statement; **MEASURED** = computed from
hash-pinned bytes; **OWNER-REPORTED** = repository/user claim without an organizer receipt;
**MODEL** = conditional calculation; **INFERENCE** = interpretation; **LIMIT** = unresolved.

## Executive conclusion

1. The exact H33-B2 pixels and construction are known, but **0.2778 is not authenticated to those
   bytes**. GEMSDOE32's own audit calls the artifact `UNSCORED` and projects `0.274673`, while its
   two local TIFFs have verified hashes and 37,654 positive cells. No organizer submission ID,
   receipt, or score-to-hash crosswalk was found. The correct wording is therefore “reportedly
   0.2778,” never “verified 0.2778.”
2. If the attribution is assumed, H33-B2's mechanism is metric-efficient pruning, not new geology.
   It starts from an owner-reported 0.2708, 40,199-dot base and deletes all 2,545 dots at raster
   distance `<=2` pixels from the supplied catalogue. Because supplied/catalogued faults are not the
   omitted-fault target, those dots are expected to cost false-positive mass while adding little
   hidden-truth coverage. The 300 m kernel also rewards sparse, non-redundant support. Fewer dots can
   therefore score higher while preserving almost the same weighted true-positive coverage.
3. A score above the owner-quoted historical 0.3195 is mathematically possible, but the repository
   has no validated method that reaches it. Under the documented hidden-mass model it requires
   roughly 41% weighted truth coverage with 30,000 dots and materially higher credit per emitted
   dot. Recombining the existing family cannot supply that missing coverage; a genuinely different
   detector is needed.
4. H55-S1 was that kind of detector in construction, but not in measured performance. The final
   600 m earthquake-geometry candidate scores local SGMC-off DTI **0.019551**, versus **0.115822**
   for frozen Candidate B, loses in all four spatial macrofolds, and has paired-subtile
   credit-per-dot CI **[-0.118667, -0.037195]**. It is a unique, format-clean research TIFF, but the
   frozen decision is **NO SLOT**.

## 1. What H33-B2 actually is

**MEASURED / OWNER REPOSITORY**

| property | value |
| --- | --- |
| candidate | `H33-2-B2` |
| zero-outside SHA-256 | `c55bafc470054e8271dcb89347a17e07fefe50de6af6e6ba6c4b169ef7ab6fa9` |
| NaN-outside SHA-256 | `baeae3219bba6a19bc8cfe79224e28555c50184b7c1ca65c2a822f54807c77dd` |
| grid | one float32 band, EPSG:32611, 3,730 x 3,292, 100 m |
| support | 37,654 binary positive cells |
| parent | owner-reported 0.2708 artifact, 40,199 cells |
| transform | remove all 2,545 parent dots within 2 pixels of the supplied catalogue |
| GEMSDOE32's status | `UNSCORED`; locally projected 0.274673 |
| score named in the request | 0.2778, owner-reported and not organizer-crosswalked |

The filename's `e5eb6e7e` is a content-family digest, not an organizer score receipt. The repository
has both format audits and local holdout results, but neither authenticates a public score. This
irregularity matters: a scientific explanation can identify a plausible causal mechanism, but it
cannot silently turn a report into a fact.

## 2. Why pruning can raise distance-weighted Tversky

The official 300 m triangular support is

```
k(d) = max(1 - d / 300 m, 0).
```

Let `T` be distance-weighted true-positive credit, `F` false-positive weight, and `G` the number of
hidden truth pixels. Since weighted false negatives are `G-T`,

```
DTI = T / [T + 0.2 F + 0.8 (G-T)]
    = T / [0.2 T + 0.2 F + 0.8 G].
```

For a new unit-valued dot with unique kernel credit `k`, `T` rises by `k` and its unmatched mass is
`1-k`; the denominator rises by exactly 0.2. At current score `s`, the dot improves the result iff

```
k > 0.2 s.
```

At 0.2778 the threshold is only 0.05556, but a dot that adds no new hidden-truth maximum has
`k=0` regardless of how geologically plausible it looks. Dense or duplicated predictions therefore
hurt. Conversely, deleting a no-credit binary dot reduces the denominator by 0.2 and leaves the
numerator unchanged.

H33-B2 applies this asymmetry directly. Its parent already had a roughly metric-matched sparse
lattice. B2 removes 2,545 dots next to *known* catalogue traces, where omitted-fault truth should be
least likely by the task definition. GEMSDOE32's local live-anchor model estimated that this removal
lost only about 55 weighted truth-credit units and projected a rise from 0.2708 to 0.274673. The
reported 0.2778 would mean either that the removed dots were even less useful on hidden truth than
that proxy predicted, that another score/file mapping is involved, or that one of the owner-reported
anchors is imprecise. No available receipt distinguishes those alternatives.

The best supported explanation is thus:

* **support economy:** 6.3% fewer dots than the 40,199-dot parent;
* **target-aware negative mask:** deletion near supplied faults, which are not the omitted target;
* **kernel non-redundancy:** isolated dots avoid paying repeatedly for the same 300 m neighbourhood;
* **not a new geological detector:** B2 inherited every retained location from its parent and added
  no new evidence layer.

Calling the result “better fault discovery” would confuse a metric optimization with an increase in
geological recall.

## 3. Conditional inversion of 0.2778

A separate repository model infers hidden mass `G approximately 12,226` pixels from a blind lattice.
For corridor-like outputs it uses matched-mass ratio `rho=M/T=1.188`, yielding

```
T_req(s,N) = s (0.2 N + 0.8 G) / [1 - 0.2 s (1-rho)].
```

This is **MODEL**, not organizer truth. Under it:

| case | dots N | DTI | required credit T | T/G | T/N |
| --- | ---: | ---: | ---: | ---: | ---: |
| reported H33-B2 | 37,654 | 0.2778 | 4,759 | 38.9% | 0.1264 |
| GEMSDOE32 local projection | 37,654 | 0.274673 | 4,706 | 38.5% | 0.1250 |
| owner-quoted target, compact budget | 30,000 | 0.3195 | 4,982 | 40.8% | 0.1661 |
| owner-quoted target, H33-B2 budget | 37,654 | 0.3195 | 5,465 | 44.7% | 0.1451 |

This makes the design problem explicit. At H33-B2's mass, 0.3195 needs approximately 706 additional
weighted credit pixels (+14.8%) without extra support cost. At 30,000 dots it needs fewer total
credits, but credit efficiency must rise from about 0.126 to 0.166 per dot (+31%). Merely thinning
cannot guarantee that: once deletion starts removing unique maxima, `T` falls faster than the
0.2-per-dot denominator saving.

## 4. Can a method exceed 0.3195?

**In principle, yes. In current evidence, no.** The bound is not physical: the model places the
best prior family at only about 39% weighted coverage, leaving substantial hidden truth. But three
constraints make the gap hard:

1. **The omitted-fault prior is sparse.** Most plausible-looking pixels are false positives at a
   300 m kernel, so adding broad corridors usually lowers efficiency.
2. **Existing submissions are one correlated family.** Reweighting or blending locations already
   explored cannot discover omitted strands outside their union. Historical score inversion
   constrains global efficiency but does not localize the missing truth.
3. **Independent proxy truth is weakly transportable.** SGMC is real mapped geology, but not the
   hidden expert labels. Passing it is necessary under this project's slot policy, not sufficient
   evidence of a future organizer score.

A credible route above 0.3195 must add an independent detector that finds at least one substantial
previously uncovered strand while retaining sparse emission. That was the rationale for testing
individual relocated-earthquake geometry rather than the old smoothed seismic-density feature.

## 5. H55-S1: what was tested

The frozen H55 protocol:

1. verifies the 183,002-row Trugman Nevada relocated catalog (Zenodo DOI
   `10.5281/zenodo.11167510`, CC BY 4.0);
2. keeps relocated, non-negative, <=25 km-depth events in finite template cells;
3. excludes events near GDR hot features and explicit ComCat blast/mine/quarry event locations;
4. space-time thins to one largest-magnitude event per 250 m cell per 90-day epoch window;
5. applies a local-density-normalized triangle-area test against 32 uniform footprint catalogues;
6. fits full local 2-D covariance eigenstructure, requiring >=10 events, >=3 years, linearity
   >=0.60, >=1.5 km length, and stable bootstrapped strike;
7. dynamically snaps only *across* each inferred axis to an independent 70/30
   LiDAR/radiometric ridge field;
8. tests 300, 600, and 1,000 m corridor half-widths, masks supplied-fault buffers, and compares with
   matched 1/2 km density, random, translation, and frozen-incumbent controls;
9. excludes every positive pixel in the complete registered prior corpus from final placement.

The normalized two-dimensional triangle-area test is an **unverified project adaptation**. It is
not Ouillon and Sornette's published three-dimensional tetrahedron method. The source catalog has no
per-event covariance, so the corridor widths are sensitivity assumptions, not measured uncertainty.

## 6. H55 falsification result

**MEASURED on one frozen SGMC-off proxy frame**

| method | pooled DTI | credit/dot | emitted dots |
| --- | ---: | ---: | ---: |
| H55-S1 300 m | 0.011175 | 0.068670 | 8,308 |
| **H55-S1 600 m** | **0.019551** | **0.074407** | **13,710** |
| H55-S1 1,000 m | 0.030946 | 0.077715 | 21,418 |
| density 1 km | 0.046398 | 0.075053 | 35,000 |
| density 2 km | 0.046807 | 0.075729 | 35,000 |
| matched random in novelty domain | 0.029964 | 0.048411 | 35,000 |
| **frozen Candidate B incumbent** | **0.115822** | **0.188856** | **35,000** |

Only 299 axes pass the point-geometry filters. Under the frozen 3-pixel spacing their corridors
cannot supply the target 35,000 dots, so the central realization emits 13,710. H55 loses to the
incumbent in all four macrofolds; the paired 16-subtile bootstrap interval for
candidate-minus-incumbent credit per dot is `[-0.118667, -0.037195]`. Broader width increases recall
but never reverses the ranking against density or the incumbent.

**INFERENCE:** recurrent earthquake epicentre axes are too spatially selective and too weakly tied
to surface SGMC traces for this emitter. The independent ridge snap does not rescue that mismatch.
This does not prove that seismic geometry is useless on hidden truth, but it directly falsifies the
registered claim that this implementation is ready to consume a weekly slot.

## 7. Artifact status and limitations

The final NaN-outside TIFF passes the competition-grid checks and a complete direct comparison
against the 50-row sibling registry plus five newer local priors (55 assertions, 54 unique
filenames, 53 unique hashes): no identical hash,
zero exact prior-positive pixels by construction, and maximum 200 m-proximity IoU 0.04007. The
all-finite zero-outside twin re-reads with values exactly `{0,1}` and exists specifically to avoid
the historical portal range-parser failure.

Neither file has an organizer score. The all-finite twin is the obvious download, while the
NaN-outside twin matches the sample footprint semantics. This duality is disclosed because local
format rules and historical portal behavior conflict.

Hard limitations remain:

* the 250 m/90-day largest-event rule is deterministic sequence thinning, not a validated
  ETAS/Reasenberg/Gardner-Knopoff declustering model;
* the mine/injection screen is incomplete;
* mixed-network ComCat contributor rights remain unresolved even though ComCat only removes sites;
* no event-specific relocated location covariance exists;
* SGMC is an imperfect proxy rather than hidden truth;
* a 2-D epicentre axis can represent a dipping structure, swarm, induced sequence, or depth trend
  rather than a surface trace;
* no weekly slot was used, and none is recommended for H55-S1.

## Reproduction

```bash
PYTHONPATH=src .venv/bin/python scripts/build_h55.py
GEMS50_CORPUS=.arena/prior_corpus PYTHONPATH=src .venv/bin/python \
  scripts/check_submission.py \
  --submission docs/downloads/gemsdoe50-h55-seisgeom-ridgesnap-13710-20261007-9b37258c-nan.tif \
  --out evidence/results/h55s1-full-corpus-check-20261007.json
PYTHONPATH=src .venv/bin/python -m pytest -q
```

Primary evidence: `evidence/results/h55s1-evaluation-20261007.json`,
`evidence/results/h55s1-full-corpus-check-20261007.json`,
`evidence/results/h55-prior-corpus-receipt-20261007.json`, and
`docs/research/h55-deviation-log.md`.
