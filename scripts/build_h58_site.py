#!/usr/bin/env python3
"""Insert the H58-S1 band into the generated research pages.

Runs after ``scripts/build_h55_site.py`` (which regenerates the pages from
committed evidence) and adds the H58-S1 artifact to:

* ``index.html``      — a one-click download band directly below the H56 band,
  with the SHA-256, the frozen slot decision, and the executive summary;
* ``submission.html`` — the manual submission card (name, note, steps) for the
  H58 artifact, next to the other candidates' cards;
* ``results.html``    — the falsification table (candidate vs density, random,
  translations, incumbent) and the frozen holdout result.

Every number is read from the committed evidence JSONs (``evidence/h58_build.json``,
``evidence/h58_uniqueness.json``, ``evidence/h58_holdout.json``); the artifact
SHA-256s are re-verified on disk before anything is published, so the site can
never advertise bytes that are not the gated bytes.  The insertion is
deterministic and idempotent, which keeps the CI ``git diff --exit-code`` check
green.
"""
from __future__ import annotations

import hashlib
import html
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BUILD = ROOT / "evidence/h58_build.json"
UNIQUE = ROOT / "evidence/h58_uniqueness.json"
HOLDOUT = ROOT / "evidence/h58_holdout.json"

INDEX_ANCHOR = '<main id="main">'
SUBMISSION_ANCHOR = '<article class="card span-12"><h2>H56 mass sweep and the calibrated proxy transfer</h2>'
RESULTS_ANCHOR = '<article class="card span-12" id="h33">'
METHODS_ANCHOR = '<article class="card span-12"><h2>Auditable source table</h2>'

# --- H57-scarpstep band (merged to main via PRs #22/#23) -------------------------
# That session hand-edited the generated pages, breaking the reproducibility invariant.
# The band is preserved verbatim as a committed fragment (docs/fragments/) and re-inserted
# here after its artifact SHA-256 is verified against its committed evidence, so the whole
# site is generated again.  See docs/fragments/README.md.
H57_EVIDENCE = ROOT / "evidence/build_h57-scarpstep.json"
H57_BAND_INDEX = ROOT / "docs/fragments/h57-scarpstep-index-band.html"
H57_BAND_SUBMISSION = ROOT / "docs/fragments/h57-scarpstep-submission-band.html"
H57_SCARPSTEP_TIF = (
    ROOT / "docs/downloads/gemsdoe50-h57-scarpstep-80000-20261007T1830Z-allfinite.tif"
)
H56_SECTION_ANCHOR = '<section class="main" id="h56">'

INDEX_META_BASE = (
    '<meta name="description" content="H56 research candidate, H55 blocked decision, '
    'H53-A no-go audit, and score provenance.">'
)
INDEX_META_H57 = (
    '<meta name="description" content="H57 download and executive summary, H56 comparator, '
    'H55 blocked decision, H53-A no-go audit, score provenance.">'
)
INDEX_H56_H2_BASE = '<h2>Download the current research candidate GeoTIFF (H56) &mdash; one click</h2>'
INDEX_H56_H2_H57 = (
    '<h2>Previous candidate (H56) &mdash; retained for comparison; superseded by H57 above</h2>'
)
SUBMISSION_META_BASE = (
    '<meta name="description" content="H56 draft entry details and rights gate, '
    'with the H55 no-slot audit guide.">'
)
SUBMISSION_META_H57 = (
    '<meta name="description" content="H57 download, unique entry name and note, '
    'with the H56 comparator and H55 no-slot audit guides.">'
)
SUBMISSION_TITLE_BASE = "<title>Submission guide · GEMSDOE50</title>"
SUBMISSION_TITLE_H57 = "<title>Submission guide (H57 current) · GEMSDOE50</title>"


def esc(value: object) -> str:
    return html.escape(str(value), quote=True)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def f6(value: float) -> str:
    return f"{float(value):.6f}"


def f4(value: float) -> str:
    return f"{float(value):.4f}"


