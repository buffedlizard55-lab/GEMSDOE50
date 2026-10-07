#!/usr/bin/env python3
"""Add the H61 "start here" band, the H61 result cards and the errata to the site.

Runs after ``scripts/build_h55_site.py`` and ``scripts/build_h58_site.py`` (same
order as ``.github/workflows/site.yml``). It

* puts a single **start-here** band at the very top of ``index.html``: one-click
  download of the recommended file, the YES/NO verdict, the entry name and note,
  a link to the step-by-step submission page, today's H61 decision and the flags;
* points the skip link at that band (it used to jump past every download band);
* corrects the false "reduces exactly to T/(0.2N + 0.8G)" wording in the
  generated bands and retires the stale 0.386 / 0.3774 card;
* inserts the H61 result table into ``results.html`` and the H61 methods/sources
  card into ``methods.html``;
* regenerates ``docs/how-to-submit.html``, ``docs/executive-summary.html`` and
  ``docs/index.html`` (they were withdrawn stubs that still pointed at H51).

Every number comes from committed evidence (``evidence/h61_build.json``,
``evidence/h61_uniqueness.json``, ``evidence/h61_sensitivity.json``,
``evidence/build_h57-scarpstep.json``) and every advertised file's SHA-256 is
re-verified on disk before anything is written. Output is deterministic and the
script refuses to insert a band twice.
"""
from __future__ import annotations

import hashlib
import html
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BUILD = ROOT / "evidence/h61_build.json"
UNIQUE = ROOT / "evidence/h61_uniqueness.json"
SENS = ROOT / "evidence/h61_sensitivity.json"
H57 = ROOT / "evidence/build_h57-scarpstep.json"
CANDS = ROOT / "evidence/h61_candidates.json"

H57_NAME = "GEMSDOE50-H57-SCARPSTEP"
H57_NOTE = (
    "H57 stratified LiDAR-scarp + topographic-step dot emitter; every dot is >=300 m from the "
    "given catalogue and >=300 m from every other dot; research model, not organizer-scored."
)
COMPETITION = "https://www.drivendata.org/competitions/306/competition-doe-gems/"
FORMAT_PAGE = "https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/"
RULES_PDF = "https://docs.nlr.gov/docs/fy26osti/96647.pdf"
VERDICT = "docs/research/h61-verdict-20261007.md"

START_MARK = '<section class="main" id="start">'
H57_SECTION = '<section class="main" id="h57">'
SKIP_OLD = '<a class="skip" href="#main">'
SKIP_NEW = '<a class="skip" href="#start">'
RESULTS_ANCHOR = '<article class="card span-12" id="h58">'
METHODS_ANCHOR = '<article class="card span-12"><h2>Auditable source table</h2>'
COLLAPSE_OLD = "reduces exactly to <code>DTI = T / (0.2N + 0.8G)</code>"
COLLAPSE_NEW = (
    "is <code>DTI = T / (0.2N + 0.8G + 0.2(T &minus; M))</code> with <code>M = &Sigma; K(dot)</code> "
    "(<b>erratum, H61:</b> this band originally said it &ldquo;reduces exactly to "
    "<code>T / (0.2N + 0.8G)</code>&rdquo;; that is exact only when T = M, and dots closer than "
    f'6 px do compete &mdash; <a href="{VERDICT}">H61 verdict &sect;4</a>)'
)
NOCOPY_OLD = (
    "No pixel of any prior submission is copied: against the 26 pinned prior artifacts the maximum "
    "full-pixel IoU is <b>0.0248</b>, while the corpus's own top artifact sits at 0.9691 against its sibling."
)
STALE_0386 = (
    "In principle, yes. H56's transfer model estimates a hidden DTI of 0.386 after positive local "
    "blocked-holdout results, numerically above 0.3774 only under that assumption. This is not an "
    "organizer score, the 0.3774 claim is unverified, and the hidden-label transfer remains "
    "uncertain. H55 and H53-A both failed their own frozen candidate gates."
)


def esc(value: object) -> str:
    return html.escape(str(value), quote=True)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def f4(x: float) -> str:
    return f"{x:.4f}"


def load() -> dict:
    build = json.loads(BUILD.read_text(encoding="utf-8"))
    uniq = json.loads(UNIQUE.read_text(encoding="utf-8"))
    sens = json.loads(SENS.read_text(encoding="utf-8"))
    h57 = json.loads(H57.read_text(encoding="utf-8"))
    cands = json.loads(CANDS.read_text(encoding="utf-8"))
    rec = cands["recommended"]
    if sha256(ROOT / rec["artifact"]) != rec["sha256"]:
        raise SystemExit(f"recommended artifact hash drift: {rec['artifact']}")
    if rec["zip"] and sha256(ROOT / rec["zip"]) != rec["zip_sha256"]:
        raise SystemExit(f"recommended zip hash drift: {rec['zip']}")
    for meta in h57["files"].values():
        if sha256(ROOT / meta["path"]) != meta["sha256"]:
            raise SystemExit(f"H57 artifact hash drift: {meta['path']}")
    art = build["artifact"]
    for key in ("all_finite", "nan_outside", "zip"):
        if sha256(ROOT / art[key]["path"]) != art[key]["sha256"]:
            raise SystemExit(f"H61 artifact hash drift: {art[key]['path']}")
    return {"build": build, "uniq": uniq, "sens": sens, "h57": h57, "cands": cands}


