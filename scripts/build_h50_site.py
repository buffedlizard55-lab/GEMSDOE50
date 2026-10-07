#!/usr/bin/env python3
"""Build the static executive-summary, results, methods, and submission pages."""

from __future__ import annotations

import argparse
import html
import json
from pathlib import Path
from typing import Any

REPORT_DEFAULT = Path("evidence/results/h50s1-evaluation-20261006.json")

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
H53_BUILD_DEFAULT = Path("evidence/h53-build-20261007.json")
H53_VALIDATION_DEFAULT = Path("evidence/h53-validation-20261007.json")
H53_PORTAL_NAME = "GEMSDOE50-H53-PROBE-TMI-POINTLINEATION-20261007"
H53_OPTIONAL_NOTE = ("Survey-normalized 2 m probe point-pattern lineations concordant with GeoDAWN "
                     "TMI_up150; 300 m known-catalogue exclusion; research proxy only, not organizer-scored.")


def load_h51(path: Path | None = None) -> dict[str, Any] | None:
    path = H51_DEFAULT if path is None else path
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def load_h53(evidence_dir: Path | None = None) -> tuple[dict[str, Any] | None, dict[str, Any] | None]:
    evidence_dir = Path("evidence") if evidence_dir is None else Path(evidence_dir)
    build_path = evidence_dir / H53_BUILD_DEFAULT.name
    validation_path = evidence_dir / H53_VALIDATION_DEFAULT.name
    build = json.loads(build_path.read_text(encoding="utf-8")) if build_path.exists() else None
    validation = json.loads(validation_path.read_text(encoding="utf-8")) if validation_path.exists() else None
    return build, validation


def _pct(value: Any) -> str:
    try:
        return f"{100.0 * float(value):.2f}%"
    except (TypeError, ValueError):
        return "—"


def h53_download_band(build: dict[str, Any] | None, validation: dict[str, Any] | None,
                      output_dir: Path) -> str:
    """Prominent download band, with the failed gate impossible to miss."""
    if not build:
        return """<section class=\"main\"><div class=\"shell\"><div class=\"callout danger\"><strong>H53-A research status pending.</strong> No slot is authorized.</div></div></section>"""
    candidate = build.get("candidate", {})
    artifact = candidate.get("artifact", {})
    path = artifact.get("path", f"docs/downloads/{candidate.get('filename', 'missing.tif')}")
    exists = (output_dir / path).is_file()
    status = build.get("status", "UNKNOWN")
    validation_status = (validation or {}).get("status", status)
    no_go = (status.startswith("NO_GO") or validation_status == "NO_SLOT" or
             not (validation or {}).get("decision", {}).get("candidate_promotes", False))
    download = (
        f'<p><a class="button" href="{esc(path)}" download>⬇ Download the H53-A no-go research TIFF</a></p>'
        if exists else '<p><strong>Raster file is not present at the expected path.</strong></p>')
    positive = int(artifact.get("positive_cells", candidate.get("build_support_count", 0)))
    sha = artifact.get("sha256", "not available")
    note = candidate.get("optional_note", H53_OPTIONAL_NOTE)
    return f"""<section id="h53-current" style="background:#482b2a;color:#fff8f2;padding:26px 0;border-bottom:4px solid #d99a52"><div class="shell">
<div class="eyebrow" style="color:#ffd2a0">CURRENT EXPERIMENT · NO-GO</div>
<h2 style="color:#ffffff;margin:.2em 0 .3em;font-size:clamp(1.5rem,3.4vw,2.3rem)">H53-A found no qualifying probe/TMI lineations</h2>
<div class="callout danger"><strong>Do not upload this artifact or spend a scoring slot.</strong> It is an all-zero no-go raster with {positive:,} predicted cells; it is provided for reproducibility and inspection only.</div>
{download}
<p class="small" style="color:#f2ded8">Unique research name: <code>{esc(H53_PORTAL_NAME)}</code><br>
Optional note (identity only; <strong>do not paste for a submission</strong>): <q>{esc(note)}</q><br>
SHA-256 <span class="hash">{esc(sha)}</span> · {artifact.get('width', '—')} × {artifact.get('height', '—')} · {esc(artifact.get('crs', '—'))} · NaN outside valid bounds; in-footprint values {fmt(artifact.get('min_in_valid_footprint'), 1)}–{fmt(artifact.get('max_in_valid_footprint'), 1)} in [0,1].</p>
<p class="small" style="color:#ffd2a0"><strong>Decision: {'NO SLOT' if no_go else 'research-only; manual review required'}.</strong> See the blocked results and provenance caveats before proceeding.</p>
</div></section>"""