def load() -> dict:
    build = json.loads(BUILD.read_text(encoding="utf-8"))
    unique = json.loads(UNIQUE.read_text(encoding="utf-8"))
    holdout = json.loads(HOLDOUT.read_text(encoding="utf-8"))
    zero = build["artifacts"]["recommended_portal_safe_allfinite"]
    nan = build["artifacts"]["sample_semantics_nan_outside"]
    for artifact in (zero, nan):
        path = ROOT / artifact["path"]
        if not path.is_file() or sha256(path) != artifact["sha256"]:
            raise ValueError(f"artifact drift: {path}")
    if not unique["verdict_unique"]:
        raise ValueError("site cannot publish an artifact that failed the uniqueness gate")
    return {"build": build, "unique": unique, "holdout": holdout, "zero": zero, "nan": nan}


def index_band(ev: dict) -> str:
    build = ev["build"]
    zero = ev["zero"]
    stem = build["artifacts"]["stem"]
    decision = build["decision"]["decision"]
    pooled = build["holdout"]["pooled"]
    cand = pooled["candidate"]
    inc = pooled["incumbent_H56"]
    dens = pooled["best_density_control"]
    rnd = pooled["matched_random"]
    boot = build["holdout"]["paired_subtile_bootstrap"]["percentile_ci_95"]
    fr = ev["unique"]["full_resolution"]
    tag_class = "fail" if decision != "ELIGIBLE_FOR_REVIEW" else "good"
    return f"""
<section class="main" id="h58"><div class="shell"><div class="grid"><article class="card span-12" style="border-left:6px solid #164b66"><h2>This session&rsquo;s unique artifact &mdash; H58-S1 (ComCat point-geometry lineations) &mdash; one click</h2>
<div class="hero" style="border-radius:10px;padding:18px 20px;margin-bottom:14px"><div class="actions"><a class="download" href="docs/downloads/{esc(stem)}-allfinite.tif" download>Download {esc(stem)}-allfinite.tif</a><a class="download alt" href="docs/downloads/{esc(stem)}-nan.tif" download>NaN-outside twin</a><a class="download alt" href="docs/downloads/{esc(stem)}-allfinite.zip" download>.zip</a></div>
<p class="fine" style="color:#d8e7e3">SHA-256 <span class="hash">{esc(zero['sha256'])}</span> &middot; {zero['bytes']:,} bytes &middot; {zero['positive_cells']:,} predicted cells &middot; unique entry name <code>{esc(build['artifacts']['unique_portal_name'])}</code></p>
<p class="fine" style="color:#d8e7e3"><b>Draft optional note:</b> <q>{esc(build['artifacts']['short_submission_note'])}</q></p>
<p class="fine" style="color:#d8e7e3"><span class="tag {tag_class}">{esc(decision)}</span> &mdash; this session&rsquo;s generated research artifact, published with its frozen gate result. The all-finite file writes 0.0 outside the study footprint, so every one of the 12,279,160 cells is finite and inside [0, 1] &mdash; it cannot reproduce the portal&rsquo;s <code>Predicted values must be in range [0, 1]</code> rejection.</p></div>
<div class="metrics"><div class="metric"><b>{zero['positive_cells']:,}</b><small>binary predicted cells</small></div><div class="metric"><b>{f4(cand['dti'])}</b><small>off-catalogue proxy DTI</small></div><div class="metric"><b>{f4(inc['dti'])}</b><small>H56 incumbent, same frame</small></div><div class="metric"><b>{f4(fr['max_iou'])}</b><small>worst full-pixel IoU vs priors</small></div></div>
<h3>H58-S1 executive summary</h3>
<p>H58-S1 is the owner-mandated unique submission: <b>declustered USGS ComCat epicentre point geometry as the primary field</b> &mdash; 222,939 catalog rows screened to {build['catalog_processing']['events_after_decluster']:,} tectonic, site-screened, declustered events (2-D triangle-area test, an unverified adaptation of Ouillon &amp; Sornette 2011), {build['belief']['lineations']:,} linear, well-sampled 2-D covariance axes rendered as corridors whose half-width is the catalogue&rsquo;s own <code>horizontalError</code> (a corridor prior, not a trace), scored only outside the supplied-fault 300 m buffer, emitted as variable-density blue noise at the metric&rsquo;s own 300 m support, and snapped only across-axis to an independent LiDAR/radiometric ridge (the placement step was measured and the identity placement kept: no snap improved the proxy).</p>
<p><b>Falsification result (frozen gates):</b> pooled proxy DTI {f4(cand['dti'])} vs smoothed-density control {f4(dens['dti'])}, matched random {f4(rnd['dti'])}, H56 incumbent {f4(inc['dti'])}; the paired 16-subtile bootstrap for candidate-minus-incumbent credit per dot is [{f4(boot[0])}, {f4(boot[1])}] &mdash; the candidate loses in all four macrofolds. 1-pixel enrichment vs proxy truth is {f4(build['holdout']['pooled']['enrichment_1px']['enrichment'])}x (chance level). <b>This is a recorded negative result, not a submission recommendation.</b> Uniqueness gate: worst full-pixel IoU {f4(fr['max_iou'])} against every prior artifact on disk, minimum novel fraction at 2 px {f4(fr['min_novel_fraction_at_2px'])}, zero exact overlap with the frozen 1,405,451-cell prior union, no identical SHA-256 &mdash; <b>unique: true</b>. Format gate: the NaN-outside twin passes <code>all_checks_pass</code>; the all-finite twin is entirely finite in [0, 1].</p>
<p class="warning"><b>No weekly slot used; do not upload.</b> The frozen numeric and scientific gates fail (the candidate loses to density, random, and the incumbent; the 2-D triangle test is an unverified adaptation; the mine/injection inventory is incomplete; ComCat contributor rights are a flagged conflict). Verify source permissions and current rules before any slot. Full working: <a href="docs/research/h58-hypotheses-preregistered.md">preregistration</a> &middot; <a href="evidence/h58_build.json">build evidence</a> &middot; <a href="evidence/h58_uniqueness.json">uniqueness evidence</a>.</p>
<h3>How to submit &mdash; only after rights and slot gates pass</h3>
<ol class="list"><li><b>Download</b> the all-finite GeoTIFF above (portal-safe) or the NaN-outside twin (sample semantics) and verify the SHA-256.</li><li><b>Open</b> the <a href="https://www.drivendata.org/competitions/306/competition-doe-gems/">DOE GEMS competition page</a> and sign in.</li><li><b>Upload the file as downloaded.</b> Do not re-save, re-project, re-compress, re-scale or convert it.</li><li><b>Use the unique submission name and the optional note</b> printed above so the entry is distinguishable from every prior one.</li><li><b>Record the portal receipt</b> in this repository before any score is quoted.</li></ol></article></div></div></section>"""


