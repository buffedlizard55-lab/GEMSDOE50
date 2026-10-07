#!/usr/bin/env python3
"""Build the static executive-summary, results, methods, and submission pages."""

from __future__ import annotations

import argparse
import hashlib
import html
import json
from pathlib import Path
from typing import Any

import numpy as np
import rasterio

REPORT_DEFAULT = Path("evidence/results/h50s1-evaluation-20261006.json")
TIFF_DEFAULT = Path("docs/downloads/gemsdoe50-h50s1-relocated-planes-20261006-research.tif")
PINNED_SPLIT_PATH = Path(__file__).resolve().parents[1] / "evidence/holdout-v1.json"

STYLE = """
:root{color-scheme:light;--ink:#172a33;--muted:#536970;--paper:#f5f2e9;--card:#fffdf7;--line:#d4ded8;--teal:#00685e;--teal2:#dcefe9;--gold:#a96519;--red:#8b382e;--redbg:#f8e8e3;--green:#145b48;--greenbg:#e1f1e8;--blue:#163e55;--shadow:0 14px 40px rgba(23,42,51,.08)}
*{box-sizing:border-box}body{margin:0;background:var(--paper);color:var(--ink);font:16px/1.6 system-ui,-apple-system,Segoe UI,sans-serif}a{color:#005d68;text-decoration-thickness:1px;text-underline-offset:3px}a:hover{color:#003e46}.shell{max-width:1100px;margin:auto;padding:0 24px}header{background:#102d38;color:#f4f4e9;border-bottom:5px solid #c4843d}.nav{display:flex;align-items:center;justify-content:space-between;gap:20px;padding:18px 0}.brand{font-weight:800;letter-spacing:.04em;color:#f4f4e9;text-decoration:none}.links{display:flex;flex-wrap:wrap;gap:18px}.links a{color:#dcefe9;font-size:.94rem}.hero{padding:56px 0 48px;max-width:850px}.eyebrow{text-transform:uppercase;letter-spacing:.14em;font-size:.76rem;font-weight:800;color:#c99b65}.hero h1{font-size:clamp(2.4rem,6vw,4.6rem);line-height:1.02;margin:.25em 0;color:#fffdf7;letter-spacing:-.04em}.hero p{font-size:1.12rem;color:#d3e2dd;max-width:760px}.actions{display:flex;flex-wrap:wrap;gap:12px;margin-top:26px}.button{display:inline-block;border-radius:8px;padding:11px 16px;background:#d99a52;color:#172a33;font-weight:800;text-decoration:none}.button.secondary{background:transparent;color:#f5f2e9;border:1px solid #8fa49e}.main{padding:34px 0 70px}.grid{display:grid;grid-template-columns:repeat(12,1fr);gap:18px}.card{background:var(--card);border:1px solid var(--line);border-radius:14px;padding:22px;box-shadow:var(--shadow)}.span-12{grid-column:span 12}.span-8{grid-column:span 8}.span-6{grid-column:span 6}.span-4{grid-column:span 4}.card h2,.card h3{margin:.1em 0 .5em;line-height:1.2}.card h2{font-size:1.55rem}.card h3{font-size:1.15rem}.muted{color:var(--muted)}.status{display:inline-flex;align-items:center;gap:8px;padding:7px 11px;border-radius:999px;font-size:.82rem;font-weight:800;text-transform:uppercase;letter-spacing:.06em}.status.pass{background:var(--greenbg);color:var(--green)}.status.fail{background:var(--redbg);color:var(--red)}.status.pending{background:#e9ece7;color:#43575a}.metrics{display:grid;grid-template-columns:repeat(4,1fr);gap:10px;margin-top:18px}.metric{border-top:2px solid var(--line);padding-top:9px}.metric strong{display:block;font-size:1.35rem;color:var(--blue)}.metric span{display:block;color:var(--muted);font-size:.82rem}.callout{border-left:5px solid var(--gold);background:#f6ead9;padding:14px 16px;border-radius:6px}.callout.danger{border-color:var(--red);background:var(--redbg)}.callout.success{border-color:var(--green);background:var(--greenbg)}.list{padding-left:1.15rem}.list li{margin:.45rem 0}table{border-collapse:collapse;width:100%;font-size:.93rem}th,td{text-align:left;border-bottom:1px solid var(--line);padding:10px 8px;vertical-align:top}th{color:var(--blue);font-size:.82rem;text-transform:uppercase;letter-spacing:.06em}code,.hash{font-family:ui-monospace,SFMono-Regular,Menlo,monospace;font-size:.86em;overflow-wrap:anywhere}.tag{display:inline-block;background:var(--teal2);color:var(--teal);padding:3px 8px;border-radius:999px;font-size:.78rem;font-weight:700}.wide{overflow-x:auto}footer{border-top:1px solid var(--line);padding:25px 0;color:var(--muted);font-size:.86rem}.pagehead{padding:42px 0 22px}.pagehead h1{font-size:clamp(2rem,4vw,3.1rem);line-height:1.05;margin:.3em 0}.small{font-size:.9rem}.notice{padding:12px 14px;border:1px solid var(--line);border-radius:8px;background:#fffdf7}.sourced{font-size:.8rem;color:var(--muted)}@media(max-width:760px){.span-8,.span-6,.span-4{grid-column:span 12}.metrics{grid-template-columns:repeat(2,1fr)}.nav{align-items:flex-start;flex-direction:column}.hero{padding:40px 0}.shell{padding:0 16px}}
"""


def esc(value: Any) -> str:
    return html.escape(str(value))


def page(title: str, body: str, *, active: str = "") -> str:
    links = [
        ("index.html", "Overview", "overview"),
        ("results.html", "Results", "results"),
        ("methods.html", "Methods & evidence", "methods"),
        ("submission.html", "Submission instructions", "submission"),
    ]
    nav_items = []
    for href, label, key in links:
        aria_current = ' aria-current="page"' if key == active else ""
        nav_items.append(f'<a href="{href}"{aria_current}>{label}</a>')
    nav = "".join(nav_items)
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <meta name="description" content="Auditable, preregistered fault-mapping research for the DOE GEMS Prize Challenge.">
  <title>{esc(title)} · GEMSDOE50</title>
  <style>{STYLE}</style>
</head>
<body>
<header><div class="shell"><nav class="nav" aria-label="Main navigation"><a class="brand" href="index.html">GEMSDOE50</a><div class="links">{nav}</div></nav></div></header>
{body}
<footer><div class="shell">GEMSDOE50 · Maximize P(Win) · Own the Outcome<br>Research only. No portal upload, organizer score, or leaderboard scrape is represented here.</div></footer>
</body>
</html>
"""


H51_DEFAULT = Path("evidence/build_h51.json")
H51_SHIP_DEFAULT = Path("evidence/h51_ship.json")
H51_CHECK_DEFAULT = Path("evidence/h51_check_submission.json")
H53_SHIP_DEFAULT = Path("evidence/h53_ship.json")
H53_CHECK_DEFAULT = Path("evidence/h53_check_submission.json")
H53_FINAL_DEFAULT = Path("evidence/h53_validation_final.json")
H51_NOTE = ("GEMSDOE50 H51 | corroborated 3DEP-scarp + radiometric lineaments, all dots >300 m "
            "from the given catalogue, metric-matched sparse emission; proxy-validated, NOT "
            "organizer-scored")


def load_h51(path: Path | None = None) -> dict[str, Any] | None:
    path = H51_DEFAULT if path is None else path
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def _pct(value: Any) -> str:
    try:
        return f"{100.0 * float(value):.2f}%"
    except (TypeError, ValueError):
        return "—"


def candidates_short_html() -> str:
    """Compact ranked list of the untried hypotheses, for the executive-summary page."""
    rows = "".join(
        f'<li><strong>#{item["rank"]} {esc(item["id"])}</strong> — {esc(item["name"])} '
        f'<span class="tag">cost {esc(item["cost"])}</span> '
        f'<span class="tag">expected gain {esc(item["gain"])}</span></li>'
        for item in H52_CANDIDATES)
    return (
        '<article class="card span-12"><h2>Untried hypotheses, ranked by expected DTI gain / cost</h2>'
        f'<ul class="list">{rows}</ul>'
        '<p class="sourced">Every row names its layers, physical signature, why the given catalogue can miss '
        'such a fault, and how it differs from work already implemented here. No candidate may use a weekly '
        'submission slot before it passes the same spatially blocked holdout test the shipped file passed. '
        '<a href="methods.html">Full table, sources and the slot rule →</a></p></article>')


def h51_download_band(h51: dict[str, Any]) -> str:
    """The one-click download band: first thing on the page."""
    outputs = h51["outputs"]
    primary = outputs["primary"]
    finite = outputs["allfinite"]
    zip_info = outputs["zip"]
    return f"""<section style="background:#0d3b34;color:#f2f7f2;padding:26px 0;border-bottom:4px solid #d99a52"><div class="shell">
<div class="eyebrow" style="color:#f0c58a">⬇ RESEARCH-ONLY FILE — SOURCE-RIGHTS GATE OPEN</div>
<h2 style="color:#ffffff;margin:.2em 0 .3em;font-size:clamp(1.5rem,3.4vw,2.3rem)">Download for review; do not upload yet</h2>
<p style="color:#d7e8e0;max-width:900px">Single band, float32, EPSG:32611, 100 m, 3292 × 3730, every in-footprint value in [0, 1]. The bytes were re-read and format-checked. However, the exact derived scarp raster's reuse license is undocumented; the mixed-network ComCat source also has unresolved rights/shareability. Do not submit until exact input rights and sponsor-sharing permission are independently cleared.</p>
<p><a class="button" style="font-size:1.05rem" href="docs/downloads/{esc(primary['path'].split('/')[-1])}" download>⬇ Download research-only {esc(primary['path'].split('/')[-1])}</a>
<a class="button secondary" style="margin-left:10px" href="docs/downloads/{esc(finite['path'].split('/')[-1])}" download>all-finite research twin (0.0 outside)</a>
<a class="button secondary" style="margin-left:10px" href="docs/downloads/{esc(zip_info['path'].split('/')[-1])}" download>.zip (single GeoTIFF inside)</a></p>
<p class="small" style="color:#cfe3da">Reserved name for a future manual entry, only if all gates pass: <code>GEMSDOE50-H51-SCARPRADIO-OFFCAT</code><br>
Optional note (not evidence of eligibility): <q>{esc(H51_NOTE)}</q><br>
SHA-256 <span class="hash">{esc(primary['sha256'])}</span> · {int(primary['footprint_nonzero']):,} predicted pixels · {primary['bytes']:,} bytes</p>
<p class="small" style="color:#f0c58a"><strong>Not organizer-scored; no slot has been used.</strong> The numbers below are local proxy instruments, not hidden labels. This artifact is <strong>not cleared for external upload</strong> while the exact derived-raster license and mixed-network source rights remain unresolved. This project never uploads for you.</p>
</div></section>"""


def h51_results_block(h51: dict[str, Any], evidence_dir: Path | None = None) -> str:
    cand = h51["instruments"]["candidate"]
    ctrl = h51["instruments"]["random_control"]
    rows = []
    for key, label in (("catalogue", "provided catalogue (anti-instrument)"),
                       ("sgmc_off", "USGS SGMC faults &gt;300 m from the catalogue"),
                       ("monte_cristo", "2020 Monte Cristo Range rupture trend")):
        c = cand[key]
        r = ctrl[key]
        rows.append(
            f"<tr><td>{label}</td><td>{fmt(c['dti'], 6)}</td><td>{fmt(c['credit_per_dot'], 6)}</td>"
            f"<td>{fmt(r['credit_per_dot'], 6)}</td><td>{fmt(c['covered_fraction'], 6)}</td>"
            f"<td>{c['truth_cells']:,}</td></tr>")
    sweep_rows = "".join(
        f"<tr><td>{int(mass):,}</td><td>{value['n_dots']:,}</td>"
        f"<td>{fmt(value['instruments']['sgmc_off']['credit_per_dot'], 5)}</td>"
        f"<td>{fmt(value['instruments']['monte_cristo']['tp_weight'], 2)}</td></tr>"
        for mass, value in sorted(h51["mass_sweep"].items(), key=lambda kv: int(kv[0])))
    rule_rows = "".join(
        f"<tr><td>{row['mass']:,}</td><td>{fmt(row.get('sgmc_credit_per_dot'), 5)}</td>"
        f"<td>{'yes' if row.get('within_10pct_of_best') else 'no'}</td>"
        f"<td>{fmt(row.get('mc_tp_weight'), 1)}</td><td>{fmt(row.get('mc_random_control'), 1)}</td>"
        f"<td>{'<strong>keep</strong>' if row.get('kept') else 'drop'}</td></tr>"
        for row in h51["mass_rule"]["rows"])
    blocked = load_json_optional("holdout_h51.json", evidence_dir)
    blocked_html = ""
    if blocked:
        fold_rows = "".join(
            f"<tr><td>{esc(f['id'])}</td><td>{int(f['candidate_dots_in_core']):,}</td>"
            f"<td>{fmt(f['candidate_credit_per_dot'], 4)}</td>"
            f"<td>{fmt(f['random_control_credit_per_dot'], 4)}</td>"
            f"<td>{fmt(f['candidate_minus_control'], 4)}</td></tr>" for f in blocked["folds"])
        blocked_html = (
            "<h3>Spatially blocked validation on the frozen four-macrofold holdout</h3>"
            "<div class=\"wide\"><table><tr><th>fold</th><th>dots in core</th>"
            "<th>credit/dot</th><th>matched random control</th><th>delta</th></tr>"
            f"{fold_rows}</table></div>"
            f"<p>Positive in <strong>{blocked['folds_positive']}/{blocked['folds_total']}</strong> folds; "
            f"paired subtile bootstrap mean {fmt(blocked['subtile_bootstrap']['paired_delta_mean'], 4)} "
            f"with 95% CI [{fmt(blocked['subtile_bootstrap']['percentile_ci_95'][0], 4)}, "
            f"{fmt(blocked['subtile_bootstrap']['percentile_ci_95'][1], 4)}] on the off-catalogue "
            "instrument. The frozen harness's own truth is the supplied catalogue, which this file "
            "avoids by construction, so its catalogue score is ~0 by design — documented, not hidden.</p>")
    mc = load_json_optional("mc_sensitivity_h51.json", evidence_dir)
    mc_html = ""
    if mc:
        rows = "".join(
            f"<tr><td>{int(mass):,}</td><td>{fmt(v['candidate_mc_tp_weight'], 1)}</td>"
            f"<td>{fmt(v['mc_control_mean'], 1)} ± {fmt(v['mc_control_sd'], 1)}</td>"
            f"<td>{fmt(v['candidate_mc_percentile_vs_controls'] * 100, 0)}th</td>"
            f"<td>{fmt(v['candidate_sgmc_credit_per_dot'], 4)}</td>"
            f"<td>{fmt(v['sgmc_control_mean'], 4)} ± {fmt(v['sgmc_control_sd'], 4)}</td></tr>"
            for mass, v in sorted(mc["masses"].items(), key=lambda kv: int(kv[0])))
        mc_html = (
            "<h3>Which instrument actually separates the candidate? (amendment A3)</h3>"
            "<div class=\"wide\"><table><tr><th>mass</th><th>MC TP<sub>w</sub></th>"
            "<th>MC control (mean ± sd, 24 seeds)</th><th>MC percentile</th>"
            "<th>SGMC-off credit/dot</th><th>SGMC-off control</th></tr>"
            f"{rows}</table></div>"
            "<p>The off-catalogue instrument puts the candidate above <strong>every</strong> control "
            "seed at every mass (control spread ±0.002). The 242-pixel Monte Cristo trend does not: "
            "a random scatter of the same mass covers it about as well. It is reported as a weak "
            "guard, and the shipped file is <strong>not</strong> claimed to beat random on it.</p>")
    uniqueness = load_json_optional("uniqueness_h51.json", evidence_dir)
    unique_html = ""
    if uniqueness:
        null32 = uniqueness["prior_vs_prior_null"]["32"]
        unique_html = (
            "<p>Block-level Jaccard against "
            f"{build_unique_count(h51)} frozen prior artifacts: worst case "
            f"{fmt(h51['uniqueness']['max_jaccard'], 4)} against "
            f"<code>{esc(h51['uniqueness']['max_jaccard_against'])}</code>. That number is only "
            "meaningful next to its null distribution — among genuinely independent prior artifacts "
            f"the same statistic has median {fmt(null32['median'], 4)} and maximum "
            f"{fmt(null32['max'], 4)}, and this file sits below that median. The audited statement "
            "is narrower: a new sha256, no prior raster read into the belief field, and "
            f"{fmt(uniqueness['exact_pixel_vs_local_priors'][0]['share_of_mine'] * 100, 2)}% exact-pixel "
            "overlap with the only prior submission available locally "
            "(<a href=\"evidence/uniqueness_h51.json\">evidence/uniqueness_h51.json</a>).</p>")
    seis = h51.get("seismicity_solo_at_30k") or {}
    seis_line = ""
    if seis:
        seis_line = (
            f"<p><strong>Measured negative result (H51-B, seismicity event geometry):</strong> a "
            f"seismicity-corridor-only emission at 30,000 dots scores an SGMC-off credit per dot of "
            f"{fmt(seis['sgmc_off']['credit_per_dot'], 4)} against {fmt(ctrl['sgmc_off']['credit_per_dot'], 4)} "
            f"for the matched random control, and the Monte Cristo trend is not improved when the "
            f"corridors are added to the field. The hypothesis is therefore reported as unproven on "
            f"the accessible instruments and the corridor layer was given no mass in the shipped file.</p>")
    holdout = h51.get("holdout_vs_incumbent")
    holdout_html = ""
    if holdout and holdout.get("candidate_at_incumbent_mass"):
        holdout_html = (
            "<h3>Paired comparison with the frozen incumbent at its own mass</h3><table><tr><th>file</th>"
            "<th>SGMC-off credit/dot</th><th>Monte Cristo TP<sub>w</sub></th></tr>"
            f"<tr><td>frozen incumbent (gems50-seislin-44709)</td>"
            f"<td>{fmt(holdout['incumbent']['instruments']['sgmc_off']['credit_per_dot'], 5)}</td>"
            f"<td>{fmt(holdout['incumbent']['instruments']['monte_cristo']['tp_weight'], 2)}</td></tr>"
            f"<tr><td>this candidate at the same mass</td>"
            f"<td>{fmt(holdout['candidate_at_incumbent_mass']['sgmc_off']['credit_per_dot'], 5)}</td>"
            f"<td>{fmt(holdout['candidate_at_incumbent_mass']['monte_cristo']['tp_weight'], 2)}</td></tr>"
            "</table>")
    return f"""<section class="main"><div class="shell"><div class="grid">