def _u(ev: dict, needle: str) -> dict:
    for label, summary in ev["uniq"]["summary"].items():
        if needle in label:
            return summary
    raise KeyError(needle)


def numbers(ev: dict) -> dict:
    b = ev["build"]
    fa = b["frame_a"]
    dec = b["decisions"]
    h57u = _u(ev, "gemsdoe50-h57-scarpstep")
    h61u = _u(ev, "gemsdoe50-h61-updipseis")
    cands = ev["cands"]
    rec = cands["recommended"]
    recu = _u(ev, Path(rec["artifact"]).name)
    cr = cands["candidates"][rec["name"]]
    c57 = cands["candidates"]["H57-scarpstep-80000"]
    enr = b["stratified_corridor_enrichment"]
    sens = ev["sens"]["variants"]
    return {
        "inc": fa["H57-incumbent-80k"]["pooled"]["score"],
        "inc_folds": {k: v["score"] for k, v in fa["H57-incumbent-80k"]["folds"].items()},
        "h61s": fa["H61-S"]["pooled"]["score"],
        "h61s_n": fa["H61-S"]["mass"],
        "h61s_cpd": fa["H61-S"]["pooled"]["credit_per_dot"],
        "rand_cpd": fa["uniform-random-matched"]["pooled"]["credit_per_dot"],
        "hyb": fa["H61-H-hybrid-80k"]["pooled"]["score"],
        "sp4": fa["H61-M-spacing4-80k"]["pooled"]["score"],
        "sp5": fa["H61-M-spacing5-80k"]["pooled"]["score"],
        "reemit": fa["H57-reemit-80k-on-novel"]["pooled"]["score"],
        "fb": b["frame_b"]["pooled"],
        "enr_median": enr["median_ratio"],
        "enr_gt1": enr["strata_with_ratio_gt_1"],
        "sens_max_enr": max(v["enrichment_median_ratio"] for v in sens.values()),
        "sens_max_lin": max(v["lineations"] for v in sens.values()),
        "lin": b["pipeline"]["lineations"]["merged_lineations"],
        "events": b["pipeline"]["events"]["events_out"],
        "bg": b["pipeline"]["zbz"]["background_kept"],
        "ci": {k: v["bootstrap_vs_incumbent"]["ci95"] for k, v in dec.items()},
        "wins": {k: v["fold_wins"] for k, v in dec.items()},
        "h57_j": h57u["max_jaccard"]["value"],
        "h57_c": h57u["max_containment"]["value"],
        "h57_e": h57u["max_excess_2px"]["value"],
        "h57_e_prior": Path(h57u["max_excess_2px"]["prior"]).name,
        "h61_j": h61u["max_jaccard"]["value"],
        "h61_e": h61u["max_excess_2px"]["value"],
        "priors": ev["uniq"]["distinct_submission_like_priors"],
        "on_union": b["h57_incumbent_prior_union_overlap"]["dots_on_prior_union"],
        "union_frac": b["h57_incumbent_prior_union_overlap"]["fraction_on_prior_union"],
        "repro": b["h57_reproduction"]["identical_support"],
        "rec": rec,
        "rec_gate": cr["frozen_gate"]["frozen_gate_pooled_dti"],
        "rec_gate_unif": cr["frozen_gate"]["frozen_gate_uniform"],
        "rec_gate_folds": cr["frozen_gate"]["frozen_gate_folds_positive"],
        "rec_full": cr["frame_a_full_pooled"],
        "rec_core": cr["frame_a_core_pooled"],
        "rec_folds": cr["frame_a_folds"],
        "rec_wins": cr["fold_wins_vs_H57-scarpstep-80000"],
        "rec_ci": cr["bootstrap_vs_H57-scarpstep-80000"]["ci95"],
        "rec_near": cr["dots_within_300m_of_catalogue"],
        "rec_oncat": cr["dots_on_catalogue_pixels"],
        "rec_j": recu["max_jaccard"]["value"],
        "rec_j_prior": Path(recu["max_jaccard"]["prior"]).name,
        "rec_c": recu["max_containment"]["value"],
        "rec_c_prior": Path(recu["max_containment"]["prior"]).name,
        "rec_e": recu["max_excess_2px"]["value"],
        "rec_e_prior": Path(recu["max_excess_2px"]["prior"]).name,
        "rec_refined": recu["refined_pass_post_hoc"],
        "h57_gate": c57["frozen_gate"]["frozen_gate_pooled_dti"],
        "h57_full": c57["frame_a_full_pooled"],
        "h57_core": c57["frame_a_core_pooled"],
        "h57_reuse": c57["dots_on_prior_union"],
        "agree": cands["instruments_agree_on_first"],
    }


