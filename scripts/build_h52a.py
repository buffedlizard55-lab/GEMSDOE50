#!/usr/bin/env python3
"""Build the H52-A submission: scarp matched filter, corroborated by drainage deflection.

Every threshold here is frozen in ``docs/h52a-protocol.md`` **before** this script was first run
to completion. The field, domain, mass-selection rule, and promotion gate are reproduced from
that document verbatim; do not change a number here without updating it there first.

Outputs: ``docs/downloads/<name>.tif`` (+ all-finite twin + zip), ``evidence/build_h52a.json``.
"""
from __future__ import annotations

import argparse
import json
import sys
import time
import zipfile
from pathlib import Path

import numpy as np
import rasterio
from scipy.ndimage import distance_transform_edt

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "src"))

from gems51 import drainage, emit, instruments, scarpmf
from gems51 import grid as g51
from gemsdoe50 import common

INPUTS = Path("/home/user/.arena/inputs")
CATALOG = REPO / "data" / "external" / "usgs_comcat_earthquakes.csv.gz"
SGMC = REPO / "data" / "external" / "derived_sgmc_faults_100m_u8.tif"
TOPO = INPUTS / "topo_u8.tif"
H51_INCUMBENT = REPO / "docs" / "downloads" / "gems51-scarpradio-offcat-35000-20261006-ecf058ea-nan.tif"

CATALOGUE_BUFFER_M = 300.0
CORROBORATION_RADIUS_PX = 3.0            # 300 m, matches CATALOGUE_BUFFER_M in pixels
DEFLECTION_HOTSPOT_PERCENTILE = 85.0     # frozen in docs/h52a-protocol.md step 7
MASS_SWEEP = (10_000, 15_000, 20_000, 25_000, 30_000, 35_000, 40_000, 45_000, 50_000)
MASS_CAP = 50_000
SGMC_TOLERANCE = 0.10
SUPPRESSION_PX = 3.0
MC_EPICENTRE = (425569.0, 4224896.0)


def monte_cristo_trend(valid: np.ndarray) -> np.ndarray:
    import pandas as pd
    from pyproj import Transformer
    df = pd.read_csv(CATALOG, low_memory=False)
    tr = Transformer.from_crs("EPSG:4326", "EPSG:32611", always_xy=True)
    x, y = tr.transform(df["longitude"].to_numpy(), df["latitude"].to_numpy())
    t = pd.to_datetime(df["time"], format="ISO8601", utc=True, errors="coerce")
    sel = ((t >= "2020-05-15") & (t <= "2022-01-01")
           & (np.hypot(x - MC_EPICENTRE[0], y - MC_EPICENTRE[1]) < 30_000))
    points = np.column_stack([x[sel], y[sel]])
    mu = points.mean(axis=0)
    _, vecs = np.linalg.eigh(np.cov((points - mu).T))
    axis = vecs[:, 1]
    ts = np.linspace(-14_000, 14_000, 281)
    col, row = g51.col_row(mu[0] + ts * axis[0], mu[1] + ts * axis[1])
    out = np.zeros(valid.shape, dtype=bool)
    ok = (col >= 0) & (col < g51.GRID["width"]) & (row >= 0) & (row < g51.GRID["height"])
    out[row[ok], col[ok]] = True
    return out & valid


