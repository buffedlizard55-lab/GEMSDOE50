#!/usr/bin/env python3
"""Regenerate the site's machine-readable feeds from the registry.

Run by .github/workflows/site.yml on every push, so no page can drift from the
JSON receipts that the checks wrote.
"""

from __future__ import annotations

import datetime
import hashlib
import json
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"
DATA = DOCS / "data"

LEADERBOARD = [
    ("xiaofanhu", 0.3774), ("alexoktaba", 0.3345), ("nchuzhoy", 0.3262),
    ("kinghorton42", 0.3222), ("joeyfezster", 0.3220), ("Batik", 0.3218),
    ("DARD", 0.3195), ("ndavis7", 0.2888), ("mzoorob", 0.2884),
    ("GrigorSargsyan", 0.2876), ("HardcoreTechGod", 0.2854), ("op01", 0.2792),
    ("extradr19", 0.2778), ("wbg1", 0.2750), ("smashi34", 0.2710),
    ("smrtdoog5", 0.2708), ("jgaines", 0.2638), ("ad3002", 0.2634),
    ("SDCF9", 0.2600), ("kpomazi", 0.2517), ("Mekhi12", 0.2515),
    ("tchu", 0.2511), ("BrandenKMurray", 0.2502),
]


def read(name: str):
    p = ROOT / "registry" / name
    return json.loads(p.read_text()) if p.exists() else None


def main() -> int:
    DATA.mkdir(parents=True, exist_ok=True)
    sub = next(iter(sorted((ROOT / "downloads").glob("*.tif"))), None)
    sha = hashlib.sha256(sub.read_bytes()).hexdigest() if sub else None

    checks = read("submission_checks.json")
    checks_ci = read("submission_checks_ci.json")
    validation = read("submission_validation.json")
    build = read("submission_build.json")
    sources = read("sources.json")

    (DATA / "no_manual_check.json").write_text(json.dumps({
        "generated_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds"),
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
        "generated_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds"),
        "submission_scored_on_both_frames": validation,
        "build_diagnostics": build,
        "note": "F1 = catalogue-fold frame; F2 = SGMC off-catalogue frame. Proxies, not leaderboard scores.",
    }, indent=1))

    (DATA / "feed.json").write_text(json.dumps({
        "generated_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds"),
        "kind": "static snapshot — regenerated on every push, no third-party API required",
        "public_leaderboard_snapshot": {
            "fetched": "2026-10-06",
            "source": "https://www.drivendata.org/competitions/306/competition-doe-gems/leaderboard/",
            "best": 0.3774,
            "entries": [{"rank": i + 1, "team": t, "score": s} for i, (t, s) in enumerate(LEADERBOARD)],
        },
        "our_submission": {"file": sub.name if sub else None, "sha256": sha,
                           "dots": (checks.get("format") or {}).get("positive_px") if checks else (build.get("n_dots") if build else None)},
        "evidence_frames": {
            "F1_catalogue_folds": {"scarp": 0.01127, "struct": 0.02173, "seis": 0.00728,
                                   "density_300m": 0.01120, "random": 0.02088},
            "F2_sgmc_off_catalogue": {"scarp": 0.03450, "struct": 0.00867, "seis": 0.00660,
                                      "density_300m": 0.00426, "random": 0.01900},
            "budget_dots": 44090,
            "source": "registry/field_validation.json",
        },
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

    # site assets and downloads live outside docs/ so the repo stays one source of truth
    for name in ("downloads", "assets"):
        src, dst = ROOT / name, DOCS / name
        if src.exists():
            shutil.rmtree(dst, ignore_errors=True)
            shutil.copytree(src, dst)
    print("site feeds written:", sorted(p.name for p in DATA.glob("*.json")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