def h53_hypotheses_short_html() -> str:
    rows = """<tr><td><strong>1 · H53-A</strong></td><td>2 m temperature-probe point-pattern PCA + GeoDAWN TMI lineament alignment</td><td>0 accepted; no-go</td></tr>
<tr><td>2 · H53-B</td><td>Depth-progressive MT conductance boundaries (five depth ranges)</td><td>Not implemented; license wording needs verification</td></tr>
<tr><td>3 · H53-C</td><td>Well/spring chemistry and deep-circulation fingerprints</td><td>Not implemented; raw geochemistry not audited</td></tr>
<tr><td>4 · H53-D</td><td>Paleo sinter/tufa/travertine corridors</td><td>Not implemented; source bytes not matched to GDR</td></tr>"""
    return f"""<article class="card span-12"><h2>Pre-implementation geological hypotheses</h2>
<p>Four distinct candidates were ranked and preregistered before H53-A implementation. The leader failed its frozen geometry and holdout gate; no alternate was promoted post hoc.</p>
<div class="wide"><table><thead><tr><th>Rank</th><th>Distinct physical signature</th><th>Status</th></tr></thead><tbody>{rows}</tbody></table></div>
<p><a href="docs/research/h53-hypotheses-20261007.md">Full ranking with layers, novelty, expected DTI direction, cost, permissions and official links →</a> · <a href="docs/research/h53-preregistration-20261007.md">Frozen protocol →</a></p></article>"""


def h53_results_block(validation: dict[str, Any] | None) -> str:
    if not validation:
        return """<article class="card span-12"><h2>H53-A validation pending</h2><p>No candidate may use a weekly slot until the frozen baseline and spatial controls are recorded.</p></article>"""
    candidate = validation["candidate"]
    incumbent = validation["frozen_incumbent"]
    decision = validation["decision"]
    folds = "".join(
        f"<tr><td>{esc(fold)}</td><td>{fmt(candidate['equal_mass_folds'][fold]['score'], 6)}</td>"
        f"<td>{fmt(incumbent['folds'][fold]['score'], 6)}</td>"
        f"<td>{fmt(validation['frozen_incumbent']['fold_dti_deltas_candidate_minus_incumbent'][fold], 6)}</td></tr>"
        for fold in ("NW", "NE", "SW", "SE")
    )
    controls = []
    for name, value in validation["registered_controls"].items():
        requested = sum(fold["requested_mass"] for fold in value["folds"].values())
        controls.append(f"<tr><td>{esc(name)}</td><td>{fmt(value['pooled_equal_incumbent_native_mass']['score'], 6)}</td>"
                        f"<td>{value['total_emitted_cells']:,} / {requested:,}</td>"
                        f"<td>{'yes' if value['all_fold_masses_match'] else 'no'}</td></tr>")
    for item in validation["matched_uniform_controls"]:
        requested = sum(fold["requested_mass"] for fold in item["folds"].values())
        controls.append(f"<tr><td>uniform draw {item['draw']} (seed {item['seed']})</td>"
                        f"<td>{fmt(item['pooled_equal_incumbent_native_mass']['score'], 6)}</td>"
                        f"<td>{item['total_emitted_cells']:,} / {requested:,}</td>"
                        f"<td>{'yes' if item['all_fold_masses_match'] else 'no'}</td></tr>")
    ci = validation["subtile_bootstrap"]["percentile_ci_95"]
    why = "".join(f"<li>{esc(item)}</li>" for item in decision.get("why", []))
    return f"""<article class="card span-12"><h2>H53-A blocked validation · {esc(decision['slot_decision'])}</h2>
<div class="metrics"><div class="metric"><strong>{fmt(candidate['native_pooled_dti']['score'], 6)}</strong><span>H53 no-go TIFF DTI</span></div>
<div class="metric"><strong>{fmt(incumbent['native_pooled_dti']['score'], 6)}</strong><span>frozen comparator DTI (not a recommendation)</span></div>
<div class="metric"><strong>{candidate['artifact']['positive_cells']:,} / {candidate['equal_mass_gate']['requested_full_grid']:,}</strong><span>candidate dots / requested budget</span></div>
<div class="metric"><strong>{fmt(ci[0], 4)} to {fmt(ci[1], 4)}</strong><span>95% spatial-subtile bootstrap, paired delta</span></div></div>
<p><strong>Local proxy only.</strong> Truth is SGMC faults more than 300 m from the supplied catalogue on the frozen spatial cores, not hidden expert labels or a leaderboard score. Among the pinned baseline files, <code>{esc(incumbent['name'])}</code> was highest on this proxy; this older seismicity map is only an incumbent comparator, not a novel validated strategy.</p>
<div class="wide"><table><thead><tr><th>Macrofold</th><th>H53 equal-mass DTI</th><th>Incumbent DTI</th><th>Delta</th></tr></thead><tbody>{folds}</tbody></table></div>
<h3>Controls (mass shortfalls shown)</h3><div class="wide"><table><thead><tr><th>Control</th><th>Pooled DTI</th><th>Dots emitted / in-core budget</th><th>All fold masses matched?</th></tr></thead><tbody>{''.join(controls)}</tbody></table></div>
<ul class="list">{why}</ul>
<p>Detector audit: {candidate['lineation_audit_recomputed']['clusters_tested']} clusters tested, {candidate['lineation_audit_recomputed']['clusters_accepted']} accepted. Exact details, file hashes and the 16-subtile table are in <a href="evidence/h53-validation-20261007.json">the machine-readable validation report</a>. Score review and caveats: <a href="docs/research/h33-score-review-20261007.md">H33-2-B2 provenance and 0.2778 review</a>.</p></article>"""


