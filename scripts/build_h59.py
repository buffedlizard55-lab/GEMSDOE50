#!/usr/bin/env python3
"""H59 build: mandated seismic-lineation artifact + frozen holdout decision.

Preregistration: ``docs/research/h59-hypotheses-preregistered.md``.

Arms (all scored on the same frozen holdout with the same instrument):

* **H59-S**  up-dip seismic corridors snapped to the H57 ridge (``src/gemsdoe50/h59.py``);
  eligible cells exclude the prior-positive union *and* every positive pixel of
  the H56/H57/H58 files, so exact overlap with any registered prior is zero by
  construction. Controls at matched mass: density supports (sigma 1 / 2 km) and
  corridor geometry translated by 10 km, both with the identical ridge
  emission; H57 at matched mass; matched uniform random.
* **H59-H**  hybrid: the corridor-snapped dots replace H57's lowest-ranked dots
  at the incumbent's 80,000 mass.
* **H59-M**  H57's own field re-emitted at Chebyshev spacing 4 and 5 px (the
  repo believed 3 px was competition-free; it is not, see section 1 of the
  preregistration).

Frames: A = SGMC-off proxy inside the four frozen macrofold cores
(``evidence/holdout-v1.json``); B = the supplied catalogue withheld per
macrofold (the prompt's "predict withheld faults better than density").

Scoring uses a vectorised implementation of the repository's
``distance_weighted_tversky`` (one distance transform per arm); every pooled
score is cross-checked against ``distance_weighted_tversky`` itself and the run
aborts on any disagreement above 1e-9.
"""
from __future__ import annotations

import argparse
import glob
import hashlib
import json
import subprocess
import sys
import time
import zipfile
from pathlib import Path
from typing import Any

import numpy as np
import rasterio
from scipy import ndimage

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "src"))
sys.path.insert(0, str(REPO / "scripts"))

import build_h57

from gemsdoe50 import h59
from gemsdoe50.common import sha256_file
from gemsdoe50.holdout import build_spatial_blocks, load_split_spec
from gemsdoe50.metric import distance_weighted_tversky

R_PX = 3.0
ALPHA, BETA = 0.2, 0.8
INCUMBENT_MASS = 80_000
BOOTSTRAP_REPLICATES = 5_000
BOOTSTRAP_SEED = 55_007
TRANSLATIONS_M = ((10_000.0, 0.0), (-10_000.0, 0.0), (0.0, 10_000.0), (0.0, -10_000.0))
SPACINGS = (4, 5)


# --------------------------------------------------------------------------- scoring
class FastScorer:
    """Exact DTI components for binary predictions, one EDT per prediction."""

    def __init__(self, truth: np.ndarray):
        self.truth = truth
        d = ndimage.distance_transform_edt(~truth)
        self.k = np.clip(1.0 - d / R_PX, 0.0, 1.0)

    @staticmethod
    def best(pred: np.ndarray) -> np.ndarray:
        if not pred.any():
            return np.zeros(pred.shape)
        return np.clip(1.0 - ndimage.distance_transform_edt(~pred) / R_PX, 0.0, 1.0)

    def components(self, pred: np.ndarray, best: np.ndarray, truth_eval: np.ndarray | None,
                   pred_eval: np.ndarray | None) -> dict[str, float]:
        te = self.truth if truth_eval is None else (self.truth & truth_eval)
        pe = pred if pred_eval is None else (pred & pred_eval)
        b = best[te]
        tp = float(b.sum())
        fn = float((1.0 - b).sum())
        fp = float((1.0 - self.k[pe]).sum())
        n = int(pe.sum())
        g = int(te.sum())
        score = tp / (tp + ALPHA * fp + BETA * fn + 1e-9)
        return {"score": score, "tp": tp, "fp": fp, "fn": fn, "n": n, "g": g,
                "credit_per_dot": tp / max(n, 1)}


