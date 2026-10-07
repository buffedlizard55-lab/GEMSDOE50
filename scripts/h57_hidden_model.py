"""H57 hidden-frame model — what per-dot credit is a new dot set likely to earn?

The competition metric is scored on labels that are not published.  Everything
this repository can do offline is to *model* that frame from the 21 corpus
artifacts whose public-leaderboard scores are pinned.  For each such artifact
the metric identity gives the hidden credit it actually earned,

    T = score * (0.2 N + 0.8 G)          (G = 14,088.75, the nested-pair solve)

and therefore its hidden credit per dot ``h = T / N``.  This script fits and
reports several candidate models of ``h`` and uses each to predict the hidden
DTI of the H57 candidate as a function of its mass.

Models
------
``transfer``   h = s * F1_c_per_dot          (frame-ratio model, s fitted)
``mass``       h = k * N ** p                (absolute-efficiency model)
``both``       h = a + b * F1_c_per_dot + c * ln N   (OLS, the headline model)

**None of these is a validation of the candidate.**  Every one is a regression
on the same 21 numbers, and the target ``h`` is derived from the score, so a
fitted R^2 measures how well the corpus grades itself, not how well the
candidate will score.  The numbers are here to bound the decision (shipped mass,
and whether the modelled score plausibly clears the 0.3774 public best), and the
scripts/report must always say so.

Usage
-----
    python scripts/h57_hidden_model.py --out evidence/h57_hidden_model.json
"""

from __future__ import annotations

import argparse
import json
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

#: Candidate masses and their measured F1 credit per dot on the *current*
#: belief field (scripts/build_h57.belief_field, stratified-verified channel
#: sets).  Measured on 2026-10-07; see evidence/build_h57-scarpstep.json and the
#: sweep recorded in this session's notes.
CANDIDATE = [
    (30000, 0.09848),
    (45000, 0.09038),
    (60000, 0.08368),
    (80000, 0.07467),
    (100000, 0.06530),
    (140000, 0.06017),
    (200000, 0.05233),
]


def ols(X: np.ndarray, y: np.ndarray):
    """OLS with intercept.  Returns beta, r2, residual sd and beta standard errors.

    The standard errors are the textbook ``sqrt(diag(sigma^2 (A'A)^-1))`` with
    ``sigma^2 = RSS / (n - k)``.  They are reported so that no coefficient in
    this file is ever quoted without its uncertainty: with n = 21 corpus rows and
    a strong mass term, the F1 coefficient is *not* significantly different from
    zero, and the report must say so.
    """
    A = np.column_stack([np.ones(len(X)), X])
    beta, *_ = np.linalg.lstsq(A, y, rcond=None)
    resid = y - A @ beta
    ss_res = float(resid @ resid)
    ss_tot = float(((y - y.mean()) ** 2).sum())
    r2 = 1.0 - ss_res / ss_tot
    dof = max(len(y) - A.shape[1], 1)
    sd = float(np.sqrt(ss_res / dof))
    cov = sd ** 2 * np.linalg.pinv(A.T @ A)
    se = np.sqrt(np.diag(cov))
    return beta, r2, sd, se


def solve_n_from_h(score: float, h: float, g: float):
    """Invert ``DTI = T / (0.2 N + 0.8 G)`` with ``T = h * N`` for the mass N.

    Returns ``None`` when the implied credit per dot cannot be reconciled with the
    score (``h <= 0.2 * score``), which is the case for a score that no dot set of
    positive mass could earn.
    """
    denom = h - 0.2 * score
    if denom <= 0:
        return None
    return 0.8 * g * score / denom


