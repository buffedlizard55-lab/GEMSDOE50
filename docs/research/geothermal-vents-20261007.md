# Geothermal-vent and structural-control research note — 2026-10-07

**Scope.** This is the deep-research pass on geothermal vent science requested as a standing
project task, done autonomously, with every claim traced to an official or peer-reviewed source
with a link for manual verification. It is written to be reused by future sessions, not re-derived.
**Nothing in this note has been implemented or scored yet** — see "Resulting H53+ candidate ideas"
at the end and `docs/h51-candidates.md` Part 3 for where this becomes an actual preregistered
hypothesis.

## 1. What actually controls blind geothermal systems in the Great Basin (the GEMS study area)

The GEMS Prize study area sits inside the Great Basin, and the authoritative, decades-long research
program on where blind (no-surface-expression) geothermal systems occur there is the Nevada
"play fairway" project led by James Faulds and collaborators at the Nevada Bureau of Mines and
Geology (NBMG, University of Nevada, Reno), USGS, LBNL, and others, funded by DOE. Findings,
each independently verifiable at the cited link:

- **Fault interaction/intersection geometry, not any single fault trace, is the primary control.**
  Most Great Basin geothermal systems sit in one of four structural settings: (a) discrete steps
  (step-overs) in normal fault zones, (b) intersections between normal faults and transversely
  oriented oblique-slip faults, (c) overlapping, oppositely dipping normal fault zones
  (accommodation zones), and (d) terminations of major normal faults / horse-tailing fault splays.
  [Faulds & Hinz, characterizing structural controls of geothermal reservoirs in the Great Basin and
  western Turkey](https://www.researchgate.net/publication/228585834_Characterizing_Structural_Controls_of_Geothermal_Reservoirs_in_the_Great_Basin_USA_and_Western_Turkey_Developing_Successful_Exploration_Strategies_in_Extended_Terranes);
  [Astor Pass blind-system case study, GRC Transactions v.36 2012, OSTI 1110516](https://www.osti.gov/servlets/purl/1110516).
- **The Nevada Play Fairway project (DOE-funded, 2014-2021) formalized this into a reproducible,
  quantitative model** combining nine parameters: structural setting quality, recency of Quaternary
  faulting, fault slip rates, regional geodetic strain rate, fault slip/dilation tendency, earthquake
  density, horizontal gravity gradient, modelled temperature at 3 km depth, and spring/well
  geochemistry. [USGS summary report, DOI 10.2172/1724080](https://www.usgs.gov/publications/discovering-blind-geothermal-systems-great-basin-region-integrated-geologic-and);
  [regional methodology paper, 41st Stanford Geothermal Workshop](https://pangea.stanford.edu/ERE/pdf/IGAstandard/SGW/2016/Faulds1.pdf).
  The project **found and drilled new blind systems** this way: Southern Gabbs Valley (fault
  intersections + displacement transfer zone; 120 °C at 150 m)
  [USGS, DOI via pubs.usgs.gov/publication/70201803](https://pubs.usgs.gov/publication/70201803),
  and Granite Springs Valley (fault terminations + accommodation zone; 80 °C at 150 m)
  [44th Stanford Geothermal Workshop, Faulds et al. 2019](https://pangea.stanford.edu/ERE/pdf/IGAstandard/SGW/2019/Faulds.pdf).
- **Slip and dilation tendency is a real, quantitative, GIS-computable favorability signal, but it
  is explicitly reported as *weak* in isolation.** The project's own correlation analysis against 34
  benchmark (known) geothermal sites found slip/dilation tendency a much weaker predictor than
  fault recency or slip rate, and assigned it the lowest weight (0.3× vs 3× for recency) in their
  blended model, "due to the relatively poor correlation with benchmarks" — because *most* Quaternary
  faults in the Basin and Range happen to be favorably oriented for the regional stress field, so the
  statistic does not discriminate well on its own. [41st Stanford Geothermal Workshop, section
  3.4.5](https://pangea.stanford.edu/ERE/pdf/IGAstandard/SGW/2016/Faulds1.pdf). This is an important,
  **contrarian, easy-to-miss caveat**: a naive "high dilation tendency ⇒ geothermal/fault signature"
  rule would reproduce a documented weak-correlation result, not a novel strong one. Any hypothesis
  using this layer must combine it with something else (as the play-fairway model itself does) and
  must not present it as a strong standalone signature.
- **Quaternary volcanic vents and paleo-geothermal deposits (tufa, sinter) are themselves official,
  mapped, point-feature datasets**, not just useful background — e.g., the Astor Pass tufa tower
  trend was used to directly infer the plunge of a buried fault-intersection conduit before any
  drilling. [Astor Pass case study](https://www.osti.gov/servlets/purl/1110516).

## 2. Officially free, obtainable data this unlocks (verified this session)

The INGENIOUS project ("INnovative Geothermal Exploration through Novel Investigations Of
Undiscovered Systems", DOE award, Great Basin Center for Geothermal Energy / NBMG) is the direct
successor to the play-fairway project and publishes its entire regional input-feature compilation
on the DOE Geothermal Data Repository, **CC BY 4.0, submission 1391**, confirmed by fetching the
page directly: <https://gdr.openei.org/submissions/1391> (DOI
[10.15121/1881483](https://doi.org/10.15121/1881483)). Project page:
<https://gbcge.org/current-projects/ingenious/>. Individual resources, each with its own direct
download URL confirmed present on that page:

| Resource | Format | Direct link | Relevance |
|---|---|---|---|
| Quaternary Volcanics (vents + flows) | Shapefile | `https://gdr.openei.org/files/1391/great_basin_q_volcanics.zip` | Literal, official, mapped geothermal-vent point/polygon locations — directly on point for "geothermal vent science" |
| Paleo Geothermal Features (springs, tufa, sinter) | Shapefile + CSV | `https://gdr.openei.org/files/1391/paleo_geothermal_regional.zip` | Independent corroboration layer distinct from everything currently implemented (H51/H52 use only topographic/radiometric/drainage physics) |
| Quaternary Faults v2 (ages, slip rates) | Shapefile | `https://gdr.openei.org/files/1391/qfaults_ingenious_nad83conus117_2023-06-27.zip` | Supersedes the fault compilation this project currently derives `derived_sgmc_faults_100m_u8.tif` from; may differ from the competition's own fault layer and could itself reveal disagreements worth investigating (cf. the already-logged, not-shipped H50-3 hypothesis) |
| Quaternary Faulting Slip and Dilation Tendency | USGS data release | <https://doi.org/10.5066/P9YL58W6> | The per-fault favorability statistic described in §1, pre-computed and citable |
| 2 m Temperature Probes | Shapefile/CSV | `https://gdr.openei.org/files/1391/2m_temperature_probe_INGENIOUS_regional_data.zip` | Direct shallow-thermal-anomaly evidence, independent of all structural/geomorphic layers already used |
| Elevation Trend and Detrended Elevation | USGS data release | <https://doi.org/10.5066/P9MQRCBY> | **Potential substitute for the `training_features.tif` `det_elev`/`det_elev_slope` bands this project confirmed permanently unobtainable** (`docs/h52a-protocol.md`) — same physical quantity, independently published, CC-equivalent USGS data release |
| Geophysical Maps — Gravity and Magnetics | USGS data release | <https://doi.org/10.5066/P9Z6SA1Z> | **Potential substitute for the `training_features.tif` magnetic/gravity bands** needed by H52-B (basement-depth step), currently blocked for the same reason |
| Heat Flow Maps | USGS data release | <https://doi.org/10.5066/P9BZPVUC> | Background conductive heat flow with hydrothermal signal removed; independent heat-axis evidence |
| Earthquake Density Models | GeoTIFF/CSV | `https://gdr.openei.org/files/1391/seismicity_INGENIOUS_regional_data.zip` | A second, independently-computed seismicity density product to cross-check against this project's own ComCat-derived density/lineation work |

**Obtainability, confirmed and flagged honestly:** every one of the above is public-domain-adjacent
(CC BY 4.0 for the GDR submission; USGS public domain for the ScienceBase data releases), free, and
requires no login or competition-specific credential — they are obtainable in principle by anyone.
**They are not obtainable by this agent in this sandbox right now**: direct `curl`/`bash` access to
`gdr.openei.org` fails with the same `SSL_ERROR_SYSCALL` this project has already documented for
every non-GitHub host tested this session (Dropbox, Zenodo, USGS, ScienceBase, TNM). The `fetch_page`
tool *can* render the GDR listing page as text (which is how the table above was built and verified),
but it cannot write a binary `.zip`/GeoTIFF into the workspace, so it cannot supply the actual raster
and vector bytes needed to build anything from this list. **This is the same data-access ceiling
already documented for `training_features.tif`, not a new failure mode** — see
`evidence/h52a_data_access.json`. Next session (or the human owner, from a normal network) should
simply download the two USGS ScienceBase data releases (`det_elev`/`det_elev_slope` substitute and
the gravity/magnetics substitute) and the `great_basin_q_volcanics.zip` / `paleo_geothermal_regional.zip`
archives and add them to `.arena/run/inputs/` or `data/external/` for a future build to consume.

## 3. Contrarian read: what is probably *not* worth doing, and why

- **A straight "high slip/dilation tendency ⇒ fault signature" detector would not be novel.** It is
  exactly the weak, already-published, already-weighted-down (0.3×) signal in the play-fairway
  model itself (§1). Any future hypothesis using this data must corroborate it with an independent
  physical quantity (as H52-A already does for scarp+drainage), not use it alone.
- **Known vent/paleo-geothermal-feature locations are themselves old evidence, not new fault
  evidence** — a tufa tower or Quaternary volcanic vent marks a conduit that was almost certainly
  already captured by existing fault mapping or by this project's own radiometric/scarp lineament
  families. Their genuine value is as an **independent corroboration/falsification layer**: a
  candidate corridor that crosses a mapped paleo-vent or tufa trend, far from any already-mapped
  fault, is stronger evidence than a corridor with no such corroboration — this is a plausible H53
  candidate (below), not a standalone detector.
- **The GEMS competition's actual scoring target is existing mapped faults the USGS/INGENIOUS
  catalogue is missing, not geothermal productivity.** A location with high geothermal favorability
  is not automatically a mapped-fault-shaped target; conflating the two would be the kind of
  overclaim this project's charter explicitly forbids (see README "Do not overstate the literature").
  Any H53 candidate built from this research must still be scored on the project's existing
  off-catalogue SGMC instrument and the spatially blocked holdout, exactly like H51/H52.

## 4. Resulting H53+ candidate ideas

See `docs/h51-candidates.md` Part 3 for the two concrete, preregistration-ready candidates this
research produced (H53-A: paleo-vent/tufa corroboration gate; H53-B: substituted det_elev/gravity
bands from the INGENIOUS USGS data releases to finally unblock the H52-B basement-depth-step
candidate that `training_features.tif`'s unavailability has blocked all session). Neither is
implemented or scored; both require the external data named in §2 to be fetched by a process with
normal network egress before any instrument score can be computed.

## 5. Irregularities and limitations flagged in this note

- All of §2's data is obtainable in principle but **not fetchable by this agent in this sandbox** —
  flagged, not hidden, and not worked around by substituting a different, uncited, or fabricated
  dataset.
- The weak-correlation finding in §1 is reported **because it argues against** a tempting naive
  hypothesis, in keeping with the "no hallucinations, contrarian but grounded" requirement — it would
  have been easy to omit and claim the opposite.
- This note draws on USGS/OSTI/DOE technical reports and conference proceedings (GRC Transactions,
  Stanford Geothermal Workshop), which are official, non-paywalled, and directly linked, but are not
  peer-reviewed journal articles in every case; where a stronger peer-reviewed citation exists
  (e.g., Faulds & Hinz, Geosphere) it is linked in addition.