def start_band(ev: dict, prefix: str = "") -> str:
    n = numbers(ev)
    rec = n["rec"]
    a = ev["build"]["artifact"]
    fold_txt = ", ".join(f"{k} {f4(v)}" for k, v in n["rec_folds"].items())
    zip_link = (f'<a class="download alt" href="{prefix}{esc(rec["zip"])}" download>same file as .zip</a>'
                if rec["zip"] else "")
    return f"""{START_MARK}<div class="shell"><div class="grid"><article class="card span-12" style="border-left:6px solid #0f6b5c">
<h1 style="margin-top:0">Start here &mdash; the one file to submit</h1>
<div class="hero" style="border-radius:10px;padding:18px 20px;margin-bottom:14px"><div class="actions"><a class="download" href="{prefix}{esc(rec['artifact'])}" download>Download the recommended GeoTIFF (portal-safe)</a>{zip_link}</div>
<p class="fine" style="color:#d8e7e3">File <code>{esc(Path(rec['artifact']).name)}</code> &middot; SHA-256 <span class="hash">{esc(rec['sha256'])}</span> &middot; {rec['bytes']:,} bytes &middot; {rec['dots']:,} predicted cells &middot; float32, EPSG:32611, 3,730 &times; 3,292, values exactly 0 or 1, no NaN anywhere.</p>
<p class="fine" style="color:#d8e7e3"><b>Entry name:</b> <code>{esc(rec['entry_name'])}</code> &middot; <b>note to paste</b> ({rec['note_chars']} characters): <q>{esc(rec['note'])}</q></p></div>
<p><span class="tag">YES</span> <b>OK to download and submit</b> (it uses one of your weekly slots). This is the highest-ranked file that reuses <b>no</b> prior prediction pixel (charter item 2): on the repository&rsquo;s frozen spatially-blocked gate it scores <b>{f4(n['rec_gate'])}</b> (matched uniform {f4(n['rec_gate_unif'])}, positive in {n['rec_gate_folds']}/4 macrofolds), ahead of H60-union and H57 ({f4(n['h57_gate'])}); this session&rsquo;s independent instrument agrees ({f4(n['rec_full'])} pooled, {f4(n['rec_core'])} inside the fold cores, vs H57 {f4(n['h57_full'])} / {f4(n['h57_core'])}; folds {fold_txt}). It uses no earthquake catalogue. <a href="{prefix}docs/how-to-submit.html"><b>Exactly how to submit, step by step &rarr;</b></a></p>
<p class="warning"><b>Read before submitting.</b> (1) The lead over H57 is real on the pooled scores but not uniform: it wins {n['rec_wins']} of 4 macrofolds against H57 and the paired 16-subtile interval is [{n['rec_ci'][0]:+.4f}, {n['rec_ci'][1]:+.4f}], which includes zero. (2) {n['rec_near']:,} of its dots lie within 300&nbsp;m of the supplied catalogue ({n['rec_oncat']} on catalogue pixels); the GEMSDOE32 B2 result suggests such dots may cost false-positive weight on the hidden labels. (3) Every number here is a proxy (USGS SGMC faults away from the given catalogue), not the organizers&rsquo; expert labels; expect roughly the low 0.2s. Beating the public best 0.3774 would need about 10,500 hidden-truth credit at 80,000&ndash;90,000 dots under the corrected metric algebra. No organizer score exists for any GEMSDOE50 file.</p>
<p><b>Uniqueness.</b> 0 of its dots sit on any of the 1,405,451 pixels of the 61 registered prior artifacts (the charter rule). Against the wider corpus of {n['priors']} distinct rasters from all 54 sibling repositories plus this one &mdash; which also holds archives and dense ensemble rasters never registered as submissions &mdash; it is not a copy of anything: largest exact-pixel Jaccard {f4(n['rec_j'])} and largest share of its dots on one file {n['rec_c']*100:.0f}&nbsp;%, both against <code>{esc(n['rec_c_prior'][:60])}</code> (the same session&rsquo;s never-submitted first revision). Its dots do sit close to earlier scarp-based files (chance-corrected 2-pixel proximity {f4(n['rec_e'])} to the dense <code>{esc(n['rec_e_prior'][:48])}</code>); every scarp-based file does, and forcing 2-pixel novelty was measured by H60 to collapse the score below random. <b>Why not H57 any more:</b> {n['h57_reuse']:,} of H57&rsquo;s 80,000 dots ({n['union_frac']*100:.0f}&nbsp;%) reuse prior prediction pixels, and it now ranks third on the frozen gate. It stays published below for the record only.</p>
<h3>Today&rsquo;s run (H61): the required seismic-lineation map &mdash; <span class="tag fail">NO SLOT</span></h3>
<p>Built as specified: {n['events']:,} screened USGS ComCat earthquakes, declustered with the Zaliapin&ndash;Ben-Zion nearest-neighbour method ({n['bg']:,} background events kept), a 2-D triangle test (my unverified adaptation of the Ouillon&ndash;Sornette 3-D tetrahedron test), local 2-D covariance with location-error removal, corridors as wide as the catalogue location error plus up-dip copies, and dots snapped to the H57 ridge. Result: only {n['lin']} lineations and <b>{n['h61s_n']} dots</b>; holdout DTI <b>{f4(n['h61s'])}</b>, credit/dot {f4(n['h61s_cpd'])} versus {f4(n['rand_cpd'])} for random dots. On withheld catalogue faults the corridors lose to smoothed density ({f4(n['fb']['H61-S'])} vs {f4(n['fb']['density-best'])}). Within every H57-strength decile, the corridors hold <i>less</i> fault credit than the cells outside them (median ratio {n['enr_median']:.3f}, {n['enr_gt1']}/10 deciles above 1); loosening every screen (up to {n['sens_max_lin']:,} lineations) never lifts that ratio above {n['sens_max_enr']:.2f}. A corridor/H57 hybrid ({f4(n['hyb'])}) and spacing H57&rsquo;s dots 4 or 5 px apart ({f4(n['sp4'])}, {f4(n['sp5'])}) also lost. The H61 file is unique (Jaccard &le; {n['h61_j']:.4f}) and valid, but <b>do not submit it</b>: <a href="{prefix}{esc(a['all_finite']['path'])}" download>H61 research file</a> (SHA-256 <span class="hash">{esc(a['all_finite']['sha256'][:16])}&hellip;</span>, entry name if ever used <code>{esc(a['entry_name'])}</code>).</p>
<h3>Flags for manual review</h3>
<ul class="list">
<li><b>Two &ldquo;current candidates&rdquo; on main</b> (fixed here): after two parallel merges the page led with H57 while the H60 receipt recommended the sharpened-scarp file; the H57 band is now marked superseded.</li>
<li><b>Metric algebra:</b> earlier pages said the score &ldquo;reduces exactly&rdquo; to <code>T/(0.2N+0.8G)</code> and that dots 3&nbsp;px apart do not compete. Both are false (tested in <code>tests/test_h61.py</code>); errata added.</li>
<li><b>Published note of the recommended file</b> cites the retracted transfer model (&ldquo;operating point at 0.45&rdquo;); use the corrected note above.</li>
<li><b>Leaderboard coincidence:</b> five owner-reported corpus scores (0.2778, 0.2750, 0.2710, 0.2708, 0.2600) equal the public scores of five different leaderboard accounts. Please check this against <a href="{RULES_PDF}">rules &sect;3.4</a> (limits per participating entity).</li>
<li><b>Sample file:</b> the local <code>sample_submission.tif</code> holds 1.0 on exactly the 60,988 training-label cells, not &ldquo;total fault absence&rdquo;.</li>
<li><b>Reference solution</b> writes float64; the <a href="{FORMAT_PAGE}">format page</a> asks for float32 (all files here are float32).</li>
<li><b>ComCat</b> contributor rights are unresolved, and USGS&rsquo;s own <code>horizontalError</code> definition link now redirects; no catalogue-derived file (H56, H58, H61) can be cleared for a slot.</li>
</ul>
<p class="muted">Full working: <a href="{prefix}{VERDICT}">H61 verdict</a> &middot; <a href="{prefix}docs/research/h61-hypotheses-preregistered.md">preregistration</a> &middot; <a href="{prefix}evidence/h61_candidates.json">candidate adjudication</a> &middot; <a href="{prefix}evidence/h61_build.json">build evidence</a> &middot; <a href="{prefix}evidence/h61_uniqueness.json">uniqueness</a> &middot; <a href="{prefix}evidence/h61_sensitivity.json">sensitivity</a> &middot; <a href="{prefix}docs/executive-summary.html">executive summary</a>. Older candidates follow below for the record; only the file above is recommended.</p>
</article></div></div></section>
"""


