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
    source_registry = json.loads((ROOT / "registry/sources.json").read_text(encoding="utf-8"))
    research_review = (ROOT / "docs/research/earthquake-geometry-review-20261006.md").read_text(encoding="utf-8")
    candidate_ranking = (ROOT / "docs/research/hypothesis-ranking-20261006.md").read_text(encoding="utf-8")
    runner = (ROOT / "scripts/run_experiment.py").read_text(encoding="utf-8")
    research_workflow = (ROOT / ".github/workflows/h50s1-research.yml").read_text(encoding="utf-8")
    site_builder = (ROOT / "scripts/build_h50_site.py").read_text(encoding="utf-8")
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

    comcat = next(
        (item for item in source_registry.get("sources", []) if "Comprehensive Earthquake Catalog" in item.get("name", "")),
        {},
    )
    check(
        "mixed-network ComCat rights remain explicitly unresolved",
        "unresolved" in comcat.get("licence", "").lower()
        and "not cleared" in comcat.get("used_for", "").lower(),
    )
    check(
        "2-D ComCat method is not represented as new",
        "do not present the 2-d comcat" in research_review.lower()
        and "unverified" in research_review.lower(),
    )
    check(
        "3–5 geological hypotheses are ranked against project history",
        all(token in candidate_ranking for token in ("H50-S1", "H50-G1", "H50-RC", "H50-S2", "H50-B")),
    )
    check(
        "H50-S1 evaluator requires both smoothed-density controls",
        "smoothed-density-1km" in evaluator
        and "smoothed-density-2km" in evaluator
        and "beats_both_smoothed_density_controls" in evaluator,
    )
    check(
        "H50-S1 output gate blocks unresolved confounds",
        all(token in runner for token in ("aftershock_declustering_complete", "mining_injection_screen_complete", "event_location_uncertainty_informs_corridor")),
    )
    check(
        "H50-S1 site describes the density and scientific gates",
        "smoothed-density controls" in site_builder and "aftershock" in site_builder,
    )
    check(
        "research workflow is pinned to this Arena branch",
        "arena/5e2ce8c3-gemsdoe50" in research_workflow
        and "arena/c4f4db48-gemsdoe50" not in research_workflow
        and "arena/c6060a3e-gemsdoe50" not in research_workflow,
    )
    check(
        "leaderboard irregularity and non-use are documented",
        "unintended automated request" in README and "no rows/scores were saved or used" in README,
    )
    check(
        "blocked H50-S1 dispatch is documented without claiming a run",
        "HTTP 403" in README and "no job ran and no data was fetched" in README,
    )

    marker_paths = [
        "README.md", "index.html", "results.html", "methods.html", "submission.html",
        "docs/index.html", "docs/executive-summary.html", "docs/how-to-submit.html",
        "docs/methods.html", "registry/sources.json", "registry/submissions.json",
        "registry/claims.json", "registry/hypotheses.json", "docs/data/feed.json",
        "docs/pass3-review-20261006.md",
    ]
    marker_hits = []
    for rel in marker_paths:
        path = ROOT / rel
        if not path.exists():
            continue
        text = path.read_text(encoding="utf-8")
        for token in ("<<<<<<< ", ">>>>>>> ", "\n=======\n"):
            if token in text:
                marker_hits.append(f"{rel}:{token.strip()}")
    check(
        "no unresolved merge-conflict markers in hand-merged text files",
        not marker_hits,
    )
    if marker_hits:
        print("     markers:", ", ".join(marker_hits[:8]))

    if failures:
        print("\nFailed guardrails:", ", ".join(failures))
        return 1
    print("\nAll current-project provenance and safety guardrails hold.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
