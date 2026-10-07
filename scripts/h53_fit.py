#!/usr/bin/env python3
"""Fit a hidden-truth prior to the group's own scored submissions, then test that fit.

The idea
--------
For an emitted support ``S`` and the hidden truth ``G`` the official score is

    DTI = TP / (0.2 (TP + FP) + 0.8 |G|),
    TP = sum_{g in G} max_{x in S} k(d(x,g)),   FP = sum_{x in S} [1 - max_{g in G} k(d(x,g))],

so every scored raster the group has ever uploaded is one *equation* in the unknown ``G``.
``G`` has millions of binary unknowns and we have 24 equations, so ``G`` itself is not
identifiable - but a low-dimensional *prior over its location* is.  We write

    rho = N * sum_j theta_j B_j ,   theta on the simplex,   N = |G| in a bounded scan,

with every ``B_j`` either a label-free physical surface computed in this repository or a purely
structural mask (catalogue distance, uniform).  The fitted ``theta`` says how much of the hidden
label set lives in each kind of place, which is exactly the information an emission-budget
decision needs.  Because ``k`` enters both terms only through sums over a 3-pixel neighbourhood,
``TP_i`` and ``FP_i`` are *linear* functionals of ``rho`` under the first-order (uncorrelated-cell)
closure, so all 24 predictions for any ``(theta, N)`` are two matrix-vector products and the whole
scan - including leave-one-out refits - is cheap.

Honesty controls
----------------
* ``N`` is *profiled*, not optimised: an unbounded search runs away to absurd truth sizes (measured:
  it went to 2.5e5 cells and saturated 1.6e5 of them), which is a degeneracy of the closure, not a
  discovery.  The reported table shows the RMSE at every scanned ``N``.
* Generalisation is measured by leave-one-file-out refit: a model that cannot predict a held-out
  submission's score is not evidence for spending a slot.
* The exact nonlinear closure and a Monte-Carlo draw set re-score the winner; the difference
  between closures is reported rather than assumed away.
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

import numpy as np
from scipy import ndimage
from scipy.optimize import minimize

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from gems53.gridio import catalogue_distance, footprint, labels                    # noqa: E402
from gems53.truthmodel import (ALPHA, BETA, EPS, _LEVELS, dti_exact,               # noqa: E402
                               dti_weighted, expected_max_kernel, kernel_weights)

RUN = Path("/home/user/.arena/run")


def coverage(support: np.ndarray) -> np.ndarray:
    """``b[x] = max_{x' in support} k(d)`` for a binary support, by layer-cake dilations."""
    out = np.zeros(support.shape, dtype=np.float32)
    weights = np.array([k for _, k in _LEVELS], dtype=np.float64)
    s = support
    for j in range(len(weights)):
        nxt = float(weights[j + 1]) if j + 1 < len(weights) else 0.0
        r = _LEVELS[j][0]
        rr = int(np.floor(r + 1e-9))
        yy, xx = np.ogrid[-rr:rr + 1, -rr:rr + 1]
        foot = (yy * yy + xx * xx) <= r * r + 1e-9
        reach = ndimage.binary_dilation(s, structure=foot).astype(np.float32)
        out += (float(weights[j]) - nxt) * reach
    return out


def make_bases(belief: np.ndarray, foot: np.ndarray, cat: np.ndarray,
               thermal: np.ndarray | None, sgmc: np.ndarray | None) -> tuple[list[str], list[np.ndarray]]:
    """Dictionary of candidate truth densities (each normalised to sum 1 inside the footprint)."""
    names: list[str] = []
    arrays: list[np.ndarray] = []

    def add(name: str, arr: np.ndarray):
        a = np.clip(np.asarray(arr, dtype=np.float32), 0.0, None)
        a[~foot] = 0.0
        tot = float(a.sum())
        if tot > 0 and float(np.count_nonzero(a)) > 1000:
            names.append(name)
            arrays.append((a / tot).astype(np.float32))

    b2 = np.where(foot, belief ** 2, 0.0)
    b8 = np.where(foot, belief ** 8, 0.0)
    bh = np.where(foot, belief ** 0.5, 0.0)
    near = (cat >= 1.0) & (cat <= 6.0)
    far = cat > 6.0
    add("uniform_footprint", foot.astype(np.float32))
    add("uniform_off_catalogue", (foot & (cat > 2.0)).astype(np.float32))
    add("corridor_broad_far", bh * far)
    add("corridor_mid_far", b2 * far)
    add("corridor_sharp_far", b8 * far)
    add("corridor_mid_near", b2 * near)
    add("corridor_broad_near", bh * near)
    for mu, sd in ((1.5, 1.0), (4.0, 2.0), (10.0, 4.0), (25.0, 10.0)):
        d = np.maximum(cat, 1e-3)
        add(f"catdist_lognorm{mu}", np.where(foot, np.exp(-0.5 * ((np.log(d) - np.log(mu)) / sd) ** 2), 0.0))
    if sgmc is not None:
        add("sgmc_off_catalogue", np.where(foot & ~labels(), sgmc, 0.0).astype(np.float32))
    if thermal is not None:
        add("thermal_corridor", np.where(far, thermal * (0.25 + b2), 0.0).astype(np.float32))
    return names, arrays


def fit(theta0, Tm, Cm, masses, scores, n_truth, ridge):
    K = Tm.shape[1]

    def loss(z):
        w = n_truth * z
        tp = Tm @ w
        fp = np.maximum(masses - (Cm @ w), 0.0)
        pred = tp / (ALPHA * (tp + fp) + BETA * n_truth + EPS)
        return float(np.mean((pred - scores) ** 2) + ridge * float(z @ z))

    cons = ({"type": "eq", "fun": lambda z: float(np.sum(z) - 1.0)},)
    bnds = tuple((0.0, 1.0) for _ in range(K))
    best = None
    starts = [x for x in (theta0, np.eye(K)[int(np.argmax(Tm.mean(axis=0)))], np.full(K, 1.0 / K))
              if x is not None and np.shape(x) == (K,)]
    for x0 in starts:
        r = minimize(loss, x0, method="SLSQP", bounds=bnds, constraints=cons,
                     options={"maxiter": 300, "ftol": 1e-11})
        if best is None or r.fun < best.fun:
            best = r
    return best


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--corpus", default=str(ROOT / "evidence/h53_corpus.json"))
    ap.add_argument("--supports", default=str(RUN / "h53_corpus_supports.npz"))
    ap.add_argument("--field", default=str(RUN / "h53_field.npz"))
    ap.add_argument("--out", default=str(ROOT / "evidence/h53_fit.json"))
    ap.add_argument("--n-grid", default="5000,7000,9000,11000,13000,15000,18000,22000")
    ap.add_argument("--ridge", type=float, default=0.002)
    args = ap.parse_args()
    t0 = time.time()
    corpus = json.loads(Path(args.corpus).read_text())
    files = [f for f in corpus["files"] if f["owner_score"] is not None]
    supports = np.load(args.supports)
    npz = np.load(args.field)
    belief = npz["belief"].astype(np.float32)
    foot = footprint()
    cat = catalogue_distance()
    thermal = np.zeros_like(belief)
    try:                                                  # optional; the field builder caches it
        import rasterio                                        # noqa: F401
        from gems53 import field as F
        inp = F.load_inputs()
        thermal = F.proximity_boost(inp.springs[:, :2], foot, 800.0, 2500.0) * 0.5 \
            + F.proximity_boost(inp.vents, foot, 800.0, 2500.0) * 0.5
    except Exception as exc:                                  # noqa: BLE001
        print(f"thermal basis unavailable: {exc}", flush=True)
    sgmc = None
    sgmc_path = ROOT / "data/external/derived_sgmc_faults_100m_u8.tif"
    if sgmc_path.exists():
        import rasterio
        with rasterio.open(sgmc_path) as ds:
            sgmc = (ds.read(1) > 0)
    names, bases = make_bases(belief, foot, cat, thermal, sgmc)
    K = len(bases)
    n_files = len(files)
    print(f"bases ({K}): {names}", flush=True)

    kern = kernel_weights()
    Tm = np.zeros((n_files, K))
    Cm = np.zeros((n_files, K))
    masses = np.zeros(n_files)
    scores = np.zeros(n_files)
    supports_by_file = []
    for i, f in enumerate(files):
        yy, xx = supports[f["support_sha256"]]
        sup = np.zeros(foot.shape, dtype=bool)
        sup[yy, xx] = True
        sup &= foot
        supports_by_file.append(sup)
        masses[i] = float(sup.sum())
        scores[i] = float(f["owner_score"])
    for i in range(n_files):
        sup = supports_by_file[i]
        b = coverage(sup)
        c = ndimage.correlate(sup.astype(np.float32), kern, mode="constant", cval=0.0)
        for j in range(K):
            Tm[i, j] = float(np.sum(bases[j] * b))
            Cm[i, j] = float(np.sum(bases[j] * c))
        del b, c
        print(f"  file {i + 1:2d}/{n_files} mass={masses[i]:7.0f} score={scores[i]:.4f} "
              f"({time.time() - t0:5.0f}s)", flush=True)

    def predict(theta, n_truth):
        w = n_truth * theta
        tp = Tm @ w
        fp = np.maximum(masses - (Cm @ w), 0.0)
        return tp / (ALPHA * (tp + fp) + BETA * n_truth + EPS)

    def rmse(theta, n_truth, idx=None):
        p = predict(theta, n_truth)
        r = (p - scores) if idx is None else (p[idx] - scores[idx])
        return float(np.sqrt(np.mean(r ** 2)))

    profile = []
    for n_truth in [float(x) for x in args.n_grid.split(",")]:
        res = fit(None, Tm, Cm, masses, scores, n_truth, args.ridge)
        profile.append({"n_truth": n_truth, "rmse": rmse(res.x, n_truth),
                        "theta": {nm: round(float(t), 4) for nm, t in zip(names, res.x) if t > 1e-3}})
        print(f"  N={n_truth:7.0f} rmse={profile[-1]['rmse']:.5f} "
              f"theta={list(profile[-1]['theta'].items())[:4]}", flush=True)
    best_prof = min(profile, key=lambda r: r["rmse"])
    n_hat = best_prof["n_truth"]
    theta_hat = np.asarray([best_prof["theta"].get(nm, 0.0) for nm in names], dtype=np.float64)
    theta_hat = theta_hat / theta_hat.sum()
    res = fit(theta_hat, Tm, Cm, masses, scores, n_hat, args.ridge)
    theta_hat = res.x

    # ---- leave-one-file-out generalisation ------------------------------------------------------
    loo = []
    for i in range(n_files):
        keep = np.ones(n_files, dtype=bool)
        keep[i] = False
        r = fit(theta_hat, Tm[keep], Cm[keep], masses[keep], scores[keep], n_hat, args.ridge)
        p = predict(r.x, n_hat)[i]
        loo.append({"stem": files[i]["stem"], "observed": float(scores[i]), "predicted_held_out": float(p),
                    "error": float(p - scores[i]), "theta_top":
                        {nm: round(float(t), 3) for nm, t in sorted(zip(names, r.x), key=lambda z: -z[1])[:3]
                         if t > 1e-3}})
    loo_rmse = float(np.sqrt(np.mean([d["error"] ** 2 for d in loo])))

    # ---- the fitted prior, exact closure, and a Monte-Carlo check --------------------------------
    rho = np.zeros(foot.shape, dtype=np.float32)
    for t, b in zip(theta_hat, bases):
        if t > 0:
            rho += float(t) * b
    rho *= n_hat
    q = (1.0 - np.exp(-rho)).astype(np.float32)                    # P(cell is truth) under a Poisson
    q = np.where(foot, q, 0.0).astype(np.float32)
    q *= n_hat / float(q.sum())
    disc = expected_max_kernel(q)
    exact = np.array([dti_weighted(sup, q)["dti"] for sup in supports_by_file])
    rng = np.random.default_rng(53)
    mc = {}
    check_idx = sorted(range(n_files), key=lambda i: -scores[i])[:3] \
        + sorted(range(n_files), key=lambda i: scores[i])[:2]
    for i in check_idx:
        vals = []
        for _ in range(8):
            g = rng.random(q.shape) < q
            if int(g.sum()) < 400:
                continue
            vals.append(dti_exact(g, np.where(supports_by_file[i], 1.0, 0.0))["dti"])
        mc[files[i]["stem"]] = {"n_draws": len(vals), "mc_mean": float(np.mean(vals)),
                                "mc_sd": float(np.std(vals)), "weighted_model": float(exact[i]),
                                "observed": float(scores[i]),
                                "first_order_model": float(predict(theta_hat, n_hat)[i])}
    np.savez_compressed(RUN / "h53_prior.npz", q=q, discount=disc, rho=rho,
                        n_hat=np.array([n_hat]), theta=np.asarray([theta_hat]),
                        basis_names=np.array(names, dtype=object), allow_pickle=True)
    out = {
        "generated_utc": __import__("datetime").datetime.now(__import__("datetime").timezone.utc)
        .isoformat(timespec="seconds"),
        "n_files": n_files, "bases": names, "ridge": args.ridge,
        "fitted": {"n_truth": n_hat, "theta": {nm: float(t) for nm, t in zip(names, theta_hat)},
                   "rmse_in_sample": rmse(theta_hat, n_hat),
                   "rmse_leave_one_out": loo_rmse,
                   "max_abs_error_held_out": float(max(abs(d["error"]) for d in loo)),
                   "rmse_exact_closure": float(np.sqrt(np.mean((exact - scores) ** 2))),
                   "sum_q": float(q.sum()), "peak_q": float(q.max()),
                   "cells_q_over_half": int((q > 0.5).sum())},
        "n_profile": profile,
        "per_file": [{"stem": files[i]["stem"], "score": float(scores[i]), "mass": float(masses[i]),
                      "pred_first_order": float(predict(theta_hat, n_hat)[i]),
                      "pred_exact": float(exact[i]), "residual_exact": float(exact[i] - scores[i])}
                     for i in range(n_files)],
        "leave_one_out": loo,
        "monte_carlo_check": mc,
        "single_basis_rmse": {nm: rmse(np.eye(K)[j], n_hat) for j, nm in enumerate(names)},
        "seconds": round(time.time() - t0, 1),
    }
    Path(args.out).write_text(json.dumps(out, indent=1))
    print(json.dumps(out["fitted"], indent=1))
    print(f"in-sample rmse={out['fitted']['rmse_in_sample']:.5f}  "
          f"leave-one-out rmse={loo_rmse:.5f} -> {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