def write_raster(path: Path, values: np.ndarray, valid: np.ndarray, *, nan_outside: bool) -> dict:
    data = np.where(valid, values.astype(np.float32), np.nan if nan_outside else 0.0).astype(np.float32)
    profile = {
        "driver": "GTiff", "height": g51.GRID["height"], "width": g51.GRID["width"],
        "count": 1, "dtype": "float32", "crs": g51.GRID["crs"],
        "transform": rasterio.transform.Affine(*g51.GRID["transform"]),
        "nodata": float("nan") if nan_outside else None,
        "compress": "deflate",
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    with rasterio.open(path, "w", **profile) as ds:
        ds.write(data, 1)
    with rasterio.open(path) as ds:
        back = ds.read(1)
        info = {
            "path": str(path.relative_to(REPO)), "bytes": path.stat().st_size,
            "sha256": common.sha256_file(path), "crs": str(ds.crs),
            "shape": [ds.height, ds.width], "dtype": ds.dtypes[0], "count": ds.count,
            "nodata": None if ds.nodata is None else float(ds.nodata),
            "transform": [float(v) for v in ds.transform][:6],
            "cells_finite": int(np.count_nonzero(np.isfinite(back))),
            "cells_nan": int(np.count_nonzero(np.isnan(back))),
            "min": float(np.nanmin(back)), "max": float(np.nanmax(back)),
            "outside_unit_interval": int(np.count_nonzero(
                np.isfinite(back) & ((back < 0.0) | (back > 1.0)))),
            "outside_footprint_nonzero": int(np.count_nonzero(back[~valid] > 0)),
            "footprint_min": float(np.nanmin(back[valid])),
            "footprint_max": float(np.nanmax(back[valid])),
            "footprint_nonzero": int(np.count_nonzero(back[valid] > 0)),
        }
    return info


def uniqueness_gate(support: np.ndarray, valid: np.ndarray) -> dict:
    sig = np.load(REPO / "registry" / "prior_artifact_signatures.npz", allow_pickle=True)
    names = [str(n) for n in sig["names"]]
    rows = []
    for index, (factor, key) in enumerate(((8, "masks_block8"), (32, "masks_block32"))):
        shape = tuple(int(v) for v in sig["coarse_shapes"][index])
        h2, w2 = shape[0] * factor, shape[1] * factor
        mine = support[:h2, :w2].reshape(shape[0], factor, shape[1], factor).any(axis=(1, 3))
        for name, prior_bits in zip(names, sig[key]):
            prior = np.unpackbits(np.asarray(prior_bits, dtype=np.uint8))[: mine.size]
            prior = prior.reshape(shape).astype(bool)
            inter = int(np.count_nonzero(mine & prior))
            union = int(np.count_nonzero(mine | prior))
            rows.append({"factor": factor, "name": name,
                         "jaccard": inter / union if union else 0.0,
                         "overlap_fraction_of_mine": inter / max(int(np.count_nonzero(mine)), 1)})
    worst_j = max(rows, key=lambda r: r["jaccard"])
    worst_o = max(rows, key=lambda r: r["overlap_fraction_of_mine"])
    return {
        "n_prior_artifacts": len(names),
        "max_jaccard": worst_j["jaccard"], "max_jaccard_against": worst_j["name"],
        "max_overlap_of_mine": worst_o["overlap_fraction_of_mine"],
        "max_overlap_against": worst_o["name"],
        "unique_at_8px": worst_j["jaccard"] < 0.5,
        "unique_at_32px": worst_j["jaccard"] < 0.5,
        "table": sorted(rows, key=lambda r: -r["jaccard"])[:10],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mass", type=int, default=None,
                        help="override the mass-selection rule and emit exactly this many dots")
    args = parser.parse_args()
    started = time.time()

    valid = g51.load_footprint()
    labels = g51.load_labels()
    catalogue_distance = distance_transform_edt(~labels)
    off_catalogue = (catalogue_distance > CATALOGUE_BUFFER_M / g51.GRID["pixel_m"]) & valid
    sgmc, _ = g51.load_raster(SGMC)
    sgmc_off = (sgmc > 0) & (catalogue_distance > 3) & valid
    mc = monte_cristo_trend(valid)
    truths = {"catalogue": labels, "sgmc_off": sgmc_off, "monte_cristo": mc}
    print(f"grid valid={int(valid.sum()):,} catalogue={int(labels.sum()):,} "
          f"sgmc_off={int(sgmc_off.sum()):,} mc={int(mc.sum()):,}", flush=True)

    print("[1/6] DEM, matched filter, flow routing, deflection field ...", flush=True)
    dem, dem_valid, dem_meta = drainage.load_dem_mean(str(TOPO))
    grid_valid = valid & dem_valid
    det = scarpmf.detrend(dem, grid_valid)
    mf = scarpmf.matched_filter(det, grid_valid)
    flow = drainage.route_flow(dem, grid_valid)
    defl = drainage.channel_deflection(flow["fdir"], flow["acc"], grid_valid)
    channel_vals = defl["deflection"][defl["channel_mask"] & (defl["deflection"] > 0)]
    hotspot_threshold = float(np.percentile(channel_vals, DEFLECTION_HOTSPOT_PERCENTILE)) if channel_vals.size else 1.0
    hotspot = defl["channel_mask"] & (defl["deflection"] >= hotspot_threshold)
    hotspot_distance = distance_transform_edt(~hotspot)
    corroborated = hotspot_distance <= CORROBORATION_RADIUS_PX
    print(f"    hotspot cells={int(hotspot.sum()):,} (threshold {hotspot_threshold:.4f}); "
          f"corroborated cells={int(corroborated.sum()):,}", flush=True)

    domain = off_catalogue & grid_valid & corroborated
    belief = np.where(domain, mf["strength"], 0.0).astype(np.float32)
    peak = float(belief.max())
    belief = belief / peak if peak > 0 else belief
    print(f"    domain cells={int(domain.sum()):,} of off_catalogue={int(off_catalogue.sum()):,} "
          f"({100.0 * domain.sum() / max(int(off_catalogue.sum()), 1):.2f}%)", flush=True)

    print("[2/6] mass sweep ...", flush=True)
    if args.mass is not None:
        print(f"    owner override: emitting exactly {args.mass:,} dots", flush=True)
    rng_base = np.random.default_rng(5207)
    sweep = {}
    for mass in MASS_SWEEP:
        support, info = emit.pack(belief, mass, valid=domain, suppression_px=SUPPRESSION_PX)
        scores = instruments.all_instruments(support, truths)
        control_support, _ = emit.pack(
            np.where(off_catalogue, rng_base.random(valid.shape).astype(np.float32), 0.0),
            mass, valid=off_catalogue, suppression_px=SUPPRESSION_PX)
        control_scores = instruments.all_instruments(control_support, truths)
        sweep[mass] = {"n_dots": info["mass"], "instruments": scores, "random_control": control_scores}
        print(f"    M={mass:6d} n={info['mass']:6d} sgmc_off_cpdot={scores['sgmc_off']['credit_per_dot']:.4f}"
              f" mc_tpw={scores['monte_cristo']['tp_weight']:.2f}"
              f" (random {control_scores['sgmc_off']['credit_per_dot']:.4f} /"
              f" {control_scores['monte_cristo']['tp_weight']:.2f})", flush=True)

    best_credit = max(v["instruments"]["sgmc_off"]["credit_per_dot"] for v in sweep.values())
    rule_rows, chosen = [], None
    for mass in MASS_SWEEP:
        credit = sweep[mass]["instruments"]["sgmc_off"]["credit_per_dot"]
        within = credit >= (1.0 - SGMC_TOLERANCE) * best_credit
        rule_rows.append({"mass": mass, "sgmc_credit_per_dot": float(credit),
                          "best_swept_credit_per_dot": float(best_credit),
                          "within_10pct_of_best": bool(within), "kept": bool(within)})
        if within and sweep[mass]["n_dots"] > 0:
            chosen = mass
    if chosen is None:
        raise SystemExit("H52-A mass-selection rule: no swept mass survives; do not ship")
    if args.mass is not None:
        chosen = args.mass
    chosen = min(chosen, MASS_CAP)
    print(f"    chose mass {chosen} (best swept SGMC-off credit/dot {best_credit:.4f})", flush=True)

    print("[3/6] emission and writing ...", flush=True)
    support, _pack_info = emit.pack(belief, chosen, valid=domain, suppression_px=SUPPRESSION_PX)
    values = support.astype(np.float32)
    content_id = common.sha256_array(support.astype(np.uint8))[:8]
    stamp = time.strftime("%Y%m%dT%H%M%SZ", time.gmtime())
    name = f"gems52a-scarpdrainage-offcat-{int(values.sum())}-{stamp}-{content_id}"
    primary = REPO / "docs" / "downloads" / f"{name}-nan.tif"
    allfinite = REPO / "docs" / "downloads" / f"{name}-allfinite.tif"
    audit = write_raster(primary, values, valid, nan_outside=True)
    audit_finite = write_raster(allfinite, values, valid, nan_outside=False)
    zpath = primary.with_suffix(".zip")
    with zipfile.ZipFile(zpath, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.write(primary, arcname=primary.name)
    checks = {"primary": audit, "allfinite": audit_finite,
              "zip": {"path": str(zpath.relative_to(REPO)), "bytes": zpath.stat().st_size,
                      "sha256": common.sha256_file(zpath), "contains": primary.name}}
    (REPO / "docs" / "downloads" / f"checks-{primary.name}.json").write_text(
        json.dumps(checks, indent=1), encoding="utf-8")

    print("[4/6] instruments, controls, incumbent comparison, uniqueness ...", flush=True)
    final_scores = instruments.all_instruments(support, truths)
    rng = np.random.default_rng(52)
    random_support, _ = emit.pack(
        np.where(off_catalogue, rng.random(valid.shape).astype(np.float32), 0.0),
        int(values.sum()), valid=off_catalogue, suppression_px=SUPPRESSION_PX)
    random_scores = instruments.all_instruments(random_support, truths)
    translated = {}
    for dr, dc in ((0, 97), (53, 0), (-61, 41), (29, -83)):
        shifted = np.roll(np.roll(support, dr, axis=0), dc, axis=1)
        translated[f"shift_{dr}_{dc}"] = instruments.score(shifted, sgmc_off)

    incumbent_comp = None
    if H51_INCUMBENT.exists():
        with rasterio.open(H51_INCUMBENT) as ds:
            inc = ds.read(1)
        inc_support = np.isfinite(inc) & (inc > 0)
        inc_scores = instruments.all_instruments(inc_support, truths)
        overlap = int(np.count_nonzero(inc_support & support))
        incumbent_comp = {
            "incumbent_file": H51_INCUMBENT.name,
            "incumbent_mass": int(inc_support.sum()),
            "incumbent_instruments": inc_scores,
            "candidate_mass": int(values.sum()),
            "candidate_instruments": final_scores,
            "beats_incumbent_sgmc_off_credit_per_dot":
                bool(final_scores["sgmc_off"]["credit_per_dot"] > inc_scores["sgmc_off"]["credit_per_dot"]),
            "overlap_cells_with_incumbent": overlap,
            "overlap_fraction_of_candidate": overlap / max(int(values.sum()), 1),
        }
        print(f"    H51 incumbent sgmc_off_cpdot={inc_scores['sgmc_off']['credit_per_dot']:.4f} "
              f"vs H52-A {final_scores['sgmc_off']['credit_per_dot']:.4f}; "
              f"overlap={overlap} cells", flush=True)

    unique = uniqueness_gate(support, valid)

    print("[5/6] diagnostics ...", flush=True)
    diagnostics = {
        "dem": {"source": str(TOPO.name), "band": 9, "band_name": "dem_mean",
                "valid_fraction": float(dem_valid.mean()), "q_lo": dem_meta["q_lo"], "q_hi": dem_meta["q_hi"]},
        "matched_filter": {"azimuths_tested": mf["azimuths_tested"],
                            "trend_sigma_px": scarpmf.TREND_SIGMA_PX,
                            "step_length_px": scarpmf.STEP_LENGTH_PX, "step_width_px": scarpmf.STEP_WIDTH_PX,
                            "raw_peak_p98": mf["raw_peak_p98"]},
        "drainage": {"channel_area_cells": defl["channel_area_cells"],
                     "channel_cells": defl["channel_cells"],
                     "deflection_window_px": defl["window_px"],
                     "hotspot_percentile": DEFLECTION_HOTSPOT_PERCENTILE,
                     "hotspot_threshold": hotspot_threshold,
                     "hotspot_cells": int(hotspot.sum()),
                     "corroboration_radius_px": CORROBORATION_RADIUS_PX,
                     "corroborated_cells": int(corroborated.sum())},
        "domain_cells": int(domain.sum()),
        "off_catalogue_cells": int(off_catalogue.sum()),
    }

    print("[6/6] evidence ...", flush=True)
    report = {
        "schema": "gems52a.build.v1",
        "built_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "builder": {"script": "scripts/build_h52a.py", "sha256": common.sha256_file(Path(__file__)),
                    "argv": sys.argv[1:],
                    "inputs": {"topo": {"path": str(TOPO), "sha256": common.sha256_file(TOPO),
                                        "bytes": TOPO.stat().st_size}},
                    "catalog_sha256": common.sha256_file(CATALOG), "sgmc_sha256": common.sha256_file(SGMC)},
        "protocol": "docs/h52a-protocol.md (frozen 2026-10-07, before any instrument score existed)",
        "name": name,
        "runtime_seconds": round(time.time() - started, 1),
        "diagnostics": diagnostics,
        "mass_sweep": {str(k): {"n_dots": v["n_dots"], "instruments": v["instruments"],
                                "random_control": v["random_control"]} for k, v in sweep.items()},
        "mass_rule": {"rule": "largest swept mass within 10% of the best swept SGMC-off credit per dot",
                      "sgmc_tolerance": SGMC_TOLERANCE, "owner_override": bool(args.mass is not None),
                      "rows": rule_rows, "chosen_mass": chosen},
        "instruments": {"candidate": final_scores, "random_control": random_scores,
                        "translation_controls": translated},
        "incumbent_comparison": incumbent_comp,
        "uniqueness": unique,
        "outputs": checks,
        "honesty": [
            "No organizer score exists for this file and none is claimed.",
            "Every local number here is a proxy instrument, not the hidden truth.",
            ("dem_mean (100 m) and a self-computed D8 flow network stand in for the missing "
            "official det_elev/det_elev_slope bands and USGS NHD flowlines; this is this "
            "project's own construction, not an official hydrography product."),
            ("The deflection field is confounded by ordinary confluences and meanders; only the "
            "conjunction with the matched-filter step evidence is used as belief."),
            ("Monte Cristo coverage is reported only as a weak guard (per the H51 A3 correction), "
            "never as a selection or promotion criterion."),
        ],
    }
    (REPO / "evidence").mkdir(exist_ok=True)
    (REPO / "evidence" / "build_h52a.json").write_text(json.dumps(report, indent=1), encoding="utf-8")
    print(json.dumps({"name": name, "mass": int(values.sum()), "sha256": audit["sha256"],
                      "instruments": {k: round(v["dti"], 4) for k, v in final_scores.items()},
                      "chosen_mass": chosen, "unique_max_jaccard": unique["max_jaccard"],
                      "beats_h51_incumbent": incumbent_comp["beats_incumbent_sgmc_off_credit_per_dot"]
                      if incumbent_comp else None}, indent=1))
    print(f"done in {time.time() - started:.0f}s")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