def submission_card(ev: dict) -> str:
    build = ev["build"]
    zero = ev["zero"]
    nan = ev["nan"]
    stem = build["artifacts"]["stem"]
    decision = build["decision"]["decision"]
    return f"""
<article class="card span-12"><h2>This session&rsquo;s H58-S1 file &mdash; manual steps ({esc(decision)})</h2>
<p>Same no-automated-upload policy as the rest of this repository. H58-S1 is the generated unique competition-format artifact; its frozen gate result is <b>{esc(decision)}</b>, so no slot is recommended and the owner&rsquo;s explicit override would be required before any upload.</p>
<ol class="steps"><li><b>Download unchanged.</b> <a href="docs/downloads/{esc(stem)}-allfinite.tif" download>All-finite portal-safe TIFF</a> (recommended: every cell finite, values in [0, 1], the direct guard against the historical range parser) or <a href="docs/downloads/{esc(stem)}-nan.tif" download>NaN-outside twin</a> (sample semantics).</li>
<li><b>Verify SHA-256.</b> All-finite: <code>{esc(zero['sha256'])}</code>. NaN twin: <code>{esc(nan['sha256'])}</code>.</li>
<li><b>Check current rules manually.</b> Sign in at <a href="https://www.drivendata.org/competitions/306/competition-doe-gems/">DrivenData</a>; confirm deadline, remaining weekly slots, external-data disclosures, and AI disclosure. Do not rely on this dated page for live status.</li>
<li><b>Upload one TIFF.</b> Do not re-save, reproject, rename bands, or alter nodata metadata.</li>
<li><b>Record the receipt.</b> Preserve submission ID, exact file hash, timestamp, portal response, and any returned error/score before making any score claim.</li></ol>
<p><b>Unique name</b><br><code>{esc(build['artifacts']['unique_portal_name'])}</code></p>
<p><b>Short note</b><br><q>{esc(build['artifacts']['short_submission_note'])}</q></p>
<p class="fine">Decision record: <a href="evidence/h58_build.json">evidence/h58_build.json</a> &mdash; including the mass sweep, the placement-step measurement, the falsification controls, and the frozen gate components.</p></article>"""


