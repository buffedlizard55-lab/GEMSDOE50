# ComCat license and external-data review — 2026-10-07 (H52)

Verification labels follow `docs/research/score-model.md`: **[OFFICIAL]** read from an
organizer or agency source, **[MEASURED]** computed here from pinned bytes, **[MODEL]**
arithmetic under stated assumptions, **[INFERENCE]** a conclusion, **[LIMIT]** a known weakness.

This note is the source-specific rights review the repository charter requires before the
ComCat extract under `data/external/` may be used as a submission input. It records the
official URL and license **first**, then the competition-rule determination.

## 1. Official URL [OFFICIAL]

- Catalog home: <https://earthquake.usgs.gov/data/comcat/> — "The ANSS Comprehensive
  Earthquake Catalog (ComCat) contains earthquake source parameters and related products
  contributed by seismic networks around the world." (read 2026-10-07)
- Machine service used for the extract: <https://earthquake.usgs.gov/fdsnws/event/1/>
  (the FDSN event web service; query bbox and row counts are pinned in
  `data/external/usgs_comcat_earthquakes.summary.json`).
- ComCat documentation (field definitions incl. `net`, `horizontalError`):
  <https://earthquake.usgs.gov/data/comcat/index.php> (read 2026-10-07)

## 2. License [OFFICIAL]

- USGS agency policy, "Copyrights and Credits"
  (<https://www.usgs.gov/information-policies-and-instructions/copyrights-and-credits>,
  read 2026-10-07): **"USGS-authored or produced data and information are considered to be
  in the U.S. Public Domain."** Credit requested as "Credit: U.S. Geological Survey".
- The same page limits that statement: "not all information, illustrations, or photographs
  on our site are [public domain]" — some contributed materials are used with permission and
  marked as copyrighted. ComCat event pages carry **no such contributor-copyright marking on
  the source parameters**; the contributed material is event origin parameters (time,
  latitude, longitude, depth, magnitude, type, errors) plus network attribution (`net`).
- Contributing-network citation practice confirms redistribution-for-public-use is the norm:
  e.g. the Alaska Earthquake Center instructs users who downloaded from ComCat to cite
  "Earthquake information … retrieved from the ANSS Comprehensive Catalog
  (https://earthquake.usgs.gov/data/comcat/), operated by the U.S. Geological Survey"
  (<https://earthquake.alaska.edu/data_citation_guidelines>, read 2026-10-07).
- A third-party registry entry (KG-Hub, **not** a USGS source) independently lists the
  ComCat license as "U.S. federal government public domain"
  (<https://kghub.org/kg-registry/resource/usgs-comcat/usgs-comcat.html>); recorded here as
  corroboration only, not authority.

## 3. What this extract uses — and does not use [MEASURED]

From `data/external/usgs_comcat_earthquakes.summary.json` (222,939 rows, bbox pinned there):

| used by H52 | field | why it is safe to share |
|---|---|---|
| yes | `time`, `latitude`, `longitude`, `depth`, `mag`, `magType` | factual event parameters |
| yes | `type` | factual; used only to *remove* anthropogenic events |
| yes | `horizontalError` | factual; sets corridor width (median 0.36 km, 63.9 % present — measured 2026-10-07) |
| yes | `net`, `locationSource` | attribution metadata, kept in evidence |
| **no** | waveforms, phase picks, moment tensors, ShakeMaps, DYFI, any "related product" | never downloaded; the CSV extract contains only the columns above |

Networks contributing this extract's rows: `nc` 62.8 %, `nn` 35.0 %, `ci` 1.6 %, `us` 0.5 %,
remainder <0.2 % [MEASURED]. All contribute to ANSS ComCat for public dissemination under
cooperative agreements; the FDSN service exposes their parameters with no access control,
no clickwrap license, and no redistribution prohibition statement.

## 4. Competition-rule determination [OFFICIAL + INFERENCE]

- The competition's external-datasets clause ([problem description, "External
  datasets"](https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/#external-datasets),
  read 2026-10-07): "Participants are allowed to use any additional data sources, provided
  that the participants possess a license that permits the data to be used in this challenge
  and shared with the sponsor for evaluation purposes."
- **Determination:** U.S. public-domain status (or, equivalently, factual parameters with no
  redistribution restriction) permits both use in the challenge and sharing with the sponsor
  for evaluation. **H52 may therefore use the ComCat origin parameters as a submission input,
  with attribution** (USGS Earthquake Hazards Program + contributing networks `nc`, `nn`,
  `ci`, `us`, others as listed in the evidence file). The frozen query bbox, service URL,
  row counts, and per-network attribution travel with the build evidence so the organizers
  can re-pull the identical public extract.

## 5. Residual limits [LIMIT]

1. This review covers **origin parameters only**. Any future use of ComCat "related
   products" (waveforms, focal mechanisms, ShakeMaps) needs its own review.
2. The determination rests on the USGS public-domain policy plus the absence of any
   contributor restriction statement on the redistributed parameters; it is not a legal
   opinion. If the organizers question any record, the build evidence pins the exact public
   query needed to re-verify.
3. Location uncertainty: `horizontalError` is a scalar, not a covariance (63.9 % present).
   H52 uses the catalog value where present and the in-extract median (0.36 km) elsewhere,
   and records both. This is **not** the ACLUD uncertainty treatment of Wang et al.
   ([arXiv:1304.6912](https://arxiv.org/abs/1304.6912)); the difference is stated in the
   method doc, not hidden.
4. "Known injection and mining sites" are removed by ComCat `type` (362 explosions,
   88 quarry blasts, 42 nuclear explosions, 15 chemical explosions, 10 mining explosions,
   9 mine collapses, plus quarry/acoustic/sonic/rockslide/not-reported rows — 545 rows total
   [MEASURED]). No separate site inventory is available in this sandbox, so site-buffer
   removal beyond the type filter is **not** performed; recorded as a limitation, with
   declustering as the remaining swarm control.