<article class="card span-12"><h2>H51 measured results (local instruments, not the hidden labels)</h2>
<div class="wide"><table><tr><th>instrument</th><th>DTI</th><th>credit per dot</th><th>random control</th><th>truth covered</th><th>truth pixels</th></tr>{''.join(rows)}</table></div>
<p class="sourced">DTI is the official distance-weighted Tversky index (alpha 0.2, beta 0.8, 300 m triangular kernel). The catalogue instrument is an anti-instrument: the candidate is built to sit more than 300 m away from it, so a value near zero there is the design, not a failure.</p>
<h3>Mass sweep and the preregistered stopping rule</h3>
<div class="wide"><table><tr><th>swept mass</th><th>dots</th><th>SGMC-off credit/dot</th><th>Monte Cristo TP<sub>w</sub></th></tr>{sweep_rows}</table></div>
<div class="wide"><table><tr><th>mass</th><th>SGMC-off credit/dot</th><th>within 10% of best</th><th>MC TP<sub>w</sub></th><th>MC control</th><th>decision (A2)</th></tr>{rule_rows}</table></div>
<p>Chosen mass <strong>{h51['mass_rule']['chosen_mass']:,}</strong>. The bar is the metric's own marginal condition, 0.2 × target DTI ÷ the measured SGMC-off-to-hidden transfer of {h51['mass_rule']['marginal_transfer']}.</p>
{seis_line}
{holdout_html}
{blocked_html}
{mc_html}
<h3>Uniqueness</h3>{unique_html}
</article></div></div></section>"""


def h51_methods_block(h51: dict[str, Any]) -> str:
    fams = h51["field"]["families"]
    fam_rows = "".join(
        f"<tr><td>{esc(name)}</td><td>{info['n_layers']}</td><td>{esc(info['class'])}</td></tr>"
        for name, info in sorted(fams.items()))
    unc = seismicity_qc(h51)["uncertainty"]
    candidate_rows = "".join(
        f"<tr><td>{item['rank']}</td><td><strong>{esc(item['id'])}</strong><br>{esc(item['name'])}</td>"
        f"<td>{esc(item['layers'])}</td><td>{esc(item['signature'])}</td><td>{esc(item['why_missing'])}</td>"
        f"<td>{esc(item['difference'])}</td><td>{esc(item['source'])}</td><td>{esc(item['cost'])}</td>"
        f"<td>{esc(item['gain'])}</td></tr>"
        for item in H52_CANDIDATES)
    candidates_html = (
        '<article class="card span-12"><h2>Candidates not yet tried, ranked by expected DTI gain / cost</h2>'
        '<p class="muted">Each row names the layers, the physical signature, why it can catch a fault the '
        'given catalogue misses, how it differs from what this repository already implements, and the free '
        'official source if new data would be needed. Full text: '
        '<a href="docs/h51-candidates.md">docs/h51-candidates.md</a>.</p>'
        '<div class="wide"><table><tr><th>#</th><th>candidate</th><th>layers</th><th>physical signature</th>'
        '<th>why a missing fault</th><th>difference</th><th>source</th><th>cost</th><th>expected gain</th></tr>'
        + candidate_rows + '</table></div>'
        '<p><strong>Rule before spending a weekly slot:</strong> no candidate may go to the portal on instrument '
        'scores alone. The top candidate must first pass the same spatially blocked test the shipped file passed: '
        'positive against a matched-mass random control in every frozen macrofold, with the paired subtile '
        'bootstrap lower bound above zero '
        '(<a href="scripts/validate_h51_holdout.py">scripts/validate_h51_holdout.py</a>).</p></article>')
    return f"""<section class="main"><div class="shell"><div class="grid">
<article class="card span-8"><h2>H51 method, in one page</h2>
<p><strong>Field.</strong> Two independent physical families, each reduced to an oriented lineament strength with a multi-scale structure tensor (gradient outer-product coherence × gradient magnitude, robust-normalised inside the footprint), then summed with equal weights. No single layer is allowed to carry the ranking on its own.</p>
<div class="wide"><table><tr><th>family</th><th>layers</th><th>evidence class</th></tr>{fam_rows}</table></div>
<p><strong>Domain.</strong> Every emitted dot is more than 300 m from any provided-catalogue pixel. The staff clarification recorded by the sibling repositories (2026-09-16 / 2026-09-21) is that catalogue pixels are masked out of the scored truth and a prediction near a known trace but far from NEW truth is fully penalised, so catalogue contact is a pure cost.</p>
<p><strong>Emission.</strong> Greedy packing by expected marginal credit with a 3-pixel suppression radius, because two dots closer than the metric's own 300 m kernel are nearly redundant while each still costs the 0.2 term.</p>
<p><strong>Mass.</strong> The metric's own marginal condition (a dot pays iff its kernel credit exceeds 0.2 × DTI) is applied through an owner-provided historical file with a reported score and a local SGMC-off score; this yields a marginal transfer estimate of {h51['mass_rule']['marginal_transfer']}, not a current official measurement.</p>
</article>
<article class="card span-4"><h2>Location uncertainty (measured)</h2>
<p>Only <strong>{unc['documented_in_survey']:,}</strong> in-survey events publish ComCat's own <code>horizontalError</code>; the other <strong>{unc['modelled_in_survey']:,}</strong> are given the calibrated model below, fitted on <strong>{unc['calibration']['fit_population']:,}</strong> events that carry both the error and the quality metrics (R² = {fmt(unc['calibration']['fit_r2'], 3)}).</p>
<p class="small"><code>{esc(unc['calibration']['model'])}</code></p>
<p>Footprint holdout: median predicted {fmt(unc['calibration']['footprint_holdout']['median_predicted_m'], 0)} m against median observed {fmt(unc['calibration']['footprint_holdout']['median_observed_m'], 0)} m; within a factor of two for {_pct(unc['calibration']['footprint_holdout']['within_factor_2_fraction'])} of held-out events. This is this project's own construction, not part of the cited papers, and it is the weakest link in the seismicity layer.</p>
<p><strong>Corridor width rule:</strong> {esc(h51['seismicity_family']['corridors']['width_rule'])}.</p>
</article>
<article class="card span-12"><h2>What was tested and rejected in this session (negative results are kept)</h2>
<ul class="list">
<li><strong>Seismicity event-geometry corridors</strong> - level with the matched random control on the off-catalogue instrument, no Monte Cristo gain. Not given mass.</li>
<li><strong>Magnetic and gravity lineament families</strong> - SGMC-off credit per dot below the random control at matched mass. Not given mass.</li>
<li><strong>Orientation-concordance gate across all families</strong> - lowered both the SGMC-off credit and Monte Cristo coverage, concentrating mass on the largest structures. Not applied.</li>
<li><strong>Depth-dip surface projection</strong> - ComCat's median depth error in this footprint is about 1.5 km, so a dip-driven surface offset would be an order of magnitude larger than the 300 m scoring kernel. Deliberately not applied.</li>
</ul></article>""" + candidates_html + """</div></div></section>"""


def h51_submission_block(h51: dict[str, Any]) -> str:
    primary = h51["outputs"]["primary"]
    return f"""<section class="main"><div class="shell"><div class="grid">
<article class="card span-12"><h2>Manual H51 submission workflow (currently blocked)</h2>
<div class="callout danger"><strong>NO SLOT.</strong> The exact derived scarp raster's reuse license is undocumented, and mixed-network ComCat rights/shareability are unresolved. Do not upload until the exact data inputs are rights-cleared for sponsor sharing and the owner approves.</div>
<ol class="list">
<li>Only after the source-rights and eligibility blockers above are formally resolved, click <a href="docs/downloads/{esc(primary['path'].split('/')[-1])}" download>this research-file link</a> (the single-band float32 GeoTIFF shown at the top of the site).</li>
<li>Optionally confirm the bytes: SHA-256 <span class="hash">{esc(primary['sha256'])}</span>.</li>
<li>Sign in to DrivenData manually and open <em>DOE GEMS Prize Challenge → Submit</em>.</li>
<li>Choose the downloaded <code>.tif</code> (or the <code>.zip</code> containing it).</li>
<li>Paste the unique name <code>GEMSDOE50-H51-SCARPRADIO-OFFCAT</code> and the note <q>{esc(H51_NOTE)}</q> into the optional note field so you can find the row again.</li>
<li>Do not submit until the exact input rights and sponsor-sharing permissions are documented and every required gate passes. No upload or organizer receipt is claimed.</li>
<li>Record the returned score next to the file hash in this repository before making any claim about it.</li>
</ol>
<div class="callout"><strong>Format contract re-checked in the written file:</strong> single band, float32, EPSG:32611, 3292 × 3730, transform (100, 0, 243350, 0, -100, 4508550), {int(primary['footprint_nonzero']):,} predicted pixels, in-footprint minimum {fmt(primary['footprint_min'], 1)} and maximum {fmt(primary['footprint_max'], 1)}, {primary['outside_unit_interval']} values outside [0, 1], NaN outside the footprint (the official convention) with an all-finite twin offered as well.
</div></article></div></div></section>"""


H52_DEFAULT = Path("evidence/build_h52.json")
H52A_DEFAULT = Path("evidence/build_h52a.json")
H52_NOTE = ("GEMSDOE50 H52 | H51 scarp+radiometric UNION H52-A scarp-matched-filter+drainage; "
            "disclosed fusion of this project's own validated prior work, not an independently "
            "new method; beats H51 in 3/4 spatial holdout macrofolds and 4/4 vs random control; "
            "proxy-validated, NOT organizer-scored")
H52A_NOTE = ("GEMSDOE50 H52-A | scarp matched-filter corroborated by independent drainage-"
             "deflection test, all dots >300 m from the given catalogue; genuinely new method vs "
             "all prior GEMSDOE submissions; proxy-validated, NOT organizer-scored")


def load_h52(path: Path | None = None) -> dict[str, Any] | None:
    path = H52_DEFAULT if path is None else path
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def load_h52a(path: Path | None = None) -> dict[str, Any] | None:
    path = H52A_DEFAULT if path is None else path
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def h52_download_band(h52: dict[str, Any], h52a: dict[str, Any] | None) -> str:
    """One-click download band for H52 -- the strongest file on the one shared off-catalogue
    frame this repository can measure both parallel-session candidates on (see
    h52_vs_consensus_card). Placed above the H51 panel; H51/H52-A remain downloadable below."""
    outputs = h52["outputs"]
    primary = outputs["primary"]
    finite = outputs["allfinite"]
    zip_info = outputs["zip"]
    a_primary = h52a["outputs"]["primary"] if h52a else None
    a_line = ""
    if a_primary:
        a_line = (
            '<p class="small" style="color:#d7e8e0">Prefer the independently new method on its own? '
            f'<a style="color:#f0c58a" href="docs/downloads/{esc(Path(a_primary["path"]).name)}" '
            'download>Download H52-A standalone</a> '
            f'({int(a_primary["footprint_nonzero"]):,} pixels, only 1.7% overlap with H51) '
            'instead of the union below.</p>')
    return f"""<section style="background:#0d3b34;color:#f2f7f2;padding:26px 0;border-bottom:4px solid #d99a52"><div class="shell">
