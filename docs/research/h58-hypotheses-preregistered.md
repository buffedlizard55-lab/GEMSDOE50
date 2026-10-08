# H58 preregistration — five hypotheses not yet tried, ranked before any H58 scoring

**Frozen:** 2026-10-07 UTC, before the H58 code was run or any H58 proxy score was computed.
**Decision criterion:** expected gain in distance-weighted Tversky index (DTI), then implementation
cost, then whether the input is obtainable with a competition-compatible licence inside this
sandbox's egress allow-list (github.com, codeload/api.github.com, registry.npmjs.org, pypi.org,
files.pythonhosted.org). A proxy pass is necessary, not sufficient, and is never an organizer score.
**Session branch:** `arena/71ff0271-gemsdoe50`.

## Verified competition state at registration time

- Public leaderboard read 2026-10-07 UTC: **#1 xiaofanhu 0.3774**, #2 alexoktaba 0.3345,
  #3 nchuzhoy 0.3262, #7 DARD 0.3195, **#13 extradr19 0.2778**
  (<https://www.drivendata.org/competitions/306/competition-doe-gems/leaderboard/>).
- Official metric (problem page, read 2026-10-07):
  `DTI = TP_w / (TP_w + 0.2·FP_w + 0.8·FN_w + ε)`, triangular kernel `k(d) = max(1 − d/300 m, 0)`;
  submission = single-band float32 GeoTIFF, EPSG:32611, 100 m, same bounds, null/NaN outside,
  values in [0, 1] (<https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/>).
- External-data rule (same page): a licence that permits challenge use **and sharing with the
  sponsor for evaluation purposes**.
- For binary unit dots the metric reduces exactly to `DTI = T / (0.2·N + 0.8·G)`; beating 0.3774
  needs T/N ≈ 0.199 at N = 30,000 or near-saturated coverage (G ≈ 12,226 calibrated) — see
  `docs/research/h56-diagnosis.md` §4.

## Source and rule gate recorded before implementation

- **H58-S1 earthquake source:** the committed, hash-pinned USGS ANSS ComCat extract
  `data/external/usgs_comcat_earthquakes.csv.gz` (SHA-256
  `19e726c8d0640ad0bdf9c239ae4a855dc1fef18956cfcc7ec9f34b45eb314c82`, 222,939 rows, fetched
  2026-10-06T20:46:25Z). Official service URL: <https://earthquake.usgs.gov/fdsnws/event/1/query>;
  catalog home: <https://earthquake.usgs.gov/data/comcat/>. Licence: USGS-authored data are U.S.
  public domain (<https://www.usgs.gov/information-policies-and-instructions/copyrights-and-credits>).
- **Flagged intra-repo rights conflict (irregularity, not silently resolved):**
  `docs/research/comcat-license-review-20261007.md` (H52 session) determined the ComCat *origin
  parameters* usable with attribution; `registry/sources.json`, `data/external/README.md`, and the
  extract's own summary record the mixed-network export as *unresolved* for external competition
  use (NCEDC terms non-transferable). **Determination for H58-S1:** building a research artifact
  that is never uploaded is permitted under either reading; any real slot requires the owner to
  resolve the conflict first. `horizontalError` is a scalar (63.9 % present, median 0.36 km), not
  a per-event covariance.
- **Injection/mining screen:** ComCat `type` filter (545 anthropogenic rows in this extract) +
  3 km buffer around explicit anthropogenic event centres. The GDR-1391 hot-feature CSV is **not
  present** in this sandbox (gdr.openei.org is outside the egress allow-list); the screen is
  recorded as incomplete. GDR-1391 is CC BY 4.0, DOI 10.15121/1881483; its derived rasters are
  committed in sibling `GEMSDOE30/data/external/` (obtainable) for H58-PALEO.
- **Ridge-snap layer:** USGS 3DEP 1 m LiDAR scarp descriptors + GeoDAWN K/Th/U/TC radiometrics,
  restored hash-pinned from `7GEMSDOE` via `scripts/restore_inputs.sh` (SHA-256 verified
  2026-10-07: `d580bb8b…` lidar, `c22420f7…` radiometrics). Raw sources are USGS public domain
  (GeoDAWN DOI 10.5066/P93LGLVQ); the derived rasters are inherited owner mirrors.
- **Frozen instruments:** off-catalogue SGMC proxy truth (`data/external/derived_sgmc_faults_100m_u8.tif`,
  USGS public domain, measurement only); frozen four-macrofold holdout `evidence/holdout-v1.json`;
  frozen prior-positive union `registry/prior_positive_union.npz` (1,405,451 cells, 61 artifacts);
  incumbent = H56 (`docs/downloads/gemsdoe50-h56-scarpdisperse-90000-allfinite.tif`).

## Ranked candidates (expected DTI improvement, then cost)

### 1 — H58-GTC: radiometric total-count (TC) gradient ridge, standalone *(screened first; cheapest expected positive)*

- **Layers:** `geodawn_rad_u8.tif` band 4 (TC), restored from `7GEMSDOE` (hash-pinned).
- **Signature:** multi-scale gradient-magnitude ridge `|∇G_σ(TC)|` at σ = 1.5/3 px with the H52-M
  line-persistence operator — a lineament matched filter, not a brightness ranking.
- **Why it can find an omitted fault:** TC gradients mark lithologic boundaries and K-alteration
  fronts that persist beneath alluvial cover where a Quaternary surface trace is absent.
- **Differs:** H52-G blended eight geophysical channels, diluting TC — the **only** geophysical
  channel that measured above 1.1 (enrichment **1.242**, `docs/hypotheses-20261007-h56.md`), and
  the register explicitly left it "deserves its own test in a future session". No artifact uses TC
  alone with persistence.
- **Expected ΔDTI / cost:** +0.01…+0.04 / **1/5**. No new data.

### 2 — H58-PALEO: paleo-geothermal deposit × structural-ridge alignment (the geothermal-vents angle)

- **Layers:** `derived_gdr_paleo_100m_u8.tif` (sinter/travertine/tufa — fossil vent deposits),
  `derived_gdr_volcanics_100m_u8.tif` (vents/flows), `derived_gdr_2m_probes_100m_u8.tif` (2 m shallow
  temperature anomalies), all committed in `GEMSDOE30/data/external/` (github.com — obtainable),
  source GDR 1391, CC BY 4.0, DOI 10.15121/1881483; plus the LiDAR-scarp / TC ridges.
- **Signature:** a ridge segment scores where (a) a paleo-vent or probe thermal feature sits within
  ~1 km and (b) the ridge azimuth matches the regional NNE–SSW normal-fault family.
- **Why it can find an omitted fault:** the competition's stated target is "structures indicative
  of geothermal resources"; the given catalogue has **no geothermal-activity attribute**, so
  thermal evidence is orthogonal to it. Fossil/active discharge marks permeability pathways.
- **Differs:** H19/H51 used thermal points only as a blurred favourability field; GEMSDOE36's PInN
  entry (0.2750) used geothermal data with an unverified recipe; no artifact gates structural ridges
  on discrete GDR deposit/vent/probe evidence.
- **Expected ΔDTI / cost:** +0.005…+0.02 / **2/5** (sparse: 244 paleo px, 2,700 probe px in
  footprint — a precision multiplier, not a standalone detector).

### 3 — H58-B1: basin-floor displacement edge

- **Layers:** `training_features.tif` bands 15 (`depth_to_base_surf`), 5/11/18 (`iso_grav_anom`
  slope/vg/hg), 17 (`cond_surf`); restored hash-pinned from `5GEMSDOE` (obtainable; the official
  copy needs DrivenData login, which this project does not have).
- **Signature:** directional step ≥ 150 m in modelled basement depth over ≤ 1 km, requiring a
  gravity-gradient maximum and a conductivity contrast within 500 m — edge detection on a modelled
  physical interface.
- **Why it can find an omitted fault:** range-front/intrabasin faults offset basement while young
  alluvium hides the surface trace; the catalogue is surface-built, so basement-offset faults are
  exactly the omission class.
- **Differs:** H51-C tested generic potential-field edges; H55-B1 preregistered this at rank 3 but
  **it was never implemented** — this implements it.
- **Expected ΔDTI / cost:** +0.005…+0.03 / **3/5** (needs the 419 MB feature cube restored).

### 4 — H58-D: up-dip depth projection of seismic lineations

- **Layers:** the ComCat extract (depth field) + the H58-S1 lineations.
- **Signature:** fit each accepted axis with its events' median hypocentral depth; project the
  corridor up-dip to the surface trace at 50–60° regional normal-fault dip (sweep 45/55/65°);
  place dots at the **projected surface trace**.
- **Why it can find an omitted fault:** epicentres of a ~55°-dipping fault at 10 km depth sit ~7 km
  downdip of the surface trace, and the competition scores **surface** fault pixels. The H56
  diagnosis measured the best seismic artifact enriched at 1 px (2.93×) but depleted at 3 px —
  placement precision is where the seismicity family can gain.
- **Differs:** H50-D archived exactly this as "depth-resolved seismicity lineations" but was blocked
  on ComCat rights; the H52 licence review unblocked it. **Every prior seismic artifact placed dots
  at the epicentre corridor, never at a depth-projected trace.**
- **Expected ΔDTI / cost:** unknown — plausibly the largest seismicity-side gain; unverified / **2/5**.

### 5 — H58-S1: ComCat epicentre point-geometry lineations as the PRIMARY submission field *(the mandated deliverable)*

- **Layers:** the committed ComCat extract (hash-pinned above).
- **Signature:** per-epicentre k-NN **2-D covariance eigenstructure** → keep linear, well-sampled
  neighbourhoods → corridors along the principal axis with half-width = catalogue `horizontalError`
  (median 0.36 km ≈ 3.6 px at 100 m — **a corridor prior, not a trace**); decluster by the 2-D
  triangle-area test (unverified adaptation, labelled); remove anthropogenic types + 3 km
  explicit-event buffers.
- **Why it can find an omitted fault:** a blind or buried active fault can organize hypocentres
  with no mapped surface trace — precisely the class the surface-built catalogue omits.
- **Differs:** H55 used the *relocated* catalogue with stricter recurrence gates and **failed**
  (0.0193 vs 0.1158 incumbent, 0/4 folds); H56 used ComCat lineations only as a 0.25-weight
  **corroboration** on LiDAR (measured lift 0.96–0.99, neutral); H50-B/H51-B were legacy.
  **No shipped artifact makes ComCat point geometry the primary field** with a hard 3 px
  Euclidean distance rule, ridge snap, and uniqueness gate; these design choices are not a
  proven metric optimum.
- **Expected ΔDTI / cost:** **expected below the incumbent** on current measurements — built
  because the owner mandates it; the slot decision follows the frozen gate / **2/5**.

## Frozen H58-S1 implementation and falsification gates

1. ComCat screens: tectonic type filter; `mag ≥ 1.5`; `depth < 25 km` finite;
   `horizontalError ≤ 10 km`; inside the finite template footprint; 3 km buffer around explicit
   anthropogenic event centres; GDR hot-feature 2 km screen only if the CSV is present (it is not —
   recorded limitation). Triangle-area declustering at quantile 0.95, seed 20261007. Sequence
   thinning is a sensitivity flag, off for the primary.
2. Lineations: k = 10 nearest neighbours, ≥ 6 events, elongation `σ1/σ2 ≥ 3.0`, `σ1 ≥ 800 m`,
   `σ2 ≤ σ_loc` (2-D reduction of the published `λ3 < Δ²` rule). Corridors via
   `h56.corridor_density` defaults (half-width = `horizontalError`, clipped to [1, 6] px).
3. Scoring domain: valid footprint AND > 300 m from the supplied catalogue; truth = SGMC fault
   pixels off-catalogue (proxy). Every prior positive pixel is excluded from placement.
4. Emission: `h56.emit_blue_noise` at exactly 3 px (the metric's own support), masses
   30,000–220,000, seed 571007; the frozen rule selects the mass by the transfer-modelled hidden
   DTI (G = 12,226, transfer 4.2, cap T ≤ G).
5. Placement step: every dot is offered to independent ridge targets (70/30 LiDAR-scarp /
   radiometric ridge from `gems55.ridge`, and the smoothed corridor belief); the identity
   placement is kept unless a snap improves the proxy. Snaps may land only on
   prior-union-excluded, off-catalogue pixels.
6. Falsification (the owner's required test): the candidate must beat **smoothed earthquake
   density** built from the *same* declustered events at matched mass, plus matched random,
   four translations, the H56 incumbent, the frozen four-macrofold holdout, and the paired
   16-subtile bootstrap (candidate − incumbent credit per dot, 5,000 replicates, seed 55007).
7. Uniqueness: zero exact overlap with the frozen prior union by construction; full-resolution
   corpus check (no identical SHA-256, full-pixel IoU < 0.5, novel fraction at 2 px > 0.5) by
   `scripts/h58_uniqueness.py` before any slot review.
8. Format: one float32 band, EPSG:32611, official shape/transform/bounds; values exactly {0, 1};
   all-finite zero-outside primary (cannot reproduce the portal range rejection) + NaN-outside
   twin; every file re-read from disk with the [0, 1] range guard asserted.
9. Decision: ELIGIBLE_FOR_REVIEW only if every numeric gate **and** every scientific/compliance
   gate passes (formal declustering validation, complete mine/injection inventory, event-specific
   covariance, resolved ComCat rights). Otherwise NO_SLOT; the artifact is still published as a
   unique research deliverable with the decision unmissable.

## Post-run code audit — emitter-spacing correction (2026-10-07; does not rewrite the preregistration)

A review of `src/gemsdoe50/h56.py::emit_blue_noise` and `tests/test_h56.py` found that the frozen
protocol's claimed 3.0 px Poisson-disk spacing was not enforced by the then-current code. It chose
one density-weighted pixel per 3×3 block, but never checked Euclidean distances between points in
neighboring blocks. The old test asserted only that each block was unique, so it could not catch
this defect. Reopening the H58 all-finite and NaN TIFFs and measuring pixel-centre nearest-neighbour
distances found a 1.0 px minimum for both files (98,598 positives; median 2.828 px). The H56 90,000-
dot artifact also measures 1.0 px; H57's separate emitter measures 3.0 px.

`emit_blue_noise` is now implemented as density-weighted exponential-race sampling with exact
Euclidean spatial-hash rejection. Its tests check the actual nearest-neighbour distance, seeded
determinism, and cells on incomplete trailing blocks. This is a **post-run implementation correction**;
it does not retroactively make the H58 artifact meet the preregistered spacing requirement. The
H58 metric results still describe the exact bytes evaluated, but the spacing sub-gate failed. The
existing verdict remains **NO SLOT**; do not rebuild, rename, or repackage H58-S1 as a new method.
See `evidence/emitter-spacing-audit-20261007.json` for per-artifact measurements.

## Post-run metric-algebra correction — 2026-10-07

The frozen preregistration's simplified equation in §1 is conditional, not a general identity.
For binary predictions, with `T = TP_w`, `M = sum_x max_g k(d(x,g))` over predicted cells, `N`
predicted cells, and `G` truth cells, the exact DTI denominator is `0.2N + 0.8G + 0.2(T-M)`
(plus epsilon). The reduced `0.2N + 0.8G` form requires `T=M`; a 3 px minimum prediction spacing
does not prove that. This does not change the archived local score receipts, which use the full
TP/FP/FN implementation, but the historical hidden-score/leaderboard arithmetic in this protocol
must be treated as a conditional, unvalidated model, not a score forecast. H58 remains NO-GO / NO
SLOT; no score-to-TIFF receipt exists.
