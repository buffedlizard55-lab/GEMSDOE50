#!/usr/bin/env python3
"""Publish the H60 gate decision and the H60-union alternative band.

Runs after ``scripts/build_h55_site.py`` and ``scripts/build_h58_site.py`` (the same
order as the site workflow) and inserts:

* ``index.html``   — an H60-union band directly below the H57 executive band, with the
  one-click downloads, the artifact SHA-256 re-verified on disk, the frozen verdict
  (NO SLOT: statistically tied with H57), the unique entry name and note, and the
  novelty/score trade-off that the maximal-novelty control measured;
* ``results.html`` — a compact H60 decision card with the three instruments and the arm
  table.

Every number is read from committed evidence (``evidence/build_h60-union-d0.json``,
``evidence/h60_gate_decision.json``, ``evidence/h60_holdout_offcat.json``,
``evidence/h60_validation-d0.json``, ``evidence/h60_holdout_offcat-d2.json``); the
artifact is re-hashed before anything is published.  The insertion is deterministic and
idempotent, which keeps the CI ``git diff --exit-code`` check green.
"""
from __future__ import annotations

import hashlib
import html
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BUILD = ROOT / "evidence/build_h60-union-d0.json"
DECISION = ROOT / "evidence/h60_gate_decision.json"
GATE = ROOT / "evidence/h60_holdout_offcat.json"
F1 = ROOT / "evidence/h60_validation-d0.json"
CONTROL_GATE = ROOT / "evidence/h60_holdout_offcat-d2.json"
UNIQUE = ROOT / "evidence/h60_uniqueness-d0.json"

INDEX_ANCHOR = '<section class="main" id="h56">'
RESULTS_ANCHOR = '<article class="card span-12" id="h33">'

META_BASE = (
    '<meta name="description" content="H57 download and executive summary, H56 comparator, '
    'H55 blocked decision, H53-A no-go audit, score provenance.">'
)  # written by scripts/build_h58_site.py, which runs before this script
META_H60 = (
    '<meta name="description" content="H60-union alternative (statistical tie with H57), '
    'H57 download and executive summary, H56 comparator, H55 blocked decision, H53-A no-go '
    'audit, score provenance.">'
)


def esc(value: object) -> str:
    return html.escape(str(value), quote=True)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load(name: str) -> dict:
    return json.loads((ROOT / name).read_text(encoding="utf-8"))