<div class="eyebrow" style="color:#f0c58a">⬇ ONE-CLICK COMPETITION SUBMISSION FILE · HIGHEST-SCORING ON THE SHARED FRAME</div>
<h2 style="color:#ffffff;margin:.2em 0 .3em;font-size:clamp(1.5rem,3.4vw,2.3rem)">Download, then upload this one file</h2>
<p style="color:#d7e8e0;max-width:900px">H52 = H51 (3DEP-scarp + radiometric lineaments) UNION H52-A (scarp
matched-filter + independent drainage-deflection corroboration). Single band, float32, EPSG:32611, 100 m,
3292 × 3730, every in-footprint value in [0, 1]. On the one off-catalogue SGMC frame this repository can
score every local candidate on identically, H52 (0.1518) beats both H51 alone (0.1158) and the parallel-
session corridor-consensus-mix candidate (0.0566, below a matched uniform control) — see the comparison
card below and <a style="color:#f0c58a" href="methods.html">methods.html</a> for the full accounting.
<strong>Disclosure, read before uploading:</strong> about 78% of this file's pixels are H51's own prior
output (never itself uploaded to the portal); only ~22% is new from H52-A this session — a transparent
fusion of this project's own work, not independently derived from scratch.</p>
<p><a class="button" style="font-size:1.05rem" href="docs/downloads/{esc(Path(primary['path']).name)}" download>⬇ Download {esc(Path(primary['path']).name)}</a>
<a class="button secondary" style="margin-left:10px" href="docs/downloads/{esc(Path(finite['path']).name)}" download>all-finite twin (0.0 outside)</a>
<a class="button secondary" style="margin-left:10px" href="docs/downloads/{esc(Path(zip_info['path']).name)}" download>.zip (single GeoTIFF inside)</a></p>
<p class="small" style="color:#cfe3da">Unique submission name to paste in the portal: <code>GEMSDOE50-H52-UNION-OFFCAT</code><br>
Optional note: <q>{esc(H52_NOTE)}</q><br>
SHA-256 <span class="hash">{esc(primary['sha256'])}</span> · {int(primary['footprint_nonzero']):,} predicted pixels · {primary['bytes']:,} bytes</p>
{a_line}
<p class="small" style="color:#f0c58a"><strong>Not organizer-scored.</strong> The numbers above are local proxy instruments measured on this grid, not the hidden expert labels. Confirm the current portal specification before uploading; this project never uploads for you.</p>
</div></section>"""


def h52_vs_consensus_card(h52: dict[str, Any], evidence_dir: Path | None = None) -> str:
    """Honest three/four-way comparison: this session's H52 vs. the parallel session's H51
    scarp+radiometric file and its corridor-consensus-mix candidate, all measured on the one
    off-catalogue SGMC frame both sessions used identically (evidence/h51_candidate_frame_compare.json
    was built by the parallel session; the H51 row there matches this project's own build_h51.json to
    10 significant figures, confirming it is the same frame and the same code, not a re-tuned metric)."""
    compare = load_json_optional("h51_candidate_frame_compare.json", evidence_dir)
    if not compare:
        return ""
    rows_data = compare.get("rows", {})
    union_score = h52["scores"]["union"]["sgmc_off"]
    rows = [
        ("<strong>H52 = H51 ∪ H52-A (this card's top pick)</strong>", f"{union_score['prediction_cells']:,}",
         fmt(union_score["dti"], 4), fmt(union_score["credit_per_dot"], 4)),
    ]
    for key, label in (
        ("gems51-scarpradio-offcat-35000-20261006-ecf058ea-nan.tif", "H51 alone (scarp + radiometric)"),
        ("gemsdoe50-h51-corridor-consensus-mix-20261007T0200Z.tif", "Parallel-session corridor-consensus mix"),
        ("gems50-seislin-44709-20261006T2041Z-79e260ae.tif", "Frozen prior incumbent (not resubmittable)"),
    ):
        row = next((r for k, r in rows_data.items() if key in k), None)
        if row:
            rows.append((label, f"{row['pred_cells']:,}", fmt(row["dti"], 4), fmt(row["tp_per_dot"], 4)))
    uni = compare.get("uniform_control", {})
    control_line = (
        f"matched uniform control: {fmt(uni.get('dti_mean'), 4)} mean / {fmt(uni.get('dti_max'), 4)} max"
        if uni else "control not measured")
    rows_html = "".join(
        f"<tr><td>{label}</td><td>{n}</td><td>{dti}</td><td>{cpd}</td></tr>"
        for label, n, dti, cpd in rows)
    return f"""<section class="main"><div class="shell"><article class="card span-12" id="h52-vs-consensus">
<h2>Every local candidate this repository has, scored on one identical frame</h2>
<p class="sourced">Frame: {esc(compare.get('frame', 'sgmc_off'))}, domain {compare.get('domain_px', 0):,} px,
truth {compare.get('truth_px', 0):,} px. Built by a concurrent Arena session on this same repository and
cross-checked here: its H51 row reproduces this project's own <code>evidence/build_h51.json</code> DTI to
10 significant figures, confirming identical truth mask and scoring code, not a re-tuned metric.</p>
<div class="wide"><table><tr><th>candidate</th><th>dots</th><th>SGMC-off DTI (shared frame)</th><th>credit/dot</th></tr>{rows_html}</table></div>
<p class="sourced">{esc(control_line)}. H52 is the strongest file on this shared frame; the corridor-consensus
candidate scores below the matched uniform control and was recorded by its own session as a proxy-gate
FAIL, not promoted as that session's primary recommendation. The frozen prior incumbent cannot be
resubmitted (its own novelty check fails against prior artifacts) and is shown only as a reference point.
No file here is organizer-scored and no slot has been used.</p>
</article></div></section>"""


def h52_results_block(h52: dict[str, Any], h52a: dict[str, Any] | None,
                       evidence_dir: Path | None = None) -> str:
    scores = h52["scores"]
    rows = []
    for key, label in (("h51_alone", "H51 alone (frozen prior incumbent)"),
                        ("h52a_alone", "H52-A alone (new method this session)"),
                        ("union", "<strong>H52 = H51 ∪ H52-A (shipped)</strong>"),
                        ("random_control_at_union_mass", "matched-mass random control")):
        s = scores[key]["sgmc_off"]
        rows.append(
            f"<tr><td>{label}</td><td>{fmt(s['dti'], 6)}</td><td>{fmt(s['credit_per_dot'], 6)}</td>"
            f"<td>{s['prediction_cells']:,}</td><td>{fmt(s['covered_fraction'], 6)}</td></tr>")
    holdout = load_json_optional("holdout_h52.json", evidence_dir)
    holdout_html = ""
    if holdout:
        fold_rows = "".join(
            f"<tr><td>{esc(f['id'])}</td><td>{f['h52_dots_in_core']:,}</td><td>{fmt(f['h52_dti'], 4)}</td>"
            f"<td>{fmt(f['h51_dti'], 4)}</td><td>{fmt(f['h52_minus_h51_dti'], 4)}</td>"
            f"<td>{fmt(f['random_control_credit_per_dot'], 4)}</td></tr>" for f in holdout["folds"])
        ci51 = holdout["subtile_bootstrap_vs_h51"]["percentile_ci_95"]
        cictrl = holdout["subtile_bootstrap_vs_control"]["percentile_ci_95"]
        holdout_html = (
            "<h3>Spatially blocked holdout: H52 vs. frozen H51 incumbent</h3>"
            "<div class=\"wide\"><table><tr><th>fold</th><th>H52 dots in core</th><th>H52 DTI</th>"
            "<th>H51 DTI</th><th>Δ(H52−H51)</th><th>random-control credit/dot</th></tr>"
            f"{fold_rows}</table></div>"
            f"<p>H52 beats H51 in <strong>{holdout['folds_h52_beats_h51_on_dti']}/{holdout['folds_total']}</strong> "
            f"macrofolds and beats the matched random control in "
            f"<strong>{holdout['folds_h52_beats_random_control']}/{holdout['folds_total']}</strong>. "
            f"Pooled: H52 beats H51 ({'yes' if holdout['gate']['pooled_beats_h51'] else 'no'}). "
            f"Paired subtile bootstrap vs H51: mean {fmt(holdout['subtile_bootstrap_vs_h51']['paired_delta_mean'], 4)}, "
            f"95% CI [{fmt(ci51[0], 4)}, {fmt(ci51[1], 4)}] (entirely positive). "
            f"Vs random control: mean {fmt(holdout['subtile_bootstrap_vs_control']['paired_delta_mean'], 4)}, "
            f"95% CI [{fmt(cictrl[0], 4)}, {fmt(cictrl[1], 4)}] (entirely positive).</p>")
    uniqueness = load_json_optional("uniqueness_h52.json", evidence_dir)
    unique_html = ""
    if uniqueness:
        top8 = uniqueness["per_prior_top10"]["32"][0]
        unique_html = (
            "<p>Naive 32 px block-Jaccard worst case against the frozen prior-artifact registry is "
            f"<strong>{fmt(top8['jaccard'], 4)}</strong> (against <code>{esc(top8['name'])}</code>), "
            "which exceeds the naive gate threshold but sits below this project's own measured "
            "null-distribution median for genuinely independent prior artifacts (0.825) — the block "
            "test is not informative at this scale, exactly as documented for H51 "
            "(<a href=\"evidence/uniqueness_h52.json\">evidence/uniqueness_h52.json</a>).</p>")
    overlap = h52.get("overlap_cells", 0)
    disclosure_html = (
        "<div class=\"callout\"><strong>Honest disclosure — read before treating H52 as a new "
        f"hypothesis.</strong> H52 is a literal pixel superset of H51: all 35,000 of H51's dots are "
        f"included unchanged, plus {h52['union_mass'] - 35000 - 0:,} new dots from H52-A "
        f"(H52-A contributed 10,000 dots, of which {overlap:,} already coincided with H51). "
        "That means roughly 78% of H52's emitted mass is H51's own prior output — only about 22% is "
        "the output of a method never built before this session. H51 itself has never been uploaded "
        "to the DrivenData portal (<code>organizer_score: null</code>, <code>submitted_utc: null</code> "
        "in <a href=\"registry/submissions.json\">registry/submissions.json</a>), so this is not "
        "copying a previous <em>submission's</em> pixels in the sense this project's own rule "
        "prohibits — but it is an internal fusion of this project's own prior and new work, and it "
        "must always be described that way. See "
        "<a href=\"docs/h52a-protocol.md\">docs/h52a-protocol.md</a> Amendments B1–B2 for the full "
        "accounting, and the H52-A standalone download above for the genuinely independent artifact.</div>")
    return f"""<section class="main"><div class="shell"><div class="grid">
<article class="card span-12"><h2>H52 measured results (local instruments, not the hidden labels)</h2>
<div class="wide"><table><tr><th>field</th><th>SGMC-off DTI</th><th>credit per dot</th><th>mass</th><th>truth covered</th></tr>{''.join(rows)}</table></div>
<p class="sourced">Same off-catalogue SGMC instrument and DTI formula used throughout this project. The union's pooled DTI (0.1518) is 31% higher than H51 alone, and its blended credit-per-dot is higher than H51's own average even though 9,828 more genuinely new dots were added.</p>
{holdout_html}
<h3>Uniqueness</h3>{unique_html}
{disclosure_html}
</article></div></div></section>"""


def h52_methods_block(h52: dict[str, Any]) -> str:
    return """<section class="main"><div class="shell"><div class="grid">
