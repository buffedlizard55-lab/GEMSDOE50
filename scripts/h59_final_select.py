"""Final H59 selection: emitter lattice, catalogue-mask handling, and mass.

Two things are decided here and nothing else.

1. *Mask handling.*  DrivenData staff ruled that pixels of the known USGS/INGENIOUS
   faults are excluded from evaluation and do not count towards the penalty terms
   (forum 11516, post 2), and that new-fault truth can occur within 300 m of a known
   trace.  A suppressed buffer around the catalogue therefore throws away dots that
   can still earn credit and saves nothing.  Measured here: buffer 0 (exclude only
   the masked pixels themselves) against buffers 1 and 3.

2. *Mass.*  The optimum dot count scales with the hidden truth mass, which is not
   known.  The field's coverage fraction c(N) = T(N)/G is measured on the frozen
   matched frame and then transferred -- "the same fraction of the truth is covered"
   -- to a grid of plausible hidden masses.  The mass that minimises the worst-case
   regret over that grid is frozen.  The transfer assumption is stated, not hidden.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from gems59 import features as FE  # noqa: E402
from gems59 import frames as FR  # noqa: E402
from gems59.metric import evaluate  # noqa: E402

SEED = 20261007
MASS_GRID = [60_000, 80_000, 120_000, 180_000, 250_000, 320_000, 400_000]
LATTICE_TESTS = [2, 3, 4]
BUFFER_TESTS = [0, 1, 3]
G_GRID = [4_000, 6_000, 8_000, 12_000, 16_000, 24_000, 36_000, 52_219]
UNIFORM_SEEDS = (11, 22, 33, 44, 55)
FIELD_NAME = "o19grad+lidar7"


def rank_of(cube, idx, name, footprint):
    return FE.rank_normalise(np.asarray(cube[:, :, idx[name]], dtype=np.float32), footprint)


def blend(parts, footprint):
    acc = np.zeros(footprint.shape, np.float32)
    cnt = np.zeros(footprint.shape, np.float32)
    for p in parts:
        g = np.isfinite(p)
        acc[g] += p[g]
        cnt[g] += 1
    return np.where(cnt > 0, acc / np.maximum(cnt, 1), np.nan).astype(np.float32)


def hex3(field, elig, n, rng, k=3):
    bh, bw = field.shape[0] // k, field.shape[1] // k
    sub = np.where(elig[: bh * k, : bw * k], np.nan_to_num(field[: bh * k, : bw * k], nan=-np.inf), -np.inf)
    view = sub.reshape(bh, k, bw, k).transpose(0, 2, 1, 3).reshape(bh, bw, k * k)
    mx, arg = view.max(axis=2), view.argmax(axis=2)
    flat = mx.ravel()
    pool = np.flatnonzero(np.isfinite(flat))
    if len(pool) < n:
        raise SystemExit(f"pool {len(pool)} < {n}")
    v = flat[pool]
    lo, hi = v.min(), v.max()
    p = (v - lo) / (hi - lo) if hi > lo else np.ones_like(v)
    p = (p + 1e-6) / (p + 1e-6).sum()
    chosen = rng.choice(pool, size=n, replace=False, p=p)
    br, bc = np.unravel_index(chosen, (bh, bw))
    off = arg[br, bc]
    out = np.zeros(field.shape, bool)
    out[br * k + off // k, bc * k + off % k] = True
    return out


def main() -> int:
    from scipy import ndimage

    work = Path(".arena/h59")
    labels, footprint = FR.load_labels()
    positives = labels == 1
    d_cat = ndimage.distance_transform_edt(~positives)
    truth = np.load(".arena/h59/truth_Smat.npy") & footprint
    G = int(truth.sum())
    fold, fold_names = FR.macrofolds(footprint)
    meta = json.loads((work / "feature_names.json").read_text())
    idx = {n: i for i, n in enumerate(meta["names"])}
    cube = np.load(work / "features.npy", mmap_mode="r")
    field = blend(
        [
            rank_of(cube, idx, "o19_gradmag", footprint),
            FE.rank_normalise(
                blend([rank_of(cube, idx, f"lidar{i:02d}", footprint) for i in range(2, 9)], footprint),
                footprint,
            ),
        ],
        footprint,
    )

    out: dict[str, object] = {"field": FIELD_NAME, "frame": "S_matched", "truth_px": G,
                              "seed": SEED, "sweeps": {}}

    print("== catalogue-mask buffer sweep at N=250,000, k=3 ==")
    for buf in BUFFER_TESTS:
        elig = footprint & (d_cat > buf)
        pred = hex3(field, elig, 250_000, np.random.default_rng(SEED))
        parts = evaluate(pred.astype(np.float32), truth)
        out["sweeps"].setdefault("buffer", {})[str(buf)] = {
            "eligible": int(elig.sum()), "dti": parts.dti, "tp_w": parts.tp_w,
            "fp_w": parts.fp_w, "fn_w": parts.fn_w,
        }
        print(f"  buffer {buf} px: eligible={int(elig.sum()):,d} DTI={parts.dti:.5f} "
              f"TPw={parts.tp_w:.0f} FPw={parts.fp_w:.0f} FNw={parts.fn_w:.0f}")

    print("== lattice sweep at N=250,000, buffer 0 ==")
    elig0 = footprint & (d_cat > 0)
    for k in LATTICE_TESTS:
        pred = hex3(field, elig0, 250_000, np.random.default_rng(SEED), k=k)
        parts = evaluate(pred.astype(np.float32), truth)
        out["sweeps"].setdefault("lattice", {})[str(k)] = {
            "dti": parts.dti, "tp_w": parts.tp_w, "fp_w": parts.fp_w, "fn_w": parts.fn_w,
            "painted": int(pred.sum()),
        }
        print(f"  k={k}: painted={int(pred.sum()):,d} DTI={parts.dti:.5f} "
              f"TPw={parts.tp_w:.0f} FPw={parts.fp_w:.0f}")

    print("== coverage curve for the mass decision (k=3, buffer 0) ==")
    cov: dict[str, float] = {}
    uni_by_n: dict[int, float] = {}
    pool_idx = np.flatnonzero(elig0.ravel())
    for n in MASS_GRID:
        pred = hex3(field, elig0, n, np.random.default_rng(SEED))
        parts = evaluate(pred.astype(np.float32), truth)
        cov[str(n)] = parts.tp_w / G
        uv = []
        for s in UNIFORM_SEEDS:
            i = np.random.default_rng(s).choice(pool_idx, n, replace=False)
            u = np.zeros(elig0.size, bool)
            u[i] = True
            uv.append(evaluate(u.reshape(elig0.shape).astype(np.float32), truth).dti)
        uni_by_n[n] = float(np.mean(uv))
        print(f"  N={n:>7,d} c(N)=TPw/G={cov[str(n)]:.4f} DTI={parts.dti:.5f} "
              f"uniform={uni_by_n[n]:.5f} lift={parts.dti/uni_by_n[n]:.3f}")
    out["coverage_curve"] = cov
    out["uniform_by_mass"] = {str(k): v for k, v in uni_by_n.items()}

    # ---- mass decision under the coverage-transfer assumption ----------------
    table: dict[str, dict[str, float]] = {}
    for g in G_GRID:
        row = {}
        for n in MASS_GRID:
            t = g * cov[str(n)]
            row[str(n)] = t / (0.2 * n + 0.8 * g + 0.2 * t)
        table[str(g)] = row
    mean_row = {str(n): float(np.mean([table[str(g)][str(n)] for g in G_GRID])) for n in MASS_GRID}
    # regret = best achievable on that row minus what we get
    regret = {str(n): 0.0 for n in MASS_GRID}
    for g in G_GRID:
        best = max(table[str(g)].values())
        for n in MASS_GRID:
            regret[str(n)] += best - table[str(g)][str(n)]
    regret = {k: v / len(G_GRID) for k, v in regret.items()}
    best_mean = max(mean_row, key=lambda k: mean_row[k])
    best_minimax = min(regret, key=lambda k: regret[k])
    out["mass_decision"] = {"table": table, "mean_by_mass": mean_row,
                            "mean_regret_by_mass": regret,
                            "best_mean": best_mean, "best_minimax_regret": best_minimax}
    print("== mass decision (model DTI by assumed hidden mass G) ==")
    hdr = "      G | " + " | ".join(f"{n:>7,d}" for n in MASS_GRID)
    print(hdr)
    for g in G_GRID:
        print(f"{g:>7,d} | " + " | ".join(f"{table[str(g)][str(n)]:.4f}" for n in MASS_GRID))
    print("mean   | " + " | ".join(f"{mean_row[str(n)]:.4f}" for n in MASS_GRID))
    print("regret | " + " | ".join(f"{regret[str(n)]:.4f}" for n in MASS_GRID))
    print(f"best mean = {best_mean}   best minimax-regret = {best_minimax}")

    Path("evidence/h59_final_select.json").write_text(json.dumps(out, indent=1))
    print("wrote evidence/h59_final_select.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