def results_card(ev: dict) -> str:
    b = ev["build"]
    fa = b["frame_a"]
    order = ["H57-incumbent-80k", "H57-reemit-80k-on-novel", "H61-H-hybrid-80k", "H61-M-spacing4-80k",
             "H61-M-spacing5-80k", "H61-S", "H61-S-support-emit", "density-1000m", "density-2000m",
             "translated-10km-0km", "translated--10km-0km", "translated-0km-10km", "translated-0km--10km",
             "H57-matched-mass-strict", "uniform-random-matched"]
    rows = "".join(
        f"<tr><td>{esc(k)}</td><td>{fa[k]['mass']:,}</td><td>{f4(fa[k]['pooled']['score'])}</td>"
        f"<td>{f4(fa[k]['pooled']['credit_per_dot'])}</td>"
        + "".join(f"<td>{f4(fa[k]['folds'][f]['score'])}</td>" for f in ("NW", "NE", "SW", "SE"))
        + "</tr>"
        for k in order
    )
    dec = b["decisions"]
    drows = "".join(
        f"<tr><td>{esc(k)}</td><td>{v['fold_wins']}/4</td><td>[{v['bootstrap_vs_incumbent']['ci95'][0]:+.4f}, "
        f"{v['bootstrap_vs_incumbent']['ci95'][1]:+.4f}]</td><td>{'yes' if v['numeric_pass'] else 'no'}</td></tr>"
        for k, v in dec.items()
    )
    fb = b["frame_b"]["pooled"]
    a = b["artifact"]
    files = (
        f'<p class="fine"><span class="tag fail">DO NOT SUBMIT</span> H61-S research files: '
        f'<a href="{esc(a["all_finite"]["path"])}" download>all-finite .tif</a> &middot; '
        f'<a href="{esc(a["nan_outside"]["path"])}" download>NaN-outside twin</a> &middot; '
        f'<a href="{esc(a["zip"]["path"])}" download>.zip</a> &middot; SHA-256 (all-finite) '
        f'<span class="hash">{esc(a["all_finite"]["sha256"])}</span></p>'
    )
    return f"""<article class="card span-12" id="h61"><h2>H61 &mdash; frozen holdout result (NO SLOT)</h2>{files}
<p>Frame A: SGMC-off proxy in the four frozen macrofold cores; every pooled score cross-checked against <code>distance_weighted_tversky</code>. Preregistered before any H61 code: <a href="docs/research/h61-hypotheses-preregistered.md">h61-hypotheses-preregistered.md</a>.</p>
<div style="overflow-x:auto"><table><thead><tr><th>Arm</th><th>N</th><th>pooled DTI</th><th>credit/dot</th><th>NW</th><th>NE</th><th>SW</th><th>SE</th></tr></thead><tbody>{rows}</tbody></table></div>
<h3>Decision gates vs the H57 incumbent</h3>
<div style="overflow-x:auto"><table><thead><tr><th>Candidate</th><th>fold wins</th><th>16-subtile bootstrap 95&nbsp;% CI (candidate &minus; H57)</th><th>numeric gates pass</th></tr></thead><tbody>{drows}</tbody></table></div>
<p>Frame B (supplied catalogue withheld per macrofold): H61-S {f4(fb['H61-S'])}, best density {f4(fb['density-best'])}, translated corridors {f4(fb['translated-mean'])}, H57 at matched mass {f4(fb['H57-matched'])}. Diagnostics, sensitivity and the corrected metric algebra: <a href="{VERDICT}">H61 verdict</a>.</p></article>
"""