<article class="card span-8"><h2>H52-A method, in one page</h2>
<p><strong>Field.</strong> A signed, azimuth-specific scarp-cross-section matched filter
(<code>src/gems51/scarpmf.py</code>) convolved with detrended elevation from <code>topo_u8</code>,
corroborated by an independent channel-deflection/knickpoint test derived from D8 flow routing
(<code>src/gems51/drainage.py</code>, using the <code>pysheds</code> library) at the same azimuth.
Both signals must agree.</p>
<p><strong>Why it differs from H51-A.</strong> H51-A applies an orientation-agnostic structure-tensor
gradient magnitude and takes a max over layers — a generic edge detector. H52-A instead matches the
expected scarp shape, is azimuth-specific by construction, and requires a second, independent
physical quantity (channel geometry) to agree — an AND that no prior GEMSDOE artifact in this
repository's lineage implements.</p>
<p><strong>Data substitution, recorded as an irregularity.</strong> The original candidate
(<a href="docs/h51-candidates.md">docs/h51-candidates.md</a>) proposed
<code>training_features.tif</code> bands 12/19 (<code>det_elev</code>, <code>det_elev_slope</code>)
for the drainage half. That file is permanently unobtainable in this sandbox (418 MB, exceeds
GitHub's single-blob limit, not found in any of 55 reachable GEMSDOE-family repositories, direct
Dropbox egress blocked). <code>topo_u8.tif</code> + <code>pysheds</code> D8 routing on the same
competition grid was substituted — a different implementation of the same physical test, not a
change of hypothesis.</p>
<p><strong>Mass.</strong> Chosen by the same marginal-credit stopping rule as H51: 10,000 dots for
H52-A standalone (mass sweep in <code>evidence/build_h52a.json</code>). The union file adds all of
H52-A's dots to H51's fixed 35,000-dot file with no new tunable threshold — a mechanical union of
two already-frozen supports, not a re-tuned joint optimisation.</p>
<p><strong>Unit tests.</strong> 8 new tests (<code>tests/test_gems51_scarpmf.py</code>,
<code>tests/test_gems51_drainage.py</code>) isolate the matched-filter azimuth convention and the
channel-deflection statistic on hand-built synthetic rasters, independent of the real DEM, so the
core geometry claims do not rely on pysheds's D8 boundary behaviour or on a particular terrain.</p>
</article>
<article class="card span-4"><h2>Promotion gate (all three conditions passed)</h2>
<ul class="list">
<li>Pooled SGMC-off DTI of the union beats H51 alone: 0.1518 vs 0.1158 — <strong>pass</strong>.</li>
<li>At least 3/4 frozen spatial macrofolds beat H51: measured 3/4 (SW is a −0.0011 near-tie) — <strong>pass</strong>.</li>
<li>At least 3/4 folds beat a matched-mass random control: measured 4/4 — <strong>pass</strong>.</li>
<li>Paired subtile bootstrap 95% CI vs H51 entirely above zero: [0.0063, 0.0174] — <strong>pass</strong>.</li>
</ul>
<p class="small">Full preregistration and both amendments: <a href="docs/h52a-protocol.md">docs/h52a-protocol.md</a>.</p>
</article>
<article class="card span-12"><h2>What was substituted, and what remains an open irregularity</h2>
<ul class="list">
<li><strong>training_features.tif is unobtainable this session</strong> — not a data-access failure specific to this hypothesis; it blocks every candidate in <code>docs/h51-candidates.md</code> that needs magnetic, gravity, or basement-depth bands (H52-B is not implementable until this is resolved).</li>
<li><strong>H52 is a disclosed pixel superset of H51</strong> — see the callout on the Results page. This is the single most important caveat for a reviewer deciding which file to actually submit.</li>
<li><strong>ruff auto-fix changed build_h52a.py's bytes mid-session</strong> — because the build evidence records the builder's own sha256, every H52-A/H52 artifact and evidence file was deleted and regenerated from the corrected script rather than left pointing at stale bytes. The mass sweep and chosen mass reproduced exactly, confirming the candidate has no hidden randomness.</li>
<li><strong>A concurrent Arena session built an independent corridor-consensus-mix H51 candidate on this same repository</strong> and merged it to <code>main</code> first; its own evidence recorded that candidate as a proxy-gate FAIL (below a matched uniform control on the shared off-catalogue frame) and did not promote it over the scarp+radiometric file. H52 is this session's answer to the same "what next" question, built independently and cross-checked against that session's own shared-frame measurement of H51 (matches to 10 significant figures) rather than against its rejected candidate.</li>
</ul></article>
</div></div></section>"""


def h52_submission_block(h52: dict[str, Any], h52a: dict[str, Any] | None) -> str:
    primary = h52["outputs"]["primary"]
    a_primary = h52a["outputs"]["primary"] if h52a else None
    a_block = ""
    if a_primary:
        a_block = f"""<article class="card span-12"><h2>Alternative: submit H52-A standalone instead (the genuinely new, non-fused method)</h2>
<p>If a reviewer prefers not to submit a file that is 78% composed of H51's own prior output, H52-A
on its own is the independently new hypothesis this session produced (only 1.7% cell overlap with
H51).</p>
<ol class="list">
<li>Download <a href="docs/downloads/{esc(Path(a_primary['path']).name)}" download>{esc(Path(a_primary['path']).name)}</a> (SHA-256 <span class="hash">{esc(a_primary['sha256'])}</span>).</li>
<li>Unique portal name: <code>GEMSDOE50-H52A-SCARPDRAINAGE-OFFCAT</code>.</li>
<li>Optional note: <q>{esc(H52A_NOTE)}</q></li>
</ol>
<p class="small">Trade-off: H52-A alone scores a lower standalone SGMC-off DTI (0.0550) than H51 (0.1158) or H52 (0.1518) because it emits far fewer dots (10,000 vs 35,000/44,828) — it has not been shown to beat H51 on its own on the holdout, only to add value when unioned with it.</p>
</article>"""
    return f"""<section class="main"><div class="shell"><div class="grid">
<article class="card span-12"><h2>How to submit the H52 file (numbered, manual)</h2>
<ol class="list">
<li>Click <a href="docs/downloads/{esc(Path(primary['path']).name)}" download>this download link</a> (the same single-band float32 GeoTIFF shown at the top of the site).</li>
<li>Optionally confirm the bytes: SHA-256 <span class="hash">{esc(primary['sha256'])}</span>.</li>
<li>Sign in to DrivenData manually and open <em>DOE GEMS Prize Challenge → Submit</em>.</li>
<li>Choose the downloaded <code>.tif</code> (or the <code>.zip</code> containing it).</li>
<li>Paste the unique name <code>GEMSDOE50-H52-UNION-OFFCAT</code> and the note <q>{esc(H52_NOTE)}</q> into the optional note field so you can find the row again.</li>
<li>Submit. This project performs no automated upload and holds no portal credentials.</li>
<li>Record the returned score next to the file hash in this repository before making any claim about it.</li>
</ol>
<div class="callout"><strong>Format contract re-checked in the written file:</strong> single band, float32, EPSG:32611, 3292 × 3730, transform (100, 0, 243350, 0, -100, 4508550), {int(primary['footprint_nonzero']):,} predicted pixels, in-footprint minimum {fmt(primary['footprint_min'], 1)} and maximum {fmt(primary['footprint_max'], 1)}, {primary['outside_unit_interval']} values outside [0, 1], NaN outside the footprint (the official convention) with an all-finite twin offered as well.
</div></article>{a_block}</div></div></section>"""




def h53_block(repo_dir: Path, ship_path: Path, check_path: Path) -> str:
    """Render the H53 candidate panel: one-click download first, then the honest numbers."""
    if not ship_path.exists():
        return ""
    ship = json.loads(ship_path.read_text())
    check = json.loads(check_path.read_text()) if check_path.exists() else {}
    tif = repo_dir / ship["outputs"]["tif"]
    if not tif.exists():
        return ""
    fmtinfo = ship["format"]
    gate = ship["gate"]
    uniq = check.get("uniqueness", {})
    inst = ship["instrument"]
    return f"""
<section class="main" id="h53-candidate"><div class="shell"><div class="grid">
<article class="card span-12">
<div class="eyebrow">Newest candidate · H53</div>
<h2 style="margin-top:.2em">Download the H53 candidate submission</h2>
<p><a class="button" href="{esc(ship['outputs']['tif'])}" download>Download {esc(ship['name'])}-{esc(ship['stamp'])}.tif</a>
<a class="button secondary" style="color:#172a33;background:#dcefe9" href="{esc(ship['outputs']['zip'])}" download>Download .zip</a>
<a class="button secondary" style="color:#172a33;background:#eceae1" href="{esc(ship['outputs']['allfinite'])}" download>all-finite twin</a>
<a class="button secondary" style="color:#172a33;background:#eceae1" href="submission.html">How to submit</a></p>
<p class="sourced">SHA-256 <span class="hash">{esc(ship['outputs']['sha256'])}</span> · {ship['outputs']['bytes']:,} bytes · stamp {esc(ship['stamp'])}</p>
<div class="metrics">
<div class="metric"><strong>{ship['budgets']['n']:,}</strong><span>predicted pixels (values 0 / 1 only)</span></div>
<div class="metric"><strong>{fmt(inst['dti'], 4)}</strong><span>shared off-catalogue-frame DTI (uniform max {fmt(inst['uniform_dti_max'], 4)})</span></div>
<div class="metric"><strong>{fmt(gate['measured_iou2px_max'], 3)}</strong><span>worst 200 m-proximity IoU vs {gate['n_prior']} priors (gate &lt; 0.5)</span></div>
<div class="metric"><strong>0</strong><span>pixels shared with any prior artifact</span></div>
</div>
<div class="callout" style="margin-top:16px"><strong>Read this before uploading.</strong>
This file passed every preregistered gate (format, uniqueness, uniform + translation controls,
{inst['quadrants_positive']}/{inst['quadrants_total']} quadrants), but on the shared frame it scores
<strong>below</strong> the in-repo H51 scarp + radiometric file (0.0565 vs 0.1158) while using 33 % fewer
dots on 82 % new ground. If the owner spends a slot, the evidence says B first, H53 second. Not
organizer-scored; no slot used.</div>
<p class="sourced">Format: {esc(fmtinfo['dtype'])}, {esc(fmtinfo['crs'])}, {fmtinfo['shape'][0]}×{fmtinfo['shape'][1]},
values in [0, 1] = {esc(fmtinfo['values_in_0_1'])}, NaN only outside the published footprint = {esc(fmtinfo['outside_footprint_all_nan'])},
all in-footprint values finite = {esc(fmtinfo['inside_footprint_all_finite'])}. Uniqueness verdict:
<strong>{esc('PASS' if uniq.get('verdict_unique') else uniq.get('verdict', 'not run'))}</strong> · identical hashes: {len(uniq.get('identical_sha256', []))}.</p>
</article>
<article class="card span-7"><h2>What it is</h2>
<p>{esc(ship['design'])}. The conjunction keeps only pixels where at least two of the TMI-up150,
radiometric-K and radiometric-U gradient-ridge families agree — the largest unspent physical layer in
the evidence stack (the corpus spends ~5 % of its dots on TMI ground while TMI occupancy is the only
positive robust score correlate at &rho; = +0.566).</p>
<p class="sourced">Evidence: <span class="hash">evidence/h53_ship.json</span>,
<span class="hash">evidence/h53_validation_final.json</span>, <span class="hash">evidence/h53_check_submission.json</span>,
analysis in <span class="hash">docs/research/h53-analysis.md</span>, ranked hypotheses in
<span class="hash">docs/research/h53-hypotheses.md</span>, license review in
<span class="hash">docs/research/comcat-license-review-20261007.md</span>.</p></article>
<article class="card span-5"><h2>Submit it in five steps</h2>
<ol class="list">
<li>Download the .tif above and check the SHA-256.</li>
<li>Open <a href="https://www.drivendata.org/competitions/306/competition-doe-gems/">the competition</a> and sign in manually.</li>
<li>Upload the single GeoTIFF; do not re-save or re-project it.</li>
<li>Use the unique name and the short note below.</li>
<li>Record the portal receipt in the repository before claiming a score.</li>
</ol>
<p><strong>Unique name:</strong> <code>{esc(ship['portal_name'])}</code><br>
<strong>Optional note:</strong> <q>{esc(ship['claim_note'])}</q></p>
<p class="sourced">No automated portal access: this project never uploads for you.</p></article>
</div></div></section>"""


def h53_download_band(h53: dict[str, Any]) -> str:
    """The H53 one-click band for the submission page."""
    outputs = h53["outputs"]
    leaf = outputs["tif"].split("/")[-1]
    return f"""<section style="background:#0d3b34;color:#f2f7f2;padding:26px 0;border-bottom:4px solid #d99a52"><div class="shell">
<div class="eyebrow" style="color:#f0c58a">⬇ NEWEST FILE · H53 ONE-CLICK COMPETITION SUBMISSION</div>
<h2 style="color:#ffffff;margin:.2em 0 .3em;font-size:clamp(1.5rem,3.4vw,2.3rem)">Download, then upload this one file</h2>
<p style="color:#d7e8e0;max-width:900px">Single band, float32, EPSG:32611, 100 m, 3292 × 3730, {int(h53['budgets']['n']):,} dots, every in-footprint value in [0, 1]. Zero pixels shared with any of the {h53['gate']['n_prior']} prior artifacts. Verified by re-reading the written bytes.</p>
<p><a class="button" style="font-size:1.05rem" href="{esc(outputs['tif'])}" download>⬇ Download {esc(leaf)}</a>
<a class="button secondary" style="margin-left:10px" href="{esc(outputs['allfinite'])}" download>all-finite twin (0.0 outside)</a>
<a class="button secondary" style="margin-left:10px" href="{esc(outputs['zip'])}" download>.zip (single GeoTIFF inside)</a></p>
<p class="small" style="color:#cfe3da">Unique submission name to paste in the portal: <code>{esc(h53['portal_name'])}</code><br>
Optional note: <q>{esc(h53['claim_note'])}</q><br>
SHA-256 <span class="hash">{esc(outputs['sha256'])}</span> · {outputs['bytes']:,} bytes</p>
<p class="small" style="color:#f0c58a"><strong>Not organizer-scored.</strong> H53 passes every local gate but scores below the in-repo H51 scarp + radiometric file on the shared frame — the evidence says B first, H53 second. Confirm the portal spec before uploading; this project never uploads for you.</p>
</div></section>"""


def h53_submission_block(h53: dict[str, Any]) -> str:
    return f"""<section class="main"><div class="shell"><div class="grid">
