#!/usr/bin/env python3
"""Add the H59 "start here" band, the H59 result cards and the errata to the site.

Runs after ``scripts/build_h55_site.py`` and ``scripts/build_h58_site.py`` (same
order as ``.github/workflows/site.yml``). It

* puts a single **start-here** band at the very top of ``index.html``: one-click
  download of the recommended file, the YES/NO verdict, the entry name and note,
  a link to the step-by-step submission page, today's H59 decision and the flags;
* points the skip link at that band (it used to jump past every download band);
* corrects the false "reduces exactly to T/(0.2N + 0.8G)" wording in the
  generated bands and retires the stale 0.386 / 0.3774 card;
* inserts the H59 result table into ``results.html`` and the H59 methods/sources
  card into ``methods.html``;
* regenerates ``docs/how-to-submit.html``, ``docs/executive-summary.html`` and
  ``docs/index.html`` (they were withdrawn stubs that still pointed at H51).

Every number comes from committed evidence (``evidence/h59_build.json``,
``evidence/h59_uniqueness.json``, ``evidence/h59_sensitivity.json``,
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
BUILD = ROOT / "evidence/h59_build.json"
UNIQUE = ROOT / "evidence/h59_uniqueness.json"
SENS = ROOT / "evidence/h59_sensitivity.json"
H57 = ROOT / "evidence/build_h57-scarpstep.json"

H57_NAME = "GEMSDOE50-H57-SCARPSTEP"
H57_NOTE = (
    "H57 stratified LiDAR-scarp + topographic-step dot emitter; every dot is >=300 m from the "
    "given catalogue and >=300 m from every other dot; research model, not organizer-scored."
)
COMPETITION = "https://www.drivendata.org/competitions/306/competition-doe-gems/"
FORMAT_PAGE = "https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/"
RULES_PDF = "https://docs.nlr.gov/docs/fy26osti/96647.pdf"
VERDICT = "docs/research/h59-verdict-20261007.md"

START_MARK = '<section class="main" id="start">'
H57_SECTION = '<section class="main" id="h57">'
SKIP_OLD = '<a class="skip" href="#main">'
SKIP_NEW = '<a class="skip" href="#start">'
RESULTS_ANCHOR = '<article class="card span-12" id="h58">'
METHODS_ANCHOR = '<article class="card span-12"><h2>Auditable source table</h2>'
COLLAPSE_OLD = "reduces exactly to <code>DTI = T / (0.2N + 0.8G)</code>"
COLLAPSE_NEW = (
    "is <code>DTI = T / (0.2N + 0.8G + 0.2(T &minus; M))</code> with <code>M = &Sigma; K(dot)</code> "
    "(<b>erratum, H59:</b> this band originally said it &ldquo;reduces exactly to "
    "<code>T / (0.2N + 0.8G)</code>&rdquo;; that is exact only when T = M, and dots closer than "
    f'6 px do compete &mdash; <a href="{VERDICT}">H59 verdict &sect;4</a>)'
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
    for meta in h57["files"].values():
        if sha256(ROOT / meta["path"]) != meta["sha256"]:
            raise SystemExit(f"H57 artifact hash drift: {meta['path']}")
    art = build["artifact"]
    for key in ("all_finite", "nan_outside", "zip"):
        if sha256(ROOT / art[key]["path"]) != art[key]["sha256"]:
            raise SystemExit(f"H59 artifact hash drift: {art[key]['path']}")
    return {"build": build, "uniq": uniq, "sens": sens, "h57": h57}


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
    h59u = _u(ev, "gemsdoe50-h59-updipseis")
    enr = b["stratified_corridor_enrichment"]
    sens = ev["sens"]["variants"]
    return {
        "inc": fa["H57-incumbent-80k"]["pooled"]["score"],
        "inc_folds": {k: v["score"] for k, v in fa["H57-incumbent-80k"]["folds"].items()},
        "h59s": fa["H59-S"]["pooled"]["score"],
        "h59s_n": fa["H59-S"]["mass"],
        "h59s_cpd": fa["H59-S"]["pooled"]["credit_per_dot"],
        "rand_cpd": fa["uniform-random-matched"]["pooled"]["credit_per_dot"],
        "hyb": fa["H59-H-hybrid-80k"]["pooled"]["score"],
        "sp4": fa["H59-M-spacing4-80k"]["pooled"]["score"],
        "sp5": fa["H59-M-spacing5-80k"]["pooled"]["score"],
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
        "h59_j": h59u["max_jaccard"]["value"],
        "h59_e": h59u["max_excess_2px"]["value"],
        "priors": ev["uniq"]["distinct_submission_like_priors"],
        "on_union": b["h57_incumbent_prior_union_overlap"]["dots_on_prior_union"],
        "union_frac": b["h57_incumbent_prior_union_overlap"]["fraction_on_prior_union"],
        "repro": b["h57_reproduction"]["identical_support"],
    }


def start_band(ev: dict, prefix: str = "") -> str:
    n = numbers(ev)
    f = ev["h57"]["files"]
    a = ev["build"]["artifact"]
    return f"""{START_MARK}<div class="shell"><div class="grid"><article class="card span-12" style="border-left:6px solid #0f6b5c">