def normal_sf(z: float) -> float:
    """Upper-tail standard-normal probability, no SciPy dependency."""
    from math import erfc, sqrt
    return 0.5 * erfc(z / sqrt(2.0))


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--transfer", default="evidence/h57_transfer.json")
    ap.add_argument("--g", type=float, default=14088.75)
    ap.add_argument("--out", default="evidence/h57_hidden_model.json")
    ap.add_argument("--target", type=float, default=0.3774)
    args = ap.parse_args(argv)

    with open(args.transfer) as fh:
        rows = json.load(fh)["rows"]
    N = np.array([r["score"] and 0 or 0 for r in rows], dtype=float)  # placeholder
    # Recover N from the emitted receipts: h57_transfer rows carry c_per_dot_hidden
    # which is T / N, and the score, so N = T / h_hidden with T = score*(0.2N+0.8G)
    # -> N = 0.8 G score / (h - 0.2 score) ... solve directly instead:
    #     h N = score (0.2 N + 0.8 G)  ->  N (h - 0.2 score) = 0.8 G score
    N_list, h_list, f1_list, names = [], [], [], []
    for r in rows:
        h = r["c_per_dot_hidden"]
        s = r["score"]
        n_recovered = solve_n_from_h(s, h, args.g)
        if n_recovered is None:
            continue
        N_list.append(n_recovered)
        h_list.append(h)
        f1_list.append(r["c_per_dot_F1"])
        names.append(r["file"])
    N = np.array(N_list)
    h = np.array(h_list)
    f1 = np.array(f1_list)

    out = {"generated_utc": None, "G": args.g, "n_corpus": len(N),
           "corpus": [], "models": {}, "candidate_predictions": {}}
    import datetime as _dt
    out["generated_utc"] = _dt.datetime.now(_dt.timezone.utc).strftime(
        "%Y-%m-%dT%H:%M:%SZ")
    for nm, n_, f_, h_ in zip(names, N, f1, h):
        out["corpus"].append({"file": nm, "N": float(n_), "F1_c_per_dot": float(f_),
                              "hidden_c_per_dot": float(h_),
                              "transfer": float(h_ / f_)})

    # ---- model 1: h = s * F1_c_per_dot (ratio, no intercept) ----------------
    s_hat = float((h * f1).sum() / (f1 * f1).sum())
    r = h - s_hat * f1
    out["models"]["transfer"] = {
        "form": "h = s * F1_c_per_dot",
        "s": s_hat,
        "r2": float(1 - (r @ r) / ((h - h.mean()) ** 2).sum()),
        "resid_sd": float(np.sqrt((r @ r) / (len(h) - 1))),
    }

    # ---- model 2: absolute efficiency h = k * N ** p ------------------------
    beta, r2, sd, se = ols(np.log(N)[:, None], np.log(h))
    out["models"]["mass"] = {
        "form": "h = exp(a) * N ** p",
        "a": float(beta[0]), "p": float(beta[1]), "r2": float(r2),
        "resid_sd_log": float(sd),
        "se_a": float(se[0]), "se_p": float(se[1]),
    }

    # ---- model 3: OLS on (F1 c/dot, ln N) -----------------------------------
    X = np.column_stack([f1, np.log(N)])
    beta3, r2_3, sd3, se3 = ols(X, h)
    out["models"]["both"] = {
        "form": "h = a + b * F1_c_per_dot + c * ln N",
        "a": float(beta3[0]), "b": float(beta3[1]), "c": float(beta3[2]),
        "se_a": float(se3[0]), "se_b": float(se3[1]), "se_c": float(se3[2]),
        "t_b": float(beta3[1] / se3[1]), "t_c": float(beta3[2] / se3[2]),
        "r2": float(r2_3), "resid_sd": float(sd3),
        # t-like 95 % interval multiplier for n=21, k=3
        "t95": 2.10,
        "note": "b (the F1 coefficient) is negative and NOT significant: "
                "|t| < 2, so no claim that F1 selectivity lowers the hidden score "
                "is supported, only that it does not measurably raise it.",
    }

    # ---- best-ever absolute credit, as an envelope --------------------------
    order = np.argsort(N)
    N_s, h_s = N[order], h[order]
    env = []
    for i in range(len(N_s)):
        hi = h_s[i:].max()
        env.append({"N_at_least": float(N_s[i]), "best_h": float(hi),
                    "best_T": float(hi * N_s[i]),
                    "implied_dti": float(hi * N_s[i] / (0.2 * N_s[i] + 0.8 * args.g))})
    out["credit_envelope"] = env

    # ---- what T would be needed to beat the public best? --------------------
    need = []
    for n_ in [20000, 30000, 40000, 60000, 80000, 100000, 140000]:
        T_need = args.target * (0.2 * n_ + 0.8 * args.g)
        need.append({"N": n_, "T_needed": float(T_need),
                     "h_needed": float(T_need / n_),
                     "coverage_needed": float(T_need / args.g)})
    out["target_T_required"] = {"target": args.target, "table": need,
                               "best_ever_T": float((h * N).max()),
                               "best_ever_h": float(h.max())}

    # ---- candidate predictions ---------------------------------------------
    for label, fn in (
        ("transfer", lambda n_, f_: s_hat * f_),
        ("mass", lambda n_, f_: float(np.exp(beta[0]) * n_ ** beta[1])),
        ("both", lambda n_, f_: float(beta3[0] + beta3[1] * f_ + beta3[2] * np.log(n_))),
    ):
        preds = []
        for n_, f_ in CANDIDATE:
            h_hat = max(fn(n_, f_), 0.0)
            T = min(h_hat * n_, args.g)          # credit cannot exceed truth mass
            preds.append({
                "N": n_, "F1_c_per_dot": f_, "hidden_c_per_dot": h_hat,
                "T": float(T), "coverage": float(T / args.g),
                "modelled_dti": float(T / (0.2 * n_ + 0.8 * args.g)),
            })
        best = max(preds, key=lambda d: d["modelled_dti"])
        out["candidate_predictions"][label] = {"rows": preds,
                                               "argmax_N": best["N"],
                                               "argmax_dti": best["modelled_dti"]}
        if label == "both":
            rows3 = []
            for n_, f_ in CANDIDATE:
                h_hat = fn(n_, f_)
                lo = max(h_hat - 2.10 * sd3, 0.0)
                hi = h_hat + 2.10 * sd3
                rows3.append({
                    "N": n_, "h_hat": h_hat, "h_lo95": lo, "h_hi95": hi,
                    "dti_central": float(min(max(h_hat, 0), args.g / n_) * n_ /
                                         (0.2 * n_ + 0.8 * args.g)),
                    "dti_lo95": float(min(lo * n_, args.g) / (0.2 * n_ + 0.8 * args.g)),
                    "dti_hi95": float(min(hi * n_, args.g) / (0.2 * n_ + 0.8 * args.g)),
                })
            out["both_interval"] = rows3
            # exceedance probabilities under the model's residual spread; these
            # assume normal, homoscedastic residuals, which 21 points cannot
            # establish - report as indicative only.
            exc = []
            for bar in (0.2778, 0.3774):
                for n_, f_ in CANDIDATE:
                    if n_ != 80000:
                        continue
                    # model's own prediction for this mass, then invert the bar
                    h_here = fn(n_, f_)
                    h_bar = bar * (0.2 * n_ + 0.8 * args.g) / n_
                    z = (h_here - h_bar) / sd3
                    # h ~ N(h_hat, sd): P(h > h_bar) = Phi(z) = P(Z > -z)
                    exc.append({"bar": bar, "N": n_, "h_model": float(h_here),
                                "h_required": float(h_bar),
                                "z": float(z), "p_above": float(normal_sf(-z))})
            out["exceedance_probabilities"] = {
                "note": "indicative only: normal residual assumption, fitted on 21 rows",
                "rows": exc,
            }

    with open(args.out, "w") as fh:
        json.dump(out, fh, indent=1, sort_keys=False)
    print(f"corpus artifacts: {len(N)}")
    for k, v in out["models"].items():
        print(f"  {k:9s} {v['form']:38s} r2={v['r2']:.3f}")
    print("\ntransfer / dot  (sorted by N):")
    for nm, n_, f_, h_ in sorted(zip(names, N, f1, h), key=lambda t: t[1]):
        print(f"  {nm:26s} N={n_:9.0f} F1c={f_:.5f} h={h_:.5f} s={h_/f_:5.2f}")
    print(f"\nT needed to beat {args.target:.4f}:")
    for d in need:
        print(f"  N={d['N']:7d} T={d['T_needed']:9.1f} h={d['h_needed']:.4f} "
              f"coverage={d['coverage_needed']:.3f}")
    _t = out["target_T_required"]
    print(f"  best ever observed: T={_t['best_ever_T']:.0f} h={_t['best_ever_h']:.4f}")
    print("\ncandidate predictions:")
    for k, v in out["candidate_predictions"].items():
        print(f"  {k:9s} argmax N={v['argmax_N']:7d} modelled DTI={v['argmax_dti']:.4f}")
        if k == "both":
            for row in v["rows"]:
                print(f"      N={row['N']:7d} h={row['hidden_c_per_dot']:.4f} "
                      f"T={row['T']:8.1f} cov={row['coverage']:.3f} "
                      f"DTI={row['modelled_dti']:.4f}")
    print("\nwrote", args.out)


if __name__ == "__main__":
    main()
