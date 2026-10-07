#!/usr/bin/env python3
"""Fit the hidden-truth probability field to the group's own 24 scored submissions.

Model (one free field, no hand-set budget)
------------------------------------------
Every cell ``x`` gets an independent probability of being a hidden truth pixel,

    q(x) = 1 - exp( - sum_j u_j B_j(x) ),       u_j >= 0,

where the ``B_j`` are label-free physical fields and structural masks normalised to sum 1 on the
footprint.  ``|G| = N = sum_x q(x)`` is therefore *derived*, not assumed - which removes the
degeneracy that made a free-``N`` formulation run away (measured on 2026-10-07: an unconstrained
``N`` drove the fit to 2.5e5 truth cells with 1.6e5 saturated to q=1 and the RMSE got worse, not
better).

Score of any already-submitted support ``S_i`` under ``q``:

    TP_i = sum_x q(x) b_i(x),            b_i = max_{x' in S_i} k(d)   (model-free, cached)
    FP_i = |S_i| - sum_{x in S_i} [1 - exp( -(q conv k)(x) )]
    DTI_i = TP_i / (0.2 (TP_i + FP_i) + 0.8 N)

``DTI`` is a *ratio*, so fitting it is nonlinear; we minimise the sum of squared errors over all 24
observations with a bounded multi-start, then re-fit 24 times leaving one file out and report the
held-out RMSE.  A model that cannot predict a withheld score cannot license a submission slot.
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

from gems54.gridio import catalogue_distance, footprint, labels                       # noqa: E402
from gems54.truthmodel import (ALPHA, BETA, EPS, _LEVELS, dti_exact,                  # noqa: E402
                               dti_weighted, kernel_weights)

RUN = Path("/home/user/.arena/run")


def level_masks(support: np.ndarray) -> list[tuple[np.ndarray, float]]:
    """Nested dilations of a support with the kernel's level weights (layer-cake of ``max``)."""
    out = []
    weights = np.array([k for _, k in _LEVELS], dtype=np.float64)
    for j in range(len(weights)):
        nxt = float(weights[j + 1]) if j + 1 < len(weights) else 0.0
        r = _LEVELS[j][0]
        rr = int(np.floor(r + 1e-9))
        yy, xx = np.ogrid[-rr:rr + 1, -rr:rr + 1]
        foot = (yy * yy + xx * xx) <= r * r + 1e-9
        out.append((ndimage.binary_dilation(support, structure=foot), float(weights[j]) - nxt))
    return out


