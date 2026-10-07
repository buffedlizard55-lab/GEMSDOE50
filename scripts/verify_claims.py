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
    check(
        "README treats 0.2778 as unresolved and 0.3195 as historical",
        "`0.2778` score-to-artifact association remains unresolved" in README
        and "not independently verified" in README,
    )
    check(
        "prior-work notes require organizer receipt for score-to-file mapping",
        "score-to-file mapping" in prior
        and "No score-to-TIFF mapping is authenticated" in prior,
    )
    check(
        "protocol fixes H50-prior before holdout scoring",
        "**Primary incumbent:** H50-prior" in protocol,
    )
    check("evaluator uses a fixed incumbent, not max holdout score", "max(baseline_names" not in evaluator)
    check("evaluator requires all 20 time-shuffle controls", "TIME_SHUFFLE_CONTROLS = 20" in evaluator)
    check(
        "legacy mixed-network ComCat inputs are excluded from H50-S1",
        "does **not** consume the mixed-network ComCat extract" in external,
    )
    check("scheduled ComCat refresh is disabled", "schedule:" not in feed_workflow and "if: ${{ false }}" in feed_workflow)
    check("ComCat fetch workflow is disabled", "if: ${{ false }}" in fetch_workflow)
    check("site workflow cannot push generated changes", "git push" not in site_workflow)

    if failures:
        print("\nFailed guardrails:", ", ".join(failures))
        return 1
    print("\nAll current-project provenance and safety guardrails hold.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
