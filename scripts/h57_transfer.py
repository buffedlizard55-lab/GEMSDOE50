"""H57 transfer calibration — which offline frame actually predicts the score?

The repository has never had a *validated* offline objective. `evidence/
h51_proxy_ranking_power.json` reports Spearman rho = +0.196 (p = 0.35) between
the F1 (SGMC-off-catalogue) proxy DTI and 25 real public-leaderboard scores —
no demonstrated power, and every H52/H56 decision was nevertheless taken on that
frame.

This script re-tests the question on the byte-verified score corpus, for **two**
frames and for the metric's own credit-per-dot statistic.

The exact published metric keeps truth-side credit ``T = TP_w`` separate from
prediction-side matched credit ``M = sum_x max_g k(d(x,g))``. With ``N`` predicted
cells and ``G`` truth cells, ``DTI = T / (0.2 N + 0.8 G + 0.2(T-M))`` (plus
epsilon). The shorter ``T/(0.2N + 0.8G)`` form requires ``T=M``; a 3 px minimum
prediction spacing does not establish that condition.

The script reports exact local-frame pixel counts, nearest-neighbour distances, and
proxy components. Its hidden-credit and ``G`` inversion are retained as a **conditional
legacy model** based on the shorter formula. The nested pair (d2.8: 44,090 px @ 0.2600,
contained in b2: 37,654 px @ 0.2778) does not independently validate ``G`` or authenticate
either score-to-file attribution. Any hidden-credit values are model outputs, not score
forecasts. The proxy-rank correlations describe this recorded corpus only.

Usage
-----
    python scripts/h57_transfer.py --prior .arena/prior --out evidence/h57_transfer.json
"""

from __future__ import annotations

import argparse
import glob
import json
import os
import sys

import numpy as np
from scipy import ndimage as ndi

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from h57_frames import build_frames, load_grid

#: Owner-recorded public-leaderboard scores (not organizer receipts).  Keyed by
#: the fixture basename in `.arena/prior`.
SCORES = {
    "g32_h33b2_02778.tif": ("h33-h33-2-b2", 0.2778),
    "anderson_pinn.tif": ("anderson-geothermal-pinn", 0.2750),
    "h36_blind.tif": ("h36-1-rung30-blind-r1", 0.2710),
    "h274_solo.tif": ("h27-4-solo-d28", 0.2708),
    "h32_prethin.tif": ("h32-1-prethin-tip-euler", 0.2649),
    "h33d_stepover.tif": ("h33d-analog-tip-stepover", 0.2632),
    "d28_poisson.tif": ("d28-poisson300m-offcat-44090", 0.2600),
    "d15_dotted.tif": ("dotted-h19-5-d1-5", 0.2477),
    "h19_5.tif": ("h19-5-mirror-group-best", 0.1922),
    "h28_dotted_ridge.tif": ("h28-dotted-ridge", 0.1839),
    "ens12.tif": ("ens12-adopted", 0.1563),
    "dual_union.tif": ("dual-family-union", 0.1560),
    "halo15.tif": ("7GEMSDOE submission (dense)", 0.1563),
    "r7_nms3_dem10_scarp.tif": ("r7-nms3-dem10-scarp", 0.1294),
    "hgb88_topk03.tif": ("gems6-hgb88-topk03", 0.0286),
    "pindrop_nodes.tif": ("pindrop-v4-nodes", 0.1193),
    "pindrop_ridge.tif": ("pindrop-v4-ridge", 0.1152),
    "pindrop_disc.tif": ("pindrop-v4-discovery", 0.0830),
    "lattice_s5.tif": ("r13-lattice-s5-v2", 0.0904),
    "lidarscarp_top2pct.tif": ("lidarscarp-ridge-top2pct", 0.1461),
    "gemsdoe4_combined.tif": ("gemsdoe4-combined", 0.0343),
}


def nn_spacing(pos: np.ndarray) -> float:
    """Minimum nearest-neighbour spacing (px) among positive pixels.

    A distance transform cannot be used here: the EDT of ``~pos`` is 0 at every
    positive pixel, so its minimum over the support is 0 for any non-empty set.
    The second-nearest neighbour in a k-d tree is exact.
    """
    n = int(pos.sum())
    if n < 2:
        return float("inf")
    from scipy.spatial import cKDTree

    r, c = np.nonzero(pos)
    tree = cKDTree(np.column_stack([r, c]))
    d, _ = tree.query(np.column_stack([r, c]), k=2, workers=-1)
    return float(d[:, 1].min())


def is_well_spaced(pos: np.ndarray, r: float = 3.0) -> bool:
    """Whether minimum prediction-to-prediction Euclidean distance is at least ``r``.

    This operational threshold does not mean kernel footprints are disjoint, does not
    establish equality of truth-side and prediction-side credit, and does not validate
    the simplified hidden-score equation used by the legacy model below.
    """
    return nn_spacing(pos) >= r


def overlap_fraction(pos: np.ndarray, r: int = 3) -> float:
    """Fraction of positive cells with another positive in a square r-neighbourhood.

    This is a local-clustering diagnostic, not an exact test of shared radial-kernel
    support or of equality between directional metric credits.
    """
    if pos.sum() == 0:
        return 0.0
    k = np.ones((2 * r + 1, 2 * r + 1), dtype=np.uint8)
    k[r, r] = 0
    n = ndi.convolve(pos.astype(np.uint8), k, mode="constant")
    return float(((n > 0) & pos).sum() / pos.sum())