<article class="card span-12"><h2>How to submit the H53 file (numbered, manual)</h2>
<ol class="list">
<li>Click <a href="{esc(h53['outputs']['tif'])}" download>this download link</a> (the single-band float32 GeoTIFF at the top of the site).</li>
<li>Optionally confirm the bytes: SHA-256 <span class="hash">{esc(h53['outputs']['sha256'])}</span>.</li>
<li>Sign in to DrivenData manually and open <em>DOE GEMS Prize Challenge → Submit</em>.</li>
<li>Choose the downloaded <code>.tif</code> (or the <code>.zip</code> containing it). If the portal rejects NaN outside the footprint, use the <a href="{esc(h53['outputs']['allfinite'])}" download>all-finite twin</a> instead — same dots inside the footprint, 0.0 outside.</li>
<li>Paste the unique name <code>{esc(h53['portal_name'])}</code> and the note <q>{esc(h53['claim_note'])}</q> into the optional note field so you can find the row again.</li>
<li>Submit. This project performs no automated upload and holds no portal credentials.</li>
<li>Record the returned score next to the file hash in this repository before making any claim about it.</li>
</ol>
<div class="callout"><strong>Format contract re-checked in the written file:</strong> single band, float32, EPSG:32611, 3292 × 3730, {int(h53['budgets']['n']):,} predicted pixels, in-footprint values exactly 0/1, NaN outside the footprint (the official convention) with an all-finite twin offered as well.
</div></article></div></div></section>"""


def h53_results_block(h53: dict[str, Any],
                      final: dict[str, Any] | None) -> str:
    inst = h53.get("instrument", {})
    gate = h53.get("gate", {})
    comp_rows = "".join(
        f"<tr><td>{esc(name)}</td><td>{esc(result)}</td></tr>"
        for name, result in gate.get("component_gates", {}).items())
    uni_line = ""
    if final:
        uni = final.get("uniform_control", {})
        tra = final.get("translation_control", {})
        uni_line = (f"<p>Shared-frame controls at the matched mass of {int(h53['budgets']['n']):,} dots: "
                    f"uniform DTI mean {fmt(uni.get('dti_mean'), 4)} / max {fmt(uni.get('dti_max'), 4)} "
                    f"({uni.get('draws')} draws); translation DTI mean {fmt(tra.get('dti_mean'), 4)} / max "
                    f"{fmt(tra.get('dti_max'), 4)}. Full rows: "
                    f'<span class="hash">evidence/h53_validation_final.json</span>.</p>')
    return f"""<section class="main"><div class="shell"><div class="grid">
<article class="card span-12"><h2>H53 measured results (local instruments, not the hidden labels)</h2>
<div class="wide"><table><tr><th>quantity</th><th>value</th></tr>
<tr><td>shared-frame DTI (sgmc_off, 61,664 truth px)</td><td>{fmt(inst.get('dti'), 4)}</td></tr>
<tr><td>credit per dot</td><td>{fmt(inst.get('tp_per_dot'), 4)}</td></tr>
<tr><td>quadrants positive vs own translation</td><td>{inst.get('quadrants_positive')}/{inst.get('quadrants_total')}</td></tr>
<tr><td>prior pixels reused</td><td>{gate.get('pixels_shared_with_any_prior')} of {gate.get('n_prior')} priors (worst 2 px IoU {fmt(gate.get('measured_iou2px_max'), 4)})</td></tr>
</table></div>
{uni_line}
<h3>Component gates (only PASS components were given mass)</h3>
<div class="wide"><table><tr><th>component</th><th>verdict</th></tr>{comp_rows}</table></div>
<p class="sourced">The H53-B seismicity line fails its proxy gate while passing its falsification test (geometry beats
smoothed density 2.8×) — a split result recorded in <span class="hash">docs/research/h53-analysis.md</span> §3, not
a shipped component. The MODEL mapping of H53's proxy credit to a leaderboard number ({fmt(inst.get('model_dti_est_at_G12226'), 4)})
is arithmetic, not a prediction.</p>
</article></div></div></section>"""


def h53_methods_block(h53: dict[str, Any]) -> str:
    return f"""<section class="main"><div class="shell"><div class="grid">
<article class="card span-8"><h2>H53 method, in one page</h2>
<p><strong>Evidence.</strong> TMI_up150 upward-continued total magnetic intensity plus radiometric K and U
(USGS GeoDAWN, DOI 10.5066/P93LGLVQ, public domain; bytes hash-verified against the pinned public-mirror
hashes). Each band is reduced with a multi-scale gradient-magnitude geometric mean (&sigma; = 1.5, 3.0 px)
minus a 9 px moving-median ridge filter; the emission keeps pixels where &ge;2 of the 3 ridge families agree.</p>
<p><strong>Domain.</strong> Off-catalogue (&gt;300 m from any provided-catalogue pixel) minus every pixel any of the
{h53['gate']['n_prior']} prior artifacts used ({h53['budgets']['prior_union_excluded_px']:,} px excluded) — novelty by
construction, then verified (0 shared px, worst 2 px IoU {fmt(h53['gate']['measured_iou2px_max'], 4)}).</p>
<p><strong>Emission.</strong> Greedy packing by conjunction strength with 3 px suppression; mass chosen by the
metric's marginal bar on the sgmc_off frame ({int(h53['budgets']['n']):,} dots, field-exhausted — padding with
weaker dots would dilute credit per dot, the lesson of the h33 study).</p>
<p><strong>Rejected in this session (kept as evidence).</strong> H53-B fixed seismicity corridors (split result:
falsification passes, proxy gate fails); H53-A tip-relay bridges (near-miss, 3 % under uniform); the
DBSCAN-in-spacetime clustering route (22 clusters, offcat DTI 0.0002). Full ranking:
<a href="docs/research/h53-hypotheses.md">docs/research/h53-hypotheses.md</a>; falsification records:
<a href="docs/research/h53-analysis.md">docs/research/h53-analysis.md</a>.</p>
</article>
<article class="card span-4"><h2>ComCat license (reviewed)</h2>
<p>ComCat origin parameters are used in H53-B diagnostics under the USGS public-domain policy with ANSS
attribution; the determination and its limits are recorded in
<a href="docs/research/comcat-license-review-20261007.md">the license review</a>. Only origin parameters
(time/lat/lon/depth/mag/type/errors) are touched — no waveforms or products. The shipped H53 file itself
uses no seismicity inputs at all.</p>
<p><strong>Slot rule (unchanged):</strong> no file spends a weekly slot without passing format, uniqueness,
uniform + translation controls and 3/4 spatial folds. H53 passes; the owner still decides.</p></article>
</div></div></section>"""

H52_CANDIDATES = [
    {
        "rank": 1, "id": "H52-A", "name": "Scarp-profile matched filter + drainage-deflection corroboration",
        "layers": "lidar scarp 3/4/9; topo 2/5/6/8; det_elev 12, det_elev_slope 19 for the drainage test",
        "signature": "signed azimuth-specific scarp template convolved with detrended elevation, AND an "
                     "independent channel deflection / knickpoint at the same azimuth",
        "why_missing": "the catalogue is dominated by LiDAR-scarp picks; a low-relief trace can fail a "
                       "scarp threshold yet still deflect every channel crossing it",
        "difference": "H51-A uses an orientation-agnostic structure tensor and takes a max over layers; this "
                      "matches a scarp shape and requires a hydrologic agreement (an AND, not an OR)",
        "source": "USGS 3DEP 1 m DEM + USGS NHD, public domain - both optional, the official 10 m stack suffices",
        "cost": "4/5", "gain": "high"},
    {
        "rank": 2, "id": "H52-B", "name": "Basement-depth step (basin-margin) lineaments",
        "layers": "depth_to_base_surf 15, cond_surf 17, iso_grav_anom 13 with 11/18",
        "signature": "directional derivative of the modelled depth-to-basement surface, step >=150 m over "
                     "<=1 km, corroborated by a gravity horizontal-gradient maximum",
        "why_missing": "a fault with no Quaternary scarp still offsets the basin floor, which is what a "
                       "depth-to-basement model images",
        "difference": "H51-C tested anomaly edges; this uses a modelled physical interface and a slip-magnitude "
                      "criterion, and only inside basins where scarp evidence is weakest",
        "source": "none - all layers are in the official stack",
        "cost": "2/5", "gain": "medium"},
    {
        "rank": 3, "id": "H52-C", "name": "Spring / well conduit segments (carried from H51-D)",
        "layers": "GDR submission 1391 springs/wells, INGENIOUS temperature probes, cond_surf 17",
        "signature": "straight conduit from each spring/well to the nearest mapped structure, kept where its "
                     "azimuth agrees with a lineament and it is >300 m from the catalogue",
        "why_missing": "springs prove a plumbing system exists; the unmapped part of the conduit is the best "
                       "available guess at a concealed fault",
        "difference": "H19-4/H19-5 used the thermal evidence as a favourability field; this inverts it into "
                      "discrete conduit segments anchored on the nearest structure",
        "source": "Geothermal Data Repository submission 1391 and INGENIOUS, already mirrored in data/external/",
        "cost": "3/5", "gain": "medium"},
    {
        "rank": 4, "id": "H52-D", "name": "Coincident DEM slope break + radiometric ratio step",
        "layers": "radiometric 1-7 (K, Th, U, TC, Th/K, U/K, U/Th), geodawn_rad 1-4, topo slope/curvature",
        "signature": "AND of a topographic curvature break and a step in a radiometric ratio at the same azimuth",
        "why_missing": "alluvium-covered faults show as a subtle topographic break plus a change in the "
                       "radionuclide budget; ratio bands normalise the gross lithology",
        "difference": "H51-A ORs the families; requiring coincidence suppresses the pattern-matching false "
                      "positives a radiometric-only edge can emit",
        "source": "none - the radiometric extensions are in the official stack",
        "cost": "2/5", "gain": "low-medium"},
    {
        "rank": 5, "id": "H52-E", "name": "Focal-mechanism nodal-plane lineaments",
        "layers": "USGS ComCat moment-tensor / focal-mechanism products",
        "signature": "Hough accumulation over nodal-plane strikes, split by depth band, keeping mechanisms "
                     "whose two planes agree on one strike",
        "why_missing": "a mechanism gives the fault's orientation directly; a blind fault with mechanisms but "
                       "no surface trace is a catalogue omission by definition",
        "difference": "H51-B used epicentre geometry only; nodal planes carry orientation information that "
                      "no epicentre pattern contains",
        "source": "Mixed-network USGS ComCat; contributor rights and sponsor-sharing are unresolved. Mechanism coverage and source-specific terms must be checked before use.",
        "cost": "4/5", "gain": "unknown (measure coverage first)"},
]


def load_json_optional(relative: str, evidence_dir: Path | None = None) -> dict[str, Any] | None:
    path = Path(relative) if evidence_dir is None else Path(evidence_dir) / relative
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None


def seismicity_qc(h51: dict[str, Any]) -> dict[str, Any]:
    family = h51.get("seismicity_family", {})
    return family.get("qc") or family.get("catalog_qc") or {}


def build_unique_count(h51: dict[str, Any]) -> int:
    return int(h51.get("uniqueness", {}).get("n_prior_artifacts", 0))


def load_report(report_path: Path) -> dict[str, Any] | None:
    if not report_path.exists():
        return None
    return json.loads(report_path.read_text(encoding="utf-8"))


def fmt(value: Any, digits: int = 4) -> str:
    if value is None:
        return "—"
    try:
        return f"{float(value):.{digits}f}"
    except (ValueError, TypeError):
        return esc(value)


def sha256_path(path: Path) -> str | None:
    if not path.is_file():
        return None
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def validation_record_matches_contract(
    validation: dict[str, Any],
    expected_sha: str | None,
    report: dict[str, Any],
    actual_bytes: int,
) -> bool:
    """Match the report's byte-validation record to the frozen grid and provenance."""
    if not expected_sha or validation.get("sha256") != expected_sha:
        return False
    try:
        positive_cells = int(validation.get("positive_cells", 0))
        minimum = float(validation["minimum_valid_value"])
        maximum = float(validation["maximum_valid_value"])
        split = json.loads(PINNED_SPLIT_PATH.read_text(encoding="utf-8"))
        grid = split["grid"]
        registered = report.get("registered_split", {})
        training = report.get("data", {}).get("competition_training_rasters", {})
        if (
            registered.get("spec_sha256") != sha256_path(PINNED_SPLIT_PATH)
            or training.get("template_sha256") != grid.get("template_sha256")
            or training.get("labels_sha256") != grid.get("official_label_raster_sha256")
        ):
            return False
        transform = grid["transform"]
        width, height = int(grid["width"]), int(grid["height"])
        left, top = float(transform[2]), float(transform[5])
        expected_bounds = [
            left,
            top + height * float(transform[4]),
            left + width * float(transform[0]),
            top,
        ]
        return (
            validation.get("range_pass") is True
            and validation.get("nodata_mask_matches_template") is True
            and validation.get("band_count") == 1
            and validation.get("dtype") == "float32"
            and validation.get("crs") == grid.get("crs") == "EPSG:32611"
            and validation.get("bytes") == actual_bytes
            and positive_cells > 0
            and 0.0 <= minimum <= maximum <= 1.0
            and validation.get("width") == width
            and validation.get("height") == height
            and validation.get("transform") == transform
            and validation.get("bounds") == expected_bounds
        )
    except (KeyError, TypeError, ValueError, OSError, json.JSONDecodeError):
        return False


def verify_h50_artifact(report: dict[str, Any] | None, tiff_path: Path) -> bool:
    """Reopen the actual TIFF bytes; never trust a report-only download link."""
    if not report or not tiff_path.is_file():
        return False
    artifact = report.get("submission_artifact", {})
    evaluation = report.get("evaluation", {})
    if (
        artifact.get("built") is not True
        or evaluation.get("promotion_gate", {}).get("pass") is not True
        or artifact.get("unique_name") != tiff_path.name
    ):
        return False
    actual_sha = sha256_path(tiff_path)
    actual_bytes = tiff_path.stat().st_size
    validation = artifact.get("validation") or {}
    if (
        actual_sha is None
        or actual_sha != artifact.get("sha256")
        or actual_bytes != artifact.get("bytes")
        or not validation_record_matches_contract(validation, actual_sha, report, actual_bytes)
    ):
        return False
    try:
        split = json.loads(PINNED_SPLIT_PATH.read_text(encoding="utf-8"))
        grid = split["grid"]
        with rasterio.open(tiff_path) as ds:
            if (
                ds.count != 1
                or ds.dtypes != ("float32",)
                or ds.crs is None
                or ds.crs.to_string() != grid["crs"]
                or ds.width != grid["width"]
                or ds.height != grid["height"]
                or list(ds.transform) != grid["transform"]
                or not np.isnan(ds.nodata)
            ):
                return False
            values = ds.read(1)
            finite = np.isfinite(values)
            valid_values = values[finite]
            if (
                valid_values.size == 0
                or not np.all((valid_values >= 0.0) & (valid_values <= 1.0))
                or int(np.count_nonzero(valid_values > 0)) != validation["positive_cells"]
                or float(valid_values.min()) != float(validation["minimum_valid_value"])
                or float(valid_values.max()) != float(validation["maximum_valid_value"])
            ):
                return False
    except (KeyError, TypeError, ValueError, OSError, rasterio.errors.RasterioError):
        return False
    return True