def h53_methods_block() -> str:
    return """<article class="card span-12"><h2>H53-A: shallow thermal point geometry + magnetic alignment</h2>
<p>Within each GDR survey Area, select positive <code>F2mDAB</code> values at or above the within-Area 75th percentile. Join probes within 1.5 km, require ≥5 points, a PCA eigenvalue ratio ≥3, an 0.8–20 km axis, then require ≥50% of samples to be within 500 m and 30° of a high-strength/high-coherence GeoDAWN <code>TMI_up150</code> ridge. Emit a 1.5-pixel Gaussian corridor; exclude predictions within 300 m of the supplied catalogue. No labels or prior prediction pixels enter the feature builder.</p>
<p><strong>Result:</strong> 145 clusters tested; 0 accepted (113 too small, 24 insufficient TMI alignment, 8 insufficient PCA ratio). No parameters were loosened after this result. See <a href="docs/research/h53-preregistration-20261007.md">the frozen preregistration</a> and <a href="src/gemsdoe50/h53.py">implementation</a>.</p>
<p><strong>Seismicity caution:</strong> H51-B already tested point/event geometry and was not validated; declustering, injection/mining confounds, event-location uncertainty and matched smoothed-density controls remain unresolved. It is not ranked here as a novel validated strategy.</p>
<h3>Source permissions and unresolved provenance</h3><ul class="list"><li><a href="https://gdr.openei.org/submissions/1391">GDR INGENIOUS, DOI 10.15121/1881483</a>: CC BY 4.0, attribution required. Local ZIP bytes match a pinned sibling mirror, not the official asset binary; direct official download failed, so no slot.</li><li><a href="https://www.usgs.gov/data/geodawn-airborne-magnetic-and-radiometric-surveys-northwestern-great-basin-nevada-and">USGS GeoDAWN, DOI 10.5066/P93LGLVQ</a>: official source CC0 1.0; local quantized extension was not independently rebuilt from official source files.</li><li><a href="https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/">Competition external-data rule</a>: the participant must have rights to use external data in the challenge and share it with the sponsor for evaluation.</li><li><a href="https://docs.nlr.gov/docs/fy26osti/96647.pdf">DOE/NLR Official Rules (September 2026)</a>: single float32 GeoTIFF; disclose generative-AI extent/use in the narrative; finalist assets must reproduce results.</li></ul></article>"""


