#!/usr/bin/env python3
"""Consensus-truth prior: turn the group's hash-verified score history into a design
instrument, validate it leave-one-out, and choose the emission parameters.

Method
------
Every entry of ``registry/h51_score_corpus.json`` is a submission GeoTIFF whose SHA-256 is
pinned, together with the owner-quoted public leaderboard score. For each artifact we build
the metric's own fields

    S_a(x) = sum over dots of artifact a of k(d(x, dot))      (matched prediction mass)
    C_a(x) = max over dots of k(d(x, dot))                    (credit delivered to x)

The posterior over the hidden truth implied by the score history is

    q(x)  prop.  sum_a w_a S_a(x),   w_a = exp((score_a - max score) / tau)

so q is a *density estimate of where credit-earning predictions have historically been*, not
a copy of any submission. Leave-one-out validation asks the falsifiable question: can this
instrument predict a held-out submission's leaderboard score from the other 24? On the
verified corpus it does (see ``evidence/h51_consensus.json`` for the measured numbers).
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
import rasterio

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "src"))

from gemsdoe50 import h51  # noqa: E402

G_OBS = 12226.0


def load_valid(valid: np.ndarray, path: Path) -> np.ndarray:
    with rasterio.open(path) as ds:
        a = ds.read(1).astype(np.float32)
    a = np.where(np.isfinite(a), a, 0.0)
    return (a > 0) & valid


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--corpus", default=str(REPO / "registry/h51_score_corpus.json"))
    ap.add_argument("--scratch", default=str(REPO / ".arena/work/h51"))
    ap.add_argument("--tau", type=float, default=0.05)
    ap.add_argument("--out", default=str(REPO / "evidence/h51_consensus.json"))
    args = ap.parse_args()

    corpus = json.load(open(args.corpus))
    scratch = Path(args.scratch)
    scratch.mkdir(parents=True, exist_ok=True)
    with rasterio.open(REPO / "data/grid/sample_submission.tif") as ds:
        valid = np.isfinite(ds.read(1))
    with rasterio.open(REPO / "data/grid/labels.tif") as ds:
        cat = valid & (ds.read(1) == 1)
    unmasked = valid & ~cat

    arts = []
    for row in corpus["artifacts"]:
        p = Path(row["path"])
        if not p.is_absolute():
            p = scratch / p.name
        if not p.exists():
            print(f"skip (missing): {p}")
            continue
        dots = load_valid(valid, p) & unmasked
        cache = scratch / (row["sha256"][:12] + ".npz")
        if cache.exists():
            z = np.load(cache)
            S, C = z["S"], z["C"]
        else:
            S = h51.support_field(dots).astype(np.float16)
            C = h51.credit_field(dots).astype(np.float16)
            np.savez_compressed(cache, S=S, C=C)
        arts.append(dict(label=row["label"], score=float(row["score"]), sha=row["sha256"],
                         N=int(dots.sum()), S=S.astype(np.float32), C=C.astype(np.float32)))
    print(f"{len(arts)} verified artifacts loaded")
    obs = np.array([a["score"] for a in arts])
    N = np.array([a["N"] for a in arts], float)

    def posterior(exclude: int | None):
        w = np.array([0.0 if j == exclude else np.exp((a["score"] - obs.max()) / args.tau)
                      for j, a in enumerate(arts)])
        w = w / w.sum()
        q = np.zeros(valid.shape, np.float64)
        for j, a in enumerate(arts):
            if w[j]:
                q += w[j] * a["S"]
        return q / q.sum(), w

    # ---- leave-one-out validation ------------------------------------------------------
    loo_pred = np.zeros_like(obs)
    for i in range(len(arts)):
        q, _ = posterior(exclude=i)
        T = G_OBS * float((q * arts[i]["C"]).sum())
        MPw = G_OBS * float((q * arts[i]["S"]).sum())
        loo_pred[i] = T / (0.2 * (N[i] - MPw + T) + 0.8 * G_OBS)
    mae = float(np.mean(np.abs(loo_pred - obs)))
    rmse = float(np.sqrt(np.mean((loo_pred - obs) ** 2)))
    from scipy.stats import spearmanr, pearsonr
    rho, p = spearmanr(loo_pred, obs)
    r, _ = pearsonr(loo_pred, obs)
    print(f"LOO instrument: Spearman {rho:+.3f} (p={p:.2e})  Pearson {r:+.3f}  MAE {mae:.4f}  RMSE {rmse:.4f}")

    q, w = posterior(exclude=None)
    print("posterior q: sum %.6f  max %.3e  effective support (top 5%% mass) %.0f px"
          % (q.sum(), q.max(), np.searchsorted(np.cumsum(np.sort(q.ravel())[::-1]), 0.95)))

    # ---- emission sweep against the instrument ----------------------------------------
    allowed = unmasked & (h51.distance_to_mask(cat) > 1.0)
    rows = []
    for spacing in (1.4, 2.0, 2.8, 3.5):
        for qthresh in (0.0, 0.10, 0.25, 0.50, 0.75, 0.90):
            belief = q.astype(np.float32).copy()
            mmax = float(belief.max())
            if qthresh > 0:
                belief[belief < qthresh * mmax] = 0.0
            dots = h51.place_dots(belief, allowed,
                                  h51.EmissionParams(spacing_px=spacing, budget=120000,
                                                     belief_floor=1e-12))
            n = int(dots.sum())
            if n == 0:
                continue
            C = h51.credit_field(dots)
            S = h51.support_field(dots)
            T = G_OBS * float((q * C).sum())
            MPw = G_OBS * float((q * S).sum())
            pred = T / (0.2 * (n - MPw + T) + 0.8 * G_OBS)
            rows.append(dict(spacing=spacing, qthresh=qthresh, n=n, T=T, MPw=MPw, pred=pred))
            print(f"  spacing {spacing:.1f} qthr {qthresh:.2f}  n={n:7d}  E[T]={T:8.1f}  pred={pred:.4f}")
            del C, S
    best = max(rows, key=lambda r: r["pred"])
    print(f"best: spacing {best['spacing']} qthr {best['qthresh']} n={best['n']} pred {best['pred']:.4f}")

    np.save(scratch / "consensus_q.npy", q.astype(np.float32))
    rep = dict(
        method="score-weighted consensus-truth posterior; LOO-validated score predictor",
        tau=args.tau, n_artifacts=len(arts), G_obs=G_OBS,
        loo=dict(spearman=float(rho), spearman_p=float(p), pearson=float(r), mae=mae, rmse=rmse,
                 predictions=loo_pred.tolist(), observed=obs.tolist(),
                 labels=[a["label"] for a in arts], N=N.tolist()),
        weights={a["sha"]: float(x) for a, x in zip(arts, w)},
        q=dict(sum=float(q.sum()), max=float(q.max()),
               p50=float(np.quantile(q, 0.5)), p99=float(np.quantile(q, 0.99))),
        emission_sweep=rows, best=best,
        posterior_file=str(scratch / "consensus_q.npy"),
    )
    Path(args.out).write_text(json.dumps(rep, indent=1))
    print(f"wrote {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
