#!/usr/bin/env python3
"""Build H52: the union of the frozen H51 support and the new H52-A support.

Registered in ``docs/h52a-protocol.md`` amendment B1, *after* H52-A was measured standalone and
found to cover less of the SGMC-off instrument than H51 on its own (lower absolute DTI at its
own best mass), but to occupy an almost entirely disjoint population of cells (1.7% overlap).
This script performs **no new threshold search**: it reads the two already-written, already-
frozen rasters and takes their pixelwise union. Any genuine difference between runs would come
only from re-running `build_h51.py` or `build_h52a.py`, not from a knob in this file.
"""
from __future__ import annotations

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

from gems51 import emit, instruments
from gems51 import grid as g51
from gemsdoe50 import common

CATALOG = REPO / "data" / "external" / "usgs_comcat_earthquakes.csv.gz"
SGMC = REPO / "data" / "external" / "derived_sgmc_faults_100m_u8.tif"
H51_FILE = REPO / "docs" / "downloads" / "gems51-scarpradio-offcat-35000-20261006-ecf058ea-nan.tif"


def monte_cristo_trend(valid: np.ndarray) -> np.ndarray:
    import pandas as pd
    from pyproj import Transformer
    MC_EPICENTRE = (425569.0, 4224896.0)
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
    started = time.time()
    build_h52a = json.loads((REPO / "evidence" / "build_h52a.json").read_text(encoding="utf-8"))
    h52a_file = REPO / build_h52a["outputs"]["primary"]["path"]

    valid = g51.load_footprint()
    labels = g51.load_labels()
    catalogue_distance = distance_transform_edt(~labels)
    off_catalogue = (catalogue_distance > 3) & valid
    sgmc, _ = g51.load_raster(SGMC)
    sgmc_off = (sgmc > 0) & off_catalogue
    mc = monte_cristo_trend(valid)
    truths = {"catalogue": labels, "sgmc_off": sgmc_off, "monte_cristo": mc}

    with rasterio.open(H51_FILE) as ds:
        h51 = ds.read(1)
    with rasterio.open(h52a_file) as ds:
        h52a = ds.read(1)
    h51_support = np.isfinite(h51) & (h51 > 0)
    h52a_support = np.isfinite(h52a) & (h52a > 0)
    union = h51_support | h52a_support
    overlap = int(np.count_nonzero(h51_support & h52a_support))

    print(f"H51 mass={int(h51_support.sum()):,} H52A mass={int(h52a_support.sum()):,} "
          f"overlap={overlap:,} union mass={int(union.sum()):,}", flush=True)

    scores = {
        "h51_alone": instruments.all_instruments(h51_support, truths),
        "h52a_alone": instruments.all_instruments(h52a_support, truths),
        "union": instruments.all_instruments(union, truths),
    }
    rng = np.random.default_rng(5200)
    control, _ = emit.pack(np.where(off_catalogue, rng.random(valid.shape).astype(np.float32), 0.0),
                           int(union.sum()), valid=off_catalogue, suppression_px=3.0)
    scores["random_control_at_union_mass"] = instruments.all_instruments(control, truths)
    for k in ("h51_alone", "h52a_alone", "union", "random_control_at_union_mass"):
        print(f"  {k}: sgmc_off_dti={scores[k]['sgmc_off']['dti']:.4f} "
              f"sgmc_off_cpdot={scores[k]['sgmc_off']['credit_per_dot']:.4f} "
              f"mc_tpw={scores[k]['monte_cristo']['tp_weight']:.2f}", flush=True)

    content_id = common.sha256_array(union.astype(np.uint8))[:8]
    stamp = time.strftime("%Y%m%dT%H%M%SZ", time.gmtime())
    name = f"gems52-union-h51-h52a-offcat-{int(union.sum())}-{stamp}-{content_id}"
    primary = REPO / "docs" / "downloads" / f"{name}-nan.tif"
    allfinite = REPO / "docs" / "downloads" / f"{name}-allfinite.tif"
    values = union.astype(np.float32)
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

    unique = uniqueness_gate(union, valid)

    report = {
        "schema": "gems52.build.v1",
        "built_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "builder": {"script": "scripts/build_h52.py", "sha256": common.sha256_file(Path(__file__))},
        "protocol": "docs/h52a-protocol.md amendment B1 (2026-10-07)",
        "name": name,
        "inputs": {
            "h51_file": {"path": str(H51_FILE.relative_to(REPO)), "sha256": common.sha256_file(H51_FILE),
                        "mass": int(h51_support.sum())},
            "h52a_file": {"path": str(h52a_file.relative_to(REPO)), "sha256": common.sha256_file(h52a_file),
                         "mass": int(h52a_support.sum())},
        },
        "overlap_cells": overlap,
        "overlap_fraction_of_h52a": overlap / max(int(h52a_support.sum()), 1),
        "union_mass": int(union.sum()),
        "runtime_seconds": round(time.time() - started, 1),
        "scores": scores,
        "uniqueness": unique,
        "outputs": checks,
        "honesty": [
            "No organizer score exists for this file and none is claimed.",
            ("This is a pixelwise union of two already-frozen, independently built supports; no "
            "threshold in this script was chosen by looking at the resulting DTI."),
            ("H52-A alone has a lower pooled SGMC-off DTI than H51 alone because it emits far "
            "fewer dots (10,000 vs 35,000); its contribution is measured as an addition to H51, "
            "not as a replacement."),
            ("Monte Cristo is reported as a weak guard only, never as a selection criterion "
            "(H51 amendment A3)."),
        ],
    }
    (REPO / "evidence").mkdir(exist_ok=True)
    (REPO / "evidence" / "build_h52.json").write_text(json.dumps(report, indent=1), encoding="utf-8")
    print(json.dumps({"name": name, "mass": int(union.sum()), "sha256": audit["sha256"],
                      "sgmc_off_dti": scores["union"]["sgmc_off"]["dti"],
                      "improvement_over_h51": scores["union"]["sgmc_off"]["dti"] - scores["h51_alone"]["sgmc_off"]["dti"],
                      "unique_max_jaccard": unique["max_jaccard"]}, indent=1))
    print(f"done in {time.time() - started:.0f}s")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