def metric_cards(report: dict[str, Any] | None) -> str:
    if not report:
        return """<div class="metrics"><div class="metric"><strong>Preregistered</strong><span>Four spatial macrofolds</span></div><div class="metric"><strong>300 m</strong><span>Official triangular metric support</span></div><div class="metric"><strong>CC BY 4.0</strong><span>Open Nevada relocated catalog</span></div><div class="metric"><strong>0 slots used</strong><span>No portal access is automated</span></div></div>"""
    evaluation = report["evaluation"]
    candidate = evaluation["method_results"]["H50-S1"]["pooled"]["score"]
    incumbent_name = evaluation["incumbent_method"]
    incumbent = evaluation["method_results"][incumbent_name]["pooled"]["score"]
    gate = evaluation["promotion_gate"]
    status = "STATISTICAL PASS" if gate["pass"] else "STATISTICAL FAIL"
    status_class = "pass" if gate["pass"] else "fail"
    return f"""<div class="metrics"><div class="metric"><strong>{fmt(candidate, 5)}</strong><span>H50-S1 pooled holdout DTI</span></div><div class="metric"><strong>{fmt(incumbent, 5)}</strong><span>{esc(incumbent_name)} pooled incumbent</span></div><div class="metric"><strong>{fmt(evaluation["candidate_minus_incumbent_pooled_dti"], 5)}</strong><span>Paired pooled delta</span></div><div class="metric"><strong><span class="status {status_class}">{esc(status)}</span></strong><span>Statistical gate only; submission eligibility is separate</span></div></div>"""


def h50_status_card(
    report: dict[str, Any] | None,
    tiff_path: Path,
    *,
    tiff_verified: bool,
) -> str:
    if not report:
        return ""
    evaluation = report.get("evaluation", {})
    statistical_pass = evaluation.get("promotion_gate", {}).get("pass") is True
    eligibility = report.get("submission_eligibility", {})
    eligibility_pass = eligibility.get("pass") is True
    artifact = report.get("submission_artifact", {})
    download = (
        f'<p><a class="button" href="{esc(tiff_path.as_posix())}" download>'
        f'Download verified H50-S1 research TIFF</a></p>'
        if tiff_verified
        else '<p><span class="tag">No verified H50-S1 download available</span></p>'
    )
    gate_rows = "".join(
        f"<li><strong>{esc(name.replace('_', ' '))}:</strong> "
        f"{'PASS' if gate else 'FAIL'}</li>"
        for name, gate in eligibility.get("gates", {}).items()
    )
    return f"""<article class="card span-12" id="h50-s1-run">
<h2>H50-S1 relocated-plane / terrain-intersection experiment</h2>
<p><strong>Statistical holdout:</strong> {'PASS — research review only' if statistical_pass else 'FAIL — no candidate TIFF is eligible for publication'}.
<strong>Scientific and submission eligibility:</strong> {'PASS' if eligibility_pass else 'NO SLOT'}.</p>
{download}
<p class="sourced">{('SHA-256 ' + esc(artifact.get('sha256'))) if tiff_verified else 'The report or raster bytes did not pass the site-side integrity checks.'}
{(' · ' + str(artifact.get('bytes')) + ' bytes') if tiff_verified else ''}. A verified local holdout artifact remains research-only unless every separate eligibility gate passes; no organizer score or portal receipt is implied.</p>
<ul class="list">{gate_rows}</ul>
<p>Historical 0.2778 score-to-artifact association remains unresolved; the owner-provided 0.3195 is not independently verified or a current-leader claim. No fresh leaderboard monitoring was performed.</p>
</article>"""


def h51_block(repo_dir: Path, ship_path: Path, check_path: Path) -> str:
    """Render the H51 candidate panel: one-click download first, then the honest numbers."""
    if not ship_path.exists():
        return ""
    ship = json.loads(ship_path.read_text())
    check = json.loads(check_path.read_text()) if check_path.exists() else {}
    tif = repo_dir / ship["outputs"]["tif"]
    if not tif.exists():
        return ""
    fmtinfo = ship["format"]
    gate = ship["gate"]
    uniq = check.get("uniqueness", {})
    inst = ship["instrument"]
    return f"""
<section class="main" id="h51-candidate"><div class="shell"><div class="grid">
<article class="card span-12">
<div class="eyebrow">Research candidate · H51</div>
<h2 style="margin-top:.2em">Download the H51 research-only GeoTIFF</h2>
<p><a class="button" href="{esc(ship['outputs']['tif'])}" download>Download {esc(ship['name'])}-{esc(ship['stamp'])}.tif</a>
<a class="button secondary" style="color:#172a33;background:#dcefe9" href="{esc(ship['outputs']['zip'])}" download>Download .zip</a>
<a class="button secondary" style="color:#172a33;background:#eceae1" href="submission.html">How to submit</a></p>
<p class="sourced">SHA-256 <span class="hash">{esc(ship['outputs']['sha256'])}</span> · {ship['outputs']['bytes']:,} bytes · stamp {esc(ship['stamp'])}</p>
<div class="metrics">
<div class="metric"><strong>{ship['budgets']['n']:,}</strong><span>predicted pixels (values 0 / 1 only)</span></div>
<div class="metric"><strong>{fmt(ship['predicted']['DTI'], 4)}</strong><span>consensus-instrument estimate, not an organizer score (LOO MAE {fmt(inst['loo_mae'], 4)})</span></div>
<div class="metric"><strong>{fmt(gate['measured_iou2px_max'], 3)}</strong><span>worst 200 m-proximity IoU vs 26 prior artifacts (gate &lt; 0.5)</span></div>
<div class="metric"><strong>0</strong><span>pixels shared with any prior artifact</span></div>
</div>
<div class="callout danger" style="margin-top:16px"><strong>Research-only; do not upload yet.</strong>
The displayed {fmt(ship['predicted']['DTI'], 2)} is a local consensus-instrument estimate (leave-one-out RMSE {fmt(inst['loo_rmse'], 3)}), not an organizer score. The often-repeated 0.2778 score-to-artifact association remains unresolved because the GEMSDOE32 owner site labels H33-2-B2 unscored and 0.2747 a model projection; 0.3195 is owner-provided historical context, not a verified current leader or like-for-like score. The exact derived scarp raster's reuse license and mixed-network ComCat rights/shareability are unresolved, so this file is not cleared for external competition upload. No slot or upload is claimed.</div>
<p class="sourced">Format: {esc(fmtinfo['dtype'])}, {esc(fmtinfo['crs'])}, {fmtinfo['shape'][0]}×{fmtinfo['shape'][1]},
values in [0, 1] = {esc(fmtinfo['values_in_0_1'])}, NaN only outside the published footprint = {esc(fmtinfo['outside_footprint_all_nan'])},
all in-footprint values finite = {esc(fmtinfo['inside_footprint_all_finite'])}. Uniqueness verdict:
<strong>{esc('PASS' if uniq.get('verdict_unique') else uniq.get('verdict', 'not run'))}</strong> · identical hashes: {len(uniq.get('identical_sha256', []))}.</p>
</article>
<article class="card span-7"><h2>What it is</h2>
<p>{esc(ship['design'])}. The core ({ship['budgets']['k_core']:,} dots) follows the score-consensus posterior
built from 25 locally archived artifact/score records (leave-one-out Spearman {fmt(inst['loo_spearman'], 3)}
within that corpus; score provenance is not independently authenticated). The exploration dots ({ship['budgets']['k_far']:,}) sit more than 200 m from every prior dot and are
placed only by independent evidence: seismicity lineament corridors, TMI magnetic ridges, radiometric-K ridges,
and thermal-spring alignment — the part of the map no prior submission has touched.</p>
<p class="sourced">Evidence: <span class="hash">evidence/h51_ship.json</span>,
<span class="hash">evidence/h51_consensus.json</span>, <span class="hash">evidence/h51_check_submission.json</span>,
analysis in <span class="hash">docs/research/h51-analysis.md</span>, ranked hypotheses in
<span class="hash">docs/research/h51-hypotheses.md</span>, and the failed truth-density inversion in
<span class="hash">docs/research/h51-truth-map.md</span>.</p></article>
<article class="card span-5"><h2>Submit it in five steps</h2>
<ol class="list">
<li>Download the .tif above and check the SHA-256.</li>
<li>Open <a href="https://www.drivendata.org/competitions/306/competition-doe-gems/">the competition</a> and sign in manually.</li>
<li>Upload the single GeoTIFF; do not re-save or re-project it.</li>
<li>Use the unique name and the short note below.</li>
<li>Record the portal receipt in the repository before claiming a score.</li>
</ol>
<p><strong>Unique name:</strong> <code>{esc(ship['name'])}-{esc(ship['stamp'])}.tif</code><br>
<strong>Optional note:</strong> <q>{esc(ship['claim_note'])}</q></p>
<p class="sourced">No automated portal access: this project never uploads for you.</p></article>
</div></div></section>"""




def three_candidates_card(ship: dict[str, Any] | None, h51: dict[str, Any] | None,
                          compare: dict[str, Any] | None,
                          h53: dict[str, Any] | None = None,
                          h53_final: dict[str, Any] | None = None) -> str:
    """All candidate GeoTIFFs on this branch, against the one frame they share.

    The sessions used different local instruments, so only the shared off-catalogue
    frame (identical truth mask, identical scoring code) can order them. Report that column next
    to each file's own instrument, and never imply an organizer score.
    """
    rows_data = (compare or {}).get("rows", {})
    truth_px = (compare or {}).get("truth_px")
    uni = (compare or {}).get("uniform_control", {})
    control = (f"{fmt(uni.get('dti_mean'), 4)} mean / {fmt(uni.get('dti_max'), 4)} max"
               if uni else "not measured")
    body = []
    if ship:
        shared = next((r for key, r in rows_data.items() if ship["name"] in key), None)
        body.append((
            "A · H51 corridor-consensus mix",
            f"{ship['budgets']['n']:,}",
            f"{fmt(ship['predicted']['DTI'], 4)} (consensus instrument, leave-one-out)",
            (f"{fmt(shared.get('dti'), 4)} ({fmt(shared.get('tp_per_dot'), 4)} credit/dot)"
             if shared else "not measured"),
            (f"{ship['gate']['pixels_shared_with_any_prior']} shared px · worst 2 px-proximity IoU "
             f"{fmt(ship['gate']['measured_iou2px_max'], 4)}"),
            (f'<a class="button" href="{esc(ship["outputs"]["tif"])}" download>Download .tif</a><br>'
             f'<a href="{esc(ship["outputs"]["allfinite"])}" download>all-finite twin</a> · '
             f'<a href="{esc(ship["outputs"]["zip"])}" download>.zip</a>')))
    if h51:
        primary = h51["outputs"]["primary"]
        leaf = primary["path"].split("/")[-1]
        shared = next((r for key, r in rows_data.items() if leaf in key), None)
        own = h51.get("instruments", {}).get("candidate", {}).get("sgmc_off", {})
        body.append((
            "B · H51 scarp + radiometric lineaments (parallel session)",
            f"{int(primary['footprint_nonzero']):,}",
            (f"{fmt(own.get('credit_per_dot'), 4)} credit/dot on its own mass sweep"
             if own else "see results.html"),
            (f"{fmt(shared.get('dti'), 4)} ({fmt(shared.get('tp_per_dot'), 4)} credit/dot)"
             if shared else "not measured"),
            ("block Jaccard not informative at 32 px · 2.7 % exact overlap with the one prior file "
             "available locally"),
            (f'<a class="button" href="{esc(primary["path"])}" download>Download .tif</a><br>'
             f'<a href="{esc(h51["outputs"]["allfinite"]["path"])}" download>all-finite twin</a> · '
             f'<a href="{esc(h51["outputs"]["zip"]["path"])}" download>.zip</a>')))
    if h53:
        inst = h53.get("instrument", {})
        body.append((
            "C · H53 TMI × K/U conjunction (this session)",
            f"{int(h53['budgets']['n']):,}",
            ("shared-frame DTI "
             f"{fmt(inst.get('dti'), 4)} vs mass-matched uniform max "
             f"{fmt(inst.get('uniform_dti_max'), 4)}; "
             f"{inst.get('quadrants_positive')}/{inst.get('quadrants_total')} quadrants"),
            (f"{fmt(inst.get('dti'), 4)} ({fmt(inst.get('tp_per_dot'), 4)} credit/dot)"),
            (f"{h53['gate']['pixels_shared_with_any_prior']} shared px · worst 2 px-proximity IoU "
             f"{fmt(h53['gate']['measured_iou2px_max'], 4)} vs {h53['gate']['n_prior']} priors"),
            (f'<a class="button" href="{esc(h53["outputs"]["tif"])}" download>Download .tif</a><br>'
             f'<a href="{esc(h53["outputs"]["allfinite"])}" download>all-finite twin</a> · '
             f'<a href="{esc(h53["outputs"]["zip"])}" download>.zip</a>')))
    if not body:
        return ""
    rows = "".join(
        "<tr><td><strong>" + r[0] + "</strong></td><td>" + r[1] + "</td><td>" + r[2]
        + "</td><td>" + r[3] + "</td><td>" + r[4] + "</td><td>" + r[5] + "</td></tr>"
        for r in body)
    incumbent = next((r for key, r in rows_data.items() if "seislin-44709" in key), None)
    inc_row = (
        '<p class="sourced">Reference point on the same frame: the frozen incumbent '
        f'<code>gems50-seislin-44709</code> scores <strong>{fmt(incumbent.get("dti"), 4)}</strong>, '
        "but it cannot be resubmitted — its novelty check fails against the prior artifacts.</p>"
        if incumbent else "")
    title = ("Three candidate GeoTIFFs on this branch — one shared frame, one ordering"
             if h53 else "Two candidate GeoTIFFs on this branch — one shared frame, one ordering")
    return f"""<section class="main"><div class="shell"><article class="card span-12" id="candidates">
<h2>{title}</h2>
<div class="wide"><table><tr><th>candidate</th><th>dots</th><th>its own instrument (not comparable)</th>
<th>shared off-catalogue frame DTI</th><th>uniqueness evidence</th><th>download</th></tr>{rows}</table></div>
<p class="sourced">All files were re-measured on one identical frame — unmasked domain, truth = SGMC fault
pixels more than 300 m from the given catalogue{f", {truth_px:,} px" if truth_px else ""} — with the same
code; uniform controls are mass-matched per row (A/B control: {control}). On this frame the
parallel-session scarp + radiometric candidate (B) is the strongest in-repo file, the H53 conjunction
file (C) matches the consensus mix (A) at 21 % fewer dots with 24 % more credit per dot, and A scores
below a matched uniform control. Neither file is organizer-scored: these are local
proxy instruments, this repository never uploads anything, and the slot decision is the owner's.
Source review found unresolved reuse/shareability for the derived scarp raster and mixed-network
ComCat; no artifact is cleared for external competition upload until its exact inputs are
rights-reviewed. These local proxy instruments do not override the no-slot rule or authorize
an upload.</p>
{inc_row}
</article></div></section>"""