def adjudication_card(ev: dict) -> str:
    c = ev["cands"]
    rows = []
    for name, r in c["candidates"].items():
        g = r["frozen_gate"]
        gate = f4(g["frozen_gate_pooled_dti"]) if g and g.get("frozen_gate_pooled_dti") is not None else "&ndash;"
        folds = " / ".join(f4(v) for v in r["frame_a_folds"].values())
        rows.append(
            f"<tr><td>{esc(name)}</td><td>{r['dots']:,}</td><td>{r['dots_on_prior_union']:,}</td>"
            f"<td>{'yes' if r['eligible_charter_item_2'] else 'no'}</td><td>{gate}</td>"
            f"<td>{f4(r['frame_a_full_pooled'])}</td><td>{f4(r['frame_a_core_pooled'])}</td><td>{folds}</td>"
            f"<td>{r['dots_within_300m_of_catalogue']:,}</td></tr>"
        )
    return f"""<article class="card span-12" id="h61-adjudication"><h2>Which file to submit &mdash; merge-time adjudication (H61)</h2>
<p>Two sessions merged new candidates while H61 ran, and main ended up recommending two different files. Rule: eligible only with zero dots on the 61-artifact prior union (charter item 2); ranked by the repository&rsquo;s frozen gate (from <a href="{esc(c['frozen_gate_source'])}">the H60 receipt</a>), confirmed with H61&rsquo;s frame A (false positives charged on every dot). Recommended: <b>{esc(c['recommended']['name'])}</b>; both instruments agree on first place: <b>{'yes' if c['instruments_agree_on_first'] else 'NO'}</b>. Source: <a href="evidence/h61_candidates.json">h61_candidates.json</a>.</p>
<div style="overflow-x:auto"><table><thead><tr><th>File</th><th>dots</th><th>prior pixels reused</th><th>eligible</th><th>frozen gate</th><th>frame A pooled</th><th>frame A cores</th><th>NW / NE / SW / SE</th><th>dots &le;300&nbsp;m from catalogue</th></tr></thead><tbody>{''.join(rows)}</tbody></table></div></article>
"""