def h53_submission_block(build: dict[str, Any] | None, validation: dict[str, Any] | None,
                         output_dir: Path) -> str:
    band = h53_download_band(build, validation, output_dir)
    if not build:
        return band
    artifact = build.get("candidate", {}).get("artifact", {})
    path = artifact.get("path", "docs/downloads/")
    exists = (output_dir / path).is_file()
    download = (f'<a class="button" href="{esc(path)}" download>Download the no-go research TIFF</a>'
                if exists else "The raster file is not available at its expected path.")
    return f"""{band}<main><section class="pagehead"><div class="shell"><div class="eyebrow">No automated portal access</div><h1>Submission instructions</h1><p class="muted">The current H53-A artifact failed its promotion gate. These instructions prevent accidental use of a no-go file.</p></div></section>
<section class="main"><div class="shell"><div class="grid"><article class="card span-12"><h2>Current file: research only, do not submit</h2><div class="callout danger"><strong>NO SLOT.</strong> The download is an all-zero no-go artifact; do not upload it. The unique name and optional note below identify the build only and are not submission instructions.</div><p>{download}</p><p><strong>Research name:</strong> <code>{esc(H53_PORTAL_NAME)}</code><br><strong>Optional note for traceability only:</strong> <q>{esc(build['candidate'].get('optional_note', H53_OPTIONAL_NOTE))}</q><br><strong>SHA-256:</strong> <span class="hash">{esc(artifact.get('sha256', 'not available'))}</span></p></article>
<article class="card span-8"><h2>Manual submission checklist for a future SLOT-ELIGIBLE artifact</h2><ol class="list"><li>Use only a file explicitly marked <strong>SLOT-ELIGIBLE</strong> after the registered blocked-holdout, control, license, and format gates pass. None is eligible now.</li><li>Download the direct single-band float32 GeoTIFF and verify its SHA-256.</li><li>Re-read the <a href="https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/">official submission format</a>: EPSG:32611, 100 m, same bounds, values in [0,1] within the study footprint, null/NaN outside.</li><li>Confirm external-data permissions and include required attribution and the rules-required generative-AI disclosure in the narrative.</li><li>Sign in to DrivenData manually and upload the one-band TIFF without reprojecting or resaving it.</li><li>Use the eligible build's unique submission name and optional note, then save the portal receipt and score with the exact file hash. Do not claim an upload or score without a receipt.</li></ol></article>
<aside class="card span-4"><h2>Why no upload?</h2><p>0 accepted lineations; 0 emitted predictions; blocked DTI 0.000000 versus 0.136074 for the comparator. The spatial bootstrap is negative. See <a href="results.html">Results</a>.</p><p><span class="tag">No weekly slot spent</span></p></aside></div></div></section></main>"""


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
        '<article class="card span-12"><h2>Historical H52-era candidate ideas (not the current ranking)</h2>'
        '<p class="muted">These rows were proposals in an older H51-era review and are preserved for context; '
        'they are not current submission recommendations. The current pre-implementation ranking is '
        '<a href="docs/research/h53-hypotheses-20261007.md">the H53 review</a>. Full archived text: '
        '<a href="docs/h51-candidates.md">docs/h51-candidates.md</a>.</p>'
        '<div class="wide"><table><tr><th>#</th><th>candidate</th><th>layers</th><th>physical signature</th>'
        '<th>why a missing fault</th><th>difference</th><th>source</th><th>cost</th><th>expected gain</th></tr>'
        + candidate_rows + '</table></div>'
        '<p><strong>Historical gate note:</strong> the older H51/H52 review used a matched-random-control '
        'test that is not the current promotion gate. No H51 file is currently slot-eligible. See the '
        'current <a href="results.html">H53-A blocked results</a> and the current H53 hypothesis ranking '
        'before considering any future experiment.</p></article>')
    return f"""<section class="main" id="historical-h51-methods"><div class="shell"><div class="grid">
<article class="card span-12"><h2>Historical H51 methods and H52 proposals — archive only</h2><p>Not the current hypothesis ranking and not a submission recommendation. These records preserve prior experiment design and local measurements. The current H53-A decision is NO-GO / NO SLOT; the current H53 ranking is linked above.</p></article>
<article class="card span-8"><h2>Historical H51 method (archive only)</h2>
<p><strong>Field.</strong> Two independent physical families, each reduced to an oriented lineament strength with a multi-scale structure tensor (gradient outer-product coherence × gradient magnitude, robust-normalised inside the footprint), then summed with equal weights. No single layer is allowed to carry the ranking on its own.</p>
<div class="wide"><table><tr><th>family</th><th>layers</th><th>evidence class</th></tr>{fam_rows}</table></div>
<p><strong>Domain.</strong> Every emitted dot is more than 300 m from any provided-catalogue pixel. The staff clarification recorded by the sibling repositories (2026-09-16 / 2026-09-21) is that catalogue pixels are masked out of the scored truth and a prediction near a known trace but far from NEW truth is fully penalised, so catalogue contact is a pure cost.</p>
<p><strong>Emission.</strong> Greedy packing by expected marginal credit with a 3-pixel suppression radius, because two dots closer than the metric's own 300 m kernel are nearly redundant while each still costs the 0.2 term.</p>
<p><strong>Mass.</strong> The metric's own marginal condition (a dot pays iff its kernel credit exceeds 0.2 × DTI) applied through an owner-reported score and local SGMC-off comparison; the resulting marginal transfer of {h51['mass_rule']['marginal_transfer']} is a historical model input, not an independently verified live score.</p>
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
        "source": "GDR submission 1391 lists CC BY 4.0; local sibling mirror is not byte-matched to official assets; provenance/shareability unresolved",
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
        "source": "USGS ANSS ComCat; mixed-network contributor rights and sponsor sharing unresolved; mechanism coverage unmeasured; do not use until cleared",
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
<div class="eyebrow">Historical artifact · H51</div>
<h2 style="margin-top:.2em">H51 file archive (not the current recommendation)</h2>
<p><a class="button" href="{esc(ship['outputs']['tif'])}" download>Download {esc(ship['name'])}-{esc(ship['stamp'])}.tif</a>
<a class="button secondary" style="color:#172a33;background:#dcefe9" href="{esc(ship['outputs']['zip'])}" download>Download .zip</a>
<a class="button secondary" style="color:#172a33;background:#eceae1" href="submission.html">Current H53 status &amp; future gates</a></p>
<p class="sourced">SHA-256 <span class="hash">{esc(ship['outputs']['sha256'])}</span> · {ship['outputs']['bytes']:,} bytes · stamp {esc(ship['stamp'])}</p>
<div class="metrics">
<div class="metric"><strong>{ship['budgets']['n']:,}</strong><span>predicted pixels (values 0 / 1 only)</span></div>
<div class="metric"><strong>{fmt(ship['predicted']['DTI'], 4)}</strong><span>legacy modeled DTI estimate (not a leaderboard score; LOO MAE {fmt(inst['loo_mae'], 4)})</span></div>
<div class="metric"><strong>{fmt(gate['measured_iou2px_max'], 3)}</strong><span>worst 200 m-proximity IoU vs 26 prior artifacts (gate &lt; 0.5)</span></div>
<div class="metric"><strong>0</strong><span>pixels shared with any prior artifact</span></div>
</div>
<div class="callout danger" style="margin-top:16px"><strong>Historical evidence only — do not treat this as a current slot recommendation.</strong>
The old instrument estimate was {fmt(ship['predicted']['DTI'], 2)} (leave-one-out RMSE {fmt(inst['loo_rmse'], 3)}),
which was below the user-provided 0.2778 H33 score claim (not authenticated) and was not an organizer score. The file failed its pre-registered
proxy gate and did not establish a route to the hidden test. The current H53-A result is NO SLOT; this archived H51
file is retained only to preserve the project record.</div>
<p class="sourced">Format: {esc(fmtinfo['dtype'])}, {esc(fmtinfo['crs'])}, {fmtinfo['shape'][0]}×{fmtinfo['shape'][1]},
values in [0, 1] = {esc(fmtinfo['values_in_0_1'])}, NaN only outside the published footprint = {esc(fmtinfo['outside_footprint_all_nan'])},
all in-footprint values finite = {esc(fmtinfo['inside_footprint_all_finite'])}. Uniqueness verdict:
<strong>{esc('PASS' if uniq.get('verdict_unique') else uniq.get('verdict', 'not run'))}</strong> · identical hashes: {len(uniq.get('identical_sha256', []))}.</p>
</article>
<article class="card span-7"><h2>Archived H51 design notes</h2>
<p>{esc(ship['design'])}. This historical design combined a score-consensus field with exploration points from seismicity, magnetic/radiometric ridges, and thermal-spring evidence. Its score instrument was fitted to owner-reported historical records; these are not verified organizer scores, and the instrument did not establish transfer to new territory.</p>
<p class="sourced">Audit records: <span class="hash">evidence/h51_ship.json</span>,
<span class="hash">evidence/h51_consensus.json</span>, <span class="hash">evidence/h51_check_submission.json</span>,
archived analysis <span class="hash">docs/research/h51-analysis.md</span>, and the failed truth-density inversion <span class="hash">docs/research/h51-truth-map.md</span>.</p></article>
<article class="card span-5"><h2>Archived file notice</h2>
<p><strong>This file is not currently eligible for a competition slot.</strong> Its historical unique-name and optional-note fields are intentionally not repeated here as portal instructions. Do not upload it based on its old format or uniqueness checks.</p>
<p>The current experiment is H53-A and its decision is <strong>NO-GO / NO SLOT</strong>. Use the current <a href="submission.html">future-only submission guide</a> for the actual status and acceptance gates.</p></article>
</div></div></section>"""




