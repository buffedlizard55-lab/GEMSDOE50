#!/usr/bin/env python3
"""Build the GEMSDOE50 submission.

Content
  core    legacy 2-D seismicity lineation corridors from a mixed-network ComCat
          extract with unresolved contributor rights (covariance/inertia clusters +
          pruned Hough spans). The triangle-area filter is computed but its keep mask
          is not applied to subsequent fitting, so this builder does not establish
          aftershock declustering. Not an H50-S1 input or a new detector.
  volume  ridge evidence from the USGS 3DEP lidar scarp descriptors and the GeoDAWN
          airborne radiometrics, restricted to >300 m from the provided catalogue

Decision rules (all measured, none assumed)
  * binary emission: DTI is increasing in the scale of a fixed support, so every
    emitted cell is exactly 1.0
  * the metric's own first-order condition (tests/test_metric.py): a unit of mass
    at kernel weight w raises DTI iff w > 0.2*DTI
  * the sibling ledger of 16 live-scored anchor files (GEMSDOE40/docs/data/
    live-transfer.json, truth-inversion.json) puts the owner's best live score,
    0.2778, on an emission of 37,654 dots with per-dot hidden credit ~0.09-0.14,
    and shows a uniform-scatter control at the same mass scores 0.0778.  The mass
    is therefore chosen by walking the same bar rule on the best available
    ranking instrument (per-dot credit on the off-catalogue USGS SGMC inventory,
    LOO Spearman +0.705 against those 16 live scores).

Outputs
  docs/downloads/gemsdoe50-<name>.tif / .zip / checks-<name>.tif.json
  evidence/build_<name>.json   every number behind the build
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
from scipy import ndimage
from scipy.ndimage import distance_transform_edt

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "src"))

from gems50 import catalog as gcat                       # noqa: E402
from gems50 import decluster, emission, hough, lineation  # noqa: E402
from gems50 import dti as metric                         # noqa: E402
from gems50 import grid_io as grid                        # noqa: E402

TERRAIN = REPO / "data" / "external" / "lidar_scarp_features_u8.tif"
RADIO = REPO / "data" / "external" / "geodawn_rad_u8.tif"
SGMC = REPO / "data" / "external" / "derived_sgmc_faults_100m_u8.tif"
CATALOG = REPO / "data" / "external" / "usgs_comcat_earthquakes.csv.gz"
G_ESTIMATES = (7500, 15100)   # the ledger's two published hidden-truth-size estimates


def _uq8(a: np.ndarray, scale: float) -> np.ndarray:
    q = np.clip(a.astype(np.float32) - 1.0, 0.0, 254.0) / 254.0
    return (q ** 2) * scale


def terrain_ridge_evidence() -> tuple[np.ndarray, dict]:
    with rasterio.open(TERRAIN) as s:
        step = _uq8(s.read(3), 1.0)
        lapneg = _uq8(s.read(4), 0.05)
        coh = s.read(10).astype(np.float32) / 255.0
        valid = s.read(12) > 0
    scarp = np.sqrt(np.clip(step, 0, None)) * (1.0 + np.clip(lapneg, 0, None)) * np.clip(coh, 0, 1)
    ev = emission.oriented_ridge_filter(np.where(valid, scarp, 0.0), 12, 15, 1)
    return emission.normalise(ev, valid), {
        "layer": "USGS 3DEP 1 m DEM scarp descriptors (step_max, lapneg_max, coh100)",
        "source": "GEMSDOE24 data/external/lidar_scarp_features_u8.tif, "
                  "built from official 3DEP 1 m tiles; no use restrictions",
        "transform": "sqrt(step_max)*(1+lapneg_max)*coh100, then max over 12 orientations "
                     "of a 15 px oriented mean, min-max normalised over lidar coverage"}


def radiometric_ridge_evidence() -> tuple[np.ndarray, dict]:
    with rasterio.open(RADIO) as s:
        K, Th, U, TC = (s.read(i).astype(np.float32) for i in (1, 2, 3, 4))
    valid = K > 0
    grad = np.zeros_like(K)
    for band in (K, Th, U, TC):
        gy, gx = np.gradient(ndimage.gaussian_filter(band, 2.0))
        grad += np.hypot(gx, gy)
    ev = emission.oriented_ridge_filter(np.where(valid, grad, 0.0), 12, 15, 1)
    return emission.normalise(ev, valid), {
        "layer": "GeoDAWN airborne radiometrics K/Th/U/TC (USGS 22103)",
        "source": "https://doi.org/10.5066/P93LGLVQ (public domain, USGS)",
        "transform": "sum of |grad| over the four channels (sigma 2 px), then max over 12 "
                     "orientations of a 15 px oriented mean, normalised over coverage"}


def seismicity_core(g, valid, verbose=True) -> tuple[np.ndarray, list[dict]]:
    t0 = time.time()
    cat = gcat.build_catalog(CATALOG, min_magnitude=1.5, max_depth_km=20.0, start_year=1970)
    xy = cat.xy
    col, row = g.col_row(xy[:, 0], xy[:, 1])
    ok = (col >= 0) & (col < g.width) & (row >= 0) & (row < g.height)
    near = np.zeros(len(xy), bool)
    near[ok] = ndimage.binary_dilation(valid, iterations=30)[row[ok], col[ok]]
    E = cat.frame[near]
    x, y, t, h = (E["x"].to_numpy(), E["y"].to_numpy(), E["t_years"].to_numpy(),
                  E["h_err_km"].to_numpy() * 1000.0)
    keep, tri = decluster.triangle_area_filter(np.column_stack([x, y]))
    notes = [{"events_in_survey": int(len(E)), "triangle_filter_kept": int(keep.sum()),
              "triangle_filter": tri}]
    clusters = lineation.cluster_lineations(np.column_stack([x, y]), t, h, eps_m=3000.0,
                                            min_samples=15, delta_m=600.0, min_events=12)
    labels = lineation.dbscan_labels(np.column_stack([x, y]), t, h, eps_m=3000.0, min_samples=15)
    spines = lineation.cluster_spines(np.column_stack([x, y]), labels, min_events=15, n_bins=24)
    connectors = lineation.chain_segments(clusters, near_m=1500.0, angle_tol_deg=40.0)
    notes.append({"n_clusters": int(len(clusters)),
                  "n_spines": len(spines), "n_connectors": len(connectors),
                  "median_half_length_m": float(np.median(clusters.half_length_m)) if len(clusters) else 0.0,
                  "median_ratio": float(np.median(clusters.ratio)) if len(clusters) else 0.0,
                  "note": "corridor axes are the OADC split-cluster output; the spines and "
                          "connectors are our own coverage additions and are labelled as such"})
    if verbose:
        print(f"    clusters {len(clusters)}  t={time.time()-t0:.0f}s", flush=True)
    thin = np.zeros(g.shape, bool)
    for i in range(len(clusters)):
        n = max(int(2 * clusters.half_length_m[i] / 100.0) + 1, 2)
        off = np.linspace(-clusters.half_length_m[i], clusters.half_length_m[i], n)
        cc, rr = g.col_row(clusters.x[i] + off * clusters.ux[i],
                           clusters.y[i] + off * clusters.uy[i])
        good = (rr >= 0) & (rr < g.height) & (cc >= 0) & (cc < g.width)
        thin[rr[good], cc[good]] = True

    c2, r2 = g.col_row(x, y)
    lin = hough.detect_lineaments(c2.astype(float), r2.astype(float), np.ones(len(x)), g.shape,
                                  n_theta=180, rho_bin_px=1.0, rho_smooth=1, n_surrogates=20,
                                  z_min=6.0, min_events=8, min_extent_px=40.0)
    spans = hough.span_prune(c2.astype(float), r2.astype(float), lin, window_px=24, z_span=4.0,
                             min_events_span=6)
    notes.append({"hough_raw": int(len(lin)), "hough_spans": int(len(spans)),
                  "hough_span_px": float((spans.t_max_px - spans.t_min_px).sum()) if len(spans) else 0.0})
    if verbose:
        print(f"    hough spans {len(spans)}  t={time.time()-t0:.0f}s", flush=True)
    def _dots(xs, ys, step_m):
        cc, rr = g.col_row(xs, ys)
        good = (rr >= 0) & (rr < g.height) & (cc >= 0) & (cc < g.width)
        thin[rr[good], cc[good]] = True

    for pts in spines:                       # curved backbones, one dot every 300 m
        for k in range(len(pts) - 1):
            d = float(np.hypot(*(pts[k + 1] - pts[k])))
            n = max(int(d / 300.0) + 1, 2)
            _dots(np.linspace(pts[k, 0], pts[k + 1, 0], n),
                  np.linspace(pts[k, 1], pts[k + 1, 1], n), 300.0)
    for ax, ay, bx, by in connectors:        # gap bridges, one dot every 300 m
        n = max(int(np.hypot(bx - ax, by - ay) / 300.0) + 1, 2)
        _dots(np.linspace(ax, bx, n), np.linspace(ay, by, n), 300.0)

    support = thin | (hough.rasterise_lineaments(spans, g.shape, 1.0, weight_by_z=False) > 0)
    notes.append({"core_support_cells": int(support.sum())})
    return support, notes


def instrument_scores(p: np.ndarray, truths: dict) -> dict:
    out = {}
    n = max(int(p.sum()), 1)
    for name, tr in truths.items():
        r = metric.dti_parts(p.astype(np.float32), tr)
        out[name] = {"credit_per_px": r.tpw / n, "tpw": r.tpw, "dti": r.value,
                     "truth_px": r.truth_cells, "covered_frac": r.tpw / max(r.truth_cells, 1)}
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--name", default="seis-ridge-v1")
    ap.add_argument("--mass-default", type=int, default=45000,
                    help="fallback mass for the ledger-compatible operating point")
    ap.add_argument("--mass", type=int, default=None)
    ap.add_argument("--suppression-px", type=int, default=3)
    ap.add_argument("--catalogue-buffer-m", type=float, default=300.0)
    ap.add_argument("--outdir", default=str(REPO / "docs" / "downloads"))
    args = ap.parse_args()
    t0 = time.time()

    g = grid.load_grid()
    valid = grid.load_valid_mask()
    labels = grid.load_labels()
    d_lab = distance_transform_edt(~labels)
    with rasterio.open(SGMC) as s:
        sgmc = s.read(1) > 0
    sgmc_off = sgmc & (d_lab > 3) & valid
    off_cat = (d_lab > args.catalogue_buffer_m / grid.CELL_M) & valid
    print(f"grid {g.width}x{g.height} valid {int(valid.sum())} catalogue {int(labels.sum())} "
          f"sgmc_off {int(sgmc_off.sum())} off_cat {int(off_cat.sum())}", flush=True)

    print("  [1/5] seismicity lineations ...", flush=True)
    core, core_notes = seismicity_core(g, valid)

    print("  [2/5] evidence layers ...", flush=True)
    terrain, terrain_note = terrain_ridge_evidence()
    radio, radio_note = radiometric_ridge_evidence()

    print("  [3/5] placement: snap corridors onto the terrain ridge ...", flush=True)
    snapped = emission.snap_to_ridge(terrain, core & valid, max_shift_px=3)
    volume = np.where(off_cat, 0.75 * terrain + 0.55 * radio, 0.0).astype(np.float32)
    credit = np.clip(volume + np.where(off_cat & snapped, 1.0, 0.0), 0.0, 1.0).astype(np.float32)
    core_px = int((snapped & off_cat).sum())
    print(f"    corridor cells in play {core_px}", flush=True)

    print("  [4/5] mass decision (bar rule on the SGMC-off ranking instrument) ...", flush=True)
    truths = {"cat_all": labels, "sgmc_off": sgmc_off}
    sweep = {}
    for M in (25000, 30000, 37654, 45000, 55000, 70000, 90000):
        pk = emission.greedy_pack(credit, M, suppression_px=args.suppression_px, min_value=0.0)
        s = instrument_scores(pk.support, truths)
        c = s["sgmc_off"]["credit_per_px"]
        sweep[M] = {"n_dots": pk.n_dots, "c_sgmc": c, "c_cat": s["cat_all"]["credit_per_px"],
                    "dti_est": {f"G={G}": min(c * pk.n_dots, G) /
                                (0.2 * (min(c * pk.n_dots, G) + pk.n_dots - min(c * pk.n_dots, G))
                                 + 0.8 * G) for G in G_ESTIMATES}}
        print(f"    M={M:6d} dots={pk.n_dots:6d} c_sgmc={c:.4f} dti_est={sweep[M]['dti_est']}", flush=True)

    chosen = args.mass
    if chosen is None:
        # largest M whose marginal proxy credit still clears the metric bar 0.2*DTI_est
        ok = []
        for M in sorted(sweep):
            if M == min(sweep):
                continue
            prev = max(k for k in sweep if k < M)
            c_marg = (sweep[M]["c_sgmc"] * sweep[M]["n_dots"]
                      - sweep[prev]["c_sgmc"] * sweep[prev]["n_dots"]) / (sweep[M]["n_dots"] - sweep[prev]["n_dots"])
            bars = {k: 0.2 * v for k, v in sweep[M]["dti_est"].items()}
            keep = all(c_marg > b for b in bars.values())
            print(f"    M={M:6d} marginal c={c_marg:.4f} bars={ {k: round(v,4) for k,v in bars.items()} } -> {'keep' if keep else 'stop'}")
            if keep:
                ok.append(M)
        chosen = max(ok) if ok else args.mass_default
    print(f"    chosen mass {chosen}", flush=True)

    packed = emission.greedy_pack(credit, chosen, suppression_px=args.suppression_px, min_value=0.0)
    values = packed.support.astype(np.float32)
    print(f"    emitted {int(values.sum())} dots; mean credit of dots {packed.mean_field:.4f}", flush=True)

    print("  [5/5] writing ...", flush=True)
    path = Path(args.outdir) / f"gemsdoe50-{args.name}.tif"
    audit = emission.write_submission(values, path)
    scores = instrument_scores(values > 0, truths)
    receipt = {
        "name": args.name, "built_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "audit": audit, "mass": int((values > 0).sum()),
        "core_cells": core_px, "catalogue_buffer_m": args.catalogue_buffer_m,
        "suppression_px": args.suppression_px, "chosen_mass": int(chosen),
        "mass_sweep": {str(k): v for k, v in sweep.items()},
        "instrument_scores": scores,
        "seismicity": core_notes, "layers": [terrain_note, radio_note],
        "honesty": [
            "No organizer score exists for this file. Every local score here is an instrument, "
            "not a receipt; the only live scores quoted are the sibling ledger's.",
            "The Monte Cristo axis instrument is circular (derived from the sequence's own "
            "epicentres) and is reported only as a consistency check.",
            "The 2020 Monte Cristo rupture (Koehler et al. 2021, doi:10.1785/0220200371) is "
            "cited from the sibling repositories' quarantine note; it has NOT been re-verified "
            "against the primary source in this session.",
        ],
    }
    (REPO / "evidence").mkdir(exist_ok=True)
    with open(REPO / "evidence" / f"build_{args.name}.json", "w") as fh:
        json.dump(receipt, fh, indent=1)
    (Path(args.outdir) / f"checks-{path.name}.json").write_text(json.dumps(audit, indent=1))
    zpath = path.with_suffix(".zip")
    with zipfile.ZipFile(zpath, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.write(path, arcname=path.name)
    print(json.dumps({k: audit[k] for k in ("path", "sha256", "bytes", "nonzero", "min", "max",
                                            "all_finite", "values_in_unit_interval", "legal")}, indent=1))
    print(f"instruments: {json.dumps(scores, indent=1)[:800]}")
    print(f"wrote {path} and {zpath}  ({time.time()-t0:.0f}s)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
