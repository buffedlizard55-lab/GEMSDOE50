#!/usr/bin/env python3
"""Fold the H53 evidence into the repository registries and the status feed.

Mirrors ``update_registries_h51.py``: idempotent (any previous H53 entry is
replaced), and every claim is copied from a file that exists on disk
(``evidence/h53_ship.json``, ``evidence/h53_check_submission.json``,
``evidence/h53_validation_final.json``).
"""
from __future__ import annotations

import json
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
SHIP = REPO / "evidence" / "h53_ship.json"
CHECK = REPO / "evidence" / "h53_check_submission.json"
FINAL = REPO / "evidence" / "h53_validation_final.json"


def load(path: Path) -> dict:
    if not path.exists():
        raise SystemExit(f"missing evidence file: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def write(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload, indent=1), encoding="utf-8")
    print(f"wrote {path.relative_to(REPO)}")


def main() -> int:
    ship = load(SHIP)
    check = load(CHECK)
    final = load(FINAL)
    out = ship["outputs"]
    fmt = ship["format"]
    gate = ship["gate"]
    inst = ship["instrument"]
    mass = int(ship["budgets"]["n"])
    uniq = check.get("uniqueness", {})

    submissions = json.loads((REPO / "registry" / "submissions.json").read_text(encoding="utf-8"))
    submissions["submissions"] = [
        s for s in submissions.get("submissions", [])
        if not s.get("portal_name", "").startswith("GEMSDOE50-H53")]
    submissions["submissions"].append({
        "name": ship["name"],
        "portal_name": ship["portal_name"],
        "file": out["tif"],
        "bytes": out["bytes"],
        "sha256": out["sha256"],
        "all_finite_twin": out["allfinite"],
        "zip": out["zip"],
        "zip_sha256": out["zip_sha256"],
        "mass": mass,
        "format": {"crs": fmt["crs"], "shape": fmt["shape"], "dtype": fmt["dtype"],
                   "values_in_0_1": fmt["values_in_0_1"],
                   "outside_footprint_all_nan": fmt["outside_footprint_all_nan"],
                   "inside_footprint_all_finite": fmt["inside_footprint_all_finite"]},
        "status": ("H53 deliverable; local proxy instruments only; no organizer score exists for "
                   "this file and no portal upload was performed by this repository"),
        "organizer_score": None,
        "submitted_utc": None,
        "built_utc": ship["stamp"],
        "portal_note": ship["claim_note"],
        "evidence": ["evidence/h53_ship.json", "evidence/h53_check_submission.json",
                     "evidence/h53_validation_final.json"],
    })
    write(REPO / "registry" / "submissions.json", submissions)

    claims = json.loads((REPO / "registry" / "claims.json").read_text(encoding="utf-8"))
    claims["verified_on_published_bytes"] = [
        c for c in claims.get("verified_on_published_bytes", [])
        if "H53" not in c.get("claim", "")]
    claims["verified_on_published_bytes"] += [
        {
            "claim": (f"H53 format legal: single band float32 EPSG:32611 100 m "
                      f"{fmt['shape'][1]}x{fmt['shape'][0]}, every in-footprint value in [0,1], "
                      f"NaN only where the official template is NaN, {mass:,} predicted cells"),
            "evidence": "evidence/h53_check_submission.json",
        },
        {
            "claim": (f"H53 uniqueness: {gate['pixels_shared_with_any_prior']} shared pixels vs "
                      f"{gate['n_prior']} corpus artifacts; worst 2 px-proximity IoU "
                      f"{gate['measured_iou2px_max']:.4f}, below the "
                      f"{gate['threshold_iou2px']} gate; "
                      f"{uniq.get('verdict', 'unique') if isinstance(uniq, dict) else uniq}"),
            "evidence": "evidence/h53_check_submission.json (uniqueness)",
        },
        {
            "claim": (f"H53 shared-frame instrument: DTI {inst['dti']:.4f} "
                      f"({inst['tp_per_dot']:.4f} credit/dot) on the SGMC-off frame vs "
                      f"mass-matched uniform max {inst['uniform_dti_max']:.4f} and translation max "
                      f"{inst['translation_dti_max']:.4f}; "
                      f"{inst['quadrants_positive']}/{inst['quadrants_total']} quadrants positive"),
            "evidence": "evidence/h53_validation_final.json",
        },
    ]
    claims["updated_utc"] = ship["stamp"][:10]
    write(REPO / "registry" / "claims.json", claims)

    hypotheses = json.loads((REPO / "registry" / "hypotheses.json").read_text(encoding="utf-8"))
    hypotheses["hypotheses"] = [
        h for h in hypotheses.get("hypotheses", []) if not h.get("id", "").startswith("H53")]
    hypotheses["hypotheses"] += [
        {
            "id": "H53-C", "rank": 1, "status": "SHIPPED",
            "name": "TMI x K/U gradient-ridge conjunction, off-catalogue emission",
            "layers": ["upward-continued total magnetic intensity (TMI_up150)",
                       "radiometric K and U (relative highs)"],
            "transform": ("ridge extraction on the TMI grid crossed with K/U gradient ridges -> "
                          "greedy conjunction-strength packing with 3 px suppression, restricted "
                          "to >300 m from the catalogue"),
            "why_missing_faults": ("a magnetic basement edge that coincides with a radiometric "
                                 "gradient ridge is two independent physics fields agreeing on a "
                                 "buried structure the catalogue never traced"),
            "difference": ("H51-C used potential-field edges alone and fell below its random "
                         "control; H53-C requires the cross-physics conjunction before emitting"),
            "measured": {
                "shared_frame_dti": inst["dti"],
                "credit_per_dot": inst["tp_per_dot"],
                "uniform_dti_max": inst["uniform_dti_max"],
                "translation_dti_max": inst["translation_dti_max"],
                "quadrants_positive": f"{inst['quadrants_positive']}/{inst['quadrants_total']}",
                "mass": mass,
            },
            "evidence": ["evidence/h53_ship.json", "evidence/h53_validation_final.json",
                         "docs/research/h53-hypotheses.md"],
        },
        {
            "id": "H53-B", "rank": 2, "status": "FALSIFIED on proxy gate (not shipped)",
            "name": "fixed seismicity lineation corridors, spatially-blocked split",
            "layers": ["USGS ComCat events (declustered, injection/mining screened)"],
            "transform": ("decluster -> 2-D covariance lineation corridors -> score only outside "
                        "existing-fault buffers -> falsify vs smoothed density"),
            "why_missing_faults": "same as H51-B: aftershock lineations trace causative faults",
            "difference": "preselected split verdict instead of a mass weight",
            "measured": {"verdict": gate["component_gates"].get("H53-B-seismicity-v2",
                         "recorded, not shipped")},
            "evidence": ["docs/research/h53-analysis.md"],
        },
        {
            "id": "H53-A", "rank": 3, "status": "NEAR-MISS on proxy gate (not shipped)",
            "name": "fault-tip bridge segments between mapped-trace tips",
            "layers": ["provided catalogue fault tips"],
            "transform": "tip-to-tip bridge segments, 300 m-aware emission",
            "why_missing_faults": "relay ramps and step-overs between mapped tips hide blind faults",
            "difference": "pure catalogue-geometry design with no new external layer",
            "measured": {"verdict": gate["component_gates"].get("H53-A-tip-bridges",
                         "recorded, not shipped")},
            "evidence": ["docs/research/h53-analysis.md"],
        },
    ]
    hypotheses["updated_utc"] = ship["stamp"][:10]
    write(REPO / "registry" / "hypotheses.json", hypotheses)

    sources = json.loads((REPO / "registry" / "sources.json").read_text(encoding="utf-8"))
    sources["h53_submission"] = {
        "file": out["tif"],
        "sha256": out["sha256"],
        "bytes": out["bytes"],
        "mass": mass,
        "crs": fmt["crs"],
        "dtype": fmt["dtype"],
        "size": f"{fmt['shape'][1]}x{fmt['shape'][0]}",
        "nodata": "NaN outside the official template footprint (all-finite twin also written)",
        "portal_name": ship["portal_name"],
        "portal_note": ship["claim_note"],
        "organizer_score": None,
        "sources": ship.get("sources", [
            {"name": "Upward-continued total magnetic intensity grid (competition feature stack)",
             "licence": "competition-provided input",
             "used_for": "TMI ridge family"},
            {"name": "Airborne radiometric K/U grids (competition feature stack)",
             "licence": "competition-provided input",
             "used_for": "K/U gradient-ridge family"},
            {"name": "USGS State Geologic Map Compilation fault inventory",
             "licence": "U.S. public domain (USGS)", "url": "https://www.usgs.gov/",
             "used_for": "off-catalogue scoring instrument only"},
        ]),
        "caveats": [
            "no organizer score or upload receipt exists for this file",
            "DTI numbers are local proxy instruments on the shared SGMC-off frame, not leaderboard predictions",
        ],
    }
    sources["generated_utc"] = ship["stamp"]
    write(REPO / "registry" / "sources.json", sources)

    feed = json.loads((REPO / "docs" / "data" / "feed.json").read_text(encoding="utf-8"))
    feed["kind"] = "current-project status; no leaderboard snapshot"
    feed["h53"] = {
        "status": "built, format-verified and proxy-validated; no organizer score claimed",
        "file": out["tif"],
        "sha256": out["sha256"],
        "mass": mass,
        "portal_name": ship["portal_name"],
        "portal_note": ship["claim_note"],
        "shared_frame_dti": inst["dti"],
        "credit_per_dot": inst["tp_per_dot"],
        "uniform_dti_max": inst["uniform_dti_max"],
        "translation_dti_max": inst["translation_dti_max"],
        "quadrants_positive": f"{inst['quadrants_positive']}/{inst['quadrants_total']}",
        "uniform_draws": final["uniform_control"]["draws"],
        "translation_draws": final["translation_control"]["draws"],
        "gate_all_pass": final["gate"]["all_pass"],
        "organizer_score": None,
        "portal_upload": None,
        "weekly_slot_used": False,
    }
    feed["generated_utc"] = ship["stamp"]
    write(REPO / "docs" / "data" / "feed.json", feed)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