def build_pages(output_dir: Path, report_path: Path, tiff_path: Path,
                evidence_dir: Path | None = None, h51_ship: Path | None = None,
                h51_check: Path | None = None, h53_ship: Path | None = None,
                h53_check: Path | None = None,
                h53_final: Path | None = None) -> list[Path]:
    report = load_report(report_path)
    relative_tiff = tiff_path.as_posix()
    tiff_verified = verify_h50_artifact(report, tiff_path)
    h50_card = h50_status_card(report, tiff_path, tiff_verified=tiff_verified)
    if report:
        status_text = "verified research-only H50-S1 artifact" if tiff_verified else "no verified H50-S1 raster"
        candidate_sha = report.get("submission_artifact", {}).get("sha256", "not available")
        candidate_hash = (
            f'<div class="sourced">H50-S1 GeoTIFF SHA-256 verified: '
            f'<span class="hash">{esc(candidate_sha)}</span></div>'
            if tiff_verified else '<div class="sourced">No H50-S1 TIFF is linked until byte and grid checks pass.</div>'
        )
    else:
        status_text = "H50-S1 awaiting a verified run (the H51 candidates above are separate)"
        candidate_hash = ""

    h51 = load_h51((evidence_dir / "build_h51.json") if evidence_dir else None)
    h52 = load_h52((evidence_dir / "build_h52.json") if evidence_dir else None)
    h52a = load_h52a((evidence_dir / "build_h52a.json") if evidence_dir else None)
    ship = load_json_optional("evidence/h51_ship.json")
    compare = load_json_optional("evidence/h51_candidate_frame_compare.json")
    h51_html = h51_block(output_dir, h51_ship or H51_SHIP_DEFAULT,
                         h51_check or H51_CHECK_DEFAULT)
    h53 = load_json_optional((h53_ship or H53_SHIP_DEFAULT).as_posix())
    h53_final_data = load_json_optional((h53_final or H53_FINAL_DEFAULT).as_posix())
    h53_html = h53_block(output_dir, h53_ship or H53_SHIP_DEFAULT,
                         h53_check or H53_CHECK_DEFAULT)
    if not (h53 and (output_dir / h53["outputs"]["tif"]).exists()):
        h53, h53_html = None, ""
    secondary_card = three_candidates_card(ship, h51, compare, h53, h53_final_data)
    h52_band = h52_download_band(h52, h52a) if h52 else ""
    h52_compare_card = h52_vs_consensus_card(h52, evidence_dir) if h52 else ""
    # H52 (this session's validated H51-union) is the strongest file on the shared off-catalogue
    # frame of every candidate this project has produced (0.1518 vs H53's 0.0565 and H51's 0.1158);
    # it is the hero download whenever it exists. H53 and the bare H51 ship file are shown below the
    # fold as the other concurrently-developed, separately-tracked candidates.
    if h52 and (output_dir / h52["outputs"]["primary"]["path"]).exists():
        hero_download = f'docs/downloads/{Path(h52["outputs"]["primary"]["path"]).name}'
        hero_label = "Download the current recommendation (H52)"
    elif h53:
        hero_download = h53["outputs"]["tif"]
        hero_label = "Download the H53 candidate GeoTIFF"
    else:
        hero_download = (ship["outputs"]["tif"]
                         if ship and (output_dir / ship["outputs"]["tif"]).exists()
                         else "downloads/")
        hero_label = "Download the H51 candidate GeoTIFF"
    index_note = ""
    candidates_card = ""
    if h51:
        candidates_card = candidates_short_html()
        primary = h51["outputs"]["primary"]
        index_note = (
            '<p class="sourced"><strong>Four in-repo candidates from three concurrent sessions,</strong> '
            f'not any organizer\'s: this page publishes the corridor-consensus mix '
            f'(<code>gemsdoe50-h51-corridor-consensus-mix-20261007T0200Z.tif</code>, recorded by its own '
            'session as a proxy-gate FAIL), the H53 TMI x K/U conjunction file '
            f'(<code>gemsdoe50-h53-tmiconj-20261007T0345Z.tif</code>, shared-frame DTI 0.0565), '
            'the scarp + radiometric lineaments file '
            f'(<code>{esc(Path(primary["path"]).name)}</code>, {int(primary["footprint_nonzero"]):,} predicted '
            'pixels, shared-frame DTI 0.1158), and <strong>H52</strong> — this session\'s union of H51 with a '
            'new scarp-matched-filter + drainage-deflection method, shared-frame DTI <strong>0.1518</strong>, '
            'the strongest of the four candidates on the one shared off-catalogue frame all were re-measured '
            'on, disclosed as a transparent fusion of this project\'s own prior and new work (~78% of its mass '
            'is H51\'s). Local proxy instruments only; <strong>not organizer-scored</strong>, no slot used. '
            '<a href="results.html">Controls, folds and uniqueness audit →</a> · '
            'machine-readable feed: <a href="docs/data/feed.json">docs/data/feed.json</a></p>'
        )

    index_body = f"""
<main><section class="hero"><div class="shell"><div class="eyebrow">DOE GEMS Prize Challenge · audit-first research</div><h1>Map what the catalogue missed.</h1><p>GEMSDOE50 tests whether waveform-relocated Nevada earthquake planes can point to plausible, previously unmapped fault traces—without copying a prior submission or spending a scoring slot before spatial validation.</p><div class="actions"><a class="button" href="{esc(hero_download)}" download>{esc(hero_label)}</a><a class="button secondary" href="submission.html">How to submit (5 steps)</a></div>{candidate_hash}</div></section>
{h52_band}
{h52_compare_card}
{h53_html}
{h51_html}
{h50_card}
{secondary_card}
<section class="main"><div class="shell"><div class="grid"><article class="card span-8"><h2>Executive summary</h2><p><strong>What the scores actually say:</strong> with binary dots the official distance-weighted Tversky index is exactly <code>DTI = T / (0.2&middot;N + 0.8&middot;G)</code>, with <code>N</code> the predicted pixel count, <code>T</code> the credit captured inside the 300 m kernel, and <code>G</code> the hidden truth mass. Inverting a pinned blind-lattice artifact fixes <code>G &asymp; 12,226 px</code> (0.24 % of the unmasked footprint).</p><p>The local archive contains 25 hash-verified artifact/score records, whose score provenance is not independently authenticated. Within that corpus the best converts 0.1097 credit per dot (with a separate owner-quoted 0.2600 claim), and best estimated coverage is 59.3 %, reached only with 183,642 dots. Conditional on the corpus-derived G estimate, a hypothetical DTI of 0.3195 at 30,000 dots corresponds to about 41.2 % estimated coverage; this does not verify the owner-provided historical 0.3195 or its provenance. Re-blending, re-spacing or pruning the existing corpus cannot establish improved geography; any new detector still needs independent validation.</p>{metric_cards(report)}{index_note}<p class="sourced">Status: {esc(status_text)}. H51/H52: the consensus instrument predicts held-out scores at leave-one-out Spearman 0.973, but a trivial similarity predictor already reaches 0.905 and a block-grid truth-density inversion fails leave-one-out, so the score history constrains efficiency, not geography. Historical sibling-repository scores are not used as current official leaderboard claims or mapped to a TIFF.</p></article><aside class="card span-4"><h2>Decision rule</h2><ul class="list"><li>At least +0.005 absolute pooled DTI over the frozen incumbent</li><li>Positive delta in at least 3 of 4 macrofolds</li><li>95% spatial-block bootstrap lower bound above zero</li><li>Beat both matched translation and year-shuffle controls</li><li>Otherwise: <strong>no slot</strong></li></ul><a href="results.html">View full evidence →</a></aside><article class="card span-6"><h2>What this is—and is not</h2><p>This is a research proxy against existing mapped faults, not the hidden expert-labeled test set. A local pass is necessary for review but is not an organizer score or a promise of prize performance.</p><p>The Nevada catalog is CC BY 4.0, but it lacks event-specific location covariance. A precise-looking coordinate is not proof of a precise location; a hypocenter projection is not automatically a surface trace.</p></article><article class="card span-6"><h2>Project values</h2><p><span class="tag">Maximize P(Win)</span> Choose evidence that can improve the final result, not merely a public proxy.</p><p><span class="tag">Own the Outcome</span> Publish hashes, controls, limitations, and a clear no-go when a gate fails.</p><p><a href="methods.html">Read the protocol, sources, and limitations →</a></p></article>{candidates_card}<article class="card span-12"><h2>Verified primary links</h2><div class="grid"><div class="span-4"><strong>Competition specification</strong><br><a href="https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/">Metric, inputs, and TIFF contract</a></div><div class="span-4"><strong>Nevada seismicity source</strong><br><a href="https://doi.org/10.5281/zenodo.11167510">Trugman (2024), Zenodo v2 · CC BY 4.0</a></div><div class="span-4"><strong>Official leaderboard</strong><br><a href="https://www.drivendata.org/competitions/306/competition-doe-gems/leaderboard/">Open manually; this project does not scrape it</a></div></div></article></div></div></section></main>
"""


    if report:
        evaluation = report["evaluation"]
        method_rows = []
        for method, result in evaluation["method_results"].items():
            pooled = result["pooled"]
            method_rows.append(
                f"<tr><td>{esc(method)}</td><td>{fmt(pooled['score'], 6)}</td><td>{pooled['truth_cells']}</td><td>{pooled['prediction_cells']}</td><td>{fmt(pooled['tp_weight'], 1)}</td><td>{fmt(pooled['fp_weight'], 1)}</td><td>{fmt(pooled['fn_weight'], 1)}</td></tr>"
            )
        fold_rows = []
        candidate_folds = evaluation["method_results"]["H50-S1"]["folds"]
        incumbent_folds = evaluation["method_results"][evaluation["incumbent_method"]]["folds"]
        for candidate_fold, incumbent_fold in zip(candidate_folds, incumbent_folds, strict=True):
            fold_rows.append(
                f"<tr><td>{esc(candidate_fold['id'])}</td><td>{fmt(candidate_fold['dti'], 6)}</td><td>{fmt(incumbent_fold['dti'], 6)}</td><td>{fmt(candidate_fold['dti'] - incumbent_fold['dti'], 6)}</td><td>{candidate_fold['prediction_cells']}</td><td>{candidate_fold['truth_cells']}</td></tr>"
            )
        controls = evaluation["translation_controls"]
        time_controls = evaluation["time_shuffle_controls"]
        control_table = "".join(
            f"<tr><td>{esc(item['id'])}</td><td>{fmt(item['pooled_dti'], 6)}</td></tr>"
            for item in controls["scores"]
        )
        time_table = "".join(
            f"<tr><td>{esc(item['id'])}</td><td>{fmt(item['pooled_dti'], 6)}</td></tr>"
            for item in time_controls["scores"]
        )
        density_scores = evaluation["smoothed_density_controls"]["pooled_dti"]
        density_table = "".join(
            f"<tr><td>{esc(name)}</td><td>{fmt(score, 6)}</td></tr>"
            for name, score in density_scores.items()
        )
        ci = evaluation["subtile_bootstrap"]["percentile_ci_95"]
        eligibility = report.get("submission_eligibility", {})
        eligibility_gates = eligibility.get("gates", {})
        eligibility_rows = "".join(
            f'<tr><td>{esc(name.replace("_", " "))}</td>'
            f'<td>{"PASS" if passed else "FAIL"}</td></tr>'
            for name, passed in eligibility_gates.items()
        )
        component_rows = []
        for name, passed in evaluation["promotion_gate"]["components"].items():
            label = name.replace("_", " ")
            result_text = "PASS" if passed else "FAIL"
            component_rows.append(
                f'<tr><td>{esc(label)}</td><td>{result_text}</td></tr>'
            )
        gate_rows_html = "".join(component_rows)
        score_summary = f"""
<article class="card span-12"><h2>Metric and pooled components</h2><p>DTI uses the official 300 m triangular kernel, α=0.2, β=0.8; predictions are compared at equal binary probability mass. Local pooled holdout is not an official test score.</p><div class="wide"><table><thead><tr><th>Method</th><th>Pooled DTI</th><th>Truth cells</th><th>Predicted cells</th><th>TP weight</th><th>FP weight</th><th>FN weight</th></tr></thead><tbody>{"".join(method_rows)}</tbody></table></div><h3>Fold-wise paired scores</h3><div class="wide"><table><thead><tr><th>Macrofold</th><th>H50-S1</th><th>Incumbent ({esc(evaluation["incumbent_method"])})</th><th>Delta</th><th>Predictions</th><th>Truth</th></tr></thead><tbody>{"".join(fold_rows)}</tbody></table></div><p><strong>16-block bootstrap 95% interval:</strong> [{fmt(ci[0], 6)}, {fmt(ci[1], 6)}]. Candidate − incumbent pooled DTI = {fmt(evaluation["candidate_minus_incumbent_pooled_dti"], 6)}.</p></article>
<article class="card span-6"><h2>Spatial translations</h2><p>32 no-wrap offsets at 5–20 km; 95th percentile DTI {fmt(controls["pooled_dti_q95"], 6)}. Candidate DTI {fmt(evaluation["method_results"]["H50-S1"]["pooled"]["score"], 6)}.</p><details><summary>Show individual controls</summary><div class="wide"><table><thead><tr><th>Control</th><th>Pooled DTI</th></tr></thead><tbody>{control_table}</tbody></table></div></details></article>
<article class="card span-6"><h2>Origin-year shuffles</h2><p>{time_controls["count"]} refits with shuffled years; 95th percentile DTI {fmt(time_controls["pooled_dti_q95"], 6)}. Candidate DTI {fmt(evaluation["method_results"]["H50-S1"]["pooled"]["score"], 6)}.</p><details><summary>Show individual controls</summary><div class="wide"><table><thead><tr><th>Control</th><th>Pooled DTI</th></tr></thead><tbody>{time_table}</tbody></table></div></details></article>
<article class="card span-12"><h2>Matched smoothed-density controls</h2><p>Gaussian-smoothed counts from the same relocated catalog events, scored at equal mass on the same blocked holdout. This controls spatial density only; it does not remove aftershocks or mine/injection confounding. Candidate must strictly beat all three scales (300 m, 1 km, and 2 km).</p><div class="wide"><table><thead><tr><th>Density map</th><th>Pooled DTI</th></tr></thead><tbody>{density_table}</tbody></table></div></article>
<article class="card span-12"><h2>Statistical holdout gate</h2><div class="wide"><table><thead><tr><th>Criterion</th><th>Result</th></tr></thead><tbody>{gate_rows_html}</tbody></table></div><p><strong>Statistical decision: {esc(evaluation["promotion_gate"]["decision"].replace("_", " "))}.</strong> This is separate from submission eligibility; no portal slot is used automatically.</p><p><a href="{esc(report_path.as_posix())}">Open machine-readable report JSON</a> · Report SHA-256: <span class="hash">{esc(sha256_report(report_path))}</span></p></article>
<article class="card span-12"><h2>Scientific and provenance eligibility</h2><p><strong>{esc(eligibility.get("decision", "NOT RECORDED"))}.</strong> A statistical pass alone does not authorize a slot.</p><div class="wide"><table><thead><tr><th>Eligibility gate</th><th>Result</th></tr></thead><tbody>{eligibility_rows}</tbody></table></div><p>{esc(eligibility.get("note", "Eligibility details not recorded."))}</p></article>
"""
    else:
        score_summary = '<article class="card span-12"><h2>Results pending</h2><p>No DTI has been computed. The holdout split and mask hashes are frozen before scoring.</p><p>Run instructions and protocol are in the repository; no submission slot has been used.</p></article>'

    results_body = f"""<main><section class="pagehead"><div class="shell"><div class="eyebrow">Evidence, not leaderboard claims</div><h1>Holdout results</h1><p class="muted">All values below come from a spatial proxy on existing labels. The competition's hidden expert-labeled labels are not available here.</p></div></section><section class="main"><div class="shell"><div class="grid">{score_summary}</div></div></section></main>"""

    if report:
        gate = report["evaluation"]["promotion_gate"]
        eligibility = report.get("submission_eligibility", {})
        eligible = eligibility.get("pass") is True
        state = (
            "Statistical proxy PASS; separate scientific/provenance gates also pass — owner review only."
            if gate.get("pass") is True and eligible
            else "Statistical proxy PASS; separate eligibility gates fail — NO SLOT."
            if gate.get("pass") is True
            else "Statistical proxy failed — no candidate TIFF or weekly slot."
        )
        artifact = report.get("submission_artifact", {})
        name = artifact.get("unique_name", tiff_path.name)
        note = artifact.get("optional_note", "")
        hash_html = (
            f'<p>SHA-256 verified against the TIFF bytes: '
            f'<span class="hash">{esc(artifact.get("sha256"))}</span></p>'
            if tiff_verified else ""
        )
        download_html = (
            f'<p><a class="button" href="{esc(relative_tiff)}" download>Download research-only {esc(name)}</a></p>'
            if tiff_verified
            else "<p>No verified, downloadable H50-S1 GeoTIFF is available.</p>"
        )
        submit_card = f"""<div class="callout {"success" if gate.get("pass") is True and eligible else "danger"}"><strong>{esc(state)}</strong> No upload was performed by this project.</div><h2>Current H50-S1 artifact</h2>{download_html}<p><strong>Planned unique filename:</strong> <code>{esc(name)}</code></p><p><strong>Optional note:</strong> <q>{esc(note)}</q></p>{hash_html}<p><strong>Submission status:</strong> {esc(eligibility.get("decision", "NO_SLOT"))}. Re-check the official specification and all data rights. A research download is not authorization to upload and is not an organizer receipt.</p>"""
    else:
        state = "Experiment not yet run. No submission slot has been used."
        submit_card = f"""<div class="callout"><strong>{esc(state)}</strong></div><p>There is no candidate GeoTIFF to upload. Do not use a weekly slot until the spatial holdout, matched controls, raster-byte validation, and owner review are complete.</p><p><strong>Planned unique filename, if a verified build is produced:</strong> <code>gemsdoe50-h50s1-relocated-planes-20261006-research.tif</code></p><p><strong>Planned optional note:</strong> <q>Relocated Nevada event-plane lineaments; 300 m known-fault exclusion; research proxy, not organizer-scored.</q></p>"""
    submission_body = f"""<main><section class="pagehead"><div class="shell"><div class="eyebrow">No automated portal access</div><h1>Submission instructions</h1><p class="muted">Use this page only if the local gate has passed and the owner independently approves the artifact.</p></div></section><section class="main"><div class="shell"><div class="grid"><article class="card span-12">{submit_card}</article><article class="card span-8"><h2>Manual checklist (only after PASS)</h2><ol class="list"><li>Download the GeoTIFF and independently verify its SHA-256 and the byte-validation report in <a href="results.html">Results</a>.</li><li>Re-read the current <a href="https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/">official problem specification</a> and rules; confirm the external-data license and required AI-use disclosure in the final narrative.</li><li>Sign in to DrivenData manually, open the DOE GEMS competition, and choose a weekly feedback slot only if one remains and the owner approves.</li><li>Upload the single-band float32 GeoTIFF. Do not change its grid, nodata footprint, or prediction values after validation.</li><li>Use the unique filename and optional note shown above, then manually verify the portal receipt and record it in this repository before making any claim of acceptance.</li></ol><div class="callout danger"><strong>Do not upload on a failed gate.</strong> A local proxy pass is not a score guarantee and is not a portal receipt.</div></article><aside class="card span-4"><h2>Portal warning caught</h2><p>The previous portal error was: <code>Predicted values must be in range [0, 1]</code>.</p><p>This pipeline reopens the actual GeoTIFF bytes and checks finite in-footprint values, `[0,1]` range, one float32 band, grid alignment, and nodata-mask agreement with the sample template.</p><p><span class="tag">No slot used by code</span></p></aside></div></div></section></main>"""

    methods_body = """<main><section class="pagehead"><div class="shell"><div class="eyebrow">Preregistered research</div><h1>Methods, sources & limitations</h1><p class="muted">The method was ranked before implementation; the exact spatial split and implementation constants were frozen before DTI calculation.</p></div></section><section class="main"><div class="shell"><div class="grid"><article class="card span-8"><h2>H50-S1: relocated event-plane geometry</h2><p>Use only waveform-relocated (`reloc=1`) Nevada catalog events inside the valid competition footprint. Fit compact local 3-D neighborhoods, require year support and stable horizontal strike, intersect plausible planes with the exact-grid USGS 3DEP terrain elevation surface, and rasterize the resulting diagnostic line proxy. Catalog/DEM vertical-datum reconciliation remains unresolved, so this is not a validated surface trace. Known mapped faults are masked by 300 m for the output; holdout labels are used only for scoring, never for line fitting.</p><p>Frozen parameters, folds, control design, and metric formula are documented in <a href="https://github.com/buffedlizard55-lab/GEMSDOE50/blob/main/docs/h50s1-protocol-addendum.md">the protocol addendum</a> and <a href="https://github.com/buffedlizard55-lab/GEMSDOE50/blob/main/docs/hypotheses-preregistered.md">the ranked preregistration</a>.</p><p>Prior-art and 3–5-hypothesis review: <a href="docs/research/earthquake-geometry-review-20261006.md">seismicity audit</a> and <a href="docs/research/hypothesis-ranking-20261006.md">candidate ranking</a>.</p><p><strong>Comparator policy:</strong> H50-prior is fixed as the primary comparator before holdout scoring. H32-D, H47-S3, and H48-DS are secondary context only; their holdout scores do not select the incumbent. Three same-event Gaussian-smoothed density maps (300 m, 1 km, and 2 km) are required matched controls. No prior prediction pixels are copied to the candidate artifact.</p><p><strong>Slot eligibility:</strong> formal aftershock declustering, mine/injection-site screening, and event-location uncertainty suitable for the raster width remain additional hard gates. Until they pass, any numeric result and unique TIFF are research-only and <strong>NO SLOT</strong>.</p></article><article class="card span-4"><h2>Data & permissions</h2><ul class="list"><li>Nevada catalog: <a href="https://doi.org/10.5281/zenodo.11167510">Zenodo v2</a>, CC BY 4.0; attribution and license link required.</li><li>Competition labels/template: SHA-pinned public Dropbox mirrors from a local source bridge manifest; provenance caveat is in the experiment report.</li><li>New H50-S1 raw data stays in ignored `.arena/`; the report records hashes and access links for verification.</li><li>Inherited ComCat/SGMC/LiDAR/radiometric files are not H50-S1 inputs. ComCat rights/shareability and location uncertainty remain unresolved; legacy refresh workflows are disabled.</li><li>Competition rules require external inputs to be licensed and shareable with the sponsor.</li></ul></article><article class="card span-6"><h2>Scientific limitations</h2><ul class="list"><li>Existing USGS/INGENIOUS labels are an imperfect proxy, not the hidden expert-labeled test set.</li><li>The catalog has no event-specific location covariance; model errors can exceed the 300 m scoring kernel, and orientation bootstrap is not a position-error estimate.</li><li>Formal aftershock declustering and mine/injection-site masks are not yet applied, so the density control alone does not clear those confounds.</li><li>Hypocenter planes are not guaranteed to intersect a mapped surface fault at the projected line.</li><li>Observed earthquakes are biased toward active faults, and waveform relocation is a subset of the full catalog.</li><li>A lineament or local DTI increase is not proof of geothermal productivity or a fault discovery.</li></ul></article><article class="card span-6"><h2>Leaderboard & AI disclosure</h2><p>DrivenData's Terms of Use restrict automated leaderboard monitoring and manual copying without written consent. This site links to the official board but does not poll, scrape, or publish a live snapshot.</p><p>Before any final competition entry, disclose AI assistance as required by the current NLR/DOE rules and describe human review. This repository does not submit on the user's behalf.</p></article></div></div></section></main>"""

    if h51:
        results_body = results_body + h51_results_block(h51, evidence_dir)
        methods_body = methods_body + h51_methods_block(h51)
        submission_body = h51_download_band(h51) + submission_body + h51_submission_block(h51)
    if h53:
        results_body = results_body + h53_results_block(h53, h53_final_data)
        methods_body = methods_body + h53_methods_block(h53)
        submission_body = (h53_download_band(h53) + submission_body
                           + h53_submission_block(h53) + h53_html)
    submission_body = submission_body + h51_html
    if h52:
        results_body = h52_compare_card + h52_results_block(h52, h52a, evidence_dir) + results_body
        methods_body = h52_methods_block(h52) + methods_body
        submission_body = (h52_band + h52_submission_block(h52, h52a) + submission_body)

    pages = {
        "index.html": page("Executive summary", index_body, active="overview"),
        "results.html": page("Holdout results", results_body, active="results"),
        "submission.html": page("Submission instructions", submission_body, active="submission"),
        "methods.html": page("Methods and evidence", methods_body, active="methods"),
    }
    output_dir.mkdir(parents=True, exist_ok=True)
    written = []
    for name, content in pages.items():
        path = output_dir / name
        path.write_text(content, encoding="utf-8")
        written.append(path)
    return written


def sha256_report(report_path: Path) -> str:
    import hashlib

    if not report_path.exists():
        return "not available"
    return hashlib.sha256(report_path.read_bytes()).hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", default=".")
    parser.add_argument("--report", default=str(REPORT_DEFAULT))
    parser.add_argument("--tiff", default=str(TIFF_DEFAULT))
    parser.add_argument("--evidence-dir", default="evidence")
    parser.add_argument("--h51-ship", default=str(H51_SHIP_DEFAULT))
    parser.add_argument("--h51-check", default=str(H51_CHECK_DEFAULT))
    parser.add_argument("--h53-ship", default=str(H53_SHIP_DEFAULT))
    parser.add_argument("--h53-check", default=str(H53_CHECK_DEFAULT))
    parser.add_argument("--h53-final", default=str(H53_FINAL_DEFAULT))
    args = parser.parse_args()
    written = build_pages(Path(args.output_dir), Path(args.report), Path(args.tiff),
                          Path(args.evidence_dir), Path(args.h51_ship), Path(args.h51_check),
                          Path(args.h53_ship), Path(args.h53_check), Path(args.h53_final))
    for path in written:
        print(path)


if __name__ == "__main__":
    main()
