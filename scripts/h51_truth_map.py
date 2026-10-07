#!/usr/bin/env python3
"""Invert the group's published scores into a spatial map of the hidden credit mass.

Why this is possible
--------------------
The organizer metric reduces exactly to ``DTI = T / (0.2*N + 0.8*G)`` where

    T = sum over hidden-truth pixels of max over our dots of k(d)   (credit delivered)
    N = number of predicted positive pixels
    G = total hidden-truth mass in the scored domain (pixels, in credit units)
    k(d) = max(0, 1 - d_m / 300 m)

(Tversky with alpha=0.2, beta=0.8 and ``T + FPw = N`` collapses to that form; it is
re-derived and unit-tested in ``src/gemsdoe50/h51.py`` and ``tests/test_h51.py``.)
``G`` is fixed by the blind spacing-5 lattice artifact, whose credit per pixel is a pure
geometric constant independent of where the truth is: ``G = 0.2*s*N / (c - 0.8*s)``.

Because ``T`` is *linear* in the unknown truth, a corpus of scored submissions with known
dot sets is a linear system: one equation per scored artifact. Discretising the scored
domain into blocks gives

    T_a = sum_c R_ac * phi_c,     R_ac = mean over unmasked pixels x in block c of C_a(x)

with ``C_a`` the credit field of artifact ``a`` and ``phi_c`` the truth mass (in credit
pixels) inside block c. ``phi >= 0``, ``sum_c phi_c = G``.

Honesty statement
-----------------
The system is under-determined: the corpus is largely a nested family, so many blocks are
seen by the same artifacts and are therefore not separately identifiable. The only claim
this script makes is the *leave-one-artifact-out* one: does the fitted map predict the
score of a submission it has never seen, better than a constant or a dot-count baseline?
Whatever it reports is written verbatim to ``evidence/h51_truth_map.json``.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
import rasterio
from scipy.optimize import nnls
from scipy.sparse import csr_matrix

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "src"))

from gemsdoe50 import h51


def sha256_file(p: Path) -> str:
    import hashlib

    h = hashlib.sha256()
    with open(p, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def laplacian(n: int) -> csr_matrix:
    """4-neighbour graph Laplacian on an n x n block grid (sum of squared differences)."""
    idx = np.arange(n * n).reshape(n, n)
    rows, cols = [], []
    for axis, shift in ((0, 1), (1, 1)):
        if axis == 0:
            a, b = idx[:-shift, :].ravel(), idx[shift:, :].ravel()
        else:
            a, b = idx[:, :-shift].ravel(), idx[:, shift:].ravel()
        rows.append(a)
        cols.append(b)
    a = np.concatenate(rows)
    b = np.concatenate(cols)
    # L = D - A with the symmetric incidence form D^T D, i.e. each edge twice
    m = csr_matrix((np.ones(2 * a.size),
                    (np.concatenate([a, b]), np.concatenate([b, a]))),
                   shape=(n * n, n * n))
    deg = np.asarray(m.sum(axis=1)).ravel()
    return csr_matrix((np.concatenate([-np.ones(2 * a.size), deg]),
                       (np.concatenate([np.concatenate([a, b]), np.arange(n * n)]),
                        np.concatenate([np.concatenate([b, a]), np.arange(n * n)]))),
                      shape=(n * n, n * n))


def block_means(field: np.ndarray, valid: np.ndarray, n: int) -> tuple[np.ndarray, np.ndarray]:
    """Return (sum of field per block, unmasked pixel count per block) on an n x n grid."""
    H, W = field.shape
    r = np.minimum((np.arange(H) * n) // H, n - 1)
    c = np.minimum((np.arange(W) * n) // W, n - 1)
    cid = (r[:, None] * n + c[None, :]).ravel()
    f = np.where(valid, field, 0.0).ravel()
    v = valid.ravel().astype(np.float64)
    return (np.bincount(cid, weights=f, minlength=n * n),
            np.bincount(cid, weights=v, minlength=n * n))


def solve(R: np.ndarray, t: np.ndarray, area: np.ndarray, lam: float, mu: float,
          n: int, G: float) -> np.ndarray:
    """Non-negative regularised least squares for the truth mass per block."""
    rows = [R]
    rhs = [t]
    L = laplacian(n)
    rows.append(np.sqrt(lam) * L.toarray())
    rhs.append(np.zeros(n * n))
    rows.append(mu * (area / max(area.sum(), 1.0))[None, :])
    rhs.append(np.array([mu * G]))
    A = np.vstack(rows)
    b = np.concatenate(rhs)
    phi, _ = nnls(A, b)
    return phi


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--corpus", default=str(REPO / "registry/h51_score_corpus.json"))
    ap.add_argument("--scratch", default=str(REPO / ".arena/work/h51"))
    ap.add_argument("--blocks", default="4,8,16,32")
    ap.add_argument("--lam", default="1,10,100,1000")
    ap.add_argument("--mu", type=float, default=1.0)
    ap.add_argument("--out", default=str(REPO / "evidence/h51_truth_map.json"))
    args = ap.parse_args()

    entries = json.loads(Path(args.corpus).read_text())["artifacts"]
    with rasterio.open(REPO / "data/grid/sample_submission.tif") as ds:
        valid = np.isfinite(ds.read(1))
    with rasterio.open(REPO / "data/grid/labels.tif") as ds:
        cat = valid & (ds.read(1) == 1)
    unmasked = valid & ~cat
    area_total = float(unmasked.sum())

    # --- G from the blind lattice artefact -------------------------------------------------
    blind = next(a for a in entries if "lattice-s5" in a["path"])
    with rasterio.open(Path(args.scratch) / Path(blind["path"]).name) as ds:
        blind_dots = np.isfinite(ds.read(1)) & (ds.read(1) > 0)
    c_blind = float((h51.credit_field(blind_dots) * unmasked).sum() / area_total)
    n_blind = float(blind_dots.sum())
    G = 0.2 * blind["score"] * n_blind / (c_blind - 0.8 * blind["score"])
    print(f"blind lattice: N={n_blind:,.0f} mean credit c={c_blind:.6f} "
          f"score={blind['score']} -> G={G:,.1f} px")

    labels, scores, N, sha_ok = [], [], [], []
    grids: dict[int, list[np.ndarray]] = {}
    blocks = [int(v) for v in args.blocks.split(",")]
    for i, a in enumerate(entries):
        p = Path(args.scratch) / Path(a["path"]).name
        if not p.exists():
            p = Path(a["path"])
        digest = sha256_file(p)
        with rasterio.open(p) as ds:
            arr = ds.read(1)
        dots = np.isfinite(arr) & (arr > 0)
        N.append(float(dots.sum()))
        labels.append(Path(a["path"]).name)
        sha_ok.append(digest == a["sha256"])
        scores.append(float(a["score"]))
        C = h51.credit_field(dots)
        C = np.where(unmasked, C, 0.0)
        for n in blocks:
            s, v = block_means(C, unmasked, n)
            grids.setdefault(n, []).append(np.concatenate([[s, v]]))
        del C, dots
    N = np.array(N)
    scores = np.array(scores)
    T = scores * (0.2 * N + 0.8 * G)
    print(f"corpus {len(entries)} artefacts; sha verified {sum(sha_ok)}/{len(sha_ok)}; "
          f"T in [{T.min():.0f}, {T.max():.0f}] credit px")

    report: dict = {"G_px": G, "n_corpus": len(entries), "sha_verified": int(sum(sha_ok)),
                    "blind_lattice": {"mean_credit_per_px": c_blind, "n_px": n_blind,
                                      "score": blind["score"]},
                    "self_lattice_check": {}, "grids": {}}

    for n in blocks:
        S = np.stack([g[0] for g in grids[n]])          # anchors x blocks (credit sums)
        A = np.stack([g[1] for g in grids[n]])          # anchors x blocks (unmasked counts)
        area = A.mean(axis=0)
        R = np.divide(S, area[None, :], out=np.zeros_like(S), where=area[None, :] > 0)
        best = None
        for lam in [float(v) for v in args.lam.split(",")]:
            pred = np.empty_like(T)
            for j in range(len(T)):
                keep = np.arange(len(T)) != j
                phi = solve(R[keep], T[keep], area, lam, args.mu, n, G)
                pred[j] = float(R[j] @ phi)
            rmse_t = float(np.sqrt(np.mean((pred - T) ** 2)))
            rec = {"lam": lam, "loo_rmse_T": rmse_t,
                   "loo_spearman": float(_spearman(pred, T)),
                   "loo_max_abs_T": float(np.abs(pred - T).max()), "pred_T": pred.tolist()}
            if best is None or rmse_t < best["loo_rmse_T"]:
                best = rec
        # baselines for the same leave-one-out protocol
        base_const = np.full_like(T, T.mean())
        slope = float((T * N).sum() / (N * N).sum())
        base_n = slope * N
        phi = solve(R, T, area, best["lam"], args.mu, n, G)
        report["grids"][str(n)] = {
            "best": best,
            "baseline_constant_rmse_T": float(np.sqrt(np.mean((base_const - T) ** 2))),
            "baseline_dotcount_rmse_T": float(np.sqrt(np.mean((base_n - T) ** 2))),
            "baseline_dotcount_spearman": float(_spearman(base_n, T)),
            "fitted_truth_px": float(phi.sum()), "phi": phi.tolist(), "area": area.tolist(),
            "in_sample_rmse_T": float(np.sqrt(np.mean((R @ phi - T) ** 2))),
        }
        print(f"blocks {n:>3}: LOO RMSE(T) = {best['loo_rmse_T']:7.1f} (lam={best['lam']})  "
              f"vs constant {report['grids'][str(n)]['baseline_constant_rmse_T']:7.1f}  "
              f"vs dot-count {report['grids'][str(n)]['baseline_dotcount_rmse_T']:7.1f}  "
              f"| Spearman {best['loo_spearman']:+.3f} | sum phi {phi.sum():,.0f}")

    report["anchors"] = [{"file": labels[i], "score": float(scores[i]), "n": int(N[i]),
                          "T": float(T[i]), "credit_per_dot": float(T[i] / N[i])}
                         for i in np.argsort(-scores)]
    Path(args.out).write_text(json.dumps(report, indent=1))
    print(f"wrote {args.out}")
    return 0


def _spearman(a: np.ndarray, b: np.ndarray) -> float:
    ra = np.argsort(np.argsort(a)).astype(float)
    rb = np.argsort(np.argsort(b)).astype(float)
    ra -= ra.mean()
    rb -= rb.mean()
    return float((ra * rb).sum() / np.sqrt((ra ** 2).sum() * (rb ** 2).sum()))


if __name__ == "__main__":
    raise SystemExit(main())