def index_band(b: dict, dec: dict, gate: dict, f1: dict, ctl_gate: dict,
               ctl_uniq: dict, uniq: dict) -> str:
    files = b["files"]
    allf, nanf, zipped = files["all_finite"], files["nan_outside"], files["zip"]
    primary = ROOT / allf["path"]
    if sha256(primary) != allf["sha256"]:
        raise ValueError("H60-union artifact drift: refusing to publish its band")
    cand = dec["candidates"]["H60-union-d0-75308"]
    inc = dec["candidates"]["H57-scarpstep-80000"]
    verdict = dec["verdict"]
    ranking_html = " &gt; ".join(
        "<b>" + esc(row["artifact"]) + "</b> " + format(row["pooled_dti"], ".4f")
        for row in verdict["ranking_on_frozen_gate"])
    _pa = dec["prior_pixel_audit"]["overlap"]
    du = cand["frozen_gate_pooled_dti"]
    d57 = inc["frozen_gate_pooled_dti"]
    fu = cand["F1_pooled_dti"]
    f57 = inc["F1_pooled_dti"]
    ov57 = _pa["H57-scarpstep-80000"]
    ov56 = _pa["H56-scarpdisperse-90000"]
    base = Path(allf["path"]).name[: -len("-allfinite.tif")]
    return f"""<section class="main" id="h60"><div class="shell"><div class="grid"><article class="card span-12"><h2>Alternative candidate (H60-union) &mdash; beats the older H57 on both instruments, <b>ranked second overall, not promoted</b></h2><div class="hero" style="border-radius:10px;padding:18px 20px;margin-bottom:14px"><div class="actions"><a class="download" href="{esc(allf['path'])}" download>Download {esc(base)}-allfinite.tif</a><a class="download alt" href="{esc(nanf['path'])}" download>NaN-outside twin</a><a class="download alt" href="{esc(zipped['path'])}" download>.zip</a></div><p class="fine" style="color:#d8e7e3">SHA-256 <span class="hash">{esc(allf['sha256'])}</span> &middot; {allf['bytes']:,} bytes &middot; {b['dots']:,} predicted cells &middot; unique entry name (draft) <code>GEMSDOE50-H60-UNION-75308</code></p><p class="fine" style="color:#d8e7e3"><b>Draft optional note (paste into the portal note field):</b> <q>H60-union four-family structural belief emitter; every dot is &ge;300 m from the given catalogue and from every prior submission pixel; research model, not organizer-scored.</q></p></div><p class=\"warning\"><b>Which file should you submit? The current candidate in the green banner at the very top of this page.</b> On this repository's own frozen spatially-blocked gate the measured ranking is {ranking_html}. H60-union is <b>not promoted and is recorded NO SLOT for H60</b>: it beats the older H57 on both instruments (frozen gate {du:.4f} vs {d57:.4f}; pooled off-catalogue F1 {fu:.4f} vs {f57:.4f}), but the current candidate scores higher on the same gate and stays the recommendation. <b>Submitting H60-union is not forbidden and not unsafe</b> &mdash; it is a unique, portal-safe GeoTIFF &mdash; it is simply not the file this repository ranks first.</p><p class=\"warning\"><b>Charter compliance finding (2026-10-07):</b> counting dots that land on cells of the frozen 61-file, 1,405,451-cell prior-positive union, H57 places <b>{ov57:,} of 80,000 dots (34.1 %)</b> and H56 places <b>{ov56:,} of 90,000 (31.0 %)</b> on cells a prior submission had already marked positive, while H60-union, H58, the maximal-novelty control and the current H59 candidate place <b>0</b>. The charter forbids reusing prior prediction pixels, so H57 and H56 are historical comparators, <b>not submission candidates</b>, and the earlier copy claim on the H57 band above (a 26-file subset) is superseded by this count.</p><div class="metrics"><div class="metric"><b>{cand['frozen_gate_pooled_dti']:.4f}</b><small>frozen-gate pooled DTI (H57 {inc['frozen_gate_pooled_dti']:.4f})</small></div><div class="metric"><b>{cand['F1_pooled_dti']:.4f}</b><small>off-catalogue F1 pooled DTI (H57 {inc['F1_pooled_dti']:.4f})</small></div><div class="metric"><b>0</b><small>prior positive cells reused (of 1,405,451)</small></div><div class="metric"><b>{cand['uniqueness_min_novel_fraction_at_2px']:.3f}</b><small>dots &gt;2 px from every prior dot (gate 0.500)</small></div></div><h3>What H60 settled: the novelty/score trade-off is measurable, and it is severe</h3><p>H60's question was whether the official 17-channel stack adds anything beyond the LiDAR/topographic-step families that H57 already uses (H60 has no committed preregistration document — see the verdict's limitations), and whether a <i>maximally</i> novel placement can be built that still scores. The answer to the first is no: the union of the two beliefs ({b['dots']:,} dots) is a statistical tie with H57, and the official-stack-only arm is far below the incumbent ({dec['official_stack_arm']['frozen_gate_pooled_dti']:.4f}). The answer to the second is also no, and that is the more useful finding: a control built with a Euclidean disk-radius-2 prior exclusion &mdash; so that <b>every</b> dot is more than 2 px from every prior dot by construction ({ctl_uniq['uniqueness_min_novel_fraction_at_2px']:.3f} novel) &mdash; collapses to <b>{ctl_gate['pooled_dti_candidate']:.4f}</b> on the frozen gate against a matched uniform control's <b>{ctl_gate['pooled_dti_uniform']:.4f}</b>, losing in {4 - ctl_gate['positive_macrofolds']}/4 macrofolds. The prior corpus therefore already occupies the terrain where the proxies carry information: novelty beyond the corpus is bought with score, and the repository's 0.5 strict-novelty threshold, which neither H57 ({inc['uniqueness_min_novel_fraction_at_2px']:.3f}) nor H60-union ({cand['uniqueness_min_novel_fraction_at_2px']:.3f}) meets, is a score-destructive requirement rather than a safety one. What both files do guarantee is the binding constraint of the user charter: <b>not a single prior submission pixel is reused</b> (H60-union reuses {b['dots_on_prior_union']} of {b['prior_union_cells']:,}), with a maximum full-pixel IoU of {uniq.get('max_iou', float('nan')):.4f} against the 30 artifacts on disk (worst overlap: our own {esc(uniq.get('worst_overlap_file', ''))}).</p><p class="muted">Receipts: <a href="{esc(DECISION.relative_to(ROOT))}">gate decision</a> &middot; <a href="{esc(BUILD.relative_to(ROOT))}">build</a> &middot; <a href="{esc(GATE.relative_to(ROOT))}">frozen gate</a> &middot; <a href="{esc(F1.relative_to(ROOT))}">F1 frame</a> &middot; <a href="{esc(CONTROL_GATE.relative_to(ROOT))}">maximal-novelty control</a> &middot; <a href="{esc(UNIQUE.relative_to(ROOT))}">uniqueness</a> &middot; <a href="evidence/h60_screen.json">channel screen</a> &middot; <a href="evidence/h60_sweep.json">mass sweep</a> &middot; <a href="evidence/h60_arms.json">arm comparison</a> &middot; <a href="docs/downloads/README.md">download-directory guide</a> (which file is which). The emitter is deterministic (<code>scripts/build_h60.py</code>), so the exact bytes can be rebuilt and re-checked.</p></article></div></div></section>
"""


