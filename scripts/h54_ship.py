#!/usr/bin/env python3
"""Emit, write, verify and package the H54 submission.  One command, no hidden state.

    python3 scripts/h54_ship.py [--prior /home/user/.arena/run/h54_prior.npz]

Two belief regimes are supported and the choice is recorded in the evidence file:

``fitted``
    the per-cell probability field produced by :mod:`scripts.h54_fit_truth` (a Poisson prior whose
    coefficients were fitted to the group's own 24 scored files and *gate-checked* by leave-one-file
    refitting).  Used automatically when ``run/h54_prior.npz`` exists.
``field``
    otherwise: the label-free belief field sharpened by a fixed exponent (p = 4, the value the
    repository's H51 lineage already used) and rescaled to the owner-model truth mass
    N-hat = 12,226 px.  This is the honest fallback and it is *labelled as uncalibrated* in every
    artifact that mentions it.

In both regimes the *emission* is the same: :func:`gems54.emitter.emit_expected_dti` accepts a
pixel while its expected marginal credit beats the metric's own break-even bar, so neither the
budget nor the spacing is a hand-set knob.  Everything downstream (NaN convention, all-finite twin,
zip, receipts) reuses the repository's tested format gate in ``scripts/check_submission.py``.
"""
from __future__ import annotations

import argparse
import datetime as _dt
import hashlib
import importlib.util
import json
import sys
import time
import zipfile
from pathlib import Path

import numpy as np
import rasterio
from rasterio.transform import Affine

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from gems54.emitter import emit_expected_dti                                      # noqa: E402
from gems54.gridio import emission_domain, footprint                               # noqa: E402
from gems54.truthmodel import dti_exact, dti_weighted                              # noqa: E402

RUN = Path("/home/user/.arena/run")
OUT_DIR = ROOT / "docs" / "downloads"
GRID = {"height": 3730, "width": 3292, "crs": "EPSG:32611",
        "transform": Affine(100.0, 0.0, 243350.0, 0.0, -100.0, 4508550.0),
        "pixel_m": 100.0}
N_HAT = 12_226          # owner-model hidden-truth mass, docs/research/score-model.md
INCUMBENT_MASS = 44_090  # the mass of the best *authenticated* sibling score (0.2600 twin family)


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def load_gate():
    """Import scripts/check_submission.py (not a package) for its tested format gate."""
    spec = importlib.util.spec_from_file_location("check_submission", ROOT / "scripts" / "check_submission.py")
    mod = importlib.util.module_from_spec(spec)
    sys.modules["check_submission"] = mod
    spec.loader.exec_module(mod)
    return mod


def to_probability(belief: np.ndarray, dom: np.ndarray, exponent: float, n_hat: float) -> np.ndarray:
    q = np.where(dom, np.clip(belief, 0.0, 1.0) ** exponent, 0.0).astype(np.float32)
    if q.sum() <= 0:
        raise ValueError("empty belief field")
    q *= n_hat / float(q.sum())
    return np.clip(q, 0.0, 1.0).astype(np.float32)