def methods_card(ev: dict) -> str:
    b = ev["build"]
    z = b["pipeline"]["zbz"]["gmm_log10_eta"]
    t = b["pipeline"]["triangle"]
    lr = b["pipeline"]["lineations"]
    return f"""<article class="card span-12" id="h61-methods"><h2>H61 seismic-lineation method and sources</h2>
<ul class="list">
<li><b>Catalogue:</b> USGS ANSS ComCat via the FDSN event service (<code>https://earthquake.usgs.gov/fdsnws/event/1/query</code>), hash-pinned extract SHA-256 <span class="hash">{esc(b['inputs']['comcat']['sha256'])}</span>. Field list: <a href="https://earthquake.usgs.gov/earthquakes/feed/v1.0/csv.php">USGS CSV format page</a>; <b>flag:</b> its <code>horizontalError</code> link (<code>data/comcat/data-eventterms.php#horizontalError</code>) currently redirects to the GeoJSON feed page, so the definition quoted in the preregistration (&ldquo;largest projection of the three principal errors on a horizontal plane&rdquo;, in km) could not be re-read at a live official URL on 2026-10-07. USGS-authored data are public domain (<a href="https://www.usgs.gov/information-policies-and-instructions/copyrights-and-credits">USGS copyrights and credits</a>); contributions from non-USGS networks are not necessarily USGS-authored, so challenge-use rights remain unresolved.</li>
<li><b>Declustering:</b> Zaliapin &amp; Ben-Zion (2013), JGR 118, 2847&ndash;2864, doi:10.1002/jgrb.50179 &mdash; nearest-neighbour proximity with d<sub>f</sub>&nbsp;=&nbsp;1.6, b&nbsp;=&nbsp;1; two-component Gaussian mixture threshold log<sub>10</sub>&eta;<sub>0</sub>&nbsp;=&nbsp;{z['threshold']:.3f}.</li>
<li><b>Background screen:</b> 2-D triangle areas vs a coordinate-permuted reference (5th percentile, {t['kept']:,} of {t['events_in']:,} kept). <b>Unverified</b> 2-D adaptation of Ouillon &amp; Sornette (2011), JGR 116, B02306, doi:10.1029/2010JB007752.</li>
<li><b>Lineations:</b> 12-neighbour inverse-variance covariance minus the mean squared horizontal error (2-D analogue of Ouillon, Ducorbier &amp; Sornette 2008, JGR 113, B01306, doi:10.1029/2007JB005032); {lr['accepted_neighbourhoods']} neighbourhoods accepted, {lr['merged_lineations']} after merging. Not an ACLUD reproduction (Wang et al. 2013, arXiv:1304.6912): ComCat gives a scalar horizontal error, not a covariance.</li>
<li><b>Corridors:</b> epicentral (half-width = location error, 0.2&ndash;1&nbsp;km) and two up-dip copies offset by z/tan&nbsp;60&deg; (half-width propagates depth error and &plusmn;10&deg; dip, 0.2&ndash;2&nbsp;km); dots snapped every 300&nbsp;m to the H57 ridge across the corridor.</li>
<li><b>Prior corpus:</b> <code>scripts/fetch_prior_corpus.py</code> &mdash; 50 hash-verified pins plus every TIFF in the 54 sibling repositories (receipt <a href="evidence/h61_prior_corpus_receipt.json">h61_prior_corpus_receipt.json</a>).</li>
</ul></article>
"""


def _page(title: str, body: str, *, root: str = "../") -> str:
    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="description" content="{esc(title)}"><title>{esc(title)} &middot; GEMSDOE50</title><link rel="stylesheet" href="{root}site.css"></head>
<body><a class="skip" href="#start">Skip to content</a><header class="site-head"><div class="shell"><nav class="nav" aria-label="Main navigation"><a class="brand" href="{root}index.html">GEMSDOE50 / Research</a><div class="links"><a href="{root}index.html">Overview</a><a href="{root}results.html">Results</a><a href="{root}methods.html">Methods &amp; sources</a><a href="{root}submission.html">Submission guide</a><a href="{root}docs/how-to-submit.html">How to submit</a></div></nav></div></header>
{body}
</body></html>
"""


def how_to_submit(ev: dict) -> str:
    rec = ev["cands"]["recommended"]
    tif = Path(rec["artifact"]).name
    zip_txt = (f' (or the <a href="../{esc(rec["zip"])}" download>.zip</a>; the portal accepts a .tif or a .zip '
               'holding one GeoTIFF)') if rec["zip"] else ""
    body = start_band(ev, prefix="../") + f"""<section class="main"><div class="shell"><div class="grid"><article class="card span-12" id="steps"><h2>Exactly how to submit</h2>
