#!/usr/bin/env python3
"""Check current-project score-provenance, data-use, and incumbent-selection guardrails."""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    failures: list[str] = []

    def check(label: str, condition: bool) -> None:
        print(f"{'OK  ' if condition else 'FAIL'} {label}")
        if not condition:
            failures.append(label)

    feed = json.loads((ROOT / "docs/data/feed.json").read_text(encoding="utf-8"))
    submissions = json.loads((ROOT / "registry/submissions.json").read_text(encoding="utf-8"))
    README = (ROOT / "README.md").read_text(encoding="utf-8")
    prior = (ROOT / "docs/prior-work.md").read_text(encoding="utf-8")
    protocol = (ROOT / "docs/h50s1-protocol-addendum.md").read_text(encoding="utf-8")
    evaluator = (ROOT / "src/gemsdoe50/evaluation.py").read_text(encoding="utf-8")
    external = (ROOT / "data/external/README.md").read_text(encoding="utf-8")
    site_workflow = (ROOT / ".github/workflows/site.yml").read_text(encoding="utf-8")
    feed_workflow = (ROOT / ".github/workflows/feed.yml").read_text(encoding="utf-8")
    fetch_workflow = (ROOT / ".github/workflows/fetch-external-data.yml").read_text(
        encoding="utf-8"
    )

    check("current feed publishes no leaderboard snapshot", feed.get("leaderboard", {}).get("published") is False)
    check("feed has no numerical public-board rows", "public_leaderboard_snapshot" not in feed)
    check(
        "legacy TIFF is explicitly comparator-only",
        feed.get("legacy_artifact", {}).get("role", "").startswith("same-fold comparator"),
    )
    check("feed maps no organizer score to TIFF", feed.get("legacy_artifact", {}).get("organizer_score") is None)
    check("H50-S1 status does not assert an organizer score", feed.get("h50_s1", {}).get("organizer_score") is None)
    check("registry carries no copied leaderboard rows", "public_leaderboard_2026_10_06" not in submissions)
    check("README rejects unverified/current score claims", "not a fresh independent official check" in README)
    check(
        "prior-work notes make no score-to-TIFF assertion",
        "no score-to-tiff mapping is authenticated" in prior.lower(),
    )
    check("protocol fixes H50-prior before holdout scoring", "H50-prior is the fixed primary incumbent" in protocol)
    check("evaluator uses a fixed incumbent, not max holdout score", "max(baseline_names" not in evaluator)
    check("evaluator requires all 20 time-shuffle controls", "TIME_SHUFFLE_CONTROLS = 20" in evaluator)
    check("legacy ComCat inputs are excluded from H50-S1", "does **not** consume these ComCat" in external)
    check("scheduled ComCat refresh is disabled", "schedule:" not in feed_workflow and "if: ${{ false }}" in feed_workflow)
    check("ComCat fetch workflow is disabled", "if: ${{ false }}" in fetch_workflow)
    check("site workflow cannot push generated changes", "git push" not in site_workflow)
    h51 = feed.get("h51_candidate") or {}
    check("H51 feed entry asserts no organizer score", h51.get("organizer_score") is None)
    check("H51 feed entry records that no slot was used", h51.get("weekly_slot_used") is False)
    ship_path = ROOT / "evidence" / "h51_ship.json"
    check("H51 feed hash matches the shipped evidence", (
        not ship_path.exists()
        or h51.get("sha256") == json.loads(ship_path.read_text()).get("outputs", {}).get("sha256")
    ))
    check("H51 candidate is not claimed to pass the proxy gate", h51.get("proxy_gate_pass") is False)

    if failures:
        print("\nFailed guardrails:", ", ".join(failures))
        return 1
    print("\nAll current-project provenance and safety guardrails hold.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
