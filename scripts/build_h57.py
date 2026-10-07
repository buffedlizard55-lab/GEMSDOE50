"""H57-S submission builder — metric-exact scarp/step corridor emission.

Design constraints, each of which is a *measured* or *proved* requirement rather
than a preference:

1.  **Spacing >= 3 px.**  For a binary emitter whose positive cells are at least
    the kernel support (3 px = 300 m) apart, no two dots compete for the same
    truth pixel, so the metric collapses **exactly** to
    ``DTI = T / (0.2 N + 0.8 G)``.  Both quantities are then interpretable: ``N``
    is the dot count and ``T`` the hidden credit captured.  The best recorded
    artifacts in the corpus have a verified minimum nearest-neighbour spacing of
    2.83-3.00 px, so this is also the empirically winning geometry.
2.  **>= 300 m from the given catalogue.**  The scored truth is a set of faults
    the given catalogue does *not* contain, so a dot on a catalogue fault is a
    pure false positive (0.2) with no credit.  The corpus's best artifact
    (`h33-h33-2-b2`, 0.2778) is exactly its parent with the 6,436 dots that lie
    within 2 px of the catalogue deleted.
3.  **Raw, un-residualised scarp/step channels.**  On the F1 frame
    (`scripts/h57_screen_f1.py`) every LiDAR scarp descriptor scores higher raw
    than 9 x 9-residualised: `step_max` 2.94x vs 1.72x, `ex_max` 2.93x vs 2.10x,
    `downface_max` 2.85x vs 1.75x.  The H52/H56 builds shipped the residual
    form; this builder uses the raw one and mixes in an independent topographic
    step family taken from the 10 m DEM derivatives.
4.  **Whole-footprint emission.**  The LiDAR coverage mask covers 75.4 % of the
    study footprint, so a LiDAR-only emitter can never reach more than about
    three quarters of the truth however good it is.  Dots are therefore drawn
    from the union of a LiDAR scarp corridor set and a 10 m topographic step
    corridor set, and the mask is used only as a *rank* input.

This builder does **not** claim to beat the leaderboard record.  See
`docs/research/h57-verdict-20261007.md`: no offline frame in this repository has
demonstrated power against the real scores, so no honest claim is available.

Usage
-----
    python scripts/build_h57.py --inputs .arena/inputs --out docs/downloads \
        --mass 60000 --tag h57-scarpstep
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import time
import zipfile

import numpy as np
import rasterio
from rasterio.transform import Affine
from scipy import ndimage as ndi

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from h57_frames import R_PX, load_grid

GRID = {"shape": (3730, 3292), "crs": "EPSG:32611",
        "transform": (100.0, 0.0, 243350.0, 0.0, -100.0, 4508550.0)}

#: Channel sets.  Membership is decided by `scripts/h57_stratified.py`, which
#: intersects the F1 truth with an elevation stratum so that the terrain term is
#: approximately constant; a channel is admitted only if it wins in the pooled
#: strata.  The measured raw-channel stratified lifts (5 strata, 6,000 dots per
#: stratum, `evidence/h57_stratified.json`) are recorded beside each name.
#:
#: Rejected by the same test and therefore deliberately absent: the whole
#: geodetic strain family (`geod_2ndinv` 0.280, `geod_dilaterate` 0.357,
#: `geod_shearrate` 0.379 - all 0/5 strata won), every magnetic and radiometric
#: channel (0.42-0.98), `dem_mean` as a *detector* (1.309, i.e. the terrain
#: confound itself), the 9 x 9 residual transform of every channel (uniformly
#: below its raw form), and the earthquake-distance band `deq_n100a15` (0.337,
#: the weakest channel tested).
LIDAR_FAMILY = ("step_max", "lapneg_max", "ex_mean", "downface_max", "ex_max",
                "relief")          # stratified lifts 2.73 / 2.62 / 2.61 / 2.53 / 2.51 / 2.41
TOPO_FAMILY = ("slope_max", "hs_lineament", "curv_prof_absmax", "slope_std",
               "relief_local", "steep_frac")  # 2.61 / 2.49 / 2.35 / 2.15 / 2.27 / 2.11


def _rank01(a: np.ndarray, mask: np.ndarray) -> np.ndarray:
    out = np.full(a.shape, np.nan, dtype=np.float32)
    v = np.where(np.isfinite(a), a, np.nan)[mask]
    order = np.argsort(v)
    r = np.empty(v.size, dtype=np.float32)
    r[order] = np.arange(v.size, dtype=np.float32)
    out[mask] = r / max(v.size - 1, 1)
    return out


def _read_bands(path: str, names, wanted):
    with rasterio.open(path) as ds:
        descs = [d.split(" - ")[0].strip() if d else f"band{i}"
                 for i, d in enumerate(ds.descriptions, 1)]
        idx = {d: i for i, d in enumerate(descs, 1)}
        out = {}
        for w in wanted:
            a = ds.read(idx[w]).astype(np.float32)
            a[a < -1e30] = np.nan
            out[w] = a
    return out


def belief_field(inputs: str, footprint: np.ndarray):
    """Rank-mean of the LiDAR scarp family and the 10 m topographic step family."""
    lid = _read_bands(os.path.join(inputs, "lidar_scarp_features_u8.tif"),
                      None, LIDAR_FAMILY)
    top = _read_bands(os.path.join(inputs, "topo_u8.tif"), None, TOPO_FAMILY)
    lidar_rank = [_rank01(lid[n], footprint) for n in LIDAR_FAMILY if n in lid]
    topo_rank = [_rank01(top[n], footprint) for n in TOPO_FAMILY if n in top]
    lf = np.nanmean(np.stack(lidar_rank), axis=0)
    tf = np.nanmean(np.stack(topo_rank), axis=0)
    belief = np.nanmean(np.stack([lf, tf]), axis=0).astype(np.float32)
    return belief, {"lidar_channels": list(lid), "topo_channels": list(top)}


def metric_emit(belief: np.ndarray, eligible: np.ndarray, mass: int,
                block: int = 3, spacing: int = 3):
    """Metric-exact emission.

    One candidate per ``block`` x ``block`` tile (the tile's highest-belief
    eligible cell), then a greedy pass that accepts candidates in descending
    belief order while keeping every accepted pair at least ``spacing`` cells
    apart in Chebyshev distance.  With ``spacing = 3`` the accepted set satisfies
    the exact metric collapse ``DTI = T / (0.2 N + 0.8 G)``.
    """
    h, w = belief.shape
    b = np.where(eligible & np.isfinite(belief), belief, -np.inf)
    hh, ww = (h // block) * block, (w // block) * block
    tiles = b[:hh, :ww].reshape(hh // block, block, ww // block, block)
    tiles = tiles.transpose(0, 2, 1, 3).reshape(-1, block * block)
    best = np.argmax(tiles, axis=1)
    score = np.take_along_axis(tiles, best[:, None], axis=1)[:, 0]
    keep = np.isfinite(score)
    ti, bi = np.nonzero(keep)[0], best[keep]
    tr = (ti // (ww // block)) * block + (bi // block)
    tc = (ti % (ww // block)) * block + (bi % block)
    order = np.argsort(-score[keep], kind="stable")

    blocked = np.zeros((h, w), dtype=bool)
    sel_r, sel_c = [], []
    r0 = spacing - 1
    for k in order:
        if len(sel_r) >= mass:
            break
        r, c = int(tr[k]), int(tc[k])
        if blocked[r, c]:
            continue
        sel_r.append(r)
        sel_c.append(c)
        blocked[max(0, r - r0):r + r0 + 1, max(0, c - r0):c + r0 + 1] = True
    sel = np.zeros((h, w), dtype=bool)
    if sel_r:
        sel[np.array(sel_r), np.array(sel_c)] = True
    return sel


def verify_spacing(sel: np.ndarray) -> int:
    """Minimum Chebyshev separation between selected cells."""
    k = np.ones((5, 5), dtype=np.uint8)
    k[2, 2] = 0
    n = ndi.convolve(sel.astype(np.uint8), k, mode="constant")
    if (n[sel] > 0).any():
        return 1
    from scipy.spatial import cKDTree

    r, c = np.nonzero(sel)
    if r.size < 2:
        return 99
    d, _ = cKDTree(np.column_stack([r, c])).query(np.column_stack([r, c]), k=2,
                                                  workers=-1)
    return int(np.floor(d[:, 1].min()))


def write_tif(path: str, arr: np.ndarray, nodata=None):
    with rasterio.open(path, "w", driver="GTiff", height=GRID["shape"][0],
                       width=GRID["shape"][1], count=1, dtype="float32",
                       crs=GRID["crs"], transform=Affine(*GRID["transform"]),
                       nodata=nodata, compress="deflate", predictor=2) as ds:
        ds.write(arr.astype(np.float32), 1)


def sha256(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--inputs", default=".arena/inputs")
    ap.add_argument("--labels", default="data/grid/labels.tif")
    ap.add_argument("--out", default="docs/downloads")
    ap.add_argument("--mass", type=int, default=60000)
    ap.add_argument("--tag", default="h57-scarpstep")
    ap.add_argument("--stamp", default=None)
    ap.add_argument("--outdir-registry", default="evidence")
    args = ap.parse_args(argv)

    t0 = time.time()
    footprint, catalogue, transform, shape = load_grid(args.labels)
    assert shape == GRID["shape"], shape
    assert tuple(transform) == GRID["transform"], transform

    d_cat = ndi.distance_transform_edt(~catalogue)
    eligible = footprint & (d_cat > R_PX)

    belief, prov = belief_field(args.inputs, footprint)
    sel = metric_emit(belief, eligible, args.mass)
    n = int(sel.sum())

    stamp = args.stamp or time.strftime("%Y%m%dT%H%M%SZ", time.gmtime())
    base = f"gemsdoe50-{args.tag}-{n}-{stamp}"

    allf = np.where(sel, 1.0, 0.0).astype(np.float32)
    nanf = np.where(sel, 1.0, np.where(footprint, 0.0, np.nan)).astype(np.float32)

    os.makedirs(args.out, exist_ok=True)
    p_all = os.path.join(args.out, base + "-allfinite.tif")
    p_nan = os.path.join(args.out, base + ".tif")
    p_zip = os.path.join(args.out, base + "-allfinite.zip")
    write_tif(p_all, allf)
    write_tif(p_nan, nanf, nodata=float("nan"))
    with zipfile.ZipFile(p_zip, "w", zipfile.ZIP_DEFLATED) as z:
        z.write(p_all, os.path.basename(p_all))

    rep = {
        "generated_utc": stamp,
        "tag": args.tag,
        "mass_requested": args.mass,
        "dots": n,
        "min_chebyshev_spacing_px": verify_spacing(sel),
        "dots_within_300m_of_catalogue": int((sel & (d_cat <= R_PX)).sum()),
        "files": {
            "all_finite": {"path": p_all, "sha256": sha256(p_all),
                           "bytes": os.path.getsize(p_all)},
            "nan_outside": {"path": p_nan, "sha256": sha256(p_nan),
                            "bytes": os.path.getsize(p_nan)},
            "zip": {"path": p_zip, "sha256": sha256(p_zip),
                    "bytes": os.path.getsize(p_zip)},
        },
        "provenance": prov,
        "grid": {"shape": list(GRID["shape"]), "crs": GRID["crs"],
                 "transform": list(GRID["transform"]), "dtype": "float32"},
        "seconds": round(time.time() - t0, 1),
    }
    os.makedirs(args.outdir_registry, exist_ok=True)
    with open(os.path.join(args.outdir_registry, f"build_{args.tag}.json"), "w") as fh:
        json.dump(rep, fh, indent=1)
    print(json.dumps(rep, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
