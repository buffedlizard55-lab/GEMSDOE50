#!/usr/bin/env python3
"""Build the static executive-summary, results, methods, and submission pages."""

from __future__ import annotations

import argparse
import html
import json
from pathlib import Path
from typing import Any

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
    import hashlib

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
    """Require byte validation, pinned split provenance, and the exact competition grid."""
    if not expected_sha or validation.get("sha256") != expected_sha:
        return False
    try:
        positive_cells = int(validation.get("positive_cells", 0))
        minimum = float(validation["minimum_valid_value"])
        maximum = float(validation["maximum_valid_value"])
    except (KeyError, TypeError, ValueError):
        return False
    if (
        validation.get("range_pass") is not True
        or validation.get("nodata_mask_matches_template") is not True
        or validation.get("band_count") != 1
        or validation.get("dtype") != "float32"
        or validation.get("crs") != "EPSG:32611"
        or validation.get("bytes") != actual_bytes
        or positive_cells <= 0
        or not 0.0 <= minimum <= maximum <= 1.0
    ):
        return False

    try:
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
        right = left + width * float(transform[0])
        bottom = top + height * float(transform[4])
        expected_bounds = [left, bottom, right, top]
        return (
            validation.get("width") == width
            and validation.get("height") == height
            and validation.get("transform") == transform
            and validation.get("bounds") == expected_bounds
        )
    except (KeyError, TypeError, ValueError, OSError, json.JSONDecodeError):
        return False


def metric_cards(report: dict[str, Any] | None) -> str:
    if not report:
        return """<div class="metrics"><div class="metric"><strong>Preregistered</strong><span>Four spatial macrofolds</span></div><div class="metric"><strong>300 m</strong><span>Official triangular metric support</span></div><div class="metric"><strong>CC BY 4.0</strong><span>Open Nevada relocated catalog</span></div><div class="metric"><strong>0 slots used</strong><span>No portal access is automated</span></div></div>"""
    evaluation = report["evaluation"]
    candidate = evaluation["method_results"]["H50-S1"]["pooled"]["score"]
    incumbent_name = evaluation["incumbent_method"]
    incumbent = evaluation["method_results"][incumbent_name]["pooled"]["score"]
    gate = evaluation["promotion_gate"]
    status = "STAT GATE PASS" if gate["pass"] else "STAT GATE FAIL"
    status_class = "pass" if gate["pass"] else "fail"
    return f"""<div class="metrics"><div class="metric"><strong>{fmt(candidate, 5)}</strong><span>H50-S1 pooled holdout DTI</span></div><div class="metric"><strong>{fmt(incumbent, 5)}</strong><span>{esc(incumbent_name)} pooled incumbent</span></div><div class="metric"><strong>{fmt(evaluation["candidate_minus_incumbent_pooled_dti"], 5)}</strong><span>Paired pooled delta</span></div><div class="metric"><strong><span class="status {status_class}">{esc(status)}</span></strong><span>Statistical gate only; science/submission eligibility is separate</span></div></div>"""