def _official(truth: np.ndarray, pred: np.ndarray, truth_eval=None, pred_eval=None) -> float:
    return float(distance_weighted_tversky(truth, pred.astype(np.float32),
                                           truth_eval_mask=truth_eval,
                                           prediction_eval_mask=pred_eval).score)


# --------------------------------------------------------------------------- helpers
def _mask_from(rows: np.ndarray, cols: np.ndarray, shape) -> np.ndarray:
    m = np.zeros(shape, dtype=bool)
    if rows.size:
        m[rows, cols] = True
    return m


def _read_positive(path: str) -> np.ndarray:
    with rasterio.open(path) as ds:
        a = ds.read(1)
    return np.isfinite(a) & (a > 0)


def _git(*args: str) -> str | None:
    try:
        return subprocess.run(["git", *args], cwd=REPO, check=True, capture_output=True,
                              text=True).stdout.strip()
    except Exception:  # noqa: BLE001
        return None


def _write_tiff(template: Path, dest: Path, support: np.ndarray, valid: np.ndarray, *,
                zero_outside: bool) -> dict[str, Any]:
    with rasterio.open(template) as src:
        profile = src.profile.copy()
    data = np.where(support, 1.0, 0.0).astype(np.float32)
    if zero_outside:
        profile.update(dtype="float32", count=1, nodata=None, compress="deflate", predictor=2)
    else:
        data = np.where(valid, data, np.nan).astype(np.float32)
        profile.update(dtype="float32", count=1, nodata=float("nan"), compress="deflate",
                       predictor=2)
    with rasterio.open(dest, "w", **profile) as dst:
        dst.write(data, 1)
    with rasterio.open(dest) as chk:
        back = chk.read(1)
        finite = back[np.isfinite(back)]
        meta = {
            "path": str(dest.relative_to(REPO)),
            "sha256": sha256_file(dest),
            "bytes": dest.stat().st_size,
            "dtype": str(chk.dtypes[0]),
            "crs": str(chk.crs),
            "shape": list(chk.shape),
            "transform": list(chk.transform)[:6],
            "nodata": None if chk.nodata is None else str(chk.nodata),
            "min": float(finite.min()),
            "max": float(finite.max()),
            "positive_cells": int((back > 0).sum()),
            "nan_cells": int(np.isnan(back).sum()),
            "nan_inside_footprint": int(np.isnan(back[valid]).sum()),
        }
    if meta["min"] < 0.0 or meta["max"] > 1.0 or meta["nan_inside_footprint"] != 0:
        raise ValueError(f"range/NaN guard failed for {dest}: {meta}")
    return meta


def _bootstrap(values: list[float]) -> dict[str, Any]:
    v = np.asarray(values, dtype=np.float64)
    rng = np.random.default_rng(BOOTSTRAP_SEED)
    s = v[rng.integers(0, v.size, size=(BOOTSTRAP_REPLICATES, v.size))].mean(axis=1)
    return {"mean": float(v.mean()), "ci95": [float(np.quantile(s, 0.025)), float(np.quantile(s, 0.975))],
            "replicates": BOOTSTRAP_REPLICATES, "seed": BOOTSTRAP_SEED, "units": len(values)}


def _translate_corridors(cors: list[dict], dx: float, dy: float) -> list[dict]:
    return [{**c, "cx": c["cx"] + dx, "cy": c["cy"] + dy} for c in cors]


def _snap_select(cors, belief, eligible, transform, shape, cap):
    cand = h59.snap_corridor_dots(cors, belief, eligible, transform)
    if cand["rows"].size == 0:
        return np.zeros(shape, dtype=bool), cand, np.zeros(0, dtype=np.int64)
    acc = h59.greedy_spaced(cand["rows"], cand["cols"], cand["vals"], shape, max_dots=cap)
    return _mask_from(cand["rows"][acc], cand["cols"][acc], shape), cand, acc