def credit_per_dot(pos: np.ndarray, frame) -> tuple[float, int]:
    """Mean local-kernel credit per prediction inside a proxy frame."""
    active = pos & frame.domain
    count = int(active.sum())
    if count == 0:
        return float("nan"), 0
    return float(np.nansum(frame.K[active])) / count, count


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--prior", default=".arena/prior")
    ap.add_argument("--inputs", default=".arena/inputs")
    ap.add_argument("--labels", default="data/grid/labels.tif")
    ap.add_argument("--sgmc", default="data/external/derived_sgmc_faults_100m_u8.tif")
    ap.add_argument("--out", default="evidence/h57_transfer.json")
    ap.add_argument("--g", type=float, default=14088.75,
                    help="hidden truth mass G (px); default = the nested-pair solve")
    args = ap.parse_args(argv)
    import rasterio

    footprint, catalogue, _transform, _shape = load_grid(args.labels)
    with rasterio.open(args.sgmc) as ds:
        sgmc = ds.read(1) == 1
    with rasterio.open(os.path.join(args.inputs, "lidar_scarp_features_u8.tif")) as ds:
        valid = ds.read(12) > 0

    allf = build_frames(footprint, catalogue, sgmc, valid)
    f1 = allf["F1_sgmc_off"]
    f2 = [allf[k] for k in sorted(allf) if k.startswith("F2_")]

    rows = []
    for path in sorted(glob.glob(os.path.join(args.prior, "*.tif"))):
        base = os.path.basename(path)
        if base not in SCORES:
            continue
        label, score = SCORES[base]
        with rasterio.open(path) as ds:
            a = ds.read(1)
        pos = np.isfinite(a) & (a > 0)
        n = int(pos.sum())
        nnd = nn_spacing(pos)
        ov = overlap_fraction(pos, 3)
        # Conditional legacy inversion only; it assumes T equals predicted-side matched credit.
        t_hidden = score * (0.2 * n + 0.8 * args.g)
        # Frame credits use only predictions visible inside each frame's domain.
        cpd1, _in1 = credit_per_dot(pos, f1)
        c2, _n2 = zip(*(credit_per_dot(pos, fr) for fr in f2))
        rows.append({
            "file": base, "label": label, "score": score, "n_dots": n,
            "min_nn_px": nnd if np.isfinite(nnd) else None,
            "overlap_frac_r3": ov,
            "well_spaced_r3": bool(nnd >= 3.0),
            "T_hidden_at_G": t_hidden,
            "T_over_G": t_hidden / args.g,
            "c_per_dot_hidden": t_hidden / n,
            "c_per_dot_F1": cpd1,
            "c_per_dot_F2": float(np.nanmean(c2)),
            "base_F1": f1.base_c_per_dot,
            "base_F2": float(np.mean([fr.base_c_per_dot for fr in f2])),
        })

    rep = {"generated_utc": None, "G": args.g,
           "G_note": ("G = 14,088.75 px is a conditional legacy nested-pair solve using "
                      "the simplified DTI = T/(0.2N + 0.8G) equation. It is not exact unless "
                      "truth-side and prediction-side matched credit are equal; 3 px spacing "
                      "does not establish that, and the public score rows have no TIFF receipt "
                      "crosswalk."),
           "rows": rows}
    _ranks(rep, rows)
    os.makedirs(os.path.dirname(args.out) or ".", exist_ok=True)
    with open(args.out, "w") as fh:
        json.dump(rep, fh, indent=1)
    _print(rows)
    print("wrote", args.out)
    return 0


def _spearman(x, y):
    from scipy import stats
    r = stats.spearmanr(x, y)
    return float(r.statistic), float(r.pvalue)


def _ranks(rep, rows):
    ws = [r for r in rows if r["well_spaced_r3"]]
    for tag, sel in (("all", rows), ("well_spaced", ws)):
        if len(sel) < 4:
            continue
        sc = [r["score"] for r in sel]
        for key in ("c_per_dot_F1", "c_per_dot_F2", "c_per_dot_hidden",
                    "n_dots", "c_per_dot_F1_base_normalised",
                    "c_per_dot_F2_base_normalised"):
            if key == "c_per_dot_F1_base_normalised":
                v = [r["c_per_dot_F1"] / r["base_F1"] for r in sel]
            elif key == "c_per_dot_F2_base_normalised":
                v = [r["c_per_dot_F2"] / r["base_F2"] for r in sel]
            else:
                v = [r[key] for r in sel]
            rho, p = _spearman(v, sc)
            rep.setdefault("spearman", {}).setdefault(tag, {})[key] = {
                "rho": rho, "p": p, "n": len(sel)}


def _print(rows):
    print(f"{'artifact':26s} {'score':>6s} {'N':>9s} {'nn':>5s} {'ovl':>5s} "
          f"{'T_hid':>7s} {'T/G':>5s} {'c/dF1':>6s} {'c/dF2':>6s}")
    for r in sorted(rows, key=lambda z: -z["score"]):
        nn = f"{r['min_nn_px']:.2f}" if r["min_nn_px"] else "inf"
        print(f"{r['label'][:26]:26s} {r['score']:6.4f} {r['n_dots']:9d} {nn:>5s} "
              f"{r['overlap_frac_r3']:5.2f} {r['T_hidden_at_G']:7.0f} "
              f"{r['T_over_G']:5.2f} {r['c_per_dot_F1']:6.4f} {r['c_per_dot_F2']:6.4f}")


if __name__ == "__main__":
    raise SystemExit(main())