def build_pages(output_dir: Path, report_path: Path, tiff_path: Path) -> list[Path]:
    report = load_report(report_path)
    output_dir = Path(output_dir)
    report_path = Path(report_path)
    tiff_path = Path(tiff_path)
    relative_tiff = tiff_path.as_posix()
    artifact_record = (report or {}).get("submission_artifact", {})
    reported_sha = artifact_record.get("sha256")
    validation = artifact_record.get("validation") or {}
    expected_sha = reported_sha
    actual_sha = sha256_path(tiff_path)
    actual_bytes = tiff_path.stat().st_size if actual_sha else 0
    tiff_verified = bool(
        report
        and artifact_record.get("built") is True
        and expected_sha
        and artifact_record.get("unique_name") == tiff_path.name
        and artifact_record.get("bytes") == actual_bytes
        and actual_sha == expected_sha
        and validation_record_matches_contract(validation, expected_sha, report, actual_bytes)
    )
    if report:
        eligibility_record = report.get("submission_eligibility", {})
        status_text = (
            "verified research-only candidate; submission eligibility remains separate"
            if tiff_verified and eligibility_record.get("pass") is not True
            else "verified candidate awaiting manual owner review"
            if tiff_verified
            else "no verified raster artifact"
        )
        candidate_hash = (
            f'<div class="sourced">GeoTIFF SHA-256 verified against report: '
            f'<span class="hash">{esc(actual_sha)}</span></div>'
            if tiff_verified
            else '<div class="sourced">No downloadable GeoTIFF is verified against this report.</div>'
        )
        artifact_link = (
            f'<a class="button" href="{esc(relative_tiff)}" download>Download research-only GeoTIFF</a>'
            if tiff_verified
            else '<span class="tag">No verified candidate download</span>'
        )
    else:
        status_text = "awaiting verified run"
        candidate_hash = ""
        artifact_link = '<span class="tag">No download until data and byte checks pass</span>'

    index_body = f"""
<main><section class="hero"><div class="shell"><div class="eyebrow">DOE GEMS Prize Challenge · audit-first research</div><h1>Map what the catalogue missed.</h1><p>GEMSDOE50 tests whether waveform-relocated Nevada earthquake planes can point to plausible, previously unmapped fault traces—without copying a prior submission or spending a scoring slot before spatial validation.</p><div class="actions">{artifact_link}<a class="button secondary" href="submission.html">Submission instructions</a></div>{candidate_hash}</div></section>
<section class="main"><div class="shell"><div class="grid"><article class="card span-8"><h2>Executive summary</h2><p><strong>Leading hypothesis:</strong> fit compact 3-D neighborhoods of waveform-relocated events, project only physically plausible planes to their surface intersection, and validate outside buffers around visible mapped faults.</p><p>The code compares the candidate against frozen, same-grid prior artifacts using four geographic holdouts, a fixed prediction-mass budget (sparse maps are not padded), the competition's distance-weighted Tversky metric, block-bootstrap uncertainty, spatial translations, 20 time-shuffles, and a same-event 300 m smoothed-density control.</p>{metric_cards(report)}<p class="sourced">Status: {esc(status_text)}. Historical sibling-repository scores are not used as current official leaderboard claims or mapped to a TIFF.</p></article><aside class="card span-4"><h2>Decision rule</h2><ul class="list"><li>At least +0.005 absolute pooled DTI over the frozen incumbent</li><li>Positive delta in at least 3 of 4 macrofolds</li><li>95% spatial-block bootstrap lower bound above zero</li><li>Beat the 95th percentile of translation and year-shuffle controls</li><li>Strictly beat the same-event 300 m smoothed-density control</li><li>Even a statistical pass does not clear scientific/submission blockers</li><li>Otherwise: <strong>no slot</strong></li></ul><a href="results.html">View full evidence →</a></aside><article class="card span-6"><h2>What this is—and is not</h2><p>This is a research proxy against existing mapped faults, not the hidden expert-labeled test set. A local pass is necessary for review but is not an organizer score or a promise of prize performance.</p><p>The Nevada catalog is CC BY 4.0, but it lacks event-specific location covariance; the DEM-to-catalog vertical datum is also unresolved. A precise-looking coordinate is not proof of a precise location, and the terrain intersection remains diagnostic.</p><p><strong>Historical score context:</strong> an archived report associates 0.2778 with H33-2-B2, but the current <a href="https://buffedlizard55-lab.github.io/GEMSDOE32/docs/index.html">owner site</a> labels H33-2-B2 unscored and 0.2747 a model projection. The 0.2778 association remains unresolved. The owner-provided 0.3195 is historical context only—not independently verified, a current-leader claim, or mapped to a verified TIFF. No fresh leaderboard monitoring was performed.</p></article><article class="card span-6"><h2>Project values</h2><p><span class="tag">Maximize P(Win)</span> Choose evidence that can improve the final result, not merely a public proxy.</p><p><span class="tag">Own the Outcome</span> Publish hashes, controls, limitations, and a clear no-go when a gate fails.</p><p><a href="methods.html">Read the protocol, sources, and limitations →</a></p></article><article class="card span-12"><h2>Verified primary links</h2><div class="grid"><div class="span-4"><strong>Competition specification</strong><br><a href="https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/">Metric, inputs, and TIFF contract</a></div><div class="span-4"><strong>Nevada seismicity source</strong><br><a href="https://doi.org/10.5281/zenodo.11167510">Trugman (2024), Zenodo v2 · CC BY 4.0</a></div><div class="span-4"><strong>Official leaderboard</strong><br><a href="https://www.drivendata.org/competitions/306/competition-doe-gems/leaderboard/">Open manually; this project does not scrape it</a></div></div></article></div></div></section></main>
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
        ci = evaluation["subtile_bootstrap"]["percentile_ci_95"]
        component_rows = []
        for name, passed in evaluation["promotion_gate"]["components"].items():
            label = name.replace("_", " ")
            result_text = "PASS" if passed else "FAIL"
            component_rows.append(
                f'<tr><td>{esc(label)}</td><td>{result_text}</td></tr>'
            )
        gate_rows_html = "".join(component_rows)
        eligibility = report.get("submission_eligibility", {})
        eligibility_gates = eligibility.get("gates", {})
        eligibility_rows = "".join(
            f'<tr><td>{esc(name.replace("_", " "))}</td><td>{"PASS" if passed else "NOT MET"}</td></tr>'
            for name, passed in eligibility_gates.items()
        ) or '<tr><td colspan="2">Eligibility evidence not recorded.</td></tr>'
        eligibility_pass = eligibility.get("pass") is True and tiff_verified
        eligibility_class = "success" if eligibility_pass else "danger"
        eligibility_status = (
            "ELIGIBLE FOR MANUAL OWNER REVIEW ONLY"
            if eligibility_pass
            else "NO SLOT — ARTIFACT OR SCIENTIFIC / PROVENANCE GATES NOT VERIFIED"
        )
        raw_eligibility_note = eligibility.get(
            "note",
            "A statistical proxy pass is not sufficient for submission eligibility.",
        )
        if eligibility.get("pass") is True and not tiff_verified:
            raw_eligibility_note = (
                "The report claims eligibility, but this site could not verify a matching "
                "GeoTIFF against its byte-validation record and frozen grid; treat the run as NO SLOT."
            )
        eligibility_note = esc(raw_eligibility_note)
        artifact_record = report.get("submission_artifact", {})
        if tiff_verified:
            artifact_status = (
                f'<p><strong>Research-only TIFF:</strong> <code>{esc(artifact_record.get("unique_name", tiff_path.name))}</code>; '
                f'{artifact_record.get("bytes", validation.get("bytes", "unknown"))} bytes; '
                f'{artifact_record.get("positive_cells", validation.get("positive_cells", "unknown"))} positive cells; '
                f'SHA-256 <span class="hash">{esc(actual_sha)}</span>.</p>'
                f'<p><strong>Optional competition note (not evidence of eligibility):</strong> '
                f'<q>{esc(artifact_record.get("optional_note", ""))}</q></p>'
            )
        else:
            artifact_status = '<p>No verified, downloadable candidate TIFF is present.</p>'
        score_summary = f"""