def two_candidates_card(ship: dict[str, Any] | None, h51: dict[str, Any] | None,
                        compare: dict[str, Any] | None) -> str:
    """Both candidate GeoTIFFs on this branch, against the one frame they share.

    The two parallel sessions used different local instruments, so only the shared off-catalogue
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
            (f'<a class="button" href="{esc(ship["outputs"]["tif"])}" download>Download archived .tif</a> · '
             f'<a href="{esc(ship["outputs"]["zip"])}" download>.zip (same TIFF)</a>')))
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
            (f'<a class="button" href="{esc(primary["path"])}" download>Download archived .tif</a> · '
             f'<a href="{esc(h51["outputs"]["zip"]["path"])}" download>.zip (same TIFF)</a>')))
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
    return f"""<section class="main"><div class="shell"><article class="card span-12" id="candidates">
<h2>Historical H51 candidate TIFFs — shared frame comparison</h2>
<div class="wide"><table><tr><th>candidate</th><th>dots</th><th>its own instrument (not comparable)</th>
<th>shared off-catalogue frame DTI</th><th>uniqueness evidence</th><th>download</th></tr>{rows}</table></div>
<p class="sourced">Both files were re-measured on one identical frame — unmasked domain, truth = SGMC fault
pixels more than 300 m from the given catalogue{f", {truth_px:,} px" if truth_px else ""} — with the same
code, so that column and the matched uniform control ({control}) are directly comparable. On this frame the
parallel-session scarp + radiometric candidate is the stronger of the two new files, and the consensus-mix
candidate scores below a matched uniform control. Neither file is organizer-scored; these are local
proxy instruments only. Both are archival experiments and neither is a current slot recommendation.</p>
{inc_row}
</article></div></section>"""


def build_pages(output_dir: Path, report_path: Path,
                evidence_dir: Path | None = None, h51_ship: Path | None = None,
                h51_check: Path | None = None) -> list[Path]:
    report = load_report(report_path)
    h51 = load_h51((evidence_dir / "build_h51.json") if evidence_dir else None)
    ship = load_json_optional("evidence/h51_ship.json")
    compare = load_json_optional("evidence/h51_candidate_frame_compare.json")
    h51_html = h51_block(output_dir, h51_ship or H51_SHIP_DEFAULT,
                         h51_check or H51_CHECK_DEFAULT)
    h53_build, h53_validation = load_h53(evidence_dir)
    h53_panel = h53_download_band(h53_build, h53_validation, output_dir)
    h53_hypotheses = h53_hypotheses_short_html()
    secondary_card = two_candidates_card(ship, h51, compare)

    index_body = f"""
