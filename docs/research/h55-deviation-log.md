# H55-S1 implementation deviations and review fixes

This file is append-only evidence for changes made **after** the H55 protocol was frozen. A change
cannot retroactively alter the preregistered promotion gate.

## Pass 1 — first executable realization

The first run implemented the frozen filters and produced 299 accepted axes. With 3-pixel spacing,
the finite corridor support could emit only 9,399 / 15,670 / 24,614 dots at 300 / 600 / 1,000 m,
not the 35,000-dot target. The central 600 m realization scored local pooled SGMC-off proxy DTI
0.017405 versus 0.090403 for the incumbent under the first draft evaluator. It therefore failed
before any attempt to promote it.

## Pass 2 — evaluator bug and uniqueness hardening

Line-by-line review found that the first draft passed SGMC proxy truth into
`build_spatial_blocks`. That changed the visible-truth buffer rather than merely reusing the frozen
macrofold geometry. It was fixed by reconstructing the registered split with the supplied
catalogue labels, then applying SGMC-off truth inside only the already-frozen cores and subtiles.
This is a correctness fix, not parameter tuning. Under the corrected evaluator, before novelty
hardening, the 600 m candidate scored 0.021677 and the incumbent 0.115822.

A full-resolution comparison then found incidental exact overlap with broad old lattices even
though no prior pixels had been used to construct H55. To enforce the request literally, the 50-row
sibling registry plus five newer in-repository H50/H51 files were hash-verified (55 assertions;
54 unique filenames; 53 unique file hashes), and a packed union of all prior positive pixels was
frozen as `registry/prior_positive_union.npz`.
Every such pixel is now an output exclusion. This is a strictly restrictive, label-blind novelty
post-process: it cannot add a prior location or improve a candidate score by copying. It was not in
the exact protocol, so it is reported as a deviation and all scores were rerun.

## Pass 3 — latest-main prior-corpus expansion

While the pull request was awaiting merge, main added H52, H52A, and H53 TIFFs. Before integration,
every new TIFF path was inventoried and the strict exclusion was rebuilt. At that stage the receipt
had 63 source assertions: 50 registered siblings and 13 repository paths, representing 62 distinct
source paths, 60 comparison filenames, 59 byte-distinct TIFFs, and 33 distinct positive masks. It
records three byte-identical multi-path groups, including both H53 copies under `docs/downloads/`
and `downloads/`, and separately groups finite/NaN twins that encode the same positive prediction.
The union grew to 1,375,484 cells. This expansion remained label-blind and only removed possible
candidate locations; all artifacts, scores, format checks, and site pages were regenerated.

| latest-main family | TIFF source assertions | byte-distinct TIFFs | distinct positive masks | positive cells / mask | copy/twin finding |
| --- | ---: | ---: | ---: | ---: | --- |
| H52 union | 2 | 2 | 1 | 44,828 | finite and NaN twins |
| H52A scarp/drainage | 2 | 2 | 1 | 10,000 | finite and NaN twins |
| H53 TMI conjunction | 4 | 2 | 1 | 23,598 | each `downloads/` TIFF is byte-identical to its `docs/downloads/` counterpart; finite and NaN twins share support |

The full per-path SHA-256, positive-mask SHA-256, byte count, and positive count are in
`evidence/results/h55-prior-corpus-receipt-20261007.json`; no TIFF copy is silently counted as a
new prediction.

## Pass 3 continuation — latest-main H54 expansion

Main advanced again with H54 while the updated branch was being pushed. Its NaN and all-finite
TIFFs are byte-distinct twins with the same 40,000-cell positive mask. Both source assertions were
added before another H55 rerun. The current receipt therefore covers 65 assertions, 64 distinct
source paths, 62 comparison filenames, 61 byte-distinct TIFFs, and 34 distinct positive masks. The
strict union grew from 1,375,484 to 1,405,451 cells. H54 itself failed its frozen random-control gate;
its two files remain prior research comparisons, not sources of candidate-positive pixels.

## Final rerun

The final central field emits **13,591**, not 35,000, binary cells. The filename records the actual
mass. It has zero exact positive-pixel overlap with the full prior union. The NaN-outside twin passes
all format checks and full-resolution uniqueness against all 62 comparison filenames: maximum
200 m-proximity IoU 0.04011, no identical hash, verdict unique. The all-finite twin was separately
re-read with every value finite and in `[0,1]` to prevent recurrence of the portal range-parser
error.

The corrected final SGMC-off proxy values are:

| support | pooled DTI | credit / dot | emitted dots |
| --- | ---: | ---: | ---: |
| H55-S1, 300 m | 0.011069 | 0.068256 | 8,278 |
| **H55-S1, 600 m (central)** | **0.019321** | **0.074141** | **13,591** |
| H55-S1, 1,000 m | 0.030960 | 0.078040 | 21,332 |
| smoothed density, 1 km | 0.046524 | 0.075258 | 35,000 |
| smoothed density, 2 km | 0.045898 | 0.074250 | 35,000 |
| matched random, novelty-constrained | 0.028893 | 0.046676 | 35,000 |
| frozen Candidate B incumbent | 0.115822 | 0.188856 | 35,000 |

The candidate loses to the incumbent in all four macrofolds. Its paired subtile credit-per-dot
bootstrap 95% interval versus the incumbent is `[-0.118959, -0.037294]`. It also fails exact mass,
width-consistency, density, random, and scientific-completeness gates. The decision is therefore
**NO SLOT**. No weekly submission slot was used.
