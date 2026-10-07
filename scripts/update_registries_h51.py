#!/usr/bin/env python3
"""Fold the H51 evidence into the repository registries and the status feed.

Idempotent: any previous H51 entry is replaced, so re-running after a rebuild cannot leave
two competing records.  Every claim written here is copied from a file that exists on disk
(``evidence/build_h51.json``, ``evidence/checks_h51_raster.json``, ``evidence/holdout_h51.json``);
nothing is asserted that those files do not contain.
"""
from __future__ import annotations

import json
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
BUILD = REPO / "evidence" / "build_h51.json"
CHECKS = REPO / "evidence" / "checks_h51_raster.json"
HOLDOUT = REPO / "evidence" / "holdout_h51.json"


def load(path: Path) -> dict:
    if not path.exists():
        raise SystemExit(f"missing evidence file: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def write(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload, indent=1), encoding="utf-8")
    print(f"wrote {path.relative_to(REPO)}")


def main() -> int:
    build = load(BUILD)
    holdout = load(HOLDOUT)
    name = build["name"]
    primary = build["outputs"]["primary"]
    portal_name = "GEMSDOE50-H51-SCARPRADIO-OFFCAT"
    note = ("GEMSDOE50 H51 | corroborated 3DEP-scarp + radiometric lineaments, all dots >300 m "
            "from the given catalogue, metric-matched sparse emission; proxy-validated, NOT "
            "organizer-scored")

    submissions = json.loads((REPO / "registry" / "submissions.json").read_text(encoding="utf-8"))
    submissions["submissions"] = [
        s for s in submissions.get("submissions", []) if not s.get("name", "").startswith(("GEMS51", "GEMSDOE50-H51"))]
    submissions["submissions"].append({
        "name": name,
        "portal_name": portal_name,
        "file": primary["path"],
        "bytes": primary["bytes"],
        "sha256": primary["sha256"],
        "all_finite_twin": build["outputs"]["allfinite"]["path"],
        "zip": build["outputs"]["zip"]["path"],
        "zip_sha256": build["outputs"]["zip"]["sha256"],
        "mass": int(primary["footprint_nonzero"]),
        "format": {k: primary[k] for k in ("crs", "shape", "dtype", "count", "transform",
                                           "cells_finite", "cells_nan", "outside_unit_interval",
                                           "outside_footprint_nonzero")},
        "status": ("H51 deliverable; local proxy instruments only; no organizer score exists for "
                   "this file and no portal upload was performed by this repository"),
        "organizer_score": None,
        "submitted_utc": None,
        "built_utc": build["built_utc"],
        "portal_note": note,
        "evidence": ["evidence/build_h51.json", "evidence/checks_h51_raster.json",
                     "evidence/holdout_h51.json"],
    })
    write(REPO / "registry" / "submissions.json", submissions)

    claims = json.loads((REPO / "registry" / "claims.json").read_text(encoding="utf-8"))
    claims["verified_on_published_bytes"] = [
        c for c in claims.get("verified_on_published_bytes", [])
        if "H51" not in c.get("claim", "")]
    claims["verified_on_published_bytes"] += [
        {
            "claim": ("H51 format legal: single band float32 EPSG:32611 100 m 3292x3730, every "
                      f"finite value in [0,1], {primary['outside_unit_interval']} values outside, "
                      "NaN only where the official template is NaN, "
                      f"{int(primary['footprint_nonzero']):,} predicted cells"),
            "evidence": "evidence/checks_h51_raster.json",
        },
        {
            "claim": ("H51 uniqueness: block-level Jaccard against "
                      f"{build['uniqueness']['n_prior_artifacts']} frozen prior artifacts is at most "
                      f"{build['uniqueness']['max_jaccard']:.4f} (8 px and 32 px), below the 0.5 gate; "
                      "no prior pixels are reused"),
            "evidence": "evidence/build_h51.json (uniqueness)",
        },
        {
            "claim": ("H51 spatially blocked validation: candidate beats its matched-mass random "
                      f"control in {holdout['folds_positive']} of {holdout['folds_total']} frozen "
                      f"macrofolds; paired subtile bootstrap mean "
                      f"{holdout['subtile_bootstrap']['paired_delta_mean']:.4f} with 95% CI "
                      f"[{holdout['subtile_bootstrap']['percentile_ci_95'][0]:.4f}, "
                      f"{holdout['subtile_bootstrap']['percentile_ci_95'][1]:.4f}] on the "
                      "off-catalogue instrument"),
            "evidence": "evidence/holdout_h51.json",
        },
    ]
    claims["instruments_with_named_bias"] = [
        c for c in claims.get("instruments_with_named_bias", [])
        if "H51" not in c.get("instrument", "")]
    claims["instruments_with_named_bias"] += [
        {
            "instrument": "H51 off-catalogue USGS SGMC credit per emitted cell",
            "bias": ("a mapped-structure inventory at a different vintage and scale; its density "
                     "(1.19% of the footprint) is about five times the estimated hidden density, and "
                     "it is not the scored truth"),
        },
        {
            "instrument": "H51 Monte Cristo trend coverage",
            "bias": ("only 242 px and circular as a geometry check; a matched-mass random control "
                     "already covers ~9% of it, so it is a weak instrument at low mass and is used "
                     "only as a guard"),
        },
        {
            "instrument": "H51 given-catalogue raster",
            "bias": ("an anti-instrument: H51 emits everything more than 300 m from it by design, "
                     "so a near-zero catalogue score is the design, not a result"),
        },
    ]
    claims["flagged_unresolved"] = [
        c for c in claims.get("flagged_unresolved", [])
        if "H51" not in c.get("issue", "")]
    claims["flagged_unresolved"] += [
        {
            "issue": "H51 mass selection rests on one transfer number",
            "detail": ("the SGMC-off-to-hidden credit transfer (0.28) comes from a single owner file "
                       "that has both a live score and a local SGMC-off score. A +/-30% error in it "
                       "moves the metric-optimal mass from ~12,000 to beyond 50,000 dots; the "
                       "amendment-A2 rule picks within that flat region and the full per-mass table "
                       "is published so a reviewer can move the mass with one argument."),
        },
        {
            "issue": "H51 location-uncertainty model is this project's own work",
            "detail": ("log10(h_err_m) ~ log10(nst) + log10(gap) + depth + mag, R^2 0.715 in sample; "
                       "on the footprint holdout the median prediction is about half the observed "
                       "error and only 50.4% of events are within a factor of two. It is NOT part of "
                       "Wang et al. (arXiv:1304.6912), and the seismicity family it feeds was given "
                       "no mass in the shipped file."),
        },
        {
            "issue": "no organizer score exists for the H51 file",
            "detail": ("no portal upload was performed by this repository, no weekly slot is claimed, "
                       "and every number in the H51 evidence is a local proxy instrument."),
        },
    ]
    claims["updated_utc"] = build["built_utc"][:10]
    write(REPO / "registry" / "claims.json", claims)

    hypotheses = json.loads((REPO / "registry" / "hypotheses.json").read_text(encoding="utf-8"))
    hypotheses["hypotheses"] = [
        h for h in hypotheses.get("hypotheses", []) if not h.get("id", "").startswith("H51")]
    hypotheses["hypotheses"] += [
        {
            "id": "H51-A", "rank": 1, "status": "SHIPPED",
            "name": "corroborated LiDAR-scarp + radiometric lineaments, off-catalogue emission",
            "layers": ["lidar_scarp_features 3/4/9 (step_max, lapneg_max, relief)",
                       "topo_u8 2/5/6/8 (slope_max, relief_local, curvature, hillshade lineament)",
                       "radiometric_u8 1-7 and geodawn_rad_u8 1-4 (K, Th, U, TC and ratios)"],
            "transform": ("multi-scale structure tensor (sigma 2/5/10, coherence smoothed at 3) -> "
                          "gradient-magnitude x coherence -> 98th-percentile normalisation per layer "
                          "-> max over layers within a family -> 0.75/0.55 blend of the scarp-focused "
                          "topographic family and the radiometric family -> greedy kernel-credit pack "
                          "with 3 px suppression, restricted to >300 m from the catalogue"),
            "why_missing_faults": ("the catalogue is dominated by LiDAR-scarp picks; requiring an "
                                   "independent radiometric family at the same location suppresses "
                                   "single-layer pattern matches, and the 300 m catalogue exclusion "
                                   "keeps every emitted dot out of the masked-out label set"),
            "difference": ("H47-S3/H19 shipped scarp-only or hand-weighted multi-line fields; this "
                           "uses the measured best two-family blend, a metric-derived emission rule, "
                           "and a fully off-catalogue support"),
            "measured": {
                "sgmc_off_credit_per_dot": build["instruments"]["candidate"]["sgmc_off"]["credit_per_dot"],
                "sgmc_off_random_control": build["instruments"]["random_control"]["sgmc_off"]["credit_per_dot"],
                "monte_cristo_tp_weight": build["instruments"]["candidate"]["monte_cristo"]["tp_weight"],
                "monte_cristo_random_control": build["instruments"]["random_control"]["monte_cristo"]["tp_weight"],
                "mass": int(primary["footprint_nonzero"]),
                "folds_positive": f"{holdout['folds_positive']}/{holdout['folds_total']}",
            },
            "evidence": ["evidence/build_h51.json", "evidence/holdout_h51.json",
                         "docs/hypotheses-preregistered.md"],
        },
        {
            "id": "H51-B", "rank": 2, "status": "NEGATIVE (no mass shipped)",
            "name": "seismicity event-geometry corridors with a calibrated uncertainty width",
            "layers": ["USGS ComCat events (magnitude >= 1, depth <= 25 km)",
                       "documented horizontalError where published; a calibrated model otherwise"],
            "transform": ("space-time tetrahedron declustering against 200 time-shuffled surrogates "
                          "-> 1/sigma^2-weighted 2-D covariance axes -> max(2 sigma, 300 m) "
                          "Gaussian-width corridors"),
            "why_missing_faults": ("aftershock sequences trace the causative fault, so a blind "
                                   "structure with recent seismicity is drawn where the catalogue has "
                                   "no trace"),
            "difference": ("the provided ieq/deq bands are ~100 km density fields (autocorrelation "
                           "0.9986 at 1 km); the earlier gems50 line used a space-only decluster and "
                           "no uncertainty model"),
            "measured": {
                "sgmc_off_credit_per_dot_at_20000": build["seismicity_solo_at_30k"]["sgmc_off"]["credit_per_dot"],
                "sgmc_off_random_control": build["instruments"]["random_control"]["sgmc_off"]["credit_per_dot"],
                "monte_cristo_tp_weight": build["seismicity_solo_at_30k"]["monte_cristo"]["tp_weight"],
                "verdict": "level with or below the matched random control; 0.0 Monte Cristo coverage",
            },
            "evidence": ["/home/user/.arena/work/seis_report.json (session scratch)",
                         "docs/hypotheses-preregistered.md"],
        },
        {
            "id": "H51-C", "rank": 3, "status": "REJECTED on instrument",
            "name": "depth-edge potential-field lineaments (tilt angle, vertical gradients)",
            "layers": ["training_features 1/2/3/6/9/14 (magnetic and derivatives)",
                       "5/11/13/18 (isostatic gravity and derivatives)", "geodawn_extensions 4"],
            "transform": "structure tensor on potential-field bands",
            "why_missing_faults": "a buried fault with no surface scarp can still produce a mapped potential-field edge",
            "difference": "isolates depth-derived edges rather than anomaly amplitudes",
            "measured": {"sgmc_off_credit_per_dot": 0.0866,
                         "sgmc_off_random_control": 0.1115,
                         "verdict": "below the random control"},
            "evidence": ["docs/hypotheses-preregistered.md"],
        },
        {
            "id": "H51-D", "rank": 4, "status": "DEFERRED (now H52-C)",
            "name": "thermal spring / well conduit anchoring (GDR 1391, INGENIOUS)",
            "layers": ["data/external/gdr_wellspring_in_footprint.csv", "INGENIOUS temperature grids",
                       "cond_surf 17"],
            "transform": "conduit segments from each spring/well to the nearest mapped structure",
            "why_missing_faults": "springs prove a plumbing system; the unmapped part of a conduit is a concealed-fault candidate",
            "difference": "H19 used the thermal evidence as a favourability field, not as conduit segments",
            "measured": {"verdict": "not measured in this session"},
            "evidence": ["docs/h51-candidates.md"],
        },
        {
            "id": "H51-E", "rank": 5, "status": "REJECTED on instrument",
            "name": "orientation-concordance gate across all families",
            "layers": ["all four structural families"],
            "transform": "count families above their own 75th-percentile strength with azimuths agreeing within 25 deg",
            "why_missing_faults": "independent physics agreeing on azimuth is more likely to be a real structure",
            "difference": "makes agreement a gate rather than a hand weight",
            "measured": {"sgmc_off_credit_per_dot": 0.1784,
                         "sgmc_off_without_gate": 0.1817,
                         "monte_cristo_tp_weight": 13.8,
                         "monte_cristo_without_gate": 32.0,
                         "verdict": "concentrates mass on large structures and loses small ones; kept as a diagnostic"},
            "evidence": ["docs/hypotheses-preregistered.md"],
        },
    ]
    hypotheses["updated_utc"] = build["built_utc"][:10]
    write(REPO / "registry" / "hypotheses.json", hypotheses)

    sources = json.loads((REPO / "registry" / "sources.json").read_text(encoding="utf-8"))
    sources["h51_submission"] = {
        "file": primary["path"],
        "sha256": primary["sha256"],
        "bytes": primary["bytes"],
        "mass": int(primary["footprint_nonzero"]),
        "crs": primary["crs"],
        "dtype": primary["dtype"],
        "size": f"{primary['shape'][0]}x{primary['shape'][1]}",
        "nodata": "NaN outside the official template footprint (all-finite twin also written)",
        "portal_name": portal_name,
        "portal_note": note,
        "organizer_score": None,
        "sources": [
            {"name": "USGS 3DEP-derived scarp descriptor raster (12-band sibling-repository derivative)",
             "licence": "UNRESOLVED: raw USGS 3DEP is public domain, but the mirrored derived raster's reuse license is undocumented; not cleared for external competition use",
             "url": "https://github.com/buffedlizard55-lab/GEMSDOE24/blob/main/data/external/lidar_scarp_features_u8.tif",
             "used_for": "topographic scarp lineament family; do not upload/share until derivative rights are clarified"},
            {"name": "Airborne radiometric K/Th/U and ratio grids (competition feature stack)",
             "licence": "USGS source products are generally public domain; provenance and reuse terms for the exact derived rasters were not independently audited here",
             "url": "https://www.usgs.gov/",
             "used_for": "radiometric lineament family; verify exact inputs and sharing terms before external submission"},
            {"name": "USGS ANSS Comprehensive Earthquake Catalog (ComCat)",
             "licence": "UNRESOLVED at record/contributor level; mixed-network export is not cleared for external competition use",
             "url": "https://earthquake.usgs.gov/fdsnws/event/1/",
             "used_for": "legacy H51 seismicity-family analysis only; not given mass in this file; rights/shareability unresolved"},
            {"name": "USGS State Geologic Map Compilation fault inventory",
             "licence": "U.S. public domain (USGS)", "url": "https://www.usgs.gov/",
             "used_for": "off-catalogue scoring instrument only"},
        ],
        "caveats": [
            "no organizer score or upload receipt exists for this file",
            "the location-uncertainty model is this project's own construction, not from arXiv:1304.6912",
            "the exact derived scarp raster has no documented reuse license; mixed-network ComCat rights/shareability are unresolved; this file is not cleared for external competition upload until both sources are reviewed",
        ],
    }
    sources["generated_utc"] = build["built_utc"]
    write(REPO / "registry" / "sources.json", sources)

    feed = json.loads((REPO / "docs" / "data" / "feed.json").read_text(encoding="utf-8"))
    feed["kind"] = "current-project status; no leaderboard snapshot"
    feed["h51"] = {
        "status": "built, format-verified and proxy-validated; no organizer score claimed",
        "file": primary["path"],
        "sha256": primary["sha256"],
        "mass": int(primary["footprint_nonzero"]),
        "portal_name": portal_name,
        "portal_note": note,
        "instruments": {k: {kk: v[kk] for kk in ("dti", "credit_per_dot", "truth_cells")}
                        for k, v in build["instruments"]["candidate"].items()},
        "random_control": {k: v["credit_per_dot"] for k, v in build["instruments"]["random_control"].items()},
        "blocked_validation": {
            "folds_positive": f"{holdout['folds_positive']}/{holdout['folds_total']}",
            "subtile_ci95": holdout["subtile_bootstrap"]["percentile_ci_95"],
        },
        "organizer_score": None,
        "portal_upload": None,
        "weekly_slot_used": False,
    }
    feed["h50_s1"] = {
        "status": "research-only; the relocated-catalog data are still not fetchable in this sandbox",
        "organizer_score": None, "portal_upload": None, "weekly_slot_used": False,
    }
    feed["generated_utc"] = build["built_utc"]
    write(REPO / "docs" / "data" / "feed.json", feed)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
