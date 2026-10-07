# H55-S1 exact protocol addendum

**Frozen:** 2026-10-07 UTC, after source acquisition and catalogue-QC counts, but before any H55
field was scored against a fault raster. No SGMC, catalogue-holdout, incumbent, or submission
similarity result was viewed when these constants were chosen.

This addendum turns `h55-hypotheses-preregistered.md` into executable constants. It does not relax
that document's gate.

## Event filters

* Geometry source: decompressed bytes of `data/external/nvreloc_catalog_newmag.txt.gz`; require
  Zenodo MD5 `38fa663f473378b61c74b597c53c416b`, `reloc == 1`, depth in `[0,25]` km, and a finite
  template cell.
* Geothermal-operation screen: remove any event within **2,000 m** of a distinct GDR-1391 point
  whose trimmed `thermalclass` is `Hot`.
* Mining/blast screen: from the inherited USGS FDSN export, use only rows explicitly typed
  `explosion`, `quarry blast`, `nuclear explosion`, `chemical explosion`, `mining explosion`,
  `mine collapse`, `quarry`, or `anthropogenic event`; remove a relocated event within **3,000 m**
  of one of those points. No mine name or unverified hard-coded coordinate is used. This screen is
  necessarily incomplete. The mixed-network export's contributor-specific redistribution status is
  unresolved, so the screen is a disclosed competition-compliance blocker even though it can only
  remove, never add, candidate locations.
* Sequence thinning: partition time into consecutive **90-day** bins from Unix epoch and space into
  fixed **250 m × 250 m** UTM cells; retain the largest-magnitude row per space-time cell, ties by
  smallest event ID.

## Uncorrelated-background test (unverified 2-D adaptation)

For each retained event, form the triangle with its two nearest retained neighbours. Divide its area
by the squared distance to its 20th nearest neighbour; this dimensionless normalization removes the
first-order local event-density scale. Form the reference CDF from **32** independent catalogues,
each containing the same number of points drawn uniformly from finite template cells with uniform
within-cell jitter. Define `p_area` as the reference-CDF value of the observed normalized area and
retain `p_area <= 0.20`.

This is **not** the published 3-D tetrahedron method of Ouillon & Sornette (2011), and no claim of
method equivalence is made. The random seed is **5501**.

## Covariance axes and recurrence

* One fit seed per occupied 1,000 m UTM cell; circular neighbourhood radius **5,000 m**.
* At least **10** retained events and **3** distinct calendar years.
* Full 2-D covariance eigensystem, with `lambda1 >= lambda2`; require
  `(lambda1-lambda2)/(lambda1+lambda2) >= 0.60`.
* Segment endpoints are the 5th and 95th percentiles along the principal axis; require at least
  **1,500 m**.
* Event-bootstrap the strike 24 times; require the 90th-percentile unsigned axial angle to be at
  most **30 degrees**.
* Quality is the geometric mean of clipped linearity, event support, year support, length support,
  bootstrap stability, and `(1-p_area)`; overlapping centreline samples combine by maximum.

## Independent ridge and placement snap

* Topographic strength uses 3DEP bands `step_max`, `lapneg_max`, `relief`, and `coh100`, decoded
  according to `data/external/lidar_scarp_features.json`; its supplied `strike` band supplies an
  axial orientation diagnostic.
* Radiometric strength is the geometric mean across Gaussian scales 1.5 and 3 pixels of the summed
  K/Th/U/TC gradient magnitude, with a 9-pixel moving-median background removed.
* Each family is robust-normalized at its 99th finite percentile. Ridge score is
  `0.70 * topographic + 0.30 * radiometric`; these label-blind weights are fixed here.
* For each axis sample and each integer cross-axis shift inside the assumed corridor half-width,
  sample ridge strength and topographic strike agreement. A dynamic-programming path maximizes
  ridge evidence plus `0.25 * cos(2*angle_difference)` where topographic orientation is available,
  minus **0.08** per pixel of shift change; adjacent samples may change by at most two shift pixels.
  This is the required ridge snap. It does not move along the inferred axis.
* Raster fields are built at half-widths **300, 600, and 1,000 m**. The snapped centreline is
  Gaussian-broadened with `sigma = half_width / 2.355`; multiply by `(0.5 + 0.5*ridge_score)` and
  mask to finite cells more than 300 m from the supplied catalogue.

The relocated catalogue contains no event-specific covariance. These widths are sensitivity
assumptions, **not measured event errors**. The 600 m field is the central candidate only if all
three widths have the same positive validation sign.

## Emission and gates

Emit **35,000** binary dots with 3-pixel minimum separation, exactly matching the frozen incumbent's
mass. Compare the same supports against 1 km and 2 km Gaussian density controls, four fixed
translations, matched uniform controls, and the 35,000-dot incumbent on the frozen spatial cores.
The exact fold/bootstrap gates are those in the preregistration. The final primary GeoTIFF uses
NaN outside the official footprint; an all-finite zero-outside twin is also written specifically to
avoid the portal's historical non-finite range parser failure. Both must re-read with finite values
in `[0,1]` and exact template CRS/shape/transform.
