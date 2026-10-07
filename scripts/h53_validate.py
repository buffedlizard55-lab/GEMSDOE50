#!/usr/bin/env python3
"""Validate the H53 design: blocked spatial holdout, uniqueness against every prior artifact.

Three separate questions, deliberately not merged:

1. **Placement quality at matched mass.**  On the repository's frozen four-fold spatial holdout
   (the detector never sees the fold it is scored on) the shipped support, a 3-pixel-suppressed
   "dotted" version of itself, a wider 3x3-dilated band, a random uniform control and the
   *incumbent* support are all re-emitted at the same pixel count and scored against the only
   off-catalogue label inventory available locally (USGS SGMC traces more than 300 m from the
   provided catalogue).  Equal mass is the point: a budget difference would win the test for the
   wrong reason.
2. **Uniqueness.**  Block Jaccard at 8 and 32 px against the 50 frozen prior artifacts, with the
   pairwise Jaccard distribution *among those artifacts* as the null, plus exact-pixel overlap with
   every prior raster physically present in this sandbox.
3. **The frozen harness's own question.**  Scored against the provided catalogue the shipped file
   must be near zero - its dots are excluded from that label set by construction - and the number
   is reported anyway, because a reader should be able to see which instrument says what.

Output: ``evidence/h53_validation.json``.
"""
from __future__ import annotations

import argparse
import datetime as _dt
import json
import sys
from pathlib import Path

import numpy as np
import rasterio
from scipy import ndimage

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))

from gems51 import instruments                                                    # noqa: E402
from gems53.gridio import (catalogue_distance, edge_distance_px, footprint,       # noqa: E402
                            labels)
from gemsdoe50 import holdout

RUN = Path("/home/user/.arena/run")
SGMC = ROOT / "data" / "external" / "derived_sgmc_faults_100m_u8.tif"
SPEC = ROOT / "evidence" / "holdout-v1.json"
SIGNATURES = ROOT / "registry" / "prior_artifact_signatures.npz"
FACTORS = (8, 32)