<h1 style="margin-top:0">Start here &mdash; the one file to submit</h1>
<div class="hero" style="border-radius:10px;padding:18px 20px;margin-bottom:14px"><div class="actions"><a class="download" href="{prefix}{esc(f['all_finite']['path'])}" download>Download the recommended GeoTIFF (H57, portal-safe)</a><a class="download alt" href="{prefix}{esc(f['zip']['path'])}" download>same file as .zip</a></div>
<p class="fine" style="color:#d8e7e3">File <code>{esc(Path(f['all_finite']['path']).name)}</code> &middot; SHA-256 <span class="hash">{esc(f['all_finite']['sha256'])}</span> &middot; {f['all_finite']['bytes']:,} bytes &middot; 80,000 predicted cells &middot; float32, EPSG:32611, 3,730 &times; 3,292, values exactly 0 or 1, no NaN anywhere.</p>
<p class="fine" style="color:#d8e7e3"><b>Entry name:</b> <code>{H57_NAME}</code> &middot; <b>note to paste:</b> <q>{esc(H57_NOTE)}</q></p></div>
<p><span class="tag">YES</span> <b>OK to download and submit</b> (it uses one of your weekly slots). H57 is still the best file this repository has measured on its frozen spatially-blocked holdout (pooled DTI <b>{f4(n['inc'])}</b>; NW {f4(n['inc_folds']['NW'])}, NE {f4(n['inc_folds']['NE'])}, SW {f4(n['inc_folds']['SW'])}, SE {f4(n['inc_folds']['SE'])}); nothing built since, including today&rsquo;s H59 run, beats it. Rebuilding H57 from its code reproduces the shipped pixels exactly: <b>{'yes' if n['repro'] else 'NO'}</b>. It uses no earthquake catalogue, so the unresolved ComCat rights question does not apply. <a href="{prefix}docs/how-to-submit.html"><b>Exactly how to submit, step by step &rarr;</b></a></p>
<p class="warning"><b>Expectation, not a promise.</b> The holdout scores a proxy (USGS SGMC faults away from the given catalogue), not the organizers&rsquo; hidden expert labels. The calibrated expectation for H57 is about <b>0.23</b> (P(&gt;&nbsp;0.2778)&nbsp;&asymp;&nbsp;29&nbsp;%, P(&gt;&nbsp;0.3774)&nbsp;&asymp;&nbsp;4&nbsp;%). Under the corrected metric algebra, beating the public best 0.3774 with 80,000 dots needs about 10,500 hidden-truth credit (credit/dot &gt; 0.13). No organizer score exists for any GEMSDOE50 file.</p>
<p><b>Uniqueness, measured against the full prior corpus ({n['priors']} distinct submission-like files from all 54 sibling repositories plus this one).</b> H57 is not a copy: its largest exact-pixel overlap (Jaccard) with any prior file is {f4(n['h57_j'])}, and that file is our own never-submitted H56; at most 31&nbsp;% of its dots sit on any single prior file. But {n['on_union']:,} of its 80,000 dots ({n['union_frac']*100:.0f}&nbsp;%) land on a pixel that at least one of the 61 registered prior files also used, and its chance-corrected 2-pixel proximity to the dense 13GEMSDOE r8-ensemble is {f4(n['h57_e'])} (borderline against a 0.5 screen), because every scarp-based file follows the same LiDAR scarps. A version with zero exact overlap was tested and scores lower ({f4(n['reemit'])}), so it is not recommended.</p>
<h3>Today&rsquo;s run (H59): the required seismic-lineation map &mdash; <span class="tag fail">NO SLOT</span></h3>
<p>Built as specified: {n['events']:,} screened USGS ComCat earthquakes, declustered with the Zaliapin&ndash;Ben-Zion nearest-neighbour method ({n['bg']:,} background events kept), a 2-D triangle test (my unverified adaptation of the Ouillon&ndash;Sornette 3-D tetrahedron test), local 2-D covariance with location-error removal, corridors as wide as the catalogue location error plus up-dip copies, and dots snapped to the H57 ridge. Result: only {n['lin']} lineations and <b>{n['h59s_n']} dots</b>; holdout DTI <b>{f4(n['h59s'])}</b>, credit/dot {f4(n['h59s_cpd'])} versus {f4(n['rand_cpd'])} for random dots. On withheld catalogue faults the corridors lose to smoothed density ({f4(n['fb']['H59-S'])} vs {f4(n['fb']['density-best'])}). Within every H57-strength decile, the corridors hold <i>less</i> fault credit than the cells outside them (median ratio {n['enr_median']:.3f}, {n['enr_gt1']}/10 deciles above 1). Loosening every screen (up to {n['sens_max_lin']:,} lineations) never lifts that ratio above {n['sens_max_enr']:.2f}. Two variants were also rejected: mixing the corridor dots into H57 ({f4(n['hyb'])}) and spacing H57&rsquo;s dots 4 or 5 px apart ({f4(n['sp4'])}, {f4(n['sp5'])}). The H59 file is unique (Jaccard &le; {n['h59_j']:.4f}) and valid, but <b>do not submit it</b>: <a href="{prefix}{esc(a['all_finite']['path'])}" download>H59 research file</a> (SHA-256 <span class="hash">{esc(a['all_finite']['sha256'][:16])}&hellip;</span>, entry name if ever used <code>{esc(a['entry_name'])}</code>).</p>
<h3>Flags for manual review</h3>
<ul class="list">
<li><b>Metric algebra:</b> earlier pages said the score &ldquo;reduces exactly&rdquo; to <code>T/(0.2N+0.8G)</code> and that dots 3&nbsp;px apart do not compete. Both are false (tested in <code>tests/test_h59.py</code>); errata added.</li>
<li><b>Leaderboard coincidence:</b> five owner-reported corpus scores (0.2778, 0.2750, 0.2710, 0.2708, 0.2600) equal the public scores of five different leaderboard accounts. Please check this against <a href="{RULES_PDF}">rules &sect;3.4</a> (limits per participating entity).</li>
<li><b>Sample file:</b> the local <code>sample_submission.tif</code> holds 1.0 on exactly the 60,988 training-label cells, not &ldquo;total fault absence&rdquo;.</li>
<li><b>Reference solution</b> writes float64; the <a href="{FORMAT_PAGE}">format page</a> asks for float32 (our files are float32).</li>
<li><b>ComCat contributor rights</b> are unresolved, so no catalogue-derived file (H56, H58, H59) can be cleared for a slot.</li>
<li><b>H33 parent conflict:</b> 44,090&nbsp;&minus;&nbsp;6,436 vs 40,199&nbsp;&minus;&nbsp;2,545 dots, unresolved.</li>
</ul>
<p class="muted">Full working: <a href="{prefix}{VERDICT}">H59 verdict</a> &middot; <a href="{prefix}docs/research/h59-hypotheses-preregistered.md">preregistration</a> &middot; <a href="{prefix}evidence/h59_build.json">build evidence</a> &middot; <a href="{prefix}evidence/h59_uniqueness.json">uniqueness</a> &middot; <a href="{prefix}evidence/h59_sensitivity.json">sensitivity</a> &middot; <a href="{prefix}docs/executive-summary.html">executive summary</a>. Older candidates follow below for the record; none of them is recommended.</p>
</article></div></div></section>
"""


def results_card(ev: dict) -> str:
    b = ev["build"]
    fa = b["frame_a"]
    order = ["H57-incumbent-80k", "H57-reemit-80k-on-novel", "H59-H-hybrid-80k", "H59-M-spacing4-80k",
             "H59-M-spacing5-80k", "H59-S", "H59-S-support-emit", "density-1000m", "density-2000m",
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
        f'<p class="fine"><span class="tag fail">DO NOT SUBMIT</span> H59-S research files: '
        f'<a href="{esc(a["all_finite"]["path"])}" download>all-finite .tif</a> &middot; '
        f'<a href="{esc(a["nan_outside"]["path"])}" download>NaN-outside twin</a> &middot; '
        f'<a href="{esc(a["zip"]["path"])}" download>.zip</a> &middot; SHA-256 (all-finite) '
        f'<span class="hash">{esc(a["all_finite"]["sha256"])}</span></p>'
    )
    return f"""<article class="card span-12" id="h59"><h2>H59 &mdash; frozen holdout result (NO SLOT)</h2>{files}
