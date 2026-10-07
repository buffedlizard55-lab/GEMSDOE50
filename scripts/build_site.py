#!/usr/bin/env python3
"""Regenerate archival feeds and current H53-A no-go status from committed evidence.

This script never fetches a leaderboard or external catalog. Inherited H50/H51 TIFFs
are historical only and must not be labeled as current submission recommendations.
Current root pages are built by scripts/build_h50_site.py.
"""

from __future__ import annotations

import hashlib
import json
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"
DATA = DOCS / "data"

def read(name: str):
    p = ROOT / "registry" / name
    return json.loads(p.read_text()) if p.exists() else None


def main() -> int:
    DATA.mkdir(parents=True, exist_ok=True)
    legacy_name = "gems50-seislin-44709-20261006T2041Z-79e260ae.tif"
    sub = ROOT / "downloads" / legacy_name
    if not sub.exists():
        sub = next(iter(sorted((ROOT / "downloads").glob("*.tif"))), None)
    sha = hashlib.sha256(sub.read_bytes()).hexdigest() if sub else None

    checks = read("submission_checks.json")
    checks_ci = read("submission_checks_ci.json")
    validation = read("submission_validation.json")
    build = read("submission_build.json")
    sources = read("sources.json")
    h53_build_path = ROOT / "evidence" / "h53-build-20261007.json"
    h53_validation_path = ROOT / "evidence" / "h53-validation-20261007.json"
    h53_build = json.loads(h53_build_path.read_text(encoding="utf-8")) if h53_build_path.exists() else None
    h53_validation = json.loads(h53_validation_path.read_text(encoding="utf-8")) if h53_validation_path.exists() else None
    h53_artifact = ((h53_build or {}).get("candidate", {}).get("artifact", {}))
    h53_current = {
        "status": "NO-GO / NO SLOT" if h53_validation else "research-only; validation pending",
        "name": (h53_build or {}).get("candidate", {}).get("name"),
        "file": h53_artifact.get("path"),
        "sha256": h53_artifact.get("sha256"),
        "positive_pixels": h53_artifact.get("positive_cells"),
        "local_dti": (((h53_validation or {}).get("candidate", {}).get("native_pooled_dti", {})).get("score")),
        "slot_decision": (((h53_validation or {}).get("decision", {})).get("slot_decision", "not evaluated")),
        "submission_eligible": False,
        "organizer_score": None,
        "portal_upload": None,
        "weekly_slot_used": False,
    }

    (DATA / "no_manual_check.json").write_text(json.dumps({
        "current_project_status": "H53-A NO-GO / NO SLOT",
        "current_candidate": h53_current,
        "role": "historical format/uniqueness audit only; not a current submission recommendation",
        "do_not_submit": True,
        "generated_from": "registry/submission_checks.json, registry/submission_checks_ci.json",
        "submission": sub.name if sub else None,
        "sha256": sha,
        "format": checks.get("format") if checks else None,
        "uniqueness": {k: v for k, v in (checks.get("uniqueness") or {}).items() if k != "corpus_entries"} if checks else None,
        "verdict": ("PASS" if checks["format"]["all_checks_pass"]
                    and checks["uniqueness"].get("verdict_unique")
                    else "SKIPPED (prior-artifact corpus not present here)"
                    if checks["uniqueness"].get("verdict") == "SKIPPED" else "UNKNOWN") if checks else "UNKNOWN",
        "checked_by": "scripts/check_submission.py",
        "uniqueness_at_ci_level": {k: v for k, v in (checks_ci.get("uniqueness") or {}).items()} if checks_ci else
                                  "not yet recorded on this branch",
        "levels": {
            "full_pixel": "prior-artifact corpus present (development machine); "
                          "fine-scale IoU and dot-novelty resolved",
            "block_signature": "bare CI runner; 8x/32x block occupancy from "
                               "registry/prior_artifact_signatures.npz",
        },
    }, indent=1))

    (DATA / "validation.json").write_text(json.dumps({
        "current_project_status": "H53-A NO-GO / NO SLOT",
        "current_candidate": h53_current,
        "historical_experiment": "archived H50 seismicity raster; local proxy only",
        "do_not_submit": True,
        "generated_from": "registry/submission_validation.json, registry/submission_build.json",
        "submission_scored_on_both_frames": validation,
        "build_diagnostics": build,
        "note": "F1 = catalogue-fold frame; F2 = SGMC off-catalogue frame. Proxies, not leaderboard scores.",
    }, indent=1))

    compare_path = ROOT / "evidence" / "h51_candidate_frame_compare.json"
    shared_frame = {"evidence": "evidence/h51_candidate_frame_compare.json"} if compare_path.exists() else None
    if shared_frame:
        cmp = json.loads(compare_path.read_text())
        shared_frame["frame"] = cmp.get("frame")
        shared_frame["truth_px"] = cmp.get("truth_px")
        shared_frame["dti"] = {name: round(row["dti"], 6) for name, row in cmp.get("rows", {}).items()}
        shared_frame["uniform_control"] = cmp.get("uniform_control")

    h51_ship = ROOT / "evidence" / "h51_ship.json"
    h51_check = ROOT / "evidence" / "h51_check_submission.json"
    h51_candidate = None
    if h51_ship.exists():
        ship = json.loads(h51_ship.read_text())
        chk = json.loads(h51_check.read_text()) if h51_check.exists() else {}
        tif = ROOT / ship["outputs"]["tif"]
        h51_candidate = {
            "role": "historical H51 research artifact; not the current recommendation",
            "current_recommendation": False,
            "archive_note": ("Historical identity only. H51 failed its pre-registered promotion proxy; "
                            "no organizer score, upload, or receipt is verified. Do not use as portal instructions."),
            "submission_eligible": False,
            "file": Path(ship["outputs"]["tif"]).name,
            "sha256": ship["outputs"]["sha256"],
            "bytes": ship["outputs"]["bytes"],
            "present": tif.exists(),
            "format_gate_pass": chk.get("format", {}).get("all_checks_pass"),
            "uniqueness_gate_pass": chk.get("uniqueness", {}).get("verdict_unique"),
            "pixels_shared_with_any_prior_artifact": ship["gate"].get("pixels_shared_with_any_prior", 0),
            "worst_proximity_iou": ship["gate"].get("measured_iou2px_max"),
            "worst_proximity_iou_file": ship["gate"].get("worst_overlap_file"),
            "predicted_score_local": ship["predicted"]["DTI"],
            "predicted_score_source": "leave-one-out score instrument over 25 hash-verified artifacts; a local prediction, not an organizer score",
            "proxy_gate_pass": False,
            "proxy_gate_note": (
                "Fails the pre-registered sgmc_off proxy; that proxy cannot rank the 25 scored "
                "artifacts (Spearman +0.196, p = 0.35), so it is reported and not used as a pass."
            ),
            "organizer_score": None,
            "portal_upload": None,
            "weekly_slot_used": False,
            "download": ship["outputs"]["tif"],
            "historical_label": Path(ship["outputs"]["tif"]).stem,
            "shared_frame_compare": shared_frame,
        }
    (DATA / "feed.json").write_text(json.dumps({
        "generated_from": "historical receipts plus the current H53-A build/validation; no third-party leaderboard data",
        "kind": "current H53-A status with historical H50/H51 records; no leaderboard snapshot is published",
        "current_status": "H53-A NO-GO / NO SLOT",
        "current_candidate": h53_current,
        "leaderboard": {
            "published": False,
            "reason": "Prior sibling-repository notes are conflicting and are not a fresh independent official check; no current score or score-to-TIFF mapping is asserted.",
            "source": "https://www.drivendata.org/competitions/306/competition-doe-gems/leaderboard/",
        },
        "legacy_artifact": {
            "file": sub.name if sub else None,
            "sha256": sha,
            "role": "same-fold comparator / historical reference only; not a current submission",
            "organizer_score": None,
        },
        "h50_s1": {
            "status": "research-only; real-data experiment not yet run",
            "organizer_score": None,
            "portal_upload": None,
            "weekly_slot_used": False,
        },
        "h51_candidate": h51_candidate,
    }, indent=1))

    if sources:
        (DATA / "sources.json").write_text(json.dumps(sources, indent=1))

    # CSV preview of the earthquake catalogue (the owner inspects CSV files)
    import csv
    import gzip

    cat = ROOT / "data" / "external" / "usgs_comcat_earthquakes.csv.gz"
    if cat.exists():
        with gzip.open(cat, "rt") as f, (DATA / "comcat_preview.csv").open("w", newline="") as g:
            r, w = csv.reader(f), csv.writer(g)
            w.writerow(next(r))
            for _ in range(25):
                try:
                    w.writerow(next(r))
                except StopIteration:
                    break
        print("csv preview: data/comcat_preview.csv (25 rows)")

    # Preserve committed docs/downloads artifacts (including the current H53 no-go
    # research raster). Merge archived root downloads without deleting newer files.
    src_downloads, dst_downloads = ROOT / "downloads", DOCS / "downloads"
    if src_downloads.exists():
        dst_downloads.mkdir(parents=True, exist_ok=True)
        for item in src_downloads.iterdir():
            target = dst_downloads / item.name
            if item.is_file() and not target.exists():
                shutil.copy2(item, target)
    # Assets remain a generated mirror; the download directory is deliberately non-destructive.
    src_assets, dst_assets = ROOT / "assets", DOCS / "assets"
    if src_assets.exists():
        shutil.rmtree(dst_assets, ignore_errors=True)
        shutil.copytree(src_assets, dst_assets)
    print("site feeds written:", sorted(p.name for p in DATA.glob("*.json")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
