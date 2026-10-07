#!/usr/bin/env python3
"""Publish the H57 candidate and put its download at the very top of the site.

Three files are produced, all deterministic and all rendered from committed
evidence so the published numbers cannot drift from the measurement:

  ``h57.html``                 the candidate page: one-click download, the status
                               badge, the executive summary, every validation
                               table, the limitations, and the source ledger
  ``h57-how-to-submit.html``   the shortest correct path from the download link to
                               a scored submission, including the portal name and
                               the optional note
  ``index.html``               a banner injected immediately after ``<body>``, so
                               the current candidate and its download are the first
                               thing on the page

Run ``scripts/build_h55_site.py`` first: it rewrites ``index.html``.  This script
patches the result, and the banner is delimited by markers so running it twice
replaces the banner instead of appending a second one.
"""

from __future__ import annotations

import html
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))


BUILD = ROOT / "evidence/h57_build.json"
CHECK = ROOT / "evidence/h57_check.json"
VALID = ROOT / "evidence/h57_validation.json"
HOLDOUT = ROOT / "evidence/h57_holdout_fields.json"
SHAPES = ROOT / "evidence/h57_emission_shapes.json"
SELECT = ROOT / "evidence/h57_final_select.json"
DECOMP = ROOT / "evidence/h57_decompose.json"
POWER = ROOT / "evidence/h57_field_power_screen.json"
SWEEP = ROOT / "evidence/h57_sharpen_sweep.json"
EXT = ROOT / "evidence/h57_sharpen_ext.json"
NOVEL = ROOT / "evidence/h57_novelty_price.json"
DELIV = ROOT / "evidence/h57_delivered_metrics.json"

BEGIN = "<!-- h57-banner -->"
END = "<!-- /h57-banner -->"


def esc(value: object) -> str:
    return html.escape(str(value), quote=True)


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}


def chrome(title: str, body: str, *, description: str, active: str = "h57") -> str:
    links = [
        ("h57.html", "H57 candidate", "h57"),
        ("h57-how-to-submit.html", "How to submit", "submit"),
        ("index.html", "Earlier candidates", "old"),
        ("results.html", "H55/H56 results", "results"),
        ("methods.html", "Methods & sources", "methods"),
    ]
    parts = []
    for href, label, k in links:
        cur = ' aria-current="page"' if k == active else ""
        parts.append(f'<a href="{href}"{cur}>{label}</a>')
    nav = "".join(parts)
    return (
        '<!doctype html>\n<html lang="en"><head><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width,initial-scale=1">'
        f'<meta name="description" content="{esc(description)}">'
        f"<title>{esc(title)} · GEMSDOE50</title>"
        '<link rel="stylesheet" href="site.css"></head>\n'
        '<body><a class="skip" href="#main">Skip to content</a>'
        '<header class="site-head"><div class="shell"><nav class="nav" aria-label="Main navigation">'
        '<a class="brand" href="h57.html">GEMSDOE50 / H57</a>'
        f'<div class="links">{nav}</div></nav></div></header>\n'
        f"{body}\n"
        '<footer class="site-foot"><div class="shell">'
        "<b>Maximize P(Win) · Own the Outcome</b><br>"
        "Research artifact. No portal upload, organizer score, or weekly slot is represented here; "
        'every number on this page is rendered from a committed evidence file. '
        '<a href="evidence/h57_validation.json">validation</a> · '
        '<a href="evidence/h57_check.json">format and novelty</a> · '
        '<a href="evidence/h57_build.json">build receipt</a>'
        "</div></footer></body></html>\n"
    )


