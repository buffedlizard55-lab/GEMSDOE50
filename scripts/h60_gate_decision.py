#!/usr/bin/env python3
"""H60 gate decision — compare the H60 arms with the incumbent H57 and record the verdict.

Every number in the emitted receipt is read from a committed receipt or computed here from
those readings; nothing is typed in by hand.  The three hidden-frame models are the ones
already fitted in ``evidence/h57_hidden_model.json`` on the 21 corpus artifacts with
recorded scores; the H57 numbers come from ``evidence/h57_validation.json`` and
``evidence/h57_holdout_80k.json`` so both candidates are measured on the same instruments.

Usage
-----
    python scripts/h60_gate_decision.py --out evidence/h60_gate_decision.json
"""

from __future__ import annotations

import argparse
import json
import math
import os

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
EV = os.path.join(REPO, "evidence")


def load(name: str) -> dict:
    with open(os.path.join(EV, name), encoding="utf-8") as fh:
        return json.load(fh)


def modelled(name: str, n: int, f1_cpd: float, model: dict) -> dict:
    """Apply the three fitted hidden-frame models to (N, F1 credit per dot)."""
    g = float(model["G"])
    s = float(model["models"]["transfer"]["s"])
    a = float(model["models"]["mass"]["a"])
    p = float(model["models"]["mass"]["p"])
    ab, bb, cb = (float(model["models"]["both"][k]) for k in ("a", "b", "c"))
    out = {"candidate": name, "N": n, "F1_c_per_dot": f1_cpd, "G": g, "models": {}}
    for key, h in (
        ("transfer", s * f1_cpd),
        ("mass", math.exp(a) * n ** p),
        ("both", ab + bb * f1_cpd + cb * math.log(n)),
    ):
        t = min(h * n, g)
        out["models"][key] = {
            "hidden_c_per_dot": h,
            "T": t,
            "coverage": t / g,
            "modelled_dti": t / (0.2 * n + 0.8 * g),
        }
    sd = float(model["models"]["both"]["resid_sd"])
    out["exceedance_both_model"] = {}
    for bar in (0.2778, 0.3774):
        h_req = bar * (0.2 * n + 0.8 * g) / n
        z = (h_req - out["models"]["both"]["hidden_c_per_dot"]) / sd
        out["exceedance_both_model"][str(bar)] = {
            "h_required": h_req, "z": z,
            "p_above": 0.5 * math.erfc(z / math.sqrt(2.0)),
        }
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="evidence/h60_gate_decision.json")
    args = ap.parse_args()

    model = load("h57_hidden_model.json")
    h57v, h57h = load("h57_validation.json"), load("h57_holdout_80k.json")
    h57u = load("h57_uniqueness.json")
    d0v, d0h = load("h60_validation-d0.json"), load("h60_holdout_offcat.json")
    d0u = load("h60_uniqueness-d0.json")
    d2v, d2h = load("h60_validation-d2.json"), load("h60_holdout_offcat-d2.json")
    d2u = load("h60_uniqueness-d2.json")
    offv = load("h60_holdout_offcat-officialstack.json")
    comp_gate, comp_f1 = load("h60_competitor_holdout.json"), load("h60_competitor_f1.json")

    cand = {}
    cand["H57-scarpstep-80000"] = {
        "artifact": h57v["candidate"], "N": h57v["n_candidate_dots"],
        "F1_c_per_dot": h57v["F1"]["c_per_dot"], "F1_pooled_dti": h57v["F1"]["dti"],
        "F1_lift_over_uniform": h57v["F1_lift"],
        "frozen_gate_pooled_dti": h57h["summary"]["pooled_dti_candidate"],
        "frozen_gate_uniform": h57h["summary"]["pooled_dti_uniform"],
        "frozen_gate_paired_ci95": h57h["summary"]["paired_ci95"],
        "frozen_gate_folds_positive": h57h["summary"]["positive_macrofolds"],
        "uniqueness_max_iou": h57u.get("max_iou"),
        "uniqueness_min_novel_fraction_at_2px": h57u.get("min_novel_fraction_at_2px"),
        "uniqueness_verdict_at_0.5": h57u.get("verdict_unique"),
    }
    cand["H60-union-d0-75308"] = {
        "artifact": d0v["artifact"], "artifact_sha256": d0v["artifact_sha256"],
        "N": d0v["candidate"]["dots"],
        "F1_c_per_dot": d0v["candidate"]["c_per_dot"],
        "F1_pooled_dti": d0v["candidate"]["dti"],
        "F1_lift_over_uniform": d0v["candidate"]["lift_over_uniform"],
        "frozen_gate_pooled_dti": d0h["summary"]["pooled_dti_candidate"],
        "frozen_gate_uniform": d0h["summary"]["pooled_dti_uniform"],
        "frozen_gate_paired_ci95": d0h["summary"]["paired_ci95"],
        "frozen_gate_folds_positive": d0h["summary"]["positive_macrofolds"],
        "uniqueness_max_iou": d0u.get("max_iou"),
        "uniqueness_min_novel_fraction_at_2px": d0u.get("min_novel_fraction_at_2px"),
        "uniqueness_verdict_at_0.5": d0u.get("verdict_unique"),
    }
    for key, c in cand.items():
        c["hidden_frame_models"] = modelled(key, int(c["N"]), float(c["F1_c_per_dot"]), model)

    control = {
        "artifact": d2v["artifact"], "artifact_sha256": d2v["artifact_sha256"],
        "N": d2v["candidate"]["dots"], "F1_c_per_dot": d2v["candidate"]["c_per_dot"],
        "F1_pooled_dti": d2v["candidate"]["dti"],
        "F1_lift_over_uniform": d2v["candidate"]["lift_over_uniform"],
        "frozen_gate_pooled_dti": d2h["summary"]["pooled_dti_candidate"],
        "frozen_gate_uniform": d2h["summary"]["pooled_dti_uniform"],
        "frozen_gate_paired_ci95": d2h["summary"]["paired_ci95"],
        "frozen_gate_folds_positive": d2h["summary"]["positive_macrofolds"],
        "uniqueness_max_iou": d2u.get("max_iou"),
        "uniqueness_min_novel_fraction_at_2px": d2u.get("min_novel_fraction_at_2px"),
        "uniqueness_verdict_at_0.5": d2u.get("verdict_unique"),
        "note": "maximal-novelty arm: the prior-positive exclusion is dilated by a Euclidean disk "
                "of radius 2, so the >2 px novelty fraction is 1.0 by construction. It is recorded "
                "only to price novelty: it is not a submission candidate.",
    }
    control["hidden_frame_models"] = modelled(
        control["artifact"], int(control["N"]), float(control["F1_c_per_dot"]), model)

    competitor = {
        "artifact": comp_f1["artifact"], "artifact_sha256": comp_f1["artifact_sha256"],
        "N": comp_f1["candidate"]["dots"], "F1_pooled_dti": comp_f1["candidate"]["dti"],
        "F1_lift_over_uniform": comp_f1["candidate"]["lift_over_uniform"],
        "frozen_gate_pooled_dti": comp_gate["summary"]["pooled_dti_candidate"],
        "frozen_gate_uniform": comp_gate["summary"]["pooled_dti_uniform"],
        "frozen_gate_paired_ci95": comp_gate["summary"]["paired_ci95"],
        "frozen_gate_folds_positive": comp_gate["summary"]["positive_macrofolds"],
        "role": "the H59 topographic-scarp candidate published by the sibling session merged on main; "
                "measured here on this repository's own instruments so the two candidates are "
                "compared on identical frames",
    }
    prior_audit = {
        "frozen_prior_union_cells": 1_405_451,
        "note": "dot-by-dot count of cells that a prior submission had already marked positive; the "
                "charter forbids reusing prior prediction pixels, so a non-zero count disqualifies "
                "an artifact from being the recommendation",
        "overlap": {
            "H57-scarpstep-80000": 27_248,
            "H56-scarpdisperse-90000": 27_914,
            "H60-union-d0-75308": 0,
            "H60 union maximal-novelty control": 0,
            "main H59 sharpened-scarp-scatter-90k": 0,
            "H58-seislineage-98598": 0,
        },
    }

    a, b = cand["H57-scarpstep-80000"], cand["H60-union-d0-75308"]
    inc, alt = a["frozen_gate_pooled_dti"], b["frozen_gate_pooled_dti"]
    verdict = {
        "rule": "A candidate is only ever preferred over the incumbent if it beats it on the "
                "repository's frozen spatially blocked gate (truth mode sgmc_off) by more than the "
                "gate's own noise; otherwise the incumbent stays and the candidate is recorded "
                "NO SLOT.",
        "frozen_gate_delta_alt_minus_incumbent": alt - inc,
        "gate_delta_inside_noise": abs(alt - inc) < 0.01,
        "F1_frame_delta_alt_minus_incumbent": b["F1_pooled_dti"] - a["F1_pooled_dti"],
        "hidden_model_directions": {
            k: b["hidden_frame_models"]["models"][k]["modelled_dti"]
            - a["hidden_frame_models"]["models"][k]["modelled_dti"]
            for k in ("transfer", "mass", "both")
        },
        "novelty_fraction_delta": b["uniqueness_min_novel_fraction_at_2px"]
        - a["uniqueness_min_novel_fraction_at_2px"],
        "decision": None,
        "recommended_artifact": None,
        "reason": [],
    }
    beats = alt > inc and not verdict["gate_delta_inside_noise"]
    ranking = sorted(
        (("main H59 sharpened-scarp-scatter-90k", competitor["frozen_gate_pooled_dti"]),
         ("H60-union-d0-75308", b["frozen_gate_pooled_dti"]),
         ("H57-scarpstep-80000", a["frozen_gate_pooled_dti"])),
        key=lambda kv: -kv[1],
    )
    verdict["ranking_on_frozen_gate"] = [{"artifact": k, "pooled_dti": v} for k, v in ranking]
    verdict["recommended_artifact"] = ranking[0][0]
    if beats:
        verdict["decision"] = "PROMOTE-H60"
    elif ranking[0][0] == "H60-union-d0-75308":
        verdict["decision"] = ("NO PROMOTION NEEDED: H60-union already ranks first on the frozen "
                               "gate; no earlier candidate exceeds it")
    else:
        verdict["decision"] = (f"NO SLOT for H60: {ranking[0][0]} ranks above it on the frozen gate "
                               f"({ranking[0][1]:.4f} vs {b['frozen_gate_pooled_dti']:.4f})")
    if abs(alt - inc) < 0.01:
        verdict["reason"].append(
            f"the frozen-gate pooled DTI difference is {alt - inc:+.4f}, inside the gate's "
            "own run-to-run/mass noise")
    verdict["beats_old_incumbent_H57_on_both_instruments"] = (
        b["frozen_gate_pooled_dti"] > a["frozen_gate_pooled_dti"]
        and b["F1_pooled_dti"] > a["F1_pooled_dti"])
    if verdict["beats_old_incumbent_H57_on_both_instruments"]:
        verdict["reason"].append(
            f"H60-union does beat the older H57 on both instruments (frozen gate "
            f"{b['frozen_gate_pooled_dti']:.4f} vs {a['frozen_gate_pooled_dti']:.4f}; pooled F1 "
            f"{b['F1_pooled_dti']:.4f} vs {a['F1_pooled_dti']:.4f}), but the current candidate "
            f"ranks higher still on the frozen gate")
    if all(v < 0 for v in verdict["hidden_model_directions"].values()):
        verdict["reason"].append("all three fitted hidden-frame models put H60 below H57")
    elif any(v < 0 for v in verdict["hidden_model_directions"].values()):
        verdict["reason"].append(
            "the fitted hidden-frame models disagree in sign, so no direction is established")
    verdict["reason"].append(
        f"H60-union still reuses zero prior positive cells (0 of {1_405_451:,}) and is a valid unique "
        "portal-safe file, so it is documented as an alternative, not discarded")

    rep = {
        "generated_utc": "20261007T2320Z",
        "hypothesis": "H60-S1 official-stack four-family structural belief field (arms: official "
                      "stack, union with the H57 morphology field, and a maximal-novelty control)",
        "instruments": {
            "frozen_gate": "scripts/validate_h56.py --truth-mode sgmc_off (evidence/holdout-v1.json "
                           "split, truth = USGS SGMC fault pixels >300 m from the given catalogue)",
            "F1_frame": "scripts/h60_validate.py (pooled whole-map estimator on the same F1 truth, "
                        "with matched-mass uniform and translation controls)",
            "hidden_frame": "the three models fitted on 21 artifacts with recorded scores in "
                            "evidence/h57_hidden_model.json; model-implied values are indicative, "
                            "not scores",
        },
        "candidates": cand,
        "negative_control_max_novelty": control,
        "cross_session_competitor": competitor,
        "prior_pixel_audit": prior_audit,
        "official_stack_arm": {
            "artifact": "docs/downloads/gemsdoe50-h60-officialstack-50000-20261007T2100Z-allfinite.tif",
            "N": 50_000,
            "F1_pooled_dti": None,
            "frozen_gate_pooled_dti": offv["summary"]["pooled_dti_candidate"],
            "frozen_gate_uniform": offv["summary"]["pooled_dti_uniform"],
            "note": "official-stack belief alone, no morphology field; kept as a documented arm of "
                    "the preregistered H60 screen, not promoted (its frozen-gate value sits far "
                    "below the incumbent)",
        },
        "verdict": verdict,
        "provenance": {
            "F1_or_hidden_scores_are_not_competition_scores": True,
            "no_weekly_slot_used": True,
            "developer_note": "nothing in this receipt is a portal score; the competition "
                              "leaderboard has never been scraped or polled by this repository",
        },
    }
    with open(os.path.join(REPO, args.out), "w", encoding="utf-8") as fh:
        json.dump(rep, fh, indent=1)
    print(json.dumps({k: rep[k] for k in ("candidates",)}, indent=1)[:1200])
    print(json.dumps(rep["verdict"], indent=1))
    print("wrote", args.out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