<article class="card span-12"><h2>Metric and pooled components</h2><p>DTI uses the official 300 m triangular kernel, α=0.2, β=0.8; methods receive the same prediction-mass budget, with sparse maps not padded. These local proxy values are not organizer scores.</p><div class="wide"><table><thead><tr><th>Method</th><th>Pooled DTI</th><th>Truth cells</th><th>Predicted cells</th><th>TP weight</th><th>FP weight</th><th>FN weight</th></tr></thead><tbody>{"".join(method_rows)}</tbody></table></div><h3>Fold-wise paired scores</h3><div class="wide"><table><thead><tr><th>Macrofold</th><th>H50-S1</th><th>Incumbent ({esc(evaluation["incumbent_method"])})</th><th>Delta</th><th>Predictions</th><th>Truth</th></tr></thead><tbody>{"".join(fold_rows)}</tbody></table></div><p><strong>16-block bootstrap 95% interval:</strong> [{fmt(ci[0], 6)}, {fmt(ci[1], 6)}]. Candidate − incumbent pooled DTI = {fmt(evaluation["candidate_minus_incumbent_pooled_dti"], 6)}.</p>{artifact_status}</article>
<article class="card span-6"><h2>Spatial translations</h2><p>32 no-wrap offsets at 5–20 km; 95th percentile DTI {fmt(controls["pooled_dti_q95"], 6)}. Candidate DTI {fmt(evaluation["method_results"]["H50-S1"]["pooled"]["score"], 6)}.</p><details><summary>Show individual controls</summary><div class="wide"><table><thead><tr><th>Control</th><th>Pooled DTI</th></tr></thead><tbody>{control_table}</tbody></table></div></details></article>
<article class="card span-6"><h2>Origin-year shuffles</h2><p>{time_controls["count"]} refits with shuffled years; 95th percentile DTI {fmt(time_controls["pooled_dti_q95"], 6)}. Candidate DTI {fmt(evaluation["method_results"]["H50-S1"]["pooled"]["score"], 6)}.</p><details><summary>Show individual controls</summary><div class="wide"><table><thead><tr><th>Control</th><th>Pooled DTI</th></tr></thead><tbody>{time_table}</tbody></table></div></details></article>
<article class="card span-12"><h2>Statistical promotion-gate components</h2><div class="wide"><table><thead><tr><th>Criterion</th><th>Result</th></tr></thead><tbody>{gate_rows_html}</tbody></table></div><p><strong>Statistical decision: {esc(evaluation["promotion_gate"]["decision"].replace("_", " "))}.</strong> A pass can authorize only a research artifact and further manual review; it does not authorize a weekly slot.</p><p><a href="{esc(report_path.as_posix())}">Open machine-readable report JSON</a> · Report SHA-256: <span class="hash">{esc(sha256_report(report_path))}</span></p></article>
<article class="card span-12"><h2>Scientific and submission eligibility (separate gate)</h2><div class="callout {eligibility_class}"><strong>{esc(eligibility_status)}</strong> {eligibility_note}</div><div class="wide"><table><thead><tr><th>Eligibility requirement</th><th>Status</th></tr></thead><tbody>{eligibility_rows}</tbody></table></div><p>No organizer upload, score, or receipt is represented.</p></article>
"""
    else:
        score_summary = '<article class="card span-12"><h2>Results pending</h2><p>No DTI has been computed. The holdout split and mask hashes are frozen before scoring.</p><p>Run instructions and protocol are in the repository; no submission slot has been used.</p></article>'

    results_body = f"""<main><section class="pagehead"><div class="shell"><div class="eyebrow">Evidence, not leaderboard claims</div><h1>Holdout results</h1><p class="muted">All values below come from a spatial proxy on existing labels. The competition's hidden expert-labeled labels are not available here.</p></div></section><section class="main"><div class="shell"><div class="grid">{score_summary}</div></div></section></main>"""

    if report:
        gate = report["evaluation"]["promotion_gate"]
        eligibility = report.get("submission_eligibility", {})
        eligibility_pass = eligibility.get("pass") is True and tiff_verified
        if not gate["pass"]:
            state = "Statistical holdout gate failed — do not use a weekly submission slot."
        elif not eligibility_pass:
            state = (
                "Statistical gate passed only — no verified artifact or separate scientific/provenance "
                "eligibility; do not use a weekly submission slot."
            )
        else:
            state = "Statistical and scientific gates passed — manual owner review still required; not portal-scored."
        artifact = report.get("submission_artifact", {})
        name = artifact.get("unique_name", tiff_path.name)
        note = artifact.get("optional_note", "")
        hash_html = (
            f'<p>SHA-256: <span class="hash">{esc(actual_sha)}</span></p>'
            if tiff_verified
            else "<p>SHA-256: no candidate bytes verified against the report.</p>"
        )
        download_html = (
            f'<p><a class="button" href="{esc(relative_tiff)}" download>Download research-only {esc(name)}</a></p>'
            if tiff_verified
            else "<p>No verified GeoTIFF is available for download.</p>"
        )
        raw_eligibility_note = eligibility.get(
            "note",
            "A statistical proxy pass alone does not authorize a submission slot.",
        )
        if eligibility.get("pass") is True and not tiff_verified:
            raw_eligibility_note = (
                "The report claims eligibility, but no matching GeoTIFF is verified against "
                "the byte-validation record and pinned grid; treat this as NO SLOT."
            )
        eligibility_note = esc(raw_eligibility_note)
        submit_card = f"""<div class="callout {"success" if eligibility_pass else "danger"}"><strong>{esc(state)}</strong> No upload was performed by this project.</div><h2>Current artifact</h2>{download_html}<p><strong>Unique filename:</strong> <code>{esc(name)}</code></p><p><strong>Optional competition note:</strong> <q>{esc(note)}</q></p>{hash_html}<p><strong>Eligibility note:</strong> {eligibility_note}</p><p>Portal specification is subject to change. Re-check the official problem page and independently test any downloaded bytes before a manual upload.</p>"""
    else:
        state = "Experiment not yet run. No submission slot has been used."
        submit_card = """<div class="callout"><strong>Experiment not yet run. No submission slot has been used.</strong></div><p>There is no candidate GeoTIFF to upload. Do not use a weekly slot until the statistical holdout, matched controls, byte validation, separate scientific-eligibility gates, and owner review are complete.</p><p><strong>Planned unique filename, if a verified research artifact is produced:</strong> <code>gemsdoe50-h50s1-relocated-planes-20261006-research.tif</code></p><p><strong>Planned optional note:</strong> <q>Terrain-intersected relocated Nevada event-plane lineaments; 300 m known-label exclusion; research diagnostic, not organizer-scored.</q></p>"""
    submission_body = f"""<main><section class="pagehead"><div class="shell"><div class="eyebrow">No automated portal access</div><h1>Submission instructions</h1><p class="muted">A local statistical pass is not submission eligibility. Use a weekly slot only after every scientific/provenance gate passes, the owner approves, and the current portal contract is rechecked.</p></div></section><section class="main"><div class="shell"><div class="grid"><article class="card span-12">{submit_card}</article><article class="card span-8"><h2>Manual checklist (only after all gates pass)</h2><ol class="list"><li>Download the GeoTIFF and independently verify its SHA-256 and byte-validation report in <a href="results.html">Results</a>.</li><li>Re-read the current <a href="https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/">official problem specification</a> and rules; confirm external-data rights, sponsor-sharing, and required AI-use disclosure in the final narrative.</li><li>Sign in to DrivenData manually, open the DOE GEMS competition, and choose a weekly feedback slot only if all gates pass, one remains, and the owner approves.</li><li>Upload the single-band float32 GeoTIFF. Do not change its grid, nodata footprint, or prediction values after validation.</li><li>Use the unique filename and optional note shown above, then manually verify the portal receipt and record it in this repository before making any claim of acceptance.</li></ol><div class="callout danger"><strong>Do not upload on a failed statistical or scientific gate.</strong> A local proxy pass is not a score guarantee and is not a portal receipt.</div></article><aside class="card span-4"><h2>Portal warning caught</h2><p>The previous portal error was: <code>Predicted values must be in range [0, 1]</code>.</p><p>This pipeline reopens the actual GeoTIFF bytes and checks finite in-footprint values, `[0,1]` range, one float32 band, exact grid alignment, and nodata-mask agreement with the sample template.</p><p><span class="tag">No slot used by code</span></p></aside></div></div></section></main>"""

    methods_body = """<main><section class="pagehead"><div class="shell"><div class="eyebrow">Preregistered research</div><h1>Methods, sources & limitations</h1><p class="muted">Three distinct hypotheses are ranked in the preregistration. H50-S1 implementation, controls, and spatial folds were frozen before any DTI; no real-catalog holdout run has been reported.</p></div></section><section class="main"><div class="shell"><div class="grid"><article class="card span-8"><h2>H50-S1: relocated event-plane geometry</h2><p>Use only waveform-relocated (<code>reloc=1</code>) Nevada catalog events within the valid competition footprint. Fit compact robust 3-D neighborhoods, require multi-year support and stable horizontal strike, and intersect each plausible plane numerically with bilinearly sampled local terrain on the exact template grid. The prior sea-level <code>z=0</code> projection was invalid and is not used. The present zero-offset catalog/DEM vertical-datum approximation is diagnostic only, not a validated surface-fault trace.</p><p>Known training labels are excluded from the final research artifact by a 300 m buffer; held-out labels are used for scoring only, never for line fitting. The statistical gate compares against the frozen H50-prior and prior-work rasters, matched spatial/time controls, and a same-event 300 m Gaussian-density control. Details: <a href="docs/h50s1-protocol-addendum.md">protocol addendum</a>, <a href="docs/hypotheses-preregistered.md">ranked preregistration</a>, and <a href="docs/research/data-rights-audit-20261006.md">data-rights audit</a>.</p><p><strong>Comparator policy:</strong> H50-prior is fixed as the primary incumbent before holdout scoring. H32-D, H47-S3, and H48-DS are descriptive secondary comparisons only; no prior prediction pixels are copied into H50-S1.</p></article><article class="card span-4"><h2>Data & permissions</h2><ul class="list"><li>Nevada catalog: <a href="https://doi.org/10.5281/zenodo.11167510">Zenodo v2</a>, CC BY 4.0; cite the dataset, link the license, and identify changes.</li><li>USGS 3DEP DEM: raw products are public domain; exact-grid export and its request/hash sidecar are recorded. Pixel-level vertical datum remains unresolved.</li><li>Competition labels/template use SHA-pinned public mirrors. Byte hashes do not independently authenticate those mirrors as organizer originals.</li><li>Inherited mixed-network ComCat and the GEMSDOE24 scarp derivative are excluded; their rights or source semantics are unresolved.</li><li>External inputs must meet the challenge's license and sponsor-sharing rules.</li></ul></article><article class="card span-6"><h2>Scientific eligibility blockers</h2><ul class="list"><li>No event-specific location-error covariance; coordinate precision is not positional accuracy and error may exceed the 300 m score kernel.</li><li>No standard declustering or sensitivity analysis; aftershock and swarm sequences can dominate.</li><li>No complete event-type, induced-seismicity, geothermal/injection-site, mine/quarry, or terrain-false-positive screening.</li><li>Nevada catalog depth is referenced to mean sea level; the dynamic 3DEP export does not establish one datum for all pixels. No defensible local transformation is applied.</li><li>Training-raster origin has not been independently authenticated from organizer downloads.</li><li>Existing mapped faults are an imperfect proxy; a lineament or proxy DTI gain does not prove a fault discovery or geothermal productivity.</li></ul></article><article class="card span-6"><h2>Historical score context — unresolved</h2><p>An archived GEMSDOE50 report associates <strong>0.2778</strong> with H33-2-B2, but the current <a href="https://buffedlizard55-lab.github.io/GEMSDOE32/docs/index.html">GEMSDOE32 owner site</a> describes H33-2-B2 as unscored and 0.2747 as a model projection. Without an organizer receipt or verified score-to-file mapping, the 0.2778 association remains unresolved.</p><p><strong>0.3195</strong> is owner-provided historical context only. It has not been independently verified, is not asserted to be the live lead, and is not mapped to a verified TIFF. No fresh leaderboard monitoring, scraping, or snapshotting was performed.</p><p><a href="https://www.drivendata.org/competitions/306/competition-doe-gems/leaderboard/">Open the official board manually</a>; automated monitoring or copying is not performed here.</p></article><article class="card span-12"><h2>Ranked candidates, metric, and disclosure</h2><p>The preregistered table compares three distinct hypotheses—H50-S1 terrain-intersected relocated planes, H50-G1 multi-physics basin-edge contacts, and H50-S2 multi-year lineament recurrence—with data, physical rationale, novelty against prior GEMSDOE work, expected impact, cost, and license gates. See <a href="docs/hypotheses-preregistered.md">the full hypothesis ranking</a>.</p><p>The local metric is the official 300 m distance-weighted Tversky index (α=0.2, β=0.8). Proxy results are not hidden-set scores. Before any competition entry, disclose AI assistance as required by current NLR/DOE rules and describe human review. No portal access or upload is automated.</p></article></div></div></section></main>"""

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
    return sha256_path(Path(report_path)) or "not available"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", default=".")
    parser.add_argument("--report", default=str(REPORT_DEFAULT))
    parser.add_argument("--tiff", default=str(TIFF_DEFAULT))
    args = parser.parse_args()
    written = build_pages(Path(args.output_dir), Path(args.report), Path(args.tiff))
    for path in written:
        print(path)


if __name__ == "__main__":
    main()