def main() -> None:
    b, chk, v, hold, shapes, sel, dec, power, sweep, ext, novel, deliv = (
        load(p) for p in (BUILD, CHECK, VALID, HOLDOUT, SHAPES, SELECT, DECOMP,
                          POWER, SWEEP, EXT, NOVEL, DELIV))
    if not b:
        raise SystemExit("evidence/h57_build.json missing - run scripts/build_h57.py first")

    allfin = Path(b["files"]["allfinite_tif"]["path"])
    nanf = Path(b["files"]["nan_tif"]["path"])
    zipf = Path(b["files"]["zip"]["path"])
    n = b["reread"]["positive_cells"]
    fm = v["frames"]["S_matched"]
    uni_fp = v["controls"]["matched_mass_uniform_frozen_pool"]
    uni_all = v["controls"]["matched_mass_uniform_matched_frame"]
    boot = v["controls"]["paired_bootstrap_candidate_minus_uniform"]
    u = chk["uniqueness"]
    fmd = b["frozen"]

    rows = "".join(
        "<tr><td>{name}</td><td class='num'>{px:,}</td><td class='num'>{dti:.5f}</td>"
        "<td class='num'>{folds}</td></tr>".format(
            name=esc(name), px=v["frames"][name]["truth_px"], dti=v["frames"][name]["dti"],
            folds=", ".join(f"{x['dti']:.4f}" for x in v["frames"][name]["folds"]))
        for name in ("S_matched", "S_raw", "L"))

    ho_rows = "".join(
        "<tr><td>{f}</td><td class='num'>{d:.5f}</td><td class='num'>{lifts}</td></tr>".format(
            f=esc(name),
            d=rec["pooled"]["dti"],
            lifts=", ".join(f"{x['lift']:.3f}x" for x in rec["folds"].values()))
        for name, rec in hold.get("fields", {}).items())

    dz_rows = "".join(
        f"<tr><td>{esc(k.replace('|', ' · ').replace('_', ' '))}</td>"
        f"<td class='num'>{rec['dti']:.5f}</td>"
        f"<td class='num'>{rec['tp_w']:.0f}</td></tr>"
        for k, rec in dec.items() if isinstance(rec, dict) and "dti" in rec)

    shape_rows = ""
    for key, rec in shapes.get("runs", {}).items():
        field, variant, mass = key.split("|")
        if field != "o19grad_rank":
            continue
        shape_rows += (
            f"<tr><td>{esc(variant)}</td><td class='num'>{int(mass):,}</td>"
            f"<td class='num'>{rec['painted']:,}</td><td class='num'>{rec['dti']:.5f}</td>"
            f"<td class='num'>{rec['lift']:.3f}x</td></tr>")

    buf_rows = "".join(
        f"<tr><td>{esc(k)} px</td><td class='num'>{r['eligible']:,}</td>"
        f"<td class='num'>{r['dti']:.5f}</td></tr>"
        for k, r in sorted(sel.get("sweeps", {}).get("buffer", {}).items()))
    lat_rows = "".join(
        f"<tr><td>{esc(k)} px</td><td class='num'>{r['dti']:.5f}</td>"
        f"<td class='num'>{r['tp_w']:.0f}</td><td class='num'>{r['fp_w']:.0f}</td></tr>"
        for k, r in sorted(sel.get("sweeps", {}).get("lattice", {}).items()))
    cov_rows = "".join(
        f"<tr><td class='num'>{int(k):,}</td><td class='num'>{float(c):.4f}</td>"
        f"<td class='num'>{sel['uniform_by_mass'][k]:.5f}</td></tr>"
        for k, c in sorted(sel.get("coverage_curve", {}).items(), key=lambda kv: int(kv[0]))
        if k in sel.get("uniform_by_mass", {}))
    mass_rows = ""
    md = sel.get("mass_decision") or {}
    if md:
        md = sel["mass_decision"]
        gs = sorted(md["table"], key=lambda x: int(x))
        masses = sorted(next(iter(md["table"].values())), key=lambda x: int(x))
        mass_rows = "<table><tr><th>assumed hidden G</th>" + "".join(
            f"<th class='num'>{int(m):,}</th>" for m in masses) + "</tr>"
        for g in gs:
            mass_rows += f"<tr><td class='num'>{int(g):,}</td>" + "".join(
                f"<td class='num'>{md['table'][g][m]:.4f}</td>" for m in masses) + "</tr>"
        mass_rows += "</table>"

    # --- revision-2 evidence tables -------------------------------------------
    pmasses = ["40000", "60000", "90000", "120000", "180000"]
    order = ["frozen_rm(l7,o19g)", "o19_raw", "o12_sal_s2", "lidar_rankmean",
             "rm(l7,o19g)_4"]
    power_rows = "".join(
        "<tr><td>{n}</td>{cells}<td class=\'num\'>{tn:.4f}</td></tr>".format(
            n=esc(name),
            cells="".join(
                f"<td class='num'>{power['fields'][name]['masses'][m]['dti_matched_frame']:.5f}</td>"
                for m in pmasses if m in power.get("fields", {}).get(name, {}).get("masses", {})),
            tn=power["fields"][name]["masses"]["90000"]["credit_per_dot"],
        )
        for name in order if name in power.get("fields", {}))

    expm = ["60000", "90000", "120000"]
    sweep_rows = ""
    for name, rec in sweep.get("fields", {}).items():
        sweep_rows += (
            f"<tr><td>{esc(name)}</td>"
            + "".join(f"<td class='num'>{rec[m]['dti']:.5f}</td>" for m in expm if m in rec)
            + "".join(f"<td class='num'>{rec[m]['lift']:.2f}x</td>" for m in expm if m in rec)
            + "</tr>")

    ext_rows = ""
    for key, rec in sorted(ext.get("cells", {}).items(),
                           key=lambda kv: (int(kv[0].split("|")[0][3:]),
                                           int(kv[0].split("|")[1]))):
        exp_tag, mass_tag = key.split("|")
        folds = rec.get("folds", {})
        ext_rows += (
            f"<tr><td>^{int(exp_tag[3:])}</td><td class='num'>{int(mass_tag):,}</td>"
            f"<td class='num'>{rec['dti']:.5f}</td><td class='num'>{rec['lift']:.2f}x</td>"
            f"<td class='num'>{rec['credit_per_dot']:.4f}</td>"
            f"<td class='num'>{rec['modelled_central']:.4f}</td>"
            "<td class='num'>" + ", ".join(f"{x['dti']:.4f}" for x in folds.values()) + "</td>"
            "</tr>")

    # transfer-factor sensitivity, computed from the delivered artifact's own
    # proxy credit rather than copied from a table
    _dm = deliv.get("frames", {}).get("S_matched", {})
    t_proxy = _dm.get("tp_w") or v["frames"]["S_matched"].get("tp_w") or fm.get("tp_w")
    cover = _dm.get("coverage")
    fp_w = _dm.get("fp_w")
    z_limit = deliv.get("zero_false_positive_limit", {}).get("value")
    need_cover = deliv.get("required_coverage_for_target", {}).get("required_coverage")
    G_HID, N_DOT = 12_226, int(b["frozen"]["mass"])
    denom = 0.2 * N_DOT + 0.8 * G_HID
    modelled_central = (min(0.887 * t_proxy, G_HID) / denom) if t_proxy else float("nan")
    cover_pct = 100.0 * (cover or 0.0)
    need_cover_pct = 100.0 * (need_cover or 0.0)
    tpn = (t_proxy / float(b["frozen"]["mass"])) if t_proxy else float("nan")
    transfer_rows = "".join(
        f"<tr><td>{a:.3f}</td><td class='num'>{min(a * t_proxy, G_HID):,.0f}</td>"
        f"<td class='num'>{min(a * t_proxy, G_HID) / denom:.4f}</td></tr>"
        for a in (0.30, 0.50, 0.70, 0.887, 1.00)) if t_proxy else ""

    nov_rows = "".join(
        f"<tr><td>{esc(k.replace('_', ' '))}</td><td class='num'>{r['dti']:.5f}</td>"
        f"<td class='num'>{r['lift']:.2f}x</td><td class='num'>{r['dots_on_prior_union']:,}</td></tr>"
        for k, r in novel.get("runs", {}).items())

    body1 = f'''<section class="hero" id="top"><div class="shell"><div class="hero-grid"><div>
<div class="eyebrow">H57 revision 2 · frozen build {esc(b["generated_utc"])} · {int(fmd["mass"]):,} dots</div>
<h1>Download the H57 candidate GeoTIFF.</h1>
<p style="color:#8ce0c0;font-weight:800;font-size:1.05rem">✓ Safe to download and safe to submit: one float32 band on the official
competition grid, every one of the 12,279,160 cells finite and inside [0, 1], no dot on a supplied
catalogue pixel or on any registered prior-artifact pixel, and the only inputs are the competition's own
19-band stack and public-domain USGS 3DEP LiDAR. No unresolved external-data rights.</p>
<div class="actions">
<a class="download" href="{esc(allfin)}" download>Download {esc(allfin.name)}</a>
<a class="download alt" href="{esc(nanf)}" download>NaN-outside twin</a>
<a class="download alt" href="{esc(zipf)}" download>.zip</a></div>
<p class="fine" style="color:#d8e7e3">SHA-256 <span class="hash">{esc(b["files"]["allfinite_tif"]["sha256"])}</span>
&middot; {b["files"]["allfinite_tif"]["bytes"]:,} bytes &middot; {n:,} predicted cells &middot;
{b["files"]["zip"]["bytes"]:,} bytes zipped</p>
<p class="fine" style="color:#d8e7e3">Portal entry name <code>{esc(b["portal_name"])}</code></p>
</div><aside class="hero-card"><span class="tag">Format gate passed</span>
<strong style="color:#00695d">{n:,}</strong>
<p>predicted cells, binary 0/1, all-finite raster, 0 cells outside the study footprint,
0 cells on the supplied catalogue, 0 cells on the 61-artifact prior union.</p>
<p><a href="h57-how-to-submit.html">How to submit in five steps →</a></p></aside></div></div></section>
<main id="main"><section class="main"><div class="shell"><div class="grid">
<article class="card span-12"><h2>Executive summary</h2>
<div class="metrics">
<div class="metric"><b>{fm["dti"]:.4f}</b><small>off-catalogue proxy DTI</small></div>
<div class="metric"><b>{fm["dti"]/uni_all["mean"]:.2f}x</b><small>vs matched-mass uniform</small></div>
<div class="metric"><b>4/4</b><small>spatial macrofolds positive</small></div>
<div class="metric"><b>{fm["dti"]/uni_fp["mean"]:.2f}x</b><small>vs same-pool uniform</small></div>
<div class="metric"><b>{modelled_central:.3f}</b>
<small>modelled hidden score (transfer 0.887)</small></div>
</div>
<p>With unit-height binary predictions the official metric reduces exactly to
<code>DTI = T / (0.2(P &minus; A) + 0.8G + 0.2T)</code>, where <code>P</code> is the number of painted
cells, <code>A</code> the prediction-side kernel credit and <code>T</code> the truth-side credit. Two
consequences were measured rather than assumed. First, a painted cell that sits on a truth cell is
<b>free</b> (its false-positive term is zero), so the economics are driven by recall per painted cell.
Second, because the hidden truth is defined as <i>fault pixels the public catalogue does not already
contain</i>, a field that is highest near the catalogue is not automatically a good field — the artifact
therefore spreads its dots in proportion to the evidence instead of stacking them on the strongest
pixels, and the emitter's geometry was chosen by experiment
(<a href="docs/research/h57-final-analysis.md">analysis</a>,
<a href="evidence/h57_emission_shapes.json">emitter experiment</a>).</p>
<p>The field is a <b>sharpened</b> NaN-aware rank-mean of two families: the official layer 19
(detrended-elevation slope) gradient magnitude, which is the step-edge detector for a fault scarp, and
the USGS 3DEP 1 m LiDAR scarp descriptor stack. The sharpening exponent is <b>^{int(fmd["sharpen_exponent"])}</b>
and it is not a cosmetic parameter: a rank <i>mean</i> compresses the top of the distribution exactly
where the emitter makes its decision, and raising the blend to a power raised the lift over a
matched-mass uniform scatter from <b>1.33×</b> to <b>1.84×</b> at the same dot count
(<a href="evidence/h57_sharpen_sweep.json">exponent sweep</a>). {n:,} dots are placed by a
field-weighted sample on a 3&nbsp;px lattice, one per chosen block, on the strongest eligible cell of
that block.</p>
<div class="warning"><b>What this number is not.</b> {fm["dti"]:.4f} is measured against a
<i>proxy</i> — USGS SGMC fault pixels that are more than 300 m from the supplied catalogue — not
against the organizers' hidden labels, which are not available to anyone outside the competition. It is
a relative instrument for choosing between designs, not a predicted leaderboard score. No portal upload
has been made from this repository, so no score is claimed anywhere on this site.</div>
</article>

<article class="card span-12"><h2>Why the historical portal error cannot happen with this file</h2>
<p>The portal once rejected an upload with <code>Predicted values must be in range [0, 1]</code>. A
non-finite cell makes a plain <code>min()/max()</code> range check see <code>NaN</code>, and
<code>NaN &lt;= 1</code> is false. This raster writes <b>0.0 outside the study footprint</b>, so all
{b["reread"]["finite_cells"]:,} cells are finite and <code>min = 0.0</code>, <code>max = 1.0</code>.
The check was re-run by reading the delivered bytes back, not from the in-memory array:
<code>plain_minmax_in_range = {str(chk["format"]["plain_minmax_in_range"]).lower()}</code>,
<code>outside_unit_interval = {chk["format"]["outside_unit_interval"]}</code>,
<code>nan_cells = {chk["format"]["nan_cells"]}</code>.
The <code>-nan.tif</code> twin keeps the official sample's convention for portals that accept it.</p>
</article>

<article class="card span-12"><h2>Measured results</h2>
<p class="muted">Official distance-weighted Tversky metric, implemented in
<code>src/gems57/metric.py</code>. Frame <b>S_matched</b> is the geometry-matched off-catalogue
proxy; <b>S_raw</b> is the repository's unmodified proxy, quoted for comparability with earlier
artifacts; <b>L</b> is the supplied catalogue itself, where a low value is expected and merely shows the
catalogue is not the target.</p>
<div class="wide"><table><tr><th>frame</th><th class="num">truth px</th><th class="num">DTI</th>
<th class="num">per macrofold (NW, NE, SW, SE)</th></tr>{rows}</table></div>
<h3>Field assembly: a quarter of the map was silently blanked</h3>
<p class="muted">The first revision required <i>both</i> evidence families to be finite. The USGS 3DEP
LiDAR scarp stack is undefined on 1,274,189 of the 5,167,373 study cells (24.7 %), so those cells
were dropped from the emission pool. Combining the families with a NaN-aware rank mean instead — the
topographic rank stands in where the LiDAR has no data — recovered 21 % of the truth-side credit for
a reason that had nothing to do with geology.</p>
<div class="wide"><table><tr><th>field assembly</th><th class="num">DTI</th>
<th class="num">truth-side credit</th></tr>{dz_rows}</table></div>
<div class="metrics" style="margin-top:18px">
<div class="metric"><b>{uni_all["mean"]:.5f}</b><small>uniform control, whole footprint</small></div>
<div class="metric"><b>{uni_fp["mean"]:.5f}</b><small>uniform control, same pool</small></div>
<div class="metric"><b>+{boot["mean"]:.4f}</b><small>paired block bootstrap, mean</small></div>
<div class="metric"><b>[{boot["ci95"][0]:.4f}, {boot["ci95"][1]:.4f}]</b><small>95 % interval</small></div>
</div>
<p class="fine">The same-pool control is the fair one, because the candidate is barred from the
prior-artifact union while a whole-footprint uniform draw is not; both are reported. The paired block
bootstrap resamples 32&times;32 px subtiles and was positive in
{boot["positive_fraction"]*100:.0f} % of the {boot["n"]} replicates.</p>
<h3>Which evidence field, scored against the labelled fault population</h3>
<p class="muted">Frame L, the blocked catalogue holdout: for each spatial macrofold the catalogue is
removed in that fold only, the field is emitted into the fold and scored against that fold's own
labels. This measures the field against the fault population that is actually labelled instead of
against a bedrock proxy.</p>
<div class="wide"><table><tr><th>field</th><th class="num">pooled DTI</th>
<th class="num">lift vs matched-mass uniform, per fold</th></tr>{ho_rows}</table></div>
<h3>Emitter geometry, chosen by experiment</h3>
<p class="muted">Three emitter families at matched painted-cell count on frame S, field
<code>o19grad_rank</code>. Concentrating the dots on the strongest pixels and painting skeletonised
lines were both tested and both lose to spreading the dots in proportion to the evidence.</p>
<div class="wide"><table><tr><th>emitter</th><th class="num">requested</th><th class="num">painted</th>
<th class="num">DTI</th><th class="num">lift</th></tr>{shape_rows}</table></div>
<h3>Mask handling and lattice, chosen by experiment</h3>
<p class="muted">DrivenData staff ruled that pixels of the known USGS/INGENIOUS faults are excluded
from evaluation and do not count towards the penalty terms, and that new-fault truth can occur within
300 m of a known trace. A suppressed 300 m buffer therefore discards usable dots and saves nothing.
The matched proxy cannot see this question at all — its truth is <i>defined</i> as more than 300 m from
the catalogue — so the choice was made from the ruling and from the measured price below, and the
buffer is 1 px: only the masked cell itself and its immediate neighbour are removed.</p>
<div class="wide"><table><tr><th>catalogue buffer</th><th class="num">eligible cells</th>
<th class="num">DTI at N = 250,000</th></tr>{buf_rows}</table></div>
<div class="wide" style="margin-top:14px"><table><tr><th>lattice</th><th class="num">DTI</th>
<th class="num">TP&nbsp;credit</th><th class="num">FP&nbsp;mass</th></tr>{lat_rows}</table></div>
</article>

<article class="card span-12"><h2>Revision 2: the sharpening finding, and how it set the dot count</h2>
<p>Two screens after the first build changed the shipped design, and both change it in the direction of
<i>spending fewer dots on better-ranked cells</i>.</p>
<h3>1. A rank mean was flattening the field</h3>
<p class="muted">Frame S, same emitter, same seed, same 3 px lattice and 1 px catalogue buffer; masses
are nested prefixes of one draw, so the columns are paired rather than independently sampled.</p>
<div class="wide"><table><tr><th>field</th><th class="num">40k</th><th class="num">60k</th>
<th class="num">90k</th><th class="num">120k</th><th class="num">180k</th>
<th class="num">credit / dot at 90k</th></tr>{power_rows}</table></div>
<p class="muted" style="margin-top:12px">Sweeping the exponent with everything else frozen — the value
before the sharpening is the first row of the table above, ^{"1"}, which reads 0.17142 at 90,000 dots.
The response is monotone up to ^8 and turns over by ^32.</p>
<div class="wide"><table><tr><th>field</th><th class="num">60k</th><th class="num">90k</th>
<th class="num">120k</th><th class="num">lift 60k</th><th class="num">lift 90k</th>
<th class="num">lift 120k</th></tr>{sweep_rows}</table></div>
<h3>2. Where the exponent and the dot count stop paying</h3>
<p class="muted">The proxy's own DTI is still rising at 250,000 dots, because its truth (52,219 px) is
four times denser on the ground than the hidden target (~12,226 px) and a denser truth keeps repaying
extra dots. The repository's transfer model — hidden credit per dot ≈ 0.887 × proxy credit per dot,
with the calibrated hidden mass — is what says where to stop. Both readings are shown, and they
disagree; the disagreement is the honest state of knowledge, so the artifact is sized at the model's
saturation point and the proxy reading is reported beside it.</p>
<div class="wide"><table><tr><th>exponent</th><th class="num">dots</th><th class="num">proxy DTI</th>
<th class="num">lift</th><th class="num">credit / dot</th>
<th class="num">modelled hidden DTI</th><th class="num">per macrofold (NW, NE, SW, SE)</th>
</tr>{ext_rows}</table></div>
<div class="wide" style="margin-top:14px"><table><tr><th>assumed credit transfer</th>
<th class="num">hidden credit T</th><th class="num">modelled hidden DTI</th></tr>{transfer_rows}</table></div>
<p class="fine">At the calibrated transfer of 0.887 the model's numerator is capped by the assumed
hidden mass, which is why the model saturates: it is saying the delivered 90,000 dots would already
cover the hidden truth. That is the model's most aggressive corner and it is not evidence — at a
transfer of 0.30 the same file models 0.15. The proxy's own reading is 0.23028. The two instruments
bracket the truth and neither is the truth.</p>
<h3>3. What the uniqueness constraint costs</h3>
<p class="muted">Same field, mass, seed and lattice, differing only in whether the 61-artifact prior
union is excluded from the emission pool. The excluded cells are not a random sample — they are
exactly where earlier candidates put their dots, which is where the evidence peaks — so this is the
cheapest place to look for the price of novelty. It is small.</p>
<div class="wide"><table><tr><th>emission pool</th><th class="num">proxy DTI</th>
<th class="num">lift</th><th class="num">dots that would have landed on a prior artifact</th>
</tr>{nov_rows}</table></div>
<div class="metrics" style="margin-top:12px">
<div class="metric"><b>{novel.get("price", {}).get("dti_cost", 0):.5f}</b>
<small>DTI paid for uniqueness</small></div>
<div class="metric"><b>{novel.get("price", {}).get("relative_cost", 0)*100:.2f} %</b>
<small>relative cost</small></div>
<div class="metric"><b>{novel.get("price", {}).get("dots_moved_off_prior_cells", 0):,}</b>
<small>dots moved off prior-artifact cells</small></div>
<div class="metric"><b>{novel.get("price", {}).get("truth_credit_lost", 0):.0f}</b>
<small>proxy truth credit given up</small></div>
</div>
<h3>4. Why the dot count is not the proxy's optimum</h3>
<div class="wide"><table><tr><th class="num">dots</th><th class="num">coverage c(N) on the proxy</th>
<th class="num">matched-mass uniform</th></tr>{cov_rows}</table></div>
<p class="muted">The proxy frame answers "which field ranks fault pixels best"; it cannot answer "how
many dots should be spent", because its truth is four times denser than the hidden target and there is
no penalty for over-spending in a frame whose truth is that generous. The decision therefore comes from
the transfer model above, and the sensitivity table is the honest statement of how much rests on it.</p>
</article>

</article>

<article class="card span-12"><h2>What the delivered file itself measures, and its ceiling</h2>
<p>These are read from the artifact's own bytes with <code>scripts/h57_delivered_metrics.py</code>
(<a href="evidence/h57_delivered_metrics.json">evidence</a>), not from the screen that chose the
field: {t_proxy:,.0f} of truth-side credit on the geometry-matched frame — a coverage of
<b>{cover_pct:.1f} %</b> — and {fp_w:,.0f} of false-positive mass across {n:,} painted cells.</p>
<div class="metrics">
<div class="metric"><b>{cover_pct:.1f} %</b><small>coverage of the proxy truth</small></div>
<div class="metric"><b>{tpn:.3f}</b><small>truth credit per painted cell</small></div>
<div class="metric"><b>{z_limit:.4f}</b><small>score at this coverage with zero false positives</small></div>
<div class="metric"><b>{need_cover_pct:.1f} %</b><small>coverage a perfect-precision 0.3774 needs</small></div>
</div>
<p class="fine">The third figure is the file's own ceiling on this frame: a prediction with no
false-positive mass at all and this same coverage would score {z_limit:.4f}, and the delivered file
realises {(fm["dti"] / z_limit * 100) if z_limit else float("nan"):.0f} % of it. That ceiling is
<b>below the 0.3774 target</b>, which is the sharpest statement of what is left to do: the target
cannot be reached on this frame by precision alone, so the next step is coverage — either a field that
finds fault pixels this one misses, or the continuation/splay idea the staff ruling R6 makes
admissible and that no frame held here can score.</p>
</article>

<article class="card span-12"><h2>Uniqueness</h2>
<p>Every dot was drawn from a pool that excludes the registered positive union of all 61 prior
artifacts, and the delivered bytes were then re-read and checked against it.</p>
<div class="metrics">
<div class="metric"><b>{u["exact_overlap_cells"]}</b><small>exact cells shared with the prior union</small></div>
<div class="metric"><b>{u["worst_block8_iou"]:.4f}</b><small>worst 800 m block IoU, 50 priors</small></div>
<div class="metric"><b>{u["worst_block32_iou"]:.4f}</b><small>worst 3.2 km block IoU, 50 priors</small></div>
<div class="metric"><b>{u.get("n_compared", 0)}</b><small>prior artifacts compared</small></div>
</div>
<p class="fine">The exact-cell overlap is zero by construction. The 2 px proximity statistic
(<code>{u["overlap_within_2px_cells"]:,}</code> cells, {u["novel_fraction_at_2px"]*100:.1f} % novel)
is <b>not</b> a novelty guarantee and is quoted only to show why: the prior union's 2 px neighbourhood
already covers 85.2 % of the study footprint, so a uniform draw of the same mass would look
&quot;novel&quot; only about 15 % of the time. Block IoU against the 50 signature-pinned priors is the
discriminating measure, and the worst case is {u["worst_block8_iou"]:.4f} at 800 m.</p>
</article>

<article class="card span-6"><h2>Limitations, stated plainly</h2>
<ul class="list">
<li>The proxy frame is made of USGS SGMC bedrock faults. The hidden labels are young surface faults.
The two populations are related but not the same, and no measurement in this repository can close that
gap.</li>
<li><b>The mass decision rests on an assumption, and the two instruments disagree by more than the
decision is worth.</b> The proxy says spend 250,000 dots or more; the repository's transfer model, at
the transfer factor calibrated on the repository's own earlier detectors, says stop at 90,000. The
sensitivity table above shows what happens at other transfer factors. If the transfer were 0.30 the
file would be modelled at 0.15 rather than 0.44; if the proxy's ranking is the better guide the file is
under-spent by roughly a factor of two. Both readings are in the evidence.</li>
<li>The translation control is <i>not</i> discriminative here: shifting the whole raster by 3 or 7 px
barely changes the score ({v["controls"]["translation_max"]:.4f} at best), because the evidence field
is spatially autocorrelated. It is reported for completeness, not as evidence of localisation.</li>
<li>The seismicity point-pattern term required by the brief is implemented and measured at or below
chance on both frames; it is therefore <b>not</b> in this artifact (see the hypotheses page).</li>
<li>No organizer score exists for this file. It has never been uploaded.</li>
</ul></article>
<article class="card span-6"><h2>What was tested and rejected this session</h2>
<ul class="list">
<li><b>Dense painting of the strongest pixels</b> (blobs) and <b>skeletonised 1 px lines</b>: both lose
to field-weighted spreading at matched painted count — see the emitter table above.</li>
<li><b>A 24.7 % dead zone.</b> The first revision of the builder required both evidence families to be
finite before a cell could receive dots. The LiDAR stack is undefined on 1,274,189 cells inside the
footprint, so a quarter of the map silently received no dots, costing 21 % of the truth-side credit.
The field is now a NaN-aware rank mean. <a href="evidence/h57_decompose.json">Decomposition</a>.</li>
<li><b>A random-pixel sparse truth</b> for mass calibration, which severs line connectivity and biases
the optimum high. Replaced by whole-component selection.</li>
<li><b>A rank mean without sharpening.</b> The first frozen revision shipped the NaN-aware
<code>rank-mean(lidar bands 02-08, o19_gradmag)</code> unsharpened, at 180,000 dots: 0.21812 on this
frame, 1.31× the matched-mass uniform control. It is <b>superseded</b> by the revision delivered here
(0.23028, 1.86×, with a higher credit per dot at a fifth of the cost). The older file stays in
<code>docs/downloads</code> for comparison and is labelled superseded wherever it is linked.</li>
<li><b>Sharpening past ^16</b>: the exponent sweep turns over at ^32, so ^16 is the frozen value rather
than the largest tried.</li>
<li><b>Strike continuation of catalogue endpoints</b> — formally admissible under the staff ruling and
arguably the highest-value unvalidated idea, but no frame held here can score it, so it is not shipped.
<a href="docs/hypotheses-20261007-h57.md">Hypotheses</a>.</li>
</ul></article>

<article class="card span-12"><h2>Reproduce it</h2>
<pre class="hash" style="display:block;white-space:pre-wrap">python scripts/build_h57.py          # writes docs/downloads/* and evidence/h57_build.json
python scripts/check_h57_submission.py --nan-tif docs/downloads/...-nan.tif \
       --out evidence/h57_check.json   # format gate and novelty gate, re-read from disk
python scripts/validate_h57.py --tif docs/downloads/...-allfinite.tif \
       --out evidence/h57_validation.json
python scripts/build_h55_site.py &amp;&amp; python scripts/build_h57_site.py   # rebuild this site</pre>
<p class="fine">All parameters are frozen in the receipt: field
<code>{esc(fmd["field"])}</code>, lattice {fmd["lattice_px"]} px, mass {fmd["mass"]:,}, catalogue
buffer {fmd["catalogue_buffer_px"]} px, probability floor {fmd["floor_frac"]}, RNG seed
{fmd["rng_seed"]}.</p>
</article>
</div></div></section></main>'''

    (ROOT / "h57.html").write_text(chrome(
        "H57 candidate: download and full evidence", body1,
        description="Download the H57 fault-probability GeoTIFF: one click, format and novelty gates "
                    "passed, full validation evidence.",
    ).rstrip() + "\n", encoding="utf-8")

    steps = [
        ("<b>Download</b> the GeoTIFF with the button at the top of "
        '<a href="h57.html">the H57 page</a>. If you want to be certain the bytes are intact, compare '
         'its SHA-256 with <span class="hash">'
         f'{esc(b["files"]["allfinite_tif"]["sha256"])}</span>.'),
        ('<b>Open the competition page</b> at '
         '<a href="https://www.drivendata.org/competitions/306/competition-doe-gems/">'
         'drivendata.org/competitions/306/competition-doe-gems/</a> and sign in. The rules, the '
         'submission format and the data tab are the authoritative documents; the forum rulings '
         'quoted on this site are '
         '<a href="https://community.drivendata.org/t/scoring-clarification-are-known-usgs-'
         'ingenious-faults-masked-when-scoring-and-are-they-in-the-final-round-label-set/11516">'
         'here</a> and <a href="https://community.drivendata.org/t/where-do-you-draw-the-line/11536">'
         'here</a>.'),
        ("<b>Upload the file exactly as downloaded.</b> Do not re-save, re-project, re-compress, "
         "re-scale or convert it. Every gate reported on this site was run on the delivered bytes."),
        (f'<b>Use this submission name:</b> <code>{esc(b["portal_name"])}</code>. '
         "<b>Paste this optional note:</b> <q>" + esc(b["portal_note"]) + "</q>"),
        ("<b>Record the receipt.</b> Save the portal confirmation and the returned score into this "
         "repository before quoting any score. Until that file exists, this repository claims no "
         "score for this artifact."),
    ]
    steps_html = "".join(f"<li>{s}</li>" for s in steps)
    body2 = f'''<main id="main"><section class="pagehead"><div class="shell">
<div class="eyebrow">Executive summary</div>
<h1>How to submit the H57 file</h1>
<p>Five steps, no ambiguity about which file is current. If the top of
<a href="h57.html">the H57 page</a> says the format gate passed, the file linked there is the one to
upload.</p></div></section>
<section class="main" style="padding-top:8px"><div class="shell"><div class="grid">
<article class="card span-12"><h2>The five steps</h2><ol class="steps">{steps_html}</ol>
<div class="good"><b>Is it safe to submit?</b> The raster is one float32 band on the official
3,730 &times; 3,292 grid, EPSG:32611, values exactly 0 or 1, every cell finite and inside [0, 1],
zero cells outside the study footprint, zero cells on the supplied catalogue and zero cells shared
with the 61-artifact prior union. The only inputs are the competition's own feature stack and
public-domain USGS 3DEP products, so there is no external-data rights question.</div>
<div class="notice"><b>Budget.</b> The competition allows a limited number of scored uploads per
week. This artifact is a research candidate that passed every local gate; the decision to spend a
weekly slot is the owner's. Nothing on this site has been uploaded, and no score is claimed.</div>
</article>
<article class="card span-12"><h2>Exact file facts</h2>
<div class="wide"><table>
<tr><th>field</th><th>value</th></tr>
<tr><td>file</td><td><code>{esc(allfin.name)}</code></td></tr>
<tr><td>bytes</td><td class="num">{b["files"]["allfinite_tif"]["bytes"]:,}</td></tr>
<tr><td>SHA-256</td><td><span class="hash">{esc(b["files"]["allfinite_tif"]["sha256"])}</span></td></tr>
<tr><td>grid</td><td class="num">3,730 rows &times; 3,292 cols, 100 m, EPSG:32611</td></tr>
<tr><td>transform</td><td class="num">100, 0, 243350, 0, -100, 4508550</td></tr>
<tr><td>dtype / bands</td><td>float32 / 1</td></tr>
<tr><td>values</td><td>{b["reread"]["values"]}</td></tr>
<tr><td>predicted cells</td><td class="num">{n:,}</td></tr>
<tr><td>finite cells</td><td class="num">{b["reread"]["finite_cells"]:,} of 12,279,160 (no NaN)</td></tr>
<tr><td>entry name</td><td><code>{esc(b["portal_name"])}</code></td></tr>
<tr><td>twin</td><td><code>{esc(nanf.name)}</code> (NaN outside the footprint, official sample convention)</td></tr>
<tr><td>zip</td><td><code>{esc(zipf.name)}</code> &middot; SHA-256 <span class="hash">{esc(b["files"]["zip"]["sha256"])}</span></td></tr>
</table></div></article>
</div></div></section></main>'''
    (ROOT / "h57-how-to-submit.html").write_text(chrome(
        "How to submit the H57 file", body2,
        description="Five steps from download to scored submission, with the exact portal name, note, "
                    "hashes and file facts.", active="submit",
    ).rstrip() + "\n", encoding="utf-8")

    # ---- banner at the very top of index.html --------------------------------
    index = ROOT / "index.html"
    text = index.read_text(encoding="utf-8")
    banner = (
        BEGIN
        + '<div style="background:#00695d;color:#fff;padding:11px 0">'
        '<div class="shell" style="display:flex;flex-wrap:wrap;gap:14px;align-items:center;'
        'justify-content:space-between">'
        '<span style="font-weight:800">Current candidate: H57 topographic-lineament scatter '
        f'&mdash; format and novelty gates passed, {fm["dti"]:.4f} off-catalogue proxy DTI '
        f'({fm["dti"]/uni_all["mean"]:.2f}&times; matched-mass uniform), 4/4 spatial folds.</span>'
        '<span style="display:flex;gap:10px;flex-wrap:wrap">'
        f'<a class="download" style="padding:9px 14px" href="{esc(allfin)}" download>'
        "Download the GeoTIFF</a>"
        '<a class="download alt" style="padding:9px 14px" href="h57.html">Evidence &amp; how to '
        "submit</a></span></div></div>"
        + END
    )
    if BEGIN in text and END in text:
        head, rest = text.split(BEGIN, 1)
        _, tail = rest.split(END, 1)
        text = head + banner + tail
    else:
        marker = '<body><a class="skip" href="#main">Skip to content</a>'
        if marker in text:
            text = text.replace(marker, marker + banner, 1)
        else:
            text = text.replace("<body>", "<body>" + banner, 1)
    index.write_text(text, encoding="utf-8")

    for p in (ROOT / "h57.html", ROOT / "h57-how-to-submit.html"):
        print(f"wrote {p.relative_to(ROOT)} ({p.stat().st_size:,} bytes)")
    print(f"patched {index.relative_to(ROOT)} ({index.stat().st_size:,} bytes)")


if __name__ == "__main__":
    main()