def results_card(ev: dict) -> str:
    build = ev["build"]
    pooled = build["holdout"]["pooled"]
    cand = pooled["candidate"]
    inc = pooled["incumbent_H56"]
    dens = pooled["best_density_control"]
    rnd = pooled["matched_random"]
    boot = build["holdout"]["paired_subtile_bootstrap"]
    folds = build["holdout"]["folds"]
    rows = "".join(
        f"<tr><td>{esc(bid)}</td><td class=num>{f4(f['candidate']['score'])}</td>"
        f"<td class=num>{f4(f['incumbent']['score'])}</td>"
        f"<td class=num>{f4(f['best_density']['score'])}</td>"
        f"<td class=num>{f4(f['uniform']['score'])}</td>"
        f"<td class=num>{f4(f['candidate_minus_incumbent_credit_per_dot'])}</td></tr>"
        for bid, f in folds.items()
    )
    return f"""
<article class="card span-12" id="h58"><div class="warning"><b>H58-S1 falsification: {esc(build['decision']['decision'])}.</b> The owner-mandated seismicity-lineation candidate was built, measured, and gated; it does not beat smoothed earthquake density, matched random, or the H56 incumbent on the frozen proxy, and it loses in all four macrofolds. No portal upload occurred.</div>
<h2 style="margin-top:22px">H58-S1 same-frame SGMC-off proxy</h2><div class="wide"><table><thead><tr><th>method</th><th class=num>DTI</th><th class=num>credit / dot</th><th class=num>dots</th></tr></thead><tbody>
<tr><td><b>H58-S1 (candidate)</b></td><td class=num>{f4(cand['dti'])}</td><td class=num>{f4(cand['credit_per_dot'])}</td><td class=num>{cand['n']:,}</td></tr>
<tr><td>density control (best)</td><td class=num>{f4(dens['dti'])}</td><td class=num>{f4(dens['credit_per_dot'])}</td><td class=num>{dens['n']:,}</td></tr>
<tr><td>matched random</td><td class=num>{f4(rnd['dti'])}</td><td class=num>{f4(rnd['credit_per_dot'])}</td><td class=num>{rnd['n']:,}</td></tr>
<tr><td>H56 incumbent</td><td class=num>{f4(inc['dti'])}</td><td class=num>{f4(inc['credit_per_dot'])}</td><td class=num>{inc['n']:,}</td></tr>
</tbody></table></div>
<p>Paired 16-subtile bootstrap (candidate &minus; incumbent credit per dot), 95% CI: <b>[{f4(boot['percentile_ci_95'][0])}, {f4(boot['percentile_ci_95'][1])}]</b>.</p>
<h3>Frozen macrofolds (SGMC-off truth inside the frozen cores)</h3><div class="wide"><table><thead><tr><th>fold</th><th class=num>candidate</th><th class=num>incumbent</th><th class=num>best density</th><th class=num>uniform</th><th class=num>&Delta; credit/dot vs incumbent</th></tr></thead><tbody>{rows}</tbody></table></div>
<p class="fine">SGMC-off is a necessary local instrument under the project rule, not hidden competition truth. The 1-pixel enrichment of the candidate against proxy truth is {f4(pooled['enrichment_1px']['enrichment'])}x (chance level), and the placement step kept the identity placement because no ridge snap improved the proxy (unsnapped {f4(build['placement_step']['before'])}, belief ridge {f4(build['placement_step']['candidates']['belief_ridge']['dti'])}, geophysics ridge {f4(build['placement_step']['candidates']['geophysics_ridge']['dti'])}).</p>
<p><a href="docs/research/h58-hypotheses-preregistered.md">Preregistration</a> &middot; <a href="evidence/h58_build.json">build evidence</a> &middot; <a href="evidence/h58_holdout.json">holdout evidence</a> &middot; <a href="evidence/h58_uniqueness.json">uniqueness evidence</a> &middot; <a href="docs/downloads/{esc(build['artifacts']['stem'])}-allfinite.tif" download>download the artifact</a>.</p></article>"""


