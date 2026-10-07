#!/usr/bin/env python3
"""H51 validation on frozen off-catalogue proxy frames, with matched controls.

Proxy frames (all label sources are *independent of the training catalogue*; none is the
competition's hidden truth):

* ``sgmc_off``  : USGS State Geologic Map Compilation fault traces rasterised on the
                  competition grid, restricted to pixels > 3 px (300 m) from the published
                  catalogue — i.e. exactly the "faults the public catalogue lacks" target.
                  GEMSDOE32 measured this family of instruments as the only one that ranks
                  live leaderboard scores above chance (Spearman +0.54, n = 12).
* ``uniform``   : matched-count uniform-random dots (seeded), the null the candidate must beat.

The scored domain is the unmasked footprint (known-catalogue pixels are excluded, exactly as
the organizers do). Reported quantities: DTI components, coverage of the proxy truth, and
false-positive mass per emitted dot.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
import rasterio
from scipy.ndimage import distance_transform_edt, binary_dilation

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "src"))

from gemsdoe50 import h51  # noqa: E402


def read(path: Path, index: int = 1) -> np.ndarray:
    with rasterio.open(path) as ds:
        return ds.read(index)


def load_frame(layers: Path, repo: Path) -> tuple[np.ndarray, np.ndarray]:
    valid = np.isfinite(read(repo / "data/grid/sample_submission.tif"))
    cat = valid & (read(repo / "data/grid/labels.tif") == 1)
    return valid, cat


def sgmc_off_truth(valid: np.ndarray, cat: np.ndarray, layers: Path, clearance_px: int = 3):
    sgmc = read(layers / "derived_sgmc_faults_100m_u8.tif") > 0
    d_cat = distance_transform_edt(~cat)
    truth = valid & sgmc & (d_cat > clearance_px) & ~cat
    return truth


def matched_uniform(n: int, allowed: np.ndarray, seed: int = 510051) -> np.ndarray:
    rng = np.random.default_rng(seed)
    flat = np.flatnonzero(allowed.ravel())
    pick = rng.choice(flat, size=min(n, flat.size), replace=False)
    out = np.zeros(allowed.shape, bool)
    out.ravel()[pick] = True
    return out


def evaluate(dots: np.ndarray, truth: np.ndarray, domain: np.ndarray) -> dict:
    comp = h51.score_components(truth, dots, domain)
    n = int((dots & domain).sum())
    comp["dots_in_domain"] = n
    comp["dots_outside_domain"] = int(dots.sum()) - n
    comp["tp_per_dot"] = comp["tp"] / n if n else 0.0
    comp["fp_per_dot"] = comp["fp"] / n if n else 0.0
    comp["truth_cells"] = int((truth & domain).sum())
    return comp


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--layers", default=str(REPO / ".arena/work/layers"))
    ap.add_argument("--candidates", nargs="+", required=True,
                    help="TIF paths; the first is the candidate under test")
    ap.add_argument("--incumbent", default=str(REPO / "downloads/gems50-seislin-44709-20261006T2041Z-79e260ae.tif"))
    ap.add_argument("--out", default=str(REPO / "evidence/h51_validation.json"))
    ap.add_argument("--repeats", type=int, default=5)
    args = ap.parse_args()

    layers = Path(args.layers)
    valid, cat = load_frame(layers, REPO)
    domain = valid & ~cat
    truth = sgmc_off_truth(valid, cat, layers)
    print(f"domain {int(domain.sum()):,}  sgmc_off truth {int(truth.sum()):,} px "
          f"({100.0 * truth.sum() / domain.sum():.3f}% of domain)")

    report = {"frame": "sgmc_off (>300 m from catalogue, unmasked domain)",
              "domain_px": int(domain.sum()), "truth_px": int(truth.sum()), "rows": {}}

    paths = [Path(p) for p in args.candidates]
    inc = Path(args.incumbent)
    if inc.exists():
        paths.append(inc)
    for p in paths:
        if not p.exists():
            print(f"missing {p}")
            continue
        a = read(p)
        dots = np.isfinite(a) & (a > 0)
        rep = evaluate(dots, truth, domain)
        rep["_file"] = p.name
        rep["_n_total"] = int(dots.sum())
        report["rows"][p.name] = rep
        print(f"{p.name[:58]:60s} n={rep['_n_total']:7d} DTI={rep['dti']:.4f} "
              f"tp={rep['tp']:9.1f} fp={rep['fp']:9.1f} tp/dot={rep['tp_per_dot']:.4f}")

    allowed = domain & (distance_transform_edt(~cat) > 1.0)
    cand = read(paths[0])
    n_cand = int((np.isfinite(cand) & (cand > 0)).sum())
    uni = []
    for r in range(args.repeats):
        u = matched_uniform(n_cand, allowed, seed=510051 + r)
        uni.append(evaluate(u, truth, domain))
    dti_u = [u["dti"] for u in uni]
    report["uniform_control"] = dict(n=n_cand, dti_mean=float(np.mean(dti_u)),
                                     dti_max=float(np.max(dti_u)), draws=len(uni))
    print(f"uniform control  n={n_cand}  DTI mean {np.mean(dti_u):.4f} max {np.max(dti_u):.4f}")

    # translation control: shift the candidate's dots by a random 5-20 km offset (no wrap)
    rng = np.random.default_rng(510052)
    shifts = []
    for _ in range(args.repeats):
        dr = int(rng.integers(50, 200)) * rng.choice([-1, 1])
        dc = int(rng.integers(50, 200)) * rng.choice([-1, 1])
        sh = np.zeros_like(cand, bool)
        d = np.isfinite(cand) & (cand > 0)
        r0, r1 = max(0, dr), min(cand.shape[0], cand.shape[0] + dr)
        c0, c1 = max(0, dc), min(cand.shape[1], cand.shape[1] + dc)
        sh[r0:r1, c0:c1] = d[r0 - dr:r1 - dr, c0 - dc:c1 - dc]
        shifts.append(evaluate(sh, truth, domain))
    dti_s = [s["dti"] for s in shifts]
    report["translation_control"] = dict(dti_mean=float(np.mean(dti_s)), dti_max=float(np.max(dti_s)),
                                         draws=len(shifts))
    print(f"translation ctrl DTI mean {np.mean(dti_s):.4f} max {np.max(dti_s):.4f}")

    cand_rep = report["rows"][paths[0].name]
    gate = dict(
        beats_uniform=bool(cand_rep["dti"] > np.max(dti_u)),
        beats_translation=bool(cand_rep["dti"] > np.max(dti_s)),
    )
    inc_key = inc.name
    if inc_key in report["rows"]:
        gate["beats_incumbent"] = bool(cand_rep["dti"] > report["rows"][inc_key]["dti"])
        gate["incumbent_dti"] = report["rows"][inc_key]["dti"]
    report["gate"] = gate
    report["gate"]["all_pass"] = bool(all(v for k, v in gate.items() if isinstance(v, bool)))
    Path(args.out).write_text(json.dumps(report, indent=1))
    print(json.dumps(gate, indent=1))
    print(f"wrote {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