<ol class="list">
<li><b>Download</b> <a href="../{esc(rec['artifact'])}" download><code>{esc(tif)}</code></a>{zip_txt}.</li>
<li><b>Check the bytes</b> (optional but recommended). The SHA-256 must be <span class="hash">{esc(rec['sha256'])}</span>.<br>macOS/Linux: <code>shasum -a 256 {esc(tif)}</code> &middot; Windows PowerShell: <code>Get-FileHash {esc(tif)} -Algorithm SHA256</code></li>
<li><b>Open</b> the <a href="{COMPETITION}">DOE GEMS competition page</a>, sign in, and go to the submissions tab. Read the <a href="{FORMAT_PAGE}">submission-format page</a> once: single-band GeoTIFF, same CRS (EPSG:32611), shape and geotransform as the training data, values between 0 and 1.</li>
<li><b>Upload</b> the file. If the form asks for a name, use <code>{esc(rec['entry_name'])}</code>.</li>
<li><b>Paste the note</b> (optional field): <q>{esc(rec['note'])}</q></li>
<li><b>Submit</b>, then record the public score and the submission time in <code>registry/submissions.json</code> so later sessions can calibrate against a real organizer number.</li>
</ol>
<h3>If the portal says &ldquo;Predicted values must be in range [0, 1]&rdquo;</h3>
<p>That message appears when any cell the validator reads is outside [0,&nbsp;1] &mdash; and a NaN counts, because <code>NaN &le; 1</code> is false. This file has no NaN, no nodata sentinel and only the values 0 and 1 in all 12,279,160 cells, so the error cannot come from it. If you see it anyway, you uploaded a different file: compare the SHA-256 above. Do not upload <code>-nan</code> twins or older files.</p>
<h3>Limits to keep in mind</h3>
<ul class="list"><li>Three submissions per week; spend one only on a file that leads the current holdout (this one does).</li>
<li>Read <a href="{RULES_PDF}">the official rules</a> &sect;3.4 on how many entries one participating entity may hold, and the generative-AI disclosure requirement, before submitting.</li>
<li>The score you see is the public split; the private split decides prizes.</li></ul>
</article></div></div></section>"""
    return _page("How to submit the recommended GEMS GeoTIFF", body)


def executive_summary(ev: dict) -> str:
    n = numbers(ev)
    rec = n["rec"]
    body = start_band(ev, prefix="../") + f"""<section class="main"><div class="shell"><div class="grid"><article class="card span-12"><h2>Executive summary</h2>
<ol class="list">
<li><b>Submit <code>{esc(rec['entry_name'])}</code></b> (download above). It is the highest-ranked file that reuses no prior prediction pixel: frozen gate {f4(n['rec_gate'])} vs H57 {f4(n['h57_gate'])}; both of this repository&rsquo;s instruments agree on the order. Expect roughly the low 0.2s on the hidden labels &mdash; a proxy, not a promise.</li>
<li><b>The mandated seismic-lineation map (H61) was built and failed</b> its preregistered tests: {n['h61s_n']} dots, DTI {f4(n['h61s'])}; it loses to random dots, to translated corridors, and to smoothed density on withheld faults.</li>
<li><b>Why 0.2778 happened (GEMSDOE32 H33-B2):</b> removing 6,436 dots that sat next to the given faults removed false-positive cost without losing credit &mdash; a dot-economy gain, not a better detector. With the corrected algebra it implies about 5,220 hidden credit and about 13,340 hidden truth cells.</li>
<li><b>Can 0.3774 be beaten?</b> Not with anything measured so far: it needs about 10,500 hidden credit at 80,000&ndash;90,000 dots.</li>
<li><b>Next:</b> hydrothermal-feature proximity and fault step-over priors, an emitter that prices the corrected metric, and pruning near-catalogue dots (the B2 lesson) &mdash; see the <a href="../{VERDICT}">H61 verdict &sect;8</a>.</li>
</ol></article></div></div></section>"""
    return _page("Executive summary", body)


def docs_index(ev: dict) -> str:
    body = start_band(ev, prefix="../") + """<section class="main"><div class="shell"><div class="grid"><article class="card span-12"><h2>Archive</h2>