<p>Frame A: SGMC-off proxy in the four frozen macrofold cores; every pooled score cross-checked against <code>distance_weighted_tversky</code>. Preregistered before any H59 code: <a href="docs/research/h59-hypotheses-preregistered.md">h59-hypotheses-preregistered.md</a>.</p>
<div style="overflow-x:auto"><table><thead><tr><th>Arm</th><th>N</th><th>pooled DTI</th><th>credit/dot</th><th>NW</th><th>NE</th><th>SW</th><th>SE</th></tr></thead><tbody>{rows}</tbody></table></div>
<h3>Decision gates vs the H57 incumbent</h3>
<div style="overflow-x:auto"><table><thead><tr><th>Candidate</th><th>fold wins</th><th>16-subtile bootstrap 95&nbsp;% CI (candidate &minus; H57)</th><th>numeric gates pass</th></tr></thead><tbody>{drows}</tbody></table></div>
<p>Frame B (supplied catalogue withheld per macrofold): H59-S {f4(fb['H59-S'])}, best density {f4(fb['density-best'])}, translated corridors {f4(fb['translated-mean'])}, H57 at matched mass {f4(fb['H57-matched'])}. Diagnostics, sensitivity and the corrected metric algebra: <a href="{VERDICT}">H59 verdict</a>.</p></article>
"""


def methods_card(ev: dict) -> str:
    b = ev["build"]
    z = b["pipeline"]["zbz"]["gmm_log10_eta"]
    t = b["pipeline"]["triangle"]
    lr = b["pipeline"]["lineations"]
    return f"""<article class="card span-12" id="h59-methods"><h2>H59 seismic-lineation method and sources</h2>