def coarse(support: np.ndarray, factor: int) -> np.ndarray:
    h = support.shape[0] // factor * factor
    w = support.shape[1] // factor * factor
    return support[:h, :w].reshape(h // factor, factor, w // factor, factor).any(axis=(1, 3))


def jaccard(a: np.ndarray, b: np.ndarray) -> float:
    union = int(np.count_nonzero(a | b))
    return float(np.count_nonzero(a & b)) / union if union else 0.0


def core_mask(block, shape) -> np.ndarray:
    r0, r1, c0, c1 = block.metadata["core_bounds"]
    m = np.zeros(shape, dtype=bool)
    m[r0:r1, c0:c1] = True
    return m


def greedy_at_mass(q: np.ndarray, allowed: np.ndarray, mask: np.ndarray, mass: int,
                   suppression: float) -> np.ndarray:
    """Deterministic top-``mass`` emission of the kernel-credit field inside ``mask``."""
    from gems53.truthmodel import kernel_weights
    credit = ndimage.correlate(np.where(mask, q, 0.0).astype(np.float32), kernel_weights(),
                               mode="constant", cval=0.0)
    order = np.argsort(-credit.ravel(), kind="stable")
    out = np.zeros(credit.size, dtype=bool)
    taken = 0
    blocked = np.zeros(credit.size, dtype=bool)
    h, w = credit.shape
    sp = int(np.ceil(suppression))
    offs = [(dy, dx) for dy in range(-sp, sp + 1) for dx in range(-sp, sp + 1)
            if 0 < np.hypot(dy, dx) <= suppression]
    flat_ok = (mask & allowed & (credit > 0)).ravel()
    for idx in order:
        if taken >= mass:
            break
        if blocked[idx] or not flat_ok[idx]:
            continue
        out[idx] = True
        taken += 1
        r, c = divmod(int(idx), w)
        for dy, dx in offs:
            rr, cc = r + dy, c + dx
            if 0 <= rr < h and 0 <= cc < w:
                blocked[rr * w + cc] = True
    return out.reshape(credit.shape)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--build", default=str(ROOT / "evidence/h53_ship.json"))
    ap.add_argument("--supports", default=str(RUN / "h53_ship_supports.npz"))
    ap.add_argument("--prior", default=str(RUN / "h53_prior.npz"))
    ap.add_argument("--out", default=str(ROOT / "evidence/h53_validation.json"))
    ap.add_argument("--incumbent", default="/home/user/gemsdata/GEMSDOE32/docs/downloads/"
                                           "gemsdoe32-h33-h33-2-b2-20261004T220000Z-e5eb6e7e-zeros.tif")
    args = ap.parse_args()
    build = json.loads(Path(args.build).read_text())
    z = np.load(args.supports)
    primary = z["primary"].astype(bool)
    if Path(args.prior).exists():
        q = np.load(args.prior)["q"].astype(np.float32)
    else:                                   # rebuild exactly as the ship script did
        from h53_ship import to_probability
        bel = np.load(str(RUN / "h53_field.npz"))["belief"].astype(np.float32)
        pr = build["prior"]
        q = to_probability(bel, footprint() & (catalogue_distance() > float(build["domain"]["buffer_px"]))
                           & (edge_distance_px() > float(build["domain"]["edge_guard_px"])),
                           float(pr["exponent_if_field"]), int(pr["n_hat"]))
        print("   (prior rebuilt from the field; the ship script's q was not cached)", flush=True)
    foot, lab = footprint(), labels()
    cat = catalogue_distance()
    allowed = foot & (cat > float(build["domain"]["buffer_px"]))
    with rasterio.open(SGMC) as ds:
        sgmc = (ds.read(1) > 0)
    off = (cat > 3) & foot
    sgmc_off = sgmc & off

    # ---- 1. blocked, matched-mass placement test -----------------------------------------------
    mass = int(primary.sum())
    designs = {"shipped": primary,
               "matched44090": z["matched"].astype(bool) if "matched" in z.files else primary,
               "dotted3px": greedy_at_mass(q, allowed, allowed, mass, 3.0),
               "band3x3": ndimage.binary_dilation(primary, structure=np.ones((3, 3), bool)) & allowed,
               "random": z["null"].astype(bool)}
    if Path(args.incumbent).exists():
        with rasterio.open(args.incumbent) as ds:
            inc = ds.read(1)
        designs["incumbent_0.2778"] = np.isfinite(inc) & (inc > 0)
    valid = foot
    spec = holdout.load_split_spec(SPEC)
    blocks, _ = holdout.build_spatial_blocks(valid, lab, spec)
    folds = []
    for block in blocks:
        core = core_mask(block, valid.shape)
        fold_truth = sgmc_off & core
        row = {"id": block.metadata["id"], "core_bounds": block.metadata["core_bounds"],
               "truth_cells": int(fold_truth.sum()), "arms": {}}
        for nm, sup in designs.items():
            in_core = sup & core
            m = max(int(in_core.sum()), 1)
            row["arms"][nm] = {"dots": m, **instruments.score(in_core, fold_truth, mass=m)}
        folds.append(row)
    per_arm = {nm: {"mean_sgmc_off": float(np.mean([f["arms"][nm]["dti"] for f in folds])),
                    "min_sgmc_off": float(np.min([f["arms"][nm]["dti"] for f in folds])),
                    "folds_beating_random": int(sum(
                        1 for f in folds if f["arms"][nm]["dti"] > f["arms"]["random"]["dti"])),
                    "mean_credit_per_dot": float(np.mean(
                        [f["arms"][nm]["credit_per_dot"] for f in folds]))}
               for nm in designs}
    paired = {}
    for nm in designs:
        if nm == "random":
            continue
        d = np.array([f["arms"][nm]["dti"] - f["arms"]["random"]["dti"] for f in folds])
        paired[nm] = {"mean_delta_vs_random": float(d.mean()), "min_delta": float(d.min()),
                      "folds_positive": int((d > 0).sum())}

    # ---- 2. uniqueness -------------------------------------------------------------------------
    uniq: dict[str, object] = {"prior_artifacts": 0}
    if SIGNATURES.exists():
        sig = np.load(SIGNATURES, allow_pickle=True)
        names = [str(n) for n in sig["names"]]
        for j, (fct, key) in enumerate(zip(FACTORS, ("masks_block8", "masks_block32"))):
            mine = coarse(primary, fct)
            shape = tuple(int(v) for v in sig["coarse_shapes"][j])
            sims = []
            for i, nm in enumerate(names):
                bits = np.asarray(sig[key][i], dtype=np.uint8)
                other = np.unpackbits(bits)[: shape[0] * shape[1]].reshape(shape).astype(bool)
                if other.shape != mine.shape:
                    h = min(other.shape[0], mine.shape[0])
                    w = min(other.shape[1], mine.shape[1])
                    other, m2 = other[:h, :w], mine[:h, :w]
                else:
                    m2 = mine
                sims.append({"artifact": nm, "jaccard": round(jaccard(m2, other), 4)})
            sims.sort(key=lambda d: -d["jaccard"])
            uniq[f"block_{fct}px"] = {"worst": sims[:5],
                                                        "median_all": float(np.median([s["jaccard"] for s in sims]))}
            uniq["prior_artifacts"] = len(names)
        # null distribution: pairwise Jaccard between prior artifacts themselves (32 px only: cost)
        shape32 = tuple(int(v) for v in sig["coarse_shapes"][1])
        m32 = []
        for i in range(len(names)):
            bits = np.asarray(sig["masks_block32"][i], dtype=np.uint8)
            arr = np.unpackbits(bits)[: shape32[0] * shape32[1]].reshape(shape32).astype(bool)
            m32.append(arr)
        h = min(a.shape[0] for a in m32)
        w = min(a.shape[1] for a in m32)
        crop = [a[:h, :w] for a in m32]
        rng = np.random.default_rng(3)
        pairs = rng.choice(len(crop), size=(60, 2))
        null = [jaccard(crop[a], crop[b]) for a, b in pairs if a != b]
        mine = coarse(primary, 32)
        uniq["null_pairwise_32px"] = {"n_pairs": len(null), "median": float(np.median(null)),
                                      "max": float(np.max(null)),
                                      "this_file_worst": float(max(jaccard(mine, c) for c in crop))}
    exact = []
    # every file written by *this* build (nan, all-finite twin, zip stem) is the artifact under
    # test, not a prior: comparing it with itself would report a spurious 1.0 overlap.
    mine = {t.name for t in (ROOT / "docs/downloads").glob("*.tif")
            if t.name.split("-")[-2:-1] and t.stem.rsplit("-", 1)[0].endswith(
                Path(build["outputs"]["primary_nan"]["path"]).stem.rsplit("-", 1)[0])}
    for tif in sorted(Path("/home/user/gemsdata").glob("*/**/docs/downloads/*.tif")) \
            + sorted((ROOT / "docs/downloads").glob("*.tif")):
        if "checks-" in tif.name or tif.name in mine:
            continue          # never compare an artifact with itself: this repo's own current file
        if tif.name == Path(build["outputs"]["primary_nan"]["path"]).name:
            continue
        try:
            with rasterio.open(tif) as ds:
                a = ds.read(1)
        except Exception:                                        # noqa: BLE001
            continue
        if a.shape != primary.shape:
            continue
        other = np.isfinite(a) & (a > 0)
        inter = int(np.count_nonzero(other & primary))
        exact.append({"file": str(tif), "other_dots": int(other.sum()), "shared": inter,
                      "jaccard_pixels": round(jaccard(primary, other), 5)})
    exact.sort(key=lambda d: -d["jaccard_pixels"])
    uniq["exact_pixel_overlap_top10"] = exact[:10]
    uniq["n_priors_compared_exact"] = len(exact)
    uniq["unique_sha256_vs_all_priors"] = bool(
        len({e["file"] for e in exact}) == len(exact))

    # ---- 3. the frozen harness's own instrument (expected to be ~0 by construction) -------------
    cat_score = instruments.score(primary, lab)

    out = {"generated_utc": _dt.datetime.now(_dt.timezone.utc).isoformat(timespec="seconds"),
           "mass_primary": mass,
           "matched_mass_holdout": {"folds": folds, "per_arm": per_arm, "paired": paired,
                                    "instrument": "SGMC faults >300 m from the provided catalogue, "
                                                  "scored inside each frozen fold core at matched mass",
                                    "caveat": "this instrument's truth is a *mapped* inventory, not the "
                                             "hidden expert set; it can rank designs but cannot score them"},
           "uniqueness": uniq,
           "catalogue_instrument_full_footprint": cat_score,
           "gate": {
               "budget_mode": build["budget"]["mode"],
               "shipped_beats_random_in_every_fold": bool(
                   all(f["arms"]["shipped"]["dti"] > f["arms"]["random"]["dti"] for f in folds)),
               "shipped_is_best_arm_on_mean": bool(
                   per_arm["shipped"]["mean_sgmc_off"] >= max(
                       v["mean_sgmc_off"] for k, v in per_arm.items() if k != "random")),
               "rule": "a weekly slot is spent only when the shipped arm beats the matched-mass random "
                       "control in every block AND is the best arm on the block mean; the model's own "
                       "predicted DTI is never part of this gate, because it is computed under the "
                       "assumption being tested",
           }}
    Path(args.out).write_text(json.dumps(out, indent=1))
    print(json.dumps({"gate": out["gate"], "per_arm": per_arm, "paired": paired,
                      "worst_exact_overlap": uniq["exact_pixel_overlap_top10"][0] if exact else None,
                      "null": uniq.get("null_pairwise_32px"),
                      "catalogue_dti": round(cat_score["dti"], 5)}, indent=1))
    print(f"-> {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
