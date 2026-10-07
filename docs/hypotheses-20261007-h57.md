# H57 — five candidate geological hypotheses, ranked and preregistered (2026-10-07)

Written **before** the H57 implementation ran. Each hypothesis names the layer(s) it
uses, its physical signature, why it should catch a fault that the USGS / INGENIOUS
catalogue misses rather than one already in it, and how it differs from what this
repository has already tried. The rank is by expected improvement in the hidden
Data-Transform Index (DTI) per unit of implementation cost.

Every hypothesis is scored on the same two frozen instruments:

* **frame S (matched)** — USGS SGMC fault pixels inside the footprint, more than
  300 m from the given catalogue, and belonging to an 8-connected component
  smaller than 500 px (the geometric repair described in
  `docs/research/h57-proxy-gap.md`); 52,219 px.
* **frame L (blocked catalogue holdout)** — for each spatial macrofold the
  catalogue is removed *in that fold only*, the field is emitted into the fold, and
  the dots are scored against that fold's own labels. This measures the field
  against the fault population that is actually being labelled rather than against a
  bedrock-fault proxy. Pooled over the four folds.
* **control** — a uniform scatter of the same dot count drawn from the same
  eligible pool, so the reported lift is apples-to-apples.

---

## H57-H1 — the official band-19 topographic-slope family carries the recoverable signal (SELECTED)

**Layer.** Official competition band 19, *detrended elevation slope*, and its
gradient magnitude (`o19_gradmag`); optionally blended with the USGS 3DEP 1 m LiDAR
scarp descriptor stack.

**Signature.** A fault that has moved the ground surface leaves a step. On a
detrended 10 m DEM the step appears as a slope anomaly whose *gradient* (i.e. the
change of slope) is a ridge-line — the classic step-edge detector. The signature is
narrow, linear, and follows the fault strike.

**Why off-catalogue, not catalogue.** The supplied catalogue rasterises published
trace polylines. A step-edge detector does not read polylines; it reads the ground.
Where the catalogue drew one generalised strand across a basin, the topography
carries several, and where the catalogue stops at a mountain front the topography
does not.

**Why it differs from repo methods.** H56 froze a LiDAR-scarp *dispersion* field;
H52-C used an eight-family coincidence vote; both were validated on a frame whose
geometry did not match the supplied catalogue. H57 measures the layer families
against the catalogue's own fault population (frame L) and against a
geometry-matched proxy (frame S) before freezing anything.

**Measured.** frame L pooled DTI **0.2262** for `o19grad` alone — the best field on
that instrument — and 0.2250 for `o19grad + lidar_top7`; `o19` alone 0.2214. On
frame S at N = 250,000 the same three read 0.2435 / 0.2432 / 0.2399 against a
matched-mass uniform of 0.1887. **Accepted.** Frozen as the
rank-mean of `o19grad` and the LiDAR rank-mean, because it is within noise of the
best and it hedges the single-layer risk.

**Cost.** Low — the layer is inside the provided stack.

---

## H57-H2 — relocated-seismicity lineaments from the *point pattern*, not the density band (SCREENED, NOT SELECTED)

**Layer.** The 19-band stack contains band 10 (*distance to earthquake*, n = 100 km
radius, a = 15° azimuth) and band 16 (*earthquake intensity / density*, same
parameters). Those are smooth kernel-density surfaces, and the brief explicitly
forbids reusing them as the seismic term. The alternative is the source point
pattern: CC BY 4.0 relocated hypocentres (Trugman, Zenodo 11167510), de-clustered
by a 90-day / 250 m largest-event rule, each event's k-nearest neighbourhood fitted
with a 2-D covariance matrix whose eigenvalue ratio measures linearity, with the
corridor half-width taken from catalogue location error, in the lineage of Ouillon,
Ducorbier & Sornette (JGR 2008, doi:10.1029/2007JB005032).

**Signature.** A fault that is seismically active produces a *line* of epicentres
whose covariance is elongated along strike. A density band cannot express that: it
is isotropic by construction.

**Why off-catalogue.** The catalogue is built from surface geology and paleoseismic
mapping. An active structure that has not been mapped at the surface but is
generating small relocated events would appear in this term and not in the
catalogue.

**Why it differs from repo methods.** Every prior seismic arm in this repository
(Trugman thinning → triangle test → covariance axes → ridge snapping, H55) used the
same family and lost to the frozen incumbent on the blocked proxy.

**Measured — and the reason it was rejected.** The rendered 3 px corridor field
scores DTI **0.0406 / 0.1008 / 0.1416 / 0.1805 / 0.2026** at 40k / 80k / 120k /
180k / 250k on frame S against matched-mass uniform **0.0742 / 0.1218 / 0.1505 /
0.1762 / 0.1880** — lift 0.55 / 0.83 / 0.94 / 1.02 / 1.07, i.e. **at or below
chance until the mass is so large that the uniform control is also saturating**.
On the single-feature audit the best seismic channel reaches DTI 0.0425 at
N = 20,000 against a uniform 0.0437 (AUC 0.525 for `seis_corridor_log1p`, 0.492 for
`seis_count10km_log`). Adding the corridor to the selected field *costs* 0.0096
DTI on frame S (0.24286 → 0.23417 at N = 250,000). **Rejected on measurement.** It
is kept in the repository as a rendered layer and as a documented negative; no
seismic term is present in the shipped artifact.

---

## H57-H3 — geological-map structural trends absent from the quaternary fault database (NOT IMPLEMENTED — data cost)