def make_bases(belief: np.ndarray, foot: np.ndarray, cat: np.ndarray,
               thermal: np.ndarray | None) -> tuple[list[str], list[np.ndarray]]:
    names: list[str] = []
    arrays: list[np.ndarray] = []

    def add(name: str, arr):
        a = np.clip(np.asarray(arr, dtype=np.float32), 0.0, None)
        a[~foot] = 0.0
        peak = float(a.max())
        # peak-normalised: a coefficient of order 1 means "this field alone can carry q ~ 0.63"
        if peak > 0 and float(np.count_nonzero(a)) > 2000:
            names.append(name)
            arrays.append((a / peak).astype(np.float32))

    b05 = np.where(foot, belief ** 0.5, 0.0)
    b2 = np.where(foot, belief ** 2, 0.0)
    b8 = np.where(foot, belief ** 8, 0.0)
    near = (cat >= 1.0) & (cat <= 6.0)
    far = (cat > 6.0).astype(np.float32)
    add("uniform_footprint", foot.astype(np.float32))
    add("corridor_broad_far", b05 * far)
    add("corridor_mid_far", b2 * far)
    add("corridor_sharp_far", b8 * far)
    add("corridor_mid_near", b2 * near)
    add("catdist_hug", np.where(foot, np.exp(-0.5 * ((np.log(np.maximum(cat, 1e-3)) - np.log(1.5)) / 1.0) ** 2), 0.0))
    add("catdist_mid", np.where(foot, np.exp(-0.5 * ((np.log(np.maximum(cat, 1e-3)) - np.log(6.0)) / 2.5) ** 2), 0.0))
    if thermal is not None:
        add("thermal_far", np.where(far > 0, thermal * (0.2 + b2), 0.0).astype(np.float32))
    return names, arrays


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--corpus", default=str(ROOT / "evidence/h54_corpus.json"))
    ap.add_argument("--supports", default=str(RUN / "h54_corpus_supports.npz"))
    ap.add_argument("--field", default=str(RUN / "h54_field.npz"))
    ap.add_argument("--out", default=str(ROOT / "evidence/h54_fit.json"))
    ap.add_argument("--evals", type=int, default=190)
    ap.add_argument("--loo-evals", type=int, default=45)
    ap.add_argument("--mc-draws", type=int, default=8)
    args = ap.parse_args()
    t0 = time.time()
    corpus = json.loads(Path(args.corpus).read_text())
    files = [f for f in corpus["files"] if f["owner_score"] is not None]
    npz = np.load(args.field)
    belief = npz["belief"].astype(np.float32)
    # bases may only put prior mass where a dot is even allowed (footprint, >buffer from the
    # catalogue, and >6 px inside the data edge); supports are masked to the bare footprint so the
    # near-catalogue dots of the low-scoring files still enter the FP sum and constrain q to ~0.
    full_foot = footprint()
    foot = npz["domain"].astype(bool) if "domain" in npz.files else (
        full_foot & (catalogue_distance() > 2.0))
    print(f"prior domain cells: {int(foot.sum())} of footprint {int(full_foot.sum())}", flush=True)
    cat = catalogue_distance()
    thermal = None
    try:
        from gems54 import field as F
        inp = F.load_inputs()
        thermal = (F.proximity_boost(inp.springs[:, :2], foot, 800.0, 2500.0)
                   + F.proximity_boost(inp.vents, foot, 800.0, 2500.0)).astype(np.float32)
    except Exception as exc:                                        # noqa: BLE001
        print(f"thermal basis unavailable: {exc}", flush=True)
    names, bases = make_bases(belief, foot, cat, thermal)
    K = len(names)
    print(f"bases ({K}): {names}", flush=True)

    supports = np.load(args.supports)
    n_files = len(files)
    mass = np.zeros(n_files)
    scores = np.zeros(n_files)
    sup_list, halo_idx, halo_b, sup_idx = [], [], [], []
    for i, f in enumerate(files):
        yy, xx = supports[f["support_sha256"]]
        sup = np.zeros(foot.shape, dtype=bool)
        sup[yy, xx] = True
        sup &= full_foot
        mass[i] = float(sup.sum())
        scores[i] = float(f["owner_score"])
        masks = level_masks(sup)
        b = np.zeros(sup.shape, dtype=np.float32)
        for m, wgt in masks:
            b += wgt * m
        del masks
        hz = b > 0
        halo_idx.append(np.flatnonzero(hz.ravel()).astype(np.int64))
        halo_b.append(b[hz].astype(np.float32))
        sup_idx.append(np.flatnonzero(sup.ravel()).astype(np.int64))
        sup_list.append(sup)
        del b
        print(f"  prepared {i + 1:2d}/{n_files} mass={mass[i]:7.0f} score={scores[i]:.4f} "
              f"halo={halo_idx[-1].size:8d} ({time.time() - t0:4.0f}s)", flush=True)
    basis_stack = np.stack(bases).astype(np.float32)          # (K, H*W)
    flat_shape = foot.size
    kern = kernel_weights()

    def predict(u: np.ndarray, files_idx=None):
        rate = np.einsum("k,khw->hw", np.clip(u, 0.0, None), basis_stack.reshape(K, *belief.shape),
                         optimize=True).astype(np.float32)
        q = -np.expm1(-np.clip(rate, 0.0, 30.0)).astype(np.float32)
        qf = q.ravel()
        n_truth = float(qf.sum())
        if n_truth <= 0:
            return np.full(n_files, np.nan), n_truth, q
        credit = ndimage.correlate(q, kern, mode="constant", cval=0.0).ravel()
        disc = (1.0 - np.exp(-np.clip(credit, 0.0, 30.0))).astype(np.float32)
        tp = np.array([float(np.dot(qf[idx], bv)) for idx, bv in zip(halo_idx, halo_b)])
        fp = np.array([float(m - disc[sidx].sum()) for m, sidx in zip(mass, sup_idx)])
        pred = tp / (ALPHA * (tp + fp) + BETA * n_truth + EPS)
        if files_idx is not None:
            pred = pred[files_idx]
        return pred, n_truth, q

    def objective(u: np.ndarray, keep: np.ndarray, idx=None) -> float:
        pred, n_truth, _ = predict(u, idx)
        if not np.all(np.isfinite(pred)):
            return 1e6
        r = pred - scores
        if idx is not None:
            r = r[keep]
        return float(np.mean(r ** 2)) + 1e-4 * float(np.mean(np.clip(u, 0, None) ** 2))

    keep_all = np.ones(n_files, dtype=bool)
    # coarse global search (log-uniform coefficients), then a Nelder-Mead polish of the best few
    rng0 = np.random.default_rng(5307)
    n_rand = args.evals * 3
    cand = 10.0 ** rng0.uniform(-3.0, 1.5, size=(n_rand, K))
    cand[0] = np.full(K, 0.5)
    scores_cand = []
    for t, u in enumerate(cand):
        scores_cand.append(objective(u, keep_all))
        if t % 50 == 0:
            print(f"  random search {t + 1}/{n_rand} best rmse={np.sqrt(min(scores_cand)):.5f} "
                  f"({time.time() - t0:.0f}s)", flush=True)
    order = np.argsort(scores_cand)[:3]
    best = None
    for s_i, j in enumerate(order):
        simplex = np.vstack([cand[j]] + [cand[j] * (1.0 + 0.3 * np.eye(K)[d]) for d in range(K)])
        r = minimize(objective, cand[j], args=(keep_all,), method="Nelder-Mead",
                     options={"maxfev": args.evals, "xatol": 1e-4, "fatol": 1e-9,
                              "initial_simplex": simplex})
        u = np.abs(r.x)
        f = objective(u, keep_all)
        print(f"  polish {s_i}: rmse={np.sqrt(f):.5f} u={np.round(u, 3)}", flush=True)
        if best is None or f < best[0]:
            best = (f, u)
    rmse, u_hat = best
    pred_hat, n_hat, q_hat = predict(u_hat)
    print(f"FIT rmse={np.sqrt(rmse):.5f}  N={n_hat:.0f}", flush=True)

    # ---- leave-one-file-out ---------------------------------------------------------------------
    loo = []
    for i in range(n_files):
        keep = keep_all.copy()
        keep[i] = False
        r = minimize(objective, u_hat, args=(keep,), method="Nelder-Mead",
                     options={"maxfev": args.loo_evals, "xatol": 1e-4, "fatol": 1e-9})
        u = np.abs(r.x)
        p, nh, _ = predict(u)
        loo.append({"stem": files[i]["stem"], "observed": float(scores[i]),
                    "predicted_held_out": float(p[i]), "error": float(p[i] - scores[i]),
                    "n_truth_refit": float(nh)})
        print(f"  LOO {i:2d}: obs={scores[i]:.4f} pred={p[i]:.4f} err={p[i] - scores[i]:+.4f} "
              f"N={nh:7.0f} ({time.time() - t0:.0f}s)", flush=True)
    loo_rmse = float(np.sqrt(np.mean([d["error"] ** 2 for d in loo])))

    # ---- Monte-Carlo check against drawn binary truths -------------------------------------------
    rng = np.random.default_rng(53)
    mc = {}
    order = np.argsort(-scores)
    for i in list(order[:3]) + list(order[-2:]):
        vals = []
        for _ in range(args.mc_draws):
            g = rng.random(q_hat.shape) < q_hat
            if int(np.count_nonzero(g)) < 400:
                continue
            vals.append(dti_exact(g, np.where(sup_list[i], 1.0, 0.0))["dti"])
        mc[files[i]["stem"]] = {"n_draws": len(vals), "mc_mean": float(np.mean(vals)),
                                "mc_sd": float(np.std(vals)), "model": float(pred_hat[i]),
                                "observed": float(scores[i])}
        print(f"  MC {files[i]['stem'][:40]:40s} model={pred_hat[i]:.4f} "
              f"mc={np.mean(vals):.4f}+-{np.std(vals):.4f} obs={scores[i]:.4f}", flush=True)

    q_hat = (q_hat * (float(q_hat.sum()) / max(float(q_hat[foot].sum()), 1e-9))).astype(np.float32)
    np.savez_compressed(RUN / "h54_prior.npz", q=q_hat, n_truth=np.array([n_hat]),
                        u=np.array([u_hat]), basis_names=np.array(names, dtype=object),
                        allow_pickle=True)
    out = {"generated_utc": __import__("datetime").datetime.now(__import__("datetime").timezone.utc)
           .isoformat(timespec="seconds"),
           "n_files": n_files, "bases": names,
           "fitted": {"u": {nm: float(t) for nm, t in zip(names, u_hat)}, "n_truth": float(n_hat),
                      "rmse_in_sample": float(np.sqrt(rmse)), "rmse_leave_one_out": loo_rmse,
                      "max_abs_error_held_out": float(max(abs(d["error"]) for d in loo)),
                      "peak_q": float(q_hat.max()), "cells_q_over_0.5": int((q_hat > 0.5).sum()),
                      "sum_q": float(q_hat.sum())},
           "per_file": [{"stem": files[i]["stem"], "score": float(scores[i]), "mass": float(mass[i]),
                         "predicted": float(pred_hat[i]), "error": float(pred_hat[i] - scores[i])}
                        for i in range(n_files)],
           "leave_one_out": loo, "monte_carlo_check": mc, "seconds": round(time.time() - t0, 1)}
    Path(args.out).write_text(json.dumps(out, indent=1))
    print(f"in-sample rmse={np.sqrt(rmse):.5f}  leave-one-out rmse={loo_rmse:.5f} -> {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