<p>Everything else in this <code>docs/</code> folder is historical material from earlier sessions, kept for audit. Do not upload any other file from it: <a href="report.html">legacy report</a> &middot; <a href="research/">research notes</a> &middot; <a href="downloads/">all downloads</a>.</p>
</article></div></div></section>"""
    return _page("GEMSDOE50 documents", body)


H57_RETIRE = (
    ("Download the current research candidate GeoTIFF (H57) &mdash; one click",
     "Former candidate (H57) &mdash; superseded, do not submit"),
    ("Current candidate (H57): download, name, and note",
     "Former candidate (H57) &mdash; superseded, do not submit"),
    ("<title>Submission guide (H57 current) &middot; GEMSDOE50</title>",
     "<title>Submission guide &middot; GEMSDOE50</title>"),
    ("<title>Submission guide (H57 current) · GEMSDOE50</title>",
     "<title>Submission guide · GEMSDOE50</title>"),
)
YES_H57 = "<b>Yes &mdash; you may download this file and submit it as your entry.</b>"


def retire_h57(text: str, ev: dict) -> str:
    """Mark the preserved H57 bands as superseded (they still said "Yes, submit")."""
    n = numbers(ev)
    for old, new in H57_RETIRE:
        text = text.replace(old, new)
    return text.replace(
        YES_H57,
        f"<b>Superseded &mdash; do not submit this file.</b> It reuses {n['h57_reuse']:,} prior prediction "
        f"pixels (charter item 2) and ranks below <code>{esc(n['rec']['entry_name'])}</code> on the frozen gate "
        f"({f4(n['h57_gate'])} vs {f4(n['rec_gate'])}); see the start-here band. The text below is kept as "
        "the original record.",
    )


def main() -> int:
    ev = load()
    index = ROOT / "index.html"
    text = index.read_text(encoding="utf-8")
    if START_MARK in text:
        raise SystemExit("index.html already has the start band; run build_h55_site.py and build_h58_site.py first")
    if H57_SECTION not in text or SKIP_OLD not in text:
        raise SystemExit("index.html anchors missing")
    text = text.replace(SKIP_OLD, SKIP_NEW, 1)
    text = text.replace(H57_SECTION, start_band(ev) + H57_SECTION, 1)
    text = text.replace(COLLAPSE_OLD, COLLAPSE_NEW)
    text = retire_h57(text, ev)
    if NOCOPY_OLD in text:
        n = numbers(ev)
        text = text.replace(
            NOCOPY_OLD,
            "<b>Erratum (H61, full corpus):</b> this band originally said that no pixel of any prior "
            "submission is copied (maximum full-pixel IoU 0.0248 against 26 pinned artifacts). Against all "
            f"{n['priors']} distinct prior files H57 is still not a copy (largest Jaccard {f4(n['h57_j'])}, with "
            f"our own never-submitted H56), but {n['union_frac']*100:.0f}&nbsp;% of its dots share a pixel with "
            "at least one registered prior file; see the start-here band above.",
        )
    if STALE_0386 in text:
        n = numbers(ev)
        text = text.replace(
            STALE_0386,
            "Not with the evidence in hand. The 0.386 figure came from H56&rsquo;s assumed transfer factor, "
            "which the scored corpus refutes (fitted R&sup2; = &minus;0.87); it is retracted. The best validated "
            f"file, H57 (holdout {f4(n['inc'])}), has an expected hidden score of about 0.23 with P(&gt;&nbsp;0.3774) "
            "&asymp; 4&nbsp;%; beating 0.3774 at 80,000 dots needs about 10,500 hidden credit under the corrected "
            "metric algebra. H55, H53-A, H58-S1 and every H61 arm failed their frozen gates.",
        )
    index.write_text(text, encoding="utf-8")

    sub = ROOT / "submission.html"
    s = sub.read_text(encoding="utf-8")
    s = s.replace(SKIP_OLD, SKIP_NEW, 1)
    if H57_SECTION in s:
        s = s.replace(H57_SECTION, start_band(ev) + H57_SECTION, 1)
    s = s.replace(COLLAPSE_OLD, COLLAPSE_NEW)
    s = retire_h57(s, ev)
    sub.write_text(s, encoding="utf-8")

    res = ROOT / "results.html"
    r = res.read_text(encoding="utf-8")
    if RESULTS_ANCHOR not in r:
        raise SystemExit("results.html anchor missing")
    res.write_text(r.replace(RESULTS_ANCHOR, adjudication_card(ev) + results_card(ev) + RESULTS_ANCHOR, 1),
                   encoding="utf-8")

    met = ROOT / "methods.html"
    m = met.read_text(encoding="utf-8")
    if METHODS_ANCHOR not in m:
        raise SystemExit("methods.html anchor missing")
    met.write_text(m.replace(METHODS_ANCHOR, methods_card(ev) + METHODS_ANCHOR, 1), encoding="utf-8")

    (ROOT / "docs/how-to-submit.html").write_text(how_to_submit(ev), encoding="utf-8")
    (ROOT / "docs/executive-summary.html").write_text(executive_summary(ev), encoding="utf-8")
    (ROOT / "docs/index.html").write_text(docs_index(ev), encoding="utf-8")
    print("H61 start band, result/method cards, errata and docs/ pages written.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