# --------------------------------------------------------------------------- main
def run(args: argparse.Namespace) -> dict[str, Any]:
    t0 = time.time()

    def log(msg: str) -> None:
        print(f"[{time.time()-t0:7.1f}s] {msg}", flush=True)

    paths = {k: REPO / getattr(args, k) for k in
             ("comcat", "template", "labels", "sgmc", "incumbent", "split", "prior_union")}
    for k, p in paths.items():
        if not p.exists():
            raise FileNotFoundError(f"missing input {k}: {p}")
    hashes = {k: sha256_file(p) for k, p in paths.items()}

    with rasterio.open(paths["template"]) as ds:
        valid = np.isfinite(ds.read(1))
        transform = ds.transform
        shape = ds.shape
    with rasterio.open(paths["labels"]) as ds:
        catalogue = ds.read(1) == 1
    d_cat = ndimage.distance_transform_edt(~catalogue).astype(np.float32)
    domain = valid & (d_cat > R_PX)
    with rasterio.open(paths["sgmc"]) as ds:
        sgmc = ds.read(1) > 0
    truth = domain & sgmc

    with np.load(paths["prior_union"], allow_pickle=False) as z:
        prior_union = np.unpackbits(z["packed"])[: int(np.prod(shape))].astype(bool).reshape(shape)
        if int(prior_union.sum()) != int(z["positive_cells"]):
            raise ValueError("prior union count mismatch")
    g50_files = sorted(set(glob.glob(str(REPO / "docs/downloads/gemsdoe50-h5[678]-*.tif"))))
    g50 = np.zeros(shape, dtype=bool)
    for f in g50_files:
        g50 |= _read_positive(f)
    novel_strict = domain & ~prior_union & ~g50
    novel_h57 = domain & ~prior_union
    log(f"valid={int(valid.sum()):,} domain={int(domain.sum()):,} truth={int(truth.sum()):,} "
        f"prior_union={int(prior_union.sum()):,} g50={int(g50.sum()):,} ({len(g50_files)} files) "
        f"novel_strict={int(novel_strict.sum()):,}")

    # ---- H57 belief (ridge layer for the placement step) --------------------------------
    cache = REPO / args.belief_cache
    lidar = REPO / args.inputs / "lidar_scarp_features_u8.tif"
    topo = REPO / args.inputs / "topo_u8.tif"
    key = hashlib.sha256((sha256_file(lidar) + sha256_file(topo) + hashes["template"]).encode()).hexdigest()
    if cache.exists() and cache.with_suffix(".key").exists() and cache.with_suffix(".key").read_text() == key:
        belief = np.load(cache)
    else:
        belief, _prov = build_h57.belief_field(str(REPO / args.inputs), valid)
        cache.parent.mkdir(parents=True, exist_ok=True)
        np.save(cache, belief)
        cache.with_suffix(".key").write_text(key)
    log("H57 belief ready")

    incumbent = _read_positive(str(paths["incumbent"]))
    reproduce = build_h57.metric_emit(belief, domain, INCUMBENT_MASS)
    reproduction = {
        "incumbent_dots": int(incumbent.sum()),
        "re_emitted_dots": int(reproduce.sum()),
        "identical_support": bool(np.array_equal(reproduce, incumbent)),
        "jaccard": float((reproduce & incumbent).sum() / max((reproduce | incumbent).sum(), 1)),
    }
    incumbent_overlap = {
        "dots_on_prior_union": int((incumbent & prior_union).sum()),
        "fraction_on_prior_union": float((incumbent & prior_union).sum() / max(incumbent.sum(), 1)),
    }
    log(f"H57 reproduction: {reproduction}; incumbent on prior union: {incumbent_overlap}")
    del reproduce

    # ---- H59-S pipeline ------------------------------------------------------------------
    events, ev_report = h59.load_events(paths["comcat"], paths["template"])
    keep_zbz, zbz_report = h59.zbz_decluster(events)
    ev_bg = events.subset(keep_zbz)
    keep_tri, tri_report = h59.triangle_keep(np.column_stack([ev_bg.x, ev_bg.y]))
    ev_cl = ev_bg.subset(keep_tri)
    lins, lin_report = h59.neighbourhood_lineations(ev_cl)
    cors = h59.corridor_geometry(lins)
    log(f"events {len(events):,} -> ZBZ background {len(ev_bg):,} -> triangle {len(ev_cl):,} "
        f"-> lineations {len(lins)} -> corridors {len(cors)}")

    cand_mask, cand, acc = _snap_select(cors, belief, novel_strict, transform, shape, h59.MAX_DOTS)
    mass = int(cand_mask.sum())
    kinds = cand["kind"][acc] if acc.size else np.zeros(0, dtype=np.int8)
    union = h59.corridor_union(cors, shape, transform)
    area = int((union & novel_strict).sum())
    log(f"H59-S: {mass:,} dots (candidates {cand['rows'].size:,}); corridor union "
        f"{int(union.sum()):,} cells, eligible {area:,}")
    if mass == 0:
        raise ValueError("H59-S produced no dots")
    if np.any(cand_mask & ~novel_strict):
        raise ValueError("H59-S support leaves the strict-novel domain")

    # ---- frame A instruments -------------------------------------------------------------
    scorer = FastScorer(truth)
    split_spec = load_split_spec(paths["split"])
    blocks, _realized = build_spatial_blocks(valid, catalogue, split_spec)
    cores = {}
    tiles = []
    for b in blocks:
        r0, r1, c0, c1 = map(int, b.metadata["core_bounds"])
        m = np.zeros(shape, dtype=bool)
        m[r0:r1, c0:c1] = True
        cores[b.block_id] = m
        for tile_id, tr_, tc_, _e, _c in b.subtile_masks:
            t = np.zeros(shape, dtype=bool)
            t[tr_[0]:tr_[1], tc_[0]:tc_[1]] = True
            tiles.append((tile_id, t))

    def frame_a(pred: np.ndarray, check: bool = False) -> dict[str, Any]:
        best = scorer.best(pred)
        pooled = scorer.components(pred, best, None, domain)
        if check:
            off = _official(truth, pred, None, domain)
            if abs(off - pooled["score"]) > 1e-9:
                raise ValueError(f"instrument disagreement {off} vs {pooled['score']}")
            pooled["official_cross_check"] = off
        folds = {bid: scorer.components(pred, best, core, domain & core) for bid, core in cores.items()}
        subt = {tid: scorer.components(pred, best, t, domain & t)["score"] for tid, t in tiles}
        return {"pooled": pooled, "folds": folds, "subtiles": subt}

    arms: dict[str, dict[str, Any]] = {}
    supports: dict[str, np.ndarray] = {}

    def add(name: str, pred: np.ndarray, check: bool = True) -> None:
        arms[name] = frame_a(pred, check=check)
        arms[name]["mass"] = int(pred.sum())
        supports[name] = pred
        log(f"  {name:<34} N={int(pred.sum()):>6,}  DTI {arms[name]['pooled']['score']:.4f}  "
            f"c/dot {arms[name]['pooled']['credit_per_dot']:.4f}")

    add("H57-incumbent-80k", incumbent)
    add("H59-S", cand_mask)
    add("H59-S-support-emit", build_h57.metric_emit(belief, novel_strict & union, mass))
    for sigma in (1_000.0, 2_000.0):
        dens = h59.density_field(ev_bg, shape, transform, sigma)
        sup = h59.top_area_support(dens, novel_strict, area)
        add(f"density-{int(sigma)}m", build_h57.metric_emit(belief, novel_strict & sup, mass))
    for dx, dy in TRANSLATIONS_M:
        tmask, _c, _a = _snap_select(_translate_corridors(cors, dx, dy), belief, novel_strict,
                                     transform, shape, mass)
        add(f"translated-{int(dx/1000)}km-{int(dy/1000)}km", tmask)
    add("H57-matched-mass-strict", build_h57.metric_emit(belief, novel_strict, mass))
    add("H57-matched-mass-domain", build_h57.metric_emit(belief, domain, mass))
    rng = np.random.default_rng(59)
    flat = np.flatnonzero(novel_strict.ravel())
    rnd = np.zeros(shape, dtype=bool)
    rnd.ravel()[rng.choice(flat, size=mass, replace=False)] = True
    add("uniform-random-matched", rnd)

    # ---- H59-H hybrid and H59-M spacing (80k, novel_h57) ---------------------------------
    h57r = build_h57.metric_emit(belief, novel_h57, INCUMBENT_MASS)
    add("H57-reemit-80k-on-novel", h57r)
    hyb_seed, _c, _a = _snap_select(cors, belief, novel_h57, transform, shape, h59.MAX_DOTS)
    blocked = ndimage.binary_dilation(hyb_seed, structure=np.ones((5, 5), dtype=bool))
    fill = build_h57.metric_emit(belief, novel_h57 & ~blocked, INCUMBENT_MASS - int(hyb_seed.sum()))
    add("H59-H-hybrid-80k", hyb_seed | fill)
    for s in SPACINGS:
        add(f"H59-M-spacing{s}-80k", build_h57.metric_emit(belief, novel_h57, INCUMBENT_MASS, spacing=s))

    # ---- frame B: withheld catalogue per macrofold (seismic arms) -------------------------
    frame_b: dict[str, Any] = {}
    sums = {k: {"tp": 0.0, "fp": 0.0, "fn": 0.0} for k in ("H59-S", "density-best", "translated-mean", "H57-matched")}
    dens_fields = {s: h59.density_field(ev_bg, shape, transform, s) for s in (1_000.0, 2_000.0)}
    for bid, core in cores.items():
        cat_out = catalogue & ~core
        elig = valid & core & (ndimage.distance_transform_edt(~cat_out) > R_PX)
        truth_b = catalogue & core
        sc = FastScorer(truth_b)
        cm, _c, _a = _snap_select(cors, belief, elig, transform, shape, h59.MAX_DOTS)
        mf = int(cm.sum())
        row: dict[str, Any] = {"mass": mf, "truth_cells": int(truth_b.sum()), "eligible": int(elig.sum())}
        if mf == 0:
            frame_b[bid] = row
            continue
        a_f = int((union & elig).sum())

        def sco(pred, sc=sc, elig=elig):
            return sc.components(pred, sc.best(pred), None, elig)

        row["H59-S"] = sco(cm)
        dens_rows = {}
        for s, fld in dens_fields.items():
            sup = h59.top_area_support(fld, elig, a_f)
            dens_rows[f"density-{int(s)}m"] = sco(build_h57.metric_emit(belief, elig & sup, mf))
        row["density"] = dens_rows
        best_d = max(dens_rows.values(), key=lambda d: d["score"])
        trans = []
        for dx, dy in TRANSLATIONS_M:
            tm, _c2, _a2 = _snap_select(_translate_corridors(cors, dx, dy), belief, elig, transform, shape, mf)
            trans.append(sco(tm))
        row["translated"] = trans
        row["H57-matched"] = sco(build_h57.metric_emit(belief, elig, mf))
        for k, v in (("H59-S", row["H59-S"]), ("density-best", best_d), ("H57-matched", row["H57-matched"])):
            for c in ("tp", "fp", "fn"):
                sums[k][c] += v[c]
        for c in ("tp", "fp", "fn"):
            sums["translated-mean"][c] += float(np.mean([t[c] for t in trans]))
        frame_b[bid] = row
        log(f"  frame B {bid}: N={mf}  H59-S {row['H59-S']['score']:.4f}  density {best_d['score']:.4f}  "
            f"translated-mean {np.mean([t['score'] for t in trans]):.4f}  H57-matched {row['H57-matched']['score']:.4f}")
    frame_b_pooled = {k: v["tp"] / (v["tp"] + ALPHA * v["fp"] + BETA * v["fn"] + 1e-9) for k, v in sums.items()}

    # ---- diagnostics -----------------------------------------------------------------------
    enrichment = h59.stratified_corridor_enrichment(scorer.k, belief, union, novel_strict)
    kind_rows = {}
    k_at = scorer.k[cand["rows"][acc], cand["cols"][acc]] if acc.size else np.zeros(0)
    for kind, name in enumerate(h59.KIND_NAMES):
        sel = kinds == kind
        kind_rows[name] = {"dots": int(sel.sum()),
                           "mean_K_at_dot": float(k_at[sel].mean()) if sel.any() else None}
    kind_rows["uniform_mean_K_on_novel_strict"] = float(scorer.k[novel_strict].mean())

    # ---- decision gates ----------------------------------------------------------------------
    inc = arms["H57-incumbent-80k"]

    def gates(name: str, seismic: bool) -> dict[str, Any]:
        a = arms[name]
        fold_wins = sum(1 for b in cores if a["folds"][b]["score"] > inc["folds"][b]["score"])
        boot = _bootstrap([a["subtiles"][t] - inc["subtiles"][t] for t, _m in tiles])
        g = {
            "pooled_above_incumbent": a["pooled"]["score"] > inc["pooled"]["score"],
            "fold_wins_vs_incumbent_ge_3": fold_wins >= 3,
            "bootstrap_lower_bound_positive": boot["ci95"][0] > 0,
        }
        if seismic:
            dens_best = max(arms["density-1000m"]["pooled"]["score"], arms["density-2000m"]["pooled"]["score"])
            trans_best = max(arms[k]["pooled"]["score"] for k in arms if k.startswith("translated-"))
            g["pooled_above_best_density"] = a["pooled"]["score"] > dens_best
            g["pooled_above_every_translation"] = a["pooled"]["score"] > trans_best
            g["frame_b_above_density"] = frame_b_pooled["H59-S"] > frame_b_pooled["density-best"]
            g["comcat_rights_resolved"] = False
        return {"gates": g, "fold_wins": fold_wins, "bootstrap_vs_incumbent": boot,
                "numeric_pass": all(v for k, v in g.items() if k != "comcat_rights_resolved"),
                "slot_eligible_pending_uniqueness": all(g.values())}

    decisions = {
        "H59-S": gates("H59-S", True),
        "H59-H-hybrid-80k": gates("H59-H-hybrid-80k", True),
        **{f"H59-M-spacing{s}-80k": gates(f"H59-M-spacing{s}-80k", False) for s in SPACINGS},
    }
    for k, v in decisions.items():
        log(f"decision {k}: numeric_pass={v['numeric_pass']} eligible(pending uniqueness)="
            f"{v['slot_eligible_pending_uniqueness']} gates={v['gates']}")

    # ---- write the H59-S artifact (do-not-submit unless every gate passes) --------------------
    slug = hashlib.sha256(np.packbits(cand_mask.ravel()).tobytes()).hexdigest()[:8]
    stamp = args.stamp or time.strftime("%Y%m%dT%H%M%SZ", time.gmtime())
    out = REPO / args.output_dir
    out.mkdir(parents=True, exist_ok=True)
    stem = f"gemsdoe50-h59-updipseis-{mass}-{stamp}-{slug}"
    zero = _write_tiff(paths["template"], out / f"{stem}-allfinite.tif", cand_mask, valid, zero_outside=True)
    nanm = _write_tiff(paths["template"], out / f"{stem}-nan.tif", cand_mask, valid, zero_outside=False)
    zpath = out / f"{stem}-allfinite.zip"
    # Deterministic archive: a fixed entry timestamp (taken from the stamp) and fixed
    # permissions, so a rebuild with the same --stamp reproduces the zip byte for byte.
    try:
        when = time.strptime(stamp, "%Y%m%dT%H%M%SZ")[:6]
    except ValueError:
        when = (1980, 1, 1, 0, 0, 0)
    info = zipfile.ZipInfo(f"{stem}-allfinite.tif", date_time=when)
    info.compress_type = zipfile.ZIP_DEFLATED
    info.external_attr = 0o644 << 16
    with zipfile.ZipFile(zpath, "w") as zf:
        zf.writestr(info, (out / f"{stem}-allfinite.tif").read_bytes())

    def slim(a: dict[str, Any]) -> dict[str, Any]:
        return {"mass": a["mass"], "pooled": a["pooled"],
                "folds": {b: {"score": v["score"], "credit_per_dot": v["credit_per_dot"], "n": v["n"]}
                          for b, v in a["folds"].items()},
                "subtiles": a["subtiles"]}

    report = {
        "schema": "gemsdoe50.h59-build.v1",
        "generated_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "git_commit": _git("rev-parse", "HEAD"),
        "preregistration": "docs/research/h59-hypotheses-preregistered.md",
        "inputs": {k: {"path": str(p.relative_to(REPO)), "sha256": hashes[k]} for k, p in paths.items()},
        "gemsdoe50_prior_files_excluded": [str(Path(f).relative_to(REPO)) for f in g50_files],
        "masks": {"valid": int(valid.sum()), "domain_gt_300m": int(domain.sum()),
                  "truth_sgmc_off": int(truth.sum()), "prior_union": int(prior_union.sum()),
                  "gemsdoe50_priors": int(g50.sum()), "novel_strict": int(novel_strict.sum()),
                  "novel_h57": int(novel_h57.sum())},
        "h57_reproduction": reproduction,
        "h57_incumbent_prior_union_overlap": incumbent_overlap,
        "pipeline": {"events": ev_report, "zbz": zbz_report, "triangle": tri_report,
                     "lineations": lin_report, "corridors": len(cors),
                     "corridor_union_cells": int(union.sum()), "corridor_union_eligible": area,
                     "snap_candidates": int(cand["rows"].size), "dots": mass,
                     "dots_by_kind": kind_rows},
        "frame_a": {k: slim(v) for k, v in arms.items()},
        "frame_b": {"per_fold": frame_b, "pooled": frame_b_pooled},
        "stratified_corridor_enrichment": enrichment,
        "decisions": decisions,
        "artifact": {"all_finite": zero, "nan_outside": nanm,
                     "zip": {"path": str(zpath.relative_to(REPO)), "sha256": sha256_file(zpath),
                             "bytes": zpath.stat().st_size},
                     "entry_name": f"GEMSDOE50-H59-UPDIPSEIS-{mass}-{slug.upper()}"},
        "seconds": round(time.time() - t0, 1),
    }
    dest = REPO / args.report
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(json.dumps(report, indent=1, sort_keys=False, default=float) + "\n", encoding="utf-8")
    np.savez_compressed(REPO / args.supports_cache,
                        **{k.replace("-", "_"): np.packbits(v.ravel()) for k, v in supports.items()})
    log(f"wrote {dest} and {zero['path']}")
    return report


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--comcat", default="data/external/usgs_comcat_earthquakes.csv.gz")
    ap.add_argument("--template", default="data/grid/sample_submission.tif")
    ap.add_argument("--labels", default="data/grid/labels.tif")
    ap.add_argument("--sgmc", default="data/external/derived_sgmc_faults_100m_u8.tif")
    ap.add_argument("--inputs", default=".arena/inputs")
    ap.add_argument("--incumbent", default="docs/downloads/gemsdoe50-h57-scarpstep-80000-20261007T1830Z-allfinite.tif")
    ap.add_argument("--split", default="evidence/holdout-v1.json")
    ap.add_argument("--prior-union", default="registry/prior_positive_union.npz")
    ap.add_argument("--belief-cache", default=".arena/cache/h57_belief.npy")
    ap.add_argument("--supports-cache", default=".arena/cache/h59_supports.npz")
    ap.add_argument("--output-dir", default="docs/downloads")
    ap.add_argument("--report", default="evidence/h59_build.json")
    ap.add_argument("--stamp", default=None)
    run(ap.parse_args())


if __name__ == "__main__":
    main()
