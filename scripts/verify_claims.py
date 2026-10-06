#!/usr/bin/env python3
"""Cross-check every headline claim in the documentation against the JSON receipts.

This is the repository's "no manual vetting" gate: if a number on the site, in the
README or in the report stops matching the evidence the checks wrote, this fails and
CI turns red.  Run it after any rebuild.
"""

from __future__ import annotations

import hashlib
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REG = ROOT / "registry"


def load(name: str):
    return json.loads((REG / name).read_text())


def main() -> int:
    checks = load("submission_checks.json")
    validation = load("submission_validation.json")
    build = load("submission_build.json")
    field = load("field_validation.json")
    sources = load("sources.json")
    failures: list[str] = []

    def expect(label: str, got, want) -> None:
        ok = got == want
        print(f"  {'OK ' if ok else 'FAIL'} {label}: {got!r}" + ("" if ok else f" != {want!r}"))
        if not ok:
            failures.append(label)

    # --- submission identity -------------------------------------------------
    tif = next(iter(sorted((ROOT / "downloads").glob("*.tif"))))
    expect("submission sha256", hashlib.sha256(tif.read_bytes()).hexdigest(), checks["uniqueness"]["my_sha256"])
    expect("submission bytes", tif.stat().st_size, sources["submission"]["bytes"])
    expect("shipped name matches sources receipt", tif.name, sources["submission"]["file"])
    expect("zip alongside the tif", (ROOT / "downloads" / (tif.stem + ".zip")).exists(), True)

    # --- format gates --------------------------------------------------------
    fmt = checks["format"]
    expect("all format checks pass", fmt["all_checks_pass"], True)
    expect("values within [0, 1]", fmt["values_in_0_1"], True)
    expect("single band", fmt["count_is_1"], True)
    expect("float32", fmt["dtype_is_float32"], True)
    expect("EPSG:32611", fmt["crs_is_epsg32611"], True)
    expect("outside footprint all NaN", fmt["outside_footprint_all_nan"], True)
    expect("unique positive value is 1.0", fmt["unique_positive_values"], [1.0])
    expect("dots equal the build diagnostic", fmt["positive_px"], build["n_dots_shipped"])

    # --- uniqueness gate -----------------------------------------------------
    u = checks["uniqueness"]
    expect("uniqueness verdict", u["verdict_unique"], True)
    expect("no identical prior hash", u["identical_sha256"], [])
    if u["max_iou"] >= 0.5:
        failures.append("max_iou")

    # --- validation of the exact file ---------------------------------------
    expect("F2 beats the random control", validation["F2_dti"] > validation["controls"]["uniform_random_same_count"]["F2"], True)
    expect("F1 beats the random control", validation["F1_mean"] > validation["controls"]["uniform_random_same_count"]["F1_mean"], True)

    # --- evidence frames quoted on the site ---------------------------------
    f1 = field["budget_44090"]["F1_smoothed"] if "budget_44090" in field else None
    f2 = field["budget_44090"]["F2_smoothed"] if "budget_44090" in field else None
    if f1 and f2:
        expect("scarp is the off-catalogue leader", max(f2, key=f2.get), "scarp")
    feed = json.loads((ROOT / "docs" / "data" / "feed.json").read_text())
    expect("feed quotes the shipped dots", feed["our_submission"]["dots"], build["n_dots_shipped"])
    expect("feed quotes the shipped sha256", feed["our_submission"]["sha256"], checks["uniqueness"]["my_sha256"])
    expect("feed best public score", feed["public_leaderboard_snapshot"]["best"], 0.3774)

    # --- the report's own numbers must exist in the receipts -----------------
    report = (ROOT / "docs" / "report.html").read_text()
    for token in (f"{validation['F2_dti']:.4f}", f"{validation['F1_mean']:.4f}"):
        expect(f"report quotes {token}", token in report, True)
    expect("report carries the no-leaderboard-score disclaimer",
           "No private-leaderboard score is claimed" in report, True)
    expect("falsification is stated on the site", "FALSIFIED" in report or "failed" in report, True)

    print()
    if failures:
        print(f"FAILED claims: {failures}")
        return 1
    print("all documented claims match the receipts")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