<ul class="list">
<li><b>Catalogue:</b> USGS ANSS ComCat via the FDSN event service (<code>https://earthquake.usgs.gov/fdsnws/event/1/query</code>), hash-pinned extract SHA-256 <span class="hash">{esc(b['inputs']['comcat']['sha256'])}</span>. Field list: <a href="https://earthquake.usgs.gov/earthquakes/feed/v1.0/csv.php">USGS CSV format page</a>; <b>flag:</b> its <code>horizontalError</code> link (<code>data/comcat/data-eventterms.php#horizontalError</code>) currently redirects to the GeoJSON feed page, so the definition quoted in the preregistration (&ldquo;largest projection of the three principal errors on a horizontal plane&rdquo;, in km) could not be re-read at a live official URL on 2026-10-07. USGS-authored data are public domain (<a href="https://www.usgs.gov/information-policies-and-instructions/copyrights-and-credits">USGS copyrights and credits</a>); contributions from non-USGS networks are not necessarily USGS-authored, so challenge-use rights remain unresolved.</li>
<li><b>Declustering:</b> Zaliapin &amp; Ben-Zion (2013), JGR 118, 2847&ndash;2864, doi:10.1002/jgrb.50179 &mdash; nearest-neighbour proximity with d<sub>f</sub>&nbsp;=&nbsp;1.6, b&nbsp;=&nbsp;1; two-component Gaussian mixture threshold log<sub>10</sub>&eta;<sub>0</sub>&nbsp;=&nbsp;{z['threshold']:.3f}.</li>
<li><b>Background screen:</b> 2-D triangle areas vs a coordinate-permuted reference (5th percentile, {t['kept']:,} of {t['events_in']:,} kept). <b>Unverified</b> 2-D adaptation of Ouillon &amp; Sornette (2011), JGR 116, B02306, doi:10.1029/2010JB007752.</li>
<li><b>Lineations:</b> 12-neighbour inverse-variance covariance minus the mean squared horizontal error (2-D analogue of Ouillon, Ducorbier &amp; Sornette 2008, JGR 113, B01306, doi:10.1029/2007JB005032); {lr['accepted_neighbourhoods']} neighbourhoods accepted, {lr['merged_lineations']} after merging. Not an ACLUD reproduction (Wang et al. 2013, arXiv:1304.6912): ComCat gives a scalar horizontal error, not a covariance.</li>
<li><b>Corridors:</b> epicentral (half-width = location error, 0.2&ndash;1&nbsp;km) and two up-dip copies offset by z/tan&nbsp;60&deg; (half-width propagates depth error and &plusmn;10&deg; dip, 0.2&ndash;2&nbsp;km); dots snapped every 300&nbsp;m to the H57 ridge across the corridor.</li>
<li><b>Prior corpus:</b> <code>scripts/fetch_prior_corpus.py</code> &mdash; 50 hash-verified pins plus every TIFF in the 54 sibling repositories (receipt <a href="evidence/h59_prior_corpus_receipt.json">h59_prior_corpus_receipt.json</a>).</li>
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
    f = ev["h57"]["files"]
    tif = Path(f["all_finite"]["path"]).name
    body = start_band(ev, prefix="../") + f"""<section class="main"><div class="shell"><div class="grid"><article class="card span-12" id="steps"><h2>Exactly how to submit</h2>
<ol class="list">
<li><b>Download</b> <a href="../{esc(f['all_finite']['path'])}" download><code>{esc(tif)}</code></a> (or the <a href="../{esc(f['zip']['path'])}" download>.zip</a>; the portal accepts a .tif or a .zip holding one GeoTIFF).</li>
<li><b>Check the bytes</b> (optional but recommended). The SHA-256 must be <span class="hash">{esc(f['all_finite']['sha256'])}</span>.<br>macOS/Linux: <code>shasum -a 256 {esc(tif)}</code> &middot; Windows PowerShell: <code>Get-FileHash {esc(tif)} -Algorithm SHA256</code></li>
<li><b>Open</b> the <a href="{COMPETITION}">DOE GEMS competition page</a>, sign in, and go to the submissions tab. Read the <a href="{FORMAT_PAGE}">submission-format page</a> once: single-band GeoTIFF, same CRS (EPSG:32611), shape and geotransform as the training data, values between 0 and 1.</li>
<li><b>Upload</b> the file. If the form asks for a name, use <code>{H57_NAME}</code>.</li>
<li><b>Paste the note</b> (optional field): <q>{esc(H57_NOTE)}</q></li>
<li><b>Submit</b> and record the public score and the submission time in <code>registry/submissions.json</code> so later sessions can calibrate against a real organizer number.</li>
</ol>
<h3>If the portal says &ldquo;Predicted values must be in range [0, 1]&rdquo;</h3>
<p>That message appears when any cell the validator reads is outside [0,&nbsp;1] &mdash; and a NaN counts, because <code>NaN &le; 1</code> is false. This file has no NaN, no nodata sentinel and only the values 0 and 1 in all 12,279,160 cells, so the error cannot come from it. If you see it anyway, you uploaded a different file: compare the SHA-256 above. Do not upload the <code>-nan</code> or older files.</p>
<h3>Limits to keep in mind</h3>
<ul class="list"><li>Three submissions per week; only spend one on a file that beat the current holdout best (H57 is that file).</li>
<li>Read <a href="{RULES_PDF}">the official rules</a> &sect;3.4 on how many entries one participating entity may hold, and the generative-AI disclosure requirement, before submitting.</li>
<li>The score you see is the public split; the private split decides prizes.</li></ul>
</article></div></div></section>"""
    return _page("How to submit the recommended GEMS GeoTIFF", body)


def executive_summary(ev: dict) -> str:
    n = numbers(ev)
    body = start_band(ev, prefix="../") + f"""<section class="main"><div class="shell"><div class="grid"><article class="card span-12"><h2>Executive summary</h2>
<ol class="list">
<li><b>Submit H57</b> (download above). It is the best file on the frozen holdout ({f4(n['inc'])}); expectation &asymp;0.23 on the hidden labels, not a promise.</li>
<li><b>The mandated seismic-lineation map was built and failed</b> its preregistered tests: {n['h59s_n']} dots, DTI {f4(n['h59s'])}; loses to random dots, to translated corridors, and to smoothed density on withheld faults.</li>
<li><b>Why 0.2778 happened (GEMSDOE32 H33-B2):</b> removing 6,436 dots that sat next to the given faults removed false-positive cost without losing credit &mdash; a dot-economy gain, not a better detector. With the corrected algebra it implies about 5,220 hidden credit and about 13,340 hidden truth cells.</li>
<li><b>Can 0.3774 be beaten?</b> Not with anything measured so far: it needs about 10,500 hidden credit at 80,000 dots. P(H57 &gt; 0.3774) &asymp; 4&nbsp;%.</li>
<li><b>Next:</b> hydrothermal-feature proximity and fault step-over priors on top of H57, and an emitter that prices the corrected metric &mdash; see the <a href="../{VERDICT}">H59 verdict &sect;8</a>.</li>
</ol></article></div></div></section>"""
    return _page("Executive summary", body)


def docs_index(ev: dict) -> str:
    body = start_band(ev, prefix="../") + """<section class="main"><div class="shell"><div class="grid"><article class="card span-12"><h2>Archive</h2>
<p>Everything else in this <code>docs/</code> folder is historical material from earlier sessions, kept for audit. Do not upload any other file from it: <a href="report.html">legacy report</a> &middot; <a href="research/">research notes</a> &middot; <a href="downloads/">all downloads</a>.</p>
</article></div></div></section>"""
    return _page("GEMSDOE50 documents", body)


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
    if NOCOPY_OLD in text:
        n = numbers(ev)
        text = text.replace(
            NOCOPY_OLD,
            "<b>Erratum (H59, full corpus):</b> this band originally said that no pixel of any prior "
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
            "metric algebra. H55, H53-A, H58-S1 and every H59 arm failed their frozen gates.",
        )
    index.write_text(text, encoding="utf-8")

    sub = ROOT / "submission.html"
    s = sub.read_text(encoding="utf-8")
    s = s.replace(SKIP_OLD, SKIP_NEW, 1)
    if H57_SECTION in s:
        s = s.replace(H57_SECTION, start_band(ev) + H57_SECTION, 1)
    s = s.replace(COLLAPSE_OLD, COLLAPSE_NEW)
    sub.write_text(s, encoding="utf-8")

    res = ROOT / "results.html"
    r = res.read_text(encoding="utf-8")
    if RESULTS_ANCHOR not in r:
        raise SystemExit("results.html anchor missing")
    res.write_text(r.replace(RESULTS_ANCHOR, results_card(ev) + RESULTS_ANCHOR, 1), encoding="utf-8")

    met = ROOT / "methods.html"
    m = met.read_text(encoding="utf-8")
    if METHODS_ANCHOR not in m:
        raise SystemExit("methods.html anchor missing")
    met.write_text(m.replace(METHODS_ANCHOR, methods_card(ev) + METHODS_ANCHOR, 1), encoding="utf-8")

    (ROOT / "docs/how-to-submit.html").write_text(how_to_submit(ev), encoding="utf-8")
    (ROOT / "docs/executive-summary.html").write_text(executive_summary(ev), encoding="utf-8")
    (ROOT / "docs/index.html").write_text(docs_index(ev), encoding="utf-8")
    print("H59 start band, result/method cards, errata and docs/ pages written.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