<main>{h53_panel}<section class="hero"><div class="shell"><div class="eyebrow">DOE GEMS Prize Challenge · audit-first research</div><h1>Test new evidence; own the no-go.</h1><p>GEMSDOE50 preserves its original goal—maximize the chance of winning without recycling submission pixels—while requiring reproducible evidence, licensed sources, blocked validation, and a clear refusal to spend a scoring slot when a candidate fails.</p><div class="actions"><a class="button" href="results.html">Read the H53-A holdout result</a><a class="button secondary" href="submission.html">Submission guide (current status: no-go)</a></div></div></section>
<section class="main"><div class="shell"><div class="grid"><article class="card span-8"><h2>Executive summary</h2><p><strong>H53-A is NO-GO / NO SLOT.</strong> Its frozen probe-temperature plus GeoDAWN magnetic-lineation detector accepted zero of 145 clusters, produced an all-zero research GeoTIFF, and scored 0.000000 on the accessible spatial proxy. It lost to the frozen local comparator (0.136074); the paired spatial-subtile 95% interval was [−0.169861, −0.079791]. Do not upload the file or spend a weekly slot.</p><p><strong>H33-2-B2 and score claims:</strong> the user-provided 0.2778 remains unverified; a pinned sibling audit labels the run UNSCORED and gives a projection of 0.274673, not an organizer receipt. Removing 2,545 catalogue-near dots from 40,199 could plausibly improve DTI by reducing false-positive mass, but the evidence does not establish that as the cause. The user-provided 0.3774 high-score claim was not independently checked. This work validates no strategy that exceeds it.</p><p>Official raster contract: single-band float32 on the specified EPSG:32611 100 m grid; values within [0,1] in the valid footprint and null/NaN outside. The linked H53 TIFF follows that contract but is all zero and expressly not a submission.</p><p><a href="docs/research/h33-score-review-20261007.md">Read the score/provenance review</a> · <a href="docs/research/h53-hypotheses-20261007.md">Review the ranked geological hypotheses</a> · <a href="docs/research/h53-preregistration-20261007.md">Frozen H53-A protocol</a>.</p></article><aside class="card span-4"><h2>Promotion rule</h2><ul class="list"><li>Beat the frozen incumbent on a spatially blocked holdout</li><li>Match prediction mass fold by fold</li><li>Beat registered controls and uncertainty bounds</li><li>Clear data rights, provenance, and raster-byte validation</li><li>Otherwise: <strong>NO SLOT</strong></li></ul><a href="results.html">View the full evidence →</a></aside><article class="card span-6"><h2>What the proxy means</h2><p>The local score uses existing mapped faults, not hidden expert labels or a competition score. A proxy win would authorize review only; it would not guarantee leaderboard performance. In this experiment the candidate lost decisively.</p></article><article class="card span-6"><h2>Project charter</h2><p><span class="tag">Maximize P(Win)</span> Prioritize strategies that can improve the final result, not merely a public proxy.</p><p><span class="tag">Own the Outcome</span> Publish hashes, controls, limitations, unresolved provenance and a clear no-go when a gate fails.</p><p>Never copy earlier submission pixels into a new candidate. Report uncertainty honestly, verify licenses and rules, and preserve historical experiments without presenting them as current recommendations.</p><p><a href="methods.html">Methods, source permissions and limitations →</a></p></article>{h53_hypotheses}<article class="card span-12"><h2>Historical record</h2><p>Older H51 files and metrics are retained as experiment history, not current upload advice. H51 did not clear its frozen promotion proxy; do not spend a slot on it based on archived site copy.</p><p><a href="results.html#historical-h51">Open preserved H51 evidence →</a></p></article><article class="card span-12"><h2>Official sources</h2><div class="grid"><div class="span-4"><strong>Competition format and external-data rule</strong><br><a href="https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/">Official DrivenData problem page</a></div><div class="span-4"><strong>DOE/NLR rules</strong><br><a href="https://docs.nlr.gov/docs/fy26osti/96647.pdf">September 2026 official rules</a></div><div class="span-4"><strong>Leaderboard</strong><br><a href="https://www.drivendata.org/competitions/306/competition-doe-gems/leaderboard/">Open manually; no automated polling</a></div></div></article></div></div></section></main>
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
        scientific_gates = evaluation["promotion_gate"].get("scientific_gates", {})
        component_rows = []
        for name, passed in evaluation["promotion_gate"]["components"].items():
            label = name.replace("_", " ")
            result_text = "PASS" if passed else "FAIL"
            detail = scientific_gates.get(name, {}).get("detail")
            detail_html = f"<br><small>{esc(detail)}</small>" if detail else ""
            component_rows.append(
                f'<tr><td>{esc(label)}</td><td>{result_text}{detail_html}</td></tr>'
            )
        gate_rows_html = "".join(component_rows)
        score_summary = f"""
<article class="card span-12"><h2>Separate H50-S1 research record — historical proxy only</h2><p>This optional report is not the current H53-A experiment, not a current slot recommendation, and not an organizer score. DTI uses the official 300 m triangular kernel, α=0.2, β=0.8; predictions are compared at equal binary probability mass.</p><h3>Metric and pooled components</h3><div class="wide"><table><thead><tr><th>Method</th><th>Pooled DTI</th><th>Truth cells</th><th>Predicted cells</th><th>TP weight</th><th>FP weight</th><th>FN weight</th></tr></thead><tbody>{"".join(method_rows)}</tbody></table></div><h3>Fold-wise paired scores</h3><div class="wide"><table><thead><tr><th>Macrofold</th><th>H50-S1</th><th>Incumbent ({esc(evaluation["incumbent_method"])})</th><th>Delta</th><th>Predictions</th><th>Truth</th></tr></thead><tbody>{"".join(fold_rows)}</tbody></table></div><p><strong>16-block bootstrap 95% interval:</strong> [{fmt(ci[0], 6)}, {fmt(ci[1], 6)}]. Candidate − incumbent pooled DTI = {fmt(evaluation["candidate_minus_incumbent_pooled_dti"], 6)}.</p></article>
<article class="card span-6"><h2>Spatial translations</h2><p>32 no-wrap offsets at 5–20 km; 95th percentile DTI {fmt(controls["pooled_dti_q95"], 6)}. Candidate DTI {fmt(evaluation["method_results"]["H50-S1"]["pooled"]["score"], 6)}.</p><details><summary>Show individual controls</summary><div class="wide"><table><thead><tr><th>Control</th><th>Pooled DTI</th></tr></thead><tbody>{control_table}</tbody></table></div></details></article>
<article class="card span-6"><h2>Origin-year shuffles</h2><p>{time_controls["count"]} refits with shuffled years; 95th percentile DTI {fmt(time_controls["pooled_dti_q95"], 6)}. Candidate DTI {fmt(evaluation["method_results"]["H50-S1"]["pooled"]["score"], 6)}.</p><details><summary>Show individual controls</summary><div class="wide"><table><thead><tr><th>Control</th><th>Pooled DTI</th></tr></thead><tbody>{time_table}</tbody></table></div></details></article>
<article class="card span-12"><h2>Matched smoothed-density controls</h2><p>Gaussian-smoothed counts from the same relocated catalog events, scored at equal mass on the same blocked holdout. This controls spatial density only; it does not remove aftershocks or mine/injection confounding. Candidate must beat both scales.</p><div class="wide"><table><thead><tr><th>Density map</th><th>Pooled DTI</th></tr></thead><tbody>{density_table}</tbody></table></div></article>
<article class="card span-12"><h2>Promotion-gate components</h2><div class="wide"><table><thead><tr><th>Criterion</th><th>Result</th></tr></thead><tbody>{gate_rows_html}</tbody></table></div><p><strong>Decision: {esc(evaluation["promotion_gate"]["decision"].replace("_", " "))}.</strong> A proxy pass authorizes review only; no portal slot is used automatically.</p><p><a href="{esc(report_path.as_posix())}">Open machine-readable report JSON</a> · Report SHA-256: <span class="hash">{esc(sha256_report(report_path))}</span></p></article>
"""
    else:
        score_summary = '<article class="card span-12"><h2>Separate H50-S1 research line</h2><p>No H50-S1 evaluation is included in this H53 results review. H53-A is the current experiment and is NO-GO / NO SLOT; no result here is an organizer score.</p></article>'

    results_body = f"""<main><section class="pagehead"><div class="shell"><div class="eyebrow">Evidence, not leaderboard claims</div><h1>Holdout results</h1><p class="muted">All values below come from a spatial proxy on existing labels. The competition's hidden expert-labeled labels are not available here; no score is organizer-reported.</p></div></section><section class="main"><div class="shell"><div class="grid">{h53_results_block(h53_validation)}{score_summary}</div></div></section></main>"""

    submission_body = h53_submission_block(h53_build, h53_validation, output_dir)

    methods_body = f"""<main><section class="pagehead"><div class="shell"><div class="eyebrow">Preregistered research</div><h1>Methods, sources & limitations</h1><p class="muted">The H53 hypotheses were ranked and its leading test frozen before holdout scoring. Failed tests are reported without threshold tuning.</p></div></section><section class="main"><div class="shell"><div class="grid">{h53_methods_block()}<article class="card span-12"><h2>Competition and project guardrails</h2><ul class="list"><li>Follow the <a href="https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/">official competition page</a>: float32 predictions on the specified EPSG:32611, 100 m grid; finite [0,1] values inside the valid footprint; null/NaN outside.</li><li>External data must be permitted for challenge use and shareable with the sponsor for evaluation. File-level license and provenance gaps are treated as blockers, not assumed away.</li><li>The <a href="https://docs.nlr.gov/docs/fy26osti/96647.pdf">official DOE/NLR rules</a> require disclosure of generative-AI assistance and support reproducibility.</li><li><a href="https://www.drivendata.org/termsofuse/">DrivenData Terms of Use</a> prohibit automated leaderboard monitoring/copying without authorization; no live board was queried for this review.</li></ul><p>Historical H50/H51 methods and measurements remain preserved in the repository and are not promoted as current competition advice. See <a href="docs/research/h33-score-review-20261007.md">score provenance</a> and <a href="results.html#historical-h51">archived H51 evidence</a>.</p></article></div></div></section></main>"""

    if h51:
        archived_h51 = (
            '<section id="historical-h51" class="main"><div class="shell"><div class="grid">'
            '<article class="card span-12"><h2>Historical H51 evidence (archive only)</h2>'
            '<p>These prior experiments are retained for auditability, not as current submission advice. '
            'Their proxy results do not establish a route to the hidden competition score.</p></article>'
            f'{secondary_card}{h51_results_block(h51, evidence_dir)}{h51_html}'
            '</div></div></section>')
        results_body = results_body.replace('</main>', archived_h51 + '</main>')
        methods_body = methods_body + h51_methods_block(h51)
    submission_body = h53_submission_block(h53_build, h53_validation, output_dir)

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
    parser.add_argument("--evidence-dir", default="evidence")
    parser.add_argument("--h51-ship", default=str(H51_SHIP_DEFAULT))
    parser.add_argument("--h51-check", default=str(H51_CHECK_DEFAULT))
    args = parser.parse_args()
    written = build_pages(Path(args.output_dir), Path(args.report), Path(args.evidence_dir),
                          Path(args.h51_ship), Path(args.h51_check))
    for path in written:
        print(path)


if __name__ == "__main__":
    main()