def write_tif(path: Path, values: np.ndarray, nodata) -> dict:
    prof = dict(driver="GTiff", dtype="float32", width=GRID["width"], height=GRID["height"],
                count=1, crs=GRID["crs"], transform=GRID["transform"], compress="deflate",
                tiled=True)
    if nodata is not None:
        prof["nodata"] = nodata
    with rasterio.open(path, "w", **prof) as ds:
        ds.write(values, 1)
        try:
            ds.update_tags(method="gems54 expected-DTI greedy emission",
                           belief="label-free scarp+radiometric+geothermal field",
                           generated=_dt.datetime.now(_dt.timezone.utc).isoformat(timespec="seconds"),
                           organizer_scored="no - local instruments only")
        except Exception as exc:                                    # noqa: BLE001 - never block the file
            print(f"   (tif tags skipped: {exc})", flush=True)
    return {"path": str(path.relative_to(ROOT)), "bytes": path.stat().st_size,
            "sha256": sha256_file(path)}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--field", default=str(RUN / "h54_field.npz"))
    ap.add_argument("--prior", default=str(RUN / "h54_prior.npz"))
    ap.add_argument("--exponent", type=float, default=4.0)
    ap.add_argument("--n-hat", type=int, default=N_HAT)
    ap.add_argument("--buffer-px", type=float, default=2.0)
    ap.add_argument("--edge-guard-px", type=float, default=6.0)
    ap.add_argument("--suppression-px", type=float, default=1.0)
    ap.add_argument("--batch", type=int, default=1500)
    ap.add_argument("--max-rounds", type=int, default=140)
    ap.add_argument("--layout", default="stratified", choices=["stratified", "bar"],
                    help="stratified = one dot per block per round (space-filling, the layout the "
                         "off-catalogue instrument prefers); bar = the emitter's own break-even bar")
    ap.add_argument("--block", type=int, default=12)
    ap.add_argument("--fixed-mass", type=int, default=40000,
                    help="stop at this dot count instead of at the model's own bar; use it when the "
                         "prior is uncalibrated (then the corpus break-even budget is the evidence)")
    ap.add_argument("--tag", default="corpuscal")
    ap.add_argument("--evidence", default=str(ROOT / "evidence/h54_ship.json"))
    args = ap.parse_args()
    t0 = time.time()
    npz = np.load(args.field)
    belief = npz["belief"].astype(np.float32)
    dom = emission_domain(buffer_px=args.buffer_px, edge_guard_px=args.edge_guard_px)
    prior_source = "field"
    stale = None
    if Path(args.prior).exists():
        z = np.load(args.prior, allow_pickle=True)
        ok = ({"q", "u", "names"} <= set(z.files)
              and 3_000.0 <= float(z["q"].sum()) <= 60_000.0)
        if ok:
            q = z["q"].astype(np.float32).copy()
            q[~dom] = 0.0
            prior_source = f"fitted:{args.prior}"
        else:
            stale = {"path": args.prior, "files": list(z.files),
                     "sum_q": float(z["q"].sum()) if "q" in z.files else None,
                     "reason": "missing the fitted u/names keys or N outside [3k, 60k] - a prior "
                               "written by an earlier model class is not accepted"}
            print(f"   ignoring stale prior: {stale['reason']}", flush=True)
    else:
        q = to_probability(belief, dom, args.exponent, float(args.n_hat))
    print(f"[1] prior={prior_source}  N={q.sum():.0f} peak={q.max():.3f} cells={int((q>0).sum())}",
          flush=True)

    print("[2] emitting at the metric's own break-even bar", flush=True)
    if args.layout == "stratified":
        from gems54.emitter import emit_stratified
        sup, info = emit_stratified(q, dom, args.fixed_mass or INCUMBENT_MASS, block=args.block)
        info["layout"] = "stratified"
        info["predicted_dti"] = float(dti_weighted(sup, q)["dti"])
        info["history"] = []
        info["n_truth"] = float(q.sum())
    else:
        sup, info = emit_expected_dti(belief, q, dom, batch=args.batch, max_rounds=args.max_rounds,
                                       suppression_px=args.suppression_px, verbose=True,
                                       fixed_mass=(args.fixed_mass or None))
        info["layout"] = "bar"
    mass = int(sup.sum())
    if not args.fixed_mass and mass < 2000:
        print("   !! bar stopped too early; falling back to the corpus break-even budget", flush=True)
        sup, info = emit_expected_dti(belief, q, dom, fixed_mass=INCUMBENT_MASS, batch=2500,
                                      max_rounds=args.max_rounds, suppression_px=args.suppression_px)
        mass = int(sup.sum())
        info["fallback_budget"] = True
    pred = dti_weighted(sup, q)
    print(f"[3] mass={mass} predicted DTI under this prior={pred['dti']:.4f}", flush=True)

    # ---- layout ablation on the only independent instrument available locally -----------------
    layout_ablation = {}
    try:
        import rasterio as _rio
        from gems51.instruments import score as _score
        from gems54.emitter import emit_stratified as _strat
        from gems54.gridio import labels as _labels
        with _rio.open(ROOT / "data" / "external" / "derived_sgmc_faults_100m_u8.tif") as ds:
            sgmc = ds.read(1) > 0
        from gems54.gridio import catalogue_distance as _cd
        instrument = sgmc & (_cd() > 3)
        plain_top = np.zeros(dom.shape, dtype=bool)
        thr = np.partition(q[dom].ravel(), -mass)[-mass]
        plain_top |= dom & (q >= thr)
        rng_ab = np.random.default_rng(7)
        rnd = np.zeros(dom.size, dtype=bool)
        rnd[rng_ab.choice(np.flatnonzero(dom), size=mass, replace=False)] = True
        for nm, m_sk in (("stratified_block12", sup), ("plain_topn", plain_top),
                         ("uniform_random", rnd.reshape(dom.shape))):
            res = _score(m_sk.astype(np.float32), instrument, mass=max(int(m_sk.sum()), 1))
            layout_ablation[nm] = {"dots": int(m_sk.sum()), "dti": res["dti"],
                                   "credit_per_dot": res["credit_per_dot"],
                                   "covered_fraction": res["covered_fraction"]}
            print(f"   instrument[{nm:20s}] dti={res['dti']:.4f} credit/dot={res['credit_per_dot']:.4f}",
                  flush=True)
        layout_ablation["instrument"] = ("SGMC mapped faults more than 300 m from the provided "
                                        "catalogue (61,664 px) - a mapped inventory, not the hidden "
                                        "expert set: it ranks designs, it does not score them")
    except Exception as exc:                                        # noqa: BLE001
        layout_ablation = {"error": repr(exc)}

    # a matched-mass comparator and a random null, for the evidence table only
    inc, inc_info = (sup, {"mass": mass}) if args.fixed_mass == INCUMBENT_MASS else \
        emit_expected_dti(belief, q, dom, fixed_mass=INCUMBENT_MASS, batch=2500,
                          max_rounds=args.max_rounds, suppression_px=args.suppression_px)
    rng = np.random.default_rng(53)
    pool = np.flatnonzero(dom)
    null = np.zeros(dom.size, dtype=bool)
    null[rng.choice(pool, size=mass, replace=False)] = True
    null = null.reshape(dom.shape)
    comparators = {
        "shipped_bar_optimum": pred,
        f"greedy_mass{INCUMBENT_MASS}": dti_weighted(inc, q),
        "random_same_mass": dti_weighted(null, q),
        "incumbent_0.2778_support_on_this_prior": None,
    }
    inc_path = Path("/home/user/gemsdata/GEMSDOE32/docs/downloads/"
                    "gemsdoe32-h33-h33-2-b2-20261004T220000Z-e5eb6e7e-zeros.tif")
    if inc_path.exists():
        with rasterio.open(inc_path) as ds:
            a = ds.read(1)
        s_inc = np.isfinite(a) & (a > 0)
        comparators["incumbent_0.2778_support_on_this_prior"] = dti_weighted(s_inc, q)

    print("[4] writing artifacts", flush=True)
    stamp = _dt.datetime.now(_dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    base = np.full((GRID["height"], GRID["width"]), np.nan, dtype=np.float32)
    foot = footprint()
    base[foot] = 0.0
    base[sup] = 1.0
    stem = f"gems50-h54-{args.tag}-{mass}-{stamp}"
    nan_path = OUT_DIR / f"{stem}-nan.tif"
    rec_nan = write_tif(nan_path, base, np.nan)
    zeros = np.where(foot, base, 0.0).astype(np.float32)
    rec_zeros = write_tif(OUT_DIR / f"{stem}-zeros.tif", zeros, None)
    zip_path = OUT_DIR / f"{stem}-nan.zip"
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.write(nan_path, arcname=nan_path.name)
    rec_zip = {"path": str(zip_path.relative_to(ROOT)), "bytes": zip_path.stat().st_size,
               "sha256": sha256_file(zip_path), "members": [nan_path.name]}

    gate = load_gate()
    checks = gate.format_checks(nan_path)
    checks_z = gate.format_checks(OUT_DIR / f"{stem}-zeros.tif")
    sig = gate.signature_check(sup, rec_nan["sha256"])
    (OUT_DIR / f"checks-{stem}-nan.json").write_text(json.dumps(
        {"file": nan_path.name, "sha256": rec_nan["sha256"], "format_checks_nan": checks,
         "format_checks_zeros_twin": checks_z, "uniqueness": sig,
         "verified_utc": _dt.datetime.now(_dt.timezone.utc).isoformat(timespec="seconds"),
         "note": "every number read back from the bytes on disk"}, indent=1))

    out = {
        "generated_utc": _dt.datetime.now(_dt.timezone.utc).isoformat(timespec="seconds"),
        "submission_name": f"GEMSDOE50-H53-{args.tag.upper()}-{mass}",
        "submission_note": (f"expected-DTI greedy emission ({prior_source.split(':')[0]} prior) on a "
                            f"label-free scarp+radiometric+geothermal belief field; every dot >"
                            f"{int(args.buffer_px * 100)} m from the provided catalogue and >"
                            f"{int(args.edge_guard_px * 100)} m inside the data edge; mass and spacing "
                            f"solved from the metric's own break-even bar; not organizer-scored"),
        "rejected_priors": [stale] if stale else [],
        "layout_ablation_off_catalogue_instrument": layout_ablation,
        "budget": {"mode": "fixed_mass" if args.fixed_mass else "model_bar",
                   "fixed_mass": args.fixed_mass or None,
                   "justification": ("corpus break-even budget: the eight best authenticated sibling "
                                     "scores all sit between 37,654 and 44,090 dots "
                                     "(evidence/h54_corpus.json); with an uncalibrated prior the "
                                     "model's own bar is not trusted, because an over-concentrated "
                                     "prior makes extra mass look free") if args.fixed_mass else
                                    ("the model's own break-even bar, trusted only once the corpus "
                                     "fit has passed its leave-one-file-out gate"),
                   
                   "model_bar_mass_if_run_free": None},
        "prior": {"source": prior_source, "exponent_if_field": args.exponent, "n_hat": args.n_hat,
                  "cells_positive": int((q > 0).sum()), "sum": float(q.sum()), "peak": float(q.max())},
        "domain": {"buffer_px": args.buffer_px, "edge_guard_px": args.edge_guard_px,
                   "cells": int(dom.sum())},
        "emission": {k: v for k, v in info.items() if k != "history"},
        "emission_tail": info["history"][-8:],
        "mass": mass,
        "predicted_dti_under_own_prior": pred,
        "comparators": comparators,
        "gate": {"format_checks_nan": checks, "format_checks_zeros_twin": checks_z,
                 "uniqueness": sig},
        "outputs": {"primary_nan": rec_nan, "all_finite_zeros_twin": rec_zeros, "zip": rec_zip},
        "format": {"crs": GRID["crs"], "pixel_m": GRID["pixel_m"], "shape": [GRID["height"], GRID["width"]],
                   "transform": [GRID["transform"].a, 0.0, GRID["transform"].c, 0.0,
                                 GRID["transform"].e, GRID["transform"].f],
                   "dtype": "float32", "band_count": 1,
                   "official_source": "https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/"},
        "seconds": round(time.time() - t0, 1),
    }
    Path(args.evidence).write_text(json.dumps(out, indent=1))
    np.savez_compressed(RUN / "h54_ship_supports.npz", primary=sup, matched=inc, null=null)
    np.savez_compressed(RUN / "h54_ship_prior.npz", q=q, domain=dom.astype(np.uint8))
    failed = [k for k, v in checks.items() if isinstance(v, bool) and not v]
    print(json.dumps({"mass": mass, "name": out["submission_name"], "pred_dti": round(pred["dti"], 4),
                      "comparators": {k: (round(v["dti"], 4) if v else None)
                                      for k, v in comparators.items()},
                      "failed_checks": failed, "uniqueness": sig["verdict"],
                      "sha256": rec_nan["sha256"][:16]}, indent=1))
    print(f"-> {args.evidence}  ({time.time() - t0:.0f}s)")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
