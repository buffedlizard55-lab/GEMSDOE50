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

## Final rerun

The final central field emits **13,710**, not 35,000, binary cells. The filename records the actual
mass. It has zero exact positive-pixel overlap with the full prior union. The NaN-outside twin passes
all format checks and full-resolution uniqueness against all 54 unique prior filenames: maximum
200 m-proximity IoU 0.04007, no identical hash, verdict unique. The all-finite twin was separately
re-read with every value finite and in `[0,1]` to prevent recurrence of the portal range-parser
error.

The corrected final SGMC-off proxy values are:

| support | pooled DTI | credit / dot | emitted dots |
| --- | ---: | ---: | ---: |
| H55-S1, 300 m | 0.011175 | 0.068670 | 8,308 |
| **H55-S1, 600 m (central)** | **0.019551** | **0.074407** | **13,710** |
| H55-S1, 1,000 m | 0.030946 | 0.077715 | 21,418 |
| smoothed density, 1 km | 0.046398 | 0.075053 | 35,000 |
| smoothed density, 2 km | 0.046807 | 0.075729 | 35,000 |
| matched random, novelty-constrained | 0.029964 | 0.048411 | 35,000 |
| frozen Candidate B incumbent | 0.115822 | 0.188856 | 35,000 |

The candidate loses to the incumbent in all four macrofolds. Its paired subtile credit-per-dot
bootstrap 95% interval versus the incumbent is `[-0.118667, -0.037195]`. It also fails exact mass,
width-consistency, density, random, and scientific-completeness gates. The decision is therefore
**NO SLOT**. No weekly submission slot was used.