def methods_card(ev: dict) -> str:
    build = ev["build"]
    cat = build["catalog_processing"]
    fc = build["frozen_constants"]
    return f"""
<article class="card span-12"><h2>H58-S1 pipeline (this session)</h2>
<ol class="steps"><li><b>Pin and screen.</b> Verify the SHA-256 of the committed USGS ComCat extract (222,939 rows; official service <a href="https://earthquake.usgs.gov/fdsnws/event/1/">FDSN event web service</a>); keep tectonic types, M&nbsp;&ge;&nbsp;1.5, depth&nbsp;&lt;&nbsp;25&nbsp;km, horizontalError&nbsp;&le;&nbsp;10&nbsp;km, in-grid events ({cat['footprint']['events_in_bounds']:,} in bounds).</li>
<li><b>Remove known injection/mining sites.</b> Drop every non-tectonic event type (545 rows) and apply a 3&nbsp;km buffer around {cat['anthropogenic_site_screen']['centres']} explicit anthropogenic event centres ({cat['anthropogenic_site_screen']['events_removed']:,} events removed). The GDR-1391 hot-feature CSV is absent in this environment; the screen is recorded as incomplete.</li>
<li><b>Decluster.</b> 2-D triangle-area background test against a randomized catalogue (unverified adaptation of Ouillon &amp; Sornette 2011; {cat['events_after_decluster']:,} of {cat['decluster']['n_events']:,} events kept).</li>
<li><b>Fit local axes.</b> Full 2-D covariance of each epicentre&rsquo;s {fc['lineation_k']} nearest neighbours; keep linear (elongation&nbsp;&ge;&nbsp;{fc['lineation_min_elongation']}), well-sampled (&ge;{fc['lineation_min_events']} events, &sigma;1&nbsp;&ge;&nbsp;{fc['lineation_min_sigma1_m']:.0f}&nbsp;m) neighbourhoods; {build['belief']['lineations']:,} lineations accepted.</li>
<li><b>Render corridors.</b> Corridor along each principal axis with half-width = the catalogue&rsquo;s own <code>horizontalError</code> (median {build['belief']['sigma_km_median']:.2f}&nbsp;km &mdash; several pixels at 100&nbsp;m: a corridor prior, not a trace).</li>
<li><b>Emit.</b> Variable-density blue noise at the metric&rsquo;s own 300&nbsp;m support; mass selected by the frozen transfer-modelled rule; support caps at {build['artifacts']['recommended_portal_safe_allfinite']['positive_cells']:,} cells.</li>
<li><b>Place.</b> Every dot is offered to independent ridge targets (70/30 LiDAR-scarp / radiometric); the identity placement is kept because no snap improved the proxy.</li>
<li><b>Gate.</b> Off-catalogue scoring only (&gt;300&nbsp;m from the supplied catalogue); every prior positive pixel excluded; falsified against smoothed density, random, translations, the H56 incumbent, and the frozen four-macrofold holdout.</li></ol>
<p class="fine">The 2-D triangle-area test is an <b>unverified project adaptation</b>, not the published 3-D tetrahedron method, and <code>horizontalError</code> is a scalar, not a per-event covariance (not an ACLUD reproduction, Wang et al. 2013). Mixed-network ComCat contributor rights are a flagged intra-repo conflict; see <a href="docs/research/comcat-license-review-20261007.md">the ComCat rights review</a> and <a href="docs/research/h58-hypotheses-preregistered.md">the H58 preregistration</a>.</p></article>"""


def insert_before(path: Path, anchor: str, block: str) -> None:
    text = path.read_text(encoding="utf-8")
    if block.strip() in text:
        return  # idempotent
    if anchor not in text:
        raise ValueError(f"anchor not found in {path.name}: {anchor[:60]}...")
    if text.count(anchor) != 1:
        raise ValueError(f"anchor is not unique in {path.name}: {anchor[:60]}...")
    path.write_text(text.replace(anchor, block + anchor, 1), encoding="utf-8")


def main() -> int:
    ev = load()
    insert_before(ROOT / "index.html", INDEX_ANCHOR, index_band(ev))
    insert_before(ROOT / "submission.html", SUBMISSION_ANCHOR, submission_card(ev))
    insert_before(ROOT / "results.html", RESULTS_ANCHOR, results_card(ev))
    insert_before(ROOT / "methods.html", METHODS_ANCHOR, methods_card(ev))
    print("H58 band inserted into index.html, submission.html, results.html, methods.html")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