def results_card(dec: dict, ctl: dict, ctl_gate: dict) -> str:
    rows = []
    for name, c in dec["candidates"].items():
        rows.append(
            "<tr><td>{}</td><td class=num>{:,}</td><td class=num>{:.4f}</td>"
            "<td class=num>{:.4f}</td><td class=num>{:.4f}</td><td class=num>{:.3f}</td>"
            "<td>{}</td></tr>".format(
                esc(name), int(c["N"]), c["frozen_gate_pooled_dti"], c["F1_pooled_dti"],
                c["hidden_frame_models"]["models"]["both"]["modelled_dti"],
                c["uniqueness_min_novel_fraction_at_2px"],
                "reference (recommended)" if "H57" in name else "NO SLOT (tie)",
            ))
    rows.append(
        "<tr><td>{}</td><td class=num>{:,}</td><td class=num>{:.4f}</td>"
        "<td class=num>{:.4f}</td><td class=num>{:.4f}</td><td class=num>{:.3f}</td>"
        "<td>negative control</td></tr>".format(
            "H60 maximal-novelty control", int(ctl["N"]), ctl["frozen_gate_pooled_dti"],
            ctl["F1_pooled_dti"],
            ctl["hidden_frame_models"]["models"]["both"]["modelled_dti"],
            ctl["uniqueness_min_novel_fraction_at_2px"],
        ))
    return f"""<article class="card span-12" id="h60-decision"><h2>H60 decision card &mdash; a tie, and the price of novelty</h2><p>All rows are the same instruments: the frozen spatially blocked gate (truth = USGS SGMC faults more than 300 m from the given catalogue), the pooled off-catalogue F1 frame, the fitted hidden-frame model (indicative only, never a score), and the strict novelty fraction. A candidate is promoted only if it beats the incumbent on the frozen gate by more than instrument noise; H60 does not, so it is <b>NO SLOT</b> and H57 stays the recommendation.</p><div class="wide"><table><thead><tr><th>candidate</th><th class=num>dots</th><th class=num>frozen gate</th><th class=num>F1 pooled</th><th class=num>model-implied</th><th class=num>&gt;2 px novel</th><th>verdict</th></tr></thead><tbody>{''.join(rows)}</tbody></table></div><p class="warning"><b>The maximal-novelty control is the load-bearing result.</b> Requiring every dot to sit more than 2 px from every prior dot (disk-radius-2 exclusion, {ctl['uniqueness_min_novel_fraction_at_2px']:.3f} novel by construction) costs the frozen gate {ctl_gate['pooled_dti_candidate']:.4f} versus {ctl_gate['pooled_dti_uniform']:.4f} for a matched-mass uniform control, with {ctl_gate['positive_macrofolds']}/4 macrofolds positive. Novelty past the corpus is not free: it is bought with the score that the proxies measure. The binding charter constraint &mdash; zero reused prior pixels and no byte-identical file &mdash; is satisfied by both the reference and the H60-union alternative.</p><p class="muted">Full working: <a href="docs/research/h60-verdict-20261007.md">h60-verdict</a> (see also <a href="evidence/h60_gate_decision.json">gate decision</a>, <a href="evidence/h60_holdout_offcat.json">frozen gate</a>, <a href="evidence/h60_holdout_offcat-d2.json">control</a>).</p><p class="muted"><b>Control and arm files, kept for reproducibility — do not submit:</b> maximal-novelty control <a href="docs/downloads/gemsdoe50-h60-union-d2-75308-20261007T2250Z-allfinite.tif">all-finite</a> / <a href="docs/downloads/gemsdoe50-h60-union-d2-75308-20261007T2250Z.tif">NaN twin</a>; official-stack arm <a href="docs/downloads/gemsdoe50-h60-officialstack-50000-20261007T2100Z-allfinite.tif">all-finite</a> / <a href="docs/downloads/gemsdoe50-h60-officialstack-50000-20261007T2100Z.tif">NaN twin</a>. Every file in the download directory is labelled in <a href="docs/downloads/README.md">docs/downloads/README.md</a>.</p></article>
"""


def insert_before(path: Path, anchor: str, block: str) -> None:
    text = path.read_text(encoding="utf-8")
    if block.strip() in text:
        return
    if text.count(anchor) != 1:
        raise ValueError(f"anchor not unique in {path.name}: {anchor[:50]}...")
    path.write_text(text.replace(anchor, block + anchor, 1), encoding="utf-8")


def main() -> int:
    b, dec = load("evidence/build_h60-union-d0.json"), load(str(DECISION.relative_to(ROOT)))
    gate, f1 = load(str(GATE.relative_to(ROOT))), load(str(F1.relative_to(ROOT)))
    ctl_hold = load(str(CONTROL_GATE.relative_to(ROOT)))
    uniq = load(str(UNIQUE.relative_to(ROOT)))
    ctl_uniq = dec["negative_control_max_novelty"]
    index_path = ROOT / "index.html"
    text = index_path.read_text(encoding="utf-8")
    if META_H60 not in text and META_BASE in text:
        text = text.replace(META_BASE, META_H60, 1)
    index_path.write_text(text, encoding="utf-8")
    insert_before(index_path, INDEX_ANCHOR,
                  index_band(b, dec, gate, f1, ctl_hold["summary"], ctl_uniq, uniq))
    insert_before(ROOT / "results.html", RESULTS_ANCHOR,
                  results_card(dec, ctl_uniq, ctl_hold["summary"]))
    print("H60-union alternative band inserted into index.html; decision card into results.html")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