**Layer.** USGS NBMG county-scale 1:24,000 / 1:100,000 bedrock maps digitised as
fault traces, differenced against the supplied catalogue.

**Signature.** A pre-Quaternary map fault drawn along a lineament is evidence that a
*structure* exists there even when no Holocene scarp is mapped. The experts who
built the hidden set explicitly allowed new geometry of existing fault systems.

**Why off-catalogue.** Bedrock mapping is compiled at county scale and is dense in
places where the statewide quaternary compilation was generalised.

**Why it differs from repo methods.** H51 used the GDR spring/well catalogue and
NBMG *faults* only as a snapping target, never as a differenced trace source.

**Measured cost.** The NBMG ArcGIS REST `Geology/Faults` layer is live and
queryable (verified 2026-10-07 for the Wassuk Range window: 10 features, UTM 11N).
A full-Nevada extraction, de-duplication against the catalogue and a
licence/attribution check is roughly a full session. **Deferred, not falsified** —
recorded as the top of the recommended next-session list.

---

## H57-H4 — strike continuation of catalogued fault ends (NOT IMPLEMENTED — cannot be validated on any frame held here)

**Layer.** The supplied catalogue itself.

**Signature.** Staff ruling (forum 11536, post 2): *"new fault" means "any fault
pixel not already captured by USGS/INGENIOUS" and can include newly mapped geometry
of an existing fault system*; forum 11516 post 2 adds that new-fault truth can
occur within 300 m of a known trace. Extending a mapped trace along its own local
strike beyond its endpoint is therefore a formally admissible prediction.

**Why it is not in this artifact.** No frame in this repository can score it: the
matched proxy is a *different* fault population with no catalogue-adjacency
structure, and the blocked holdout removes the catalogue before scoring, so a
continuation rule has nothing to continue from. Shipping an unmeasured rule would
violate the frozen rule that a hypothesis must beat the current best on a frozen
holdout before it is spent on the map. **Flagged for the next session as the single
highest-expected-value unvalidated idea**, together with the exact experiment that
would test it (hold out whole catalogue *strands*, continue their ends into the
held-out strand, score the continuation against the held-out pixels).

---

## H57-H5 — magnetic / radiometric / gravity lineament families (RE-SCREENED, NEGATIVE)

**Layer.** Bands 1–9, 11, 13, 14, 15, 17, 18 (magnetics, radiometrics, gravity,
depth to basement, conductivity) and the GeoDAWN radiometric mosaic.

**Signature.** A fault can juxtapose magnetic or radiometric domains, so its
signature is an *edge* in those layers rather than a scarp.

**Why off-catalogue.** A structure with no Holocene expression but a geophysical
contrast is invisible to a surface-fault catalogue.

**Measured.** Consistent with every earlier screening in this repository: at
N = 20,000 on frame S the best magnetic or gravity channel reaches DTI 0.0450
(`o12_gradmag`) against a uniform 0.0437, versus 0.0693 for the best LiDAR scarp
channel and 0.0563 for `o19_gradmag`. On frame S the whole family behaves as noise.
**Rejected again**, with the same caveat as before: frame S is a bedrock-fault
proxy, and a geophysics-only structure with no surface expression is exactly what
this proxy cannot contain.

---

## Ranking, as preregistered

| rank | hypothesis | expected improvement | cost | fate |
|---|---|---|---|---|
| 1 | H57-H1 topographic slope / LiDAR family | high | low | **selected** |
| 2 | H57-H4 catalogue strike continuation | unknown, potentially high | low | not validatable on any frame here |
| 3 | H57-H2 seismicity point-pattern lineaments | moderate (brief requires it) | medium | measured at or below chance |
| 4 | H57-H3 county-scale bedrock traces | moderate | high | data cost; deferred |
| 5 | H57-H5 magnetics / radiometrics | low | low | negative again |

The brief's eighth requirement — a seismicity lineation term built from the point
pattern rather than the density band — is implemented, rendered, audited and
retained in the repository; it is reported here as measured at chance rather than
silently shipped into a submission.

---

## Post-hoc addendum (revision 2) — status after the delivered build

None of H57-H1…H5 was re-ranked by revision 2; what changed is the *implementation* of H57-H1.

| id | status after the delivered build |
|---|---|
| H57-H1 topographic lineament scatter | **SELECTED and shipped** (revision 2): sharpened NaN-aware rank-mean of the LiDAR scarp stack and the official band-19 gradient, 3 px lattice, 90,000 dots, 0.23028 on `S_matched` measured from the delivered bytes, 1.86× a matched-mass whole-footprint uniform control and 2.07× a same-pool one, 4/4 macrofolds positive, paired block bootstrap [+0.0948, +0.1141]. |
| H57-H2 seismicity point-pattern corridors | **NEGATIVE, documented, excluded.** At or below chance on both frames on these truth sets; the 2-D covariance adaptation of the Ouillon–Sornette test remains an unverified approximation of the published 3-D algorithm. |
| H57-H3 multi-scale (macrofold-conditional) field | deferred — unchanged. |
| H57-H4 catalogue-endpoint continuation / splays | **admissible, unvalidated, not shipped.** Staff ruling R6 makes newly mapped geometry of an existing fault system count as truth, and the delivered file's own ceiling analysis shows coverage — not precision — is what separates it from 0.3774. This is the highest-value next experiment and the honest recommendation. |
| H57-H5 ridge-snap placement | NEGATIVE — unchanged. |
