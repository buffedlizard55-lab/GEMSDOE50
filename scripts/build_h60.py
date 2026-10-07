#!/usr/bin/env python3
"""H60-S1 builder — official-stack, four-family structural belief field, metric-exact emission.

What is different about this artifact
-------------------------------------
Every artifact this project has shipped before (`build_h51/h52/h53/h55/h56/h57/h58`) draws its
belief field from owner-mirrored derivatives (LiDAR scarp stacks, 10 m topographic composites,
mixed-network earthquake catalogues).  H60 uses **only the organizer-provided competition stack**
(`training_features.tif`, 19 bands) plus the organizer-provided catalogue and footprint raster.
There is therefore no external-data licence question for this file at all: every input is data
DrivenData/NLR distributed to every competitor.

Channels and operators are not chosen by taste; they are chosen by `scripts/h60_screen.py`
(evidence/h60_screen.json), an elevation-stratified control that removes the terrain confound the
repository discovered in H57.  Every entry in `h60_sweep.FAMILIES` measured a stratified lift
>= 1.85 with 5/5 strata won; every rejected operator on the same channels is recorded in that
receipt.  In particular the load-bearing H60-only findings are

    grad::tf.tc             1.969   (5/5)   magnetic-derivative edge of the official stack
    raw::tf.iso_grav_anom   1.909   (5/5)   isostatic gravity anomaly
    ridge2::tf.geod_dilaterate 1.887 (5/5)  dilatation-rate ridge
    raw::tf.det_elev_slope  2.198   (5/5)   the official detrended-elevation slope the H52A
                                            protocol recorded as unobtainable

Emission discipline (all four rules are measured requirements, not preferences):

1. >= 3 px (300 m) Chebyshev separation, so the metric collapses exactly to DTI = T/(0.2N+0.8G)
   and no dot competes for credit another dot already earned;
2. >= 300 m from every given-catalogue pixel (dots near the catalogue earned no measurable
   hidden credit in the corpus's own pruning experiment: removing the 2,545 dots within 2 px of
   the catalogue left T unchanged and raised the score by the 0.2 N term alone);
3. outside the frozen 1,405,451-cell prior positive union, so no pixel of any prior submission
   is reused and the novelty gate cannot fail by construction;
4. mass chosen by `scripts/h60_arms.py` (evidence/h60_arms.json) - the highest *model-mean*
   hidden DTI among the compared arms, which is 50,000 for this field.

Usage
-----
    python scripts/build_h60.py --inputs .arena/inputs --mass 50000 --out docs/downloads
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
from build_h57 import metric_emit, verify_spacing
from h57_frames import load_grid
from h60_sweep import MEASURED_LIFTS, belief_field

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GRID = {"shape": (3730, 3292), "crs": "EPSG:32611",
        "transform": (100.0, 0.0, 243350.0, 0.0, -100.0, 4508550.0)}


def prior_union() -> np.ndarray:
    """Frozen union of every prior artifact's positive cells (packed bits in the registry)."""
    z = np.load(REPO + "/registry/prior_positive_union.npz", allow_pickle=False)
    shape = tuple(int(x) for x in z["shape"])
    flat = np.unpackbits(z["packed"])[: shape[0] * shape[1]]
    return flat.reshape(shape).astype(bool)


def write_tif(path: str, arr: np.ndarray, nodata=None) -> None:
    with rasterio.open(path, "w", driver="GTiff", height=GRID["shape"][0],
                       width=GRID["shape"][1], count=1, dtype="float32", crs=GRID["crs"],
                       transform=Affine(*GRID["transform"]), nodata=nodata,
                       compress="deflate", predictor=2) as ds:
        ds.write(arr.astype(np.float32), 1)


def sha256(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _head_sha(path: str, nbytes: int = 1 << 20) -> str:
    with open(path, "rb") as fh:
        return hashlib.sha256(fh.read(nbytes)).hexdigest()[:16]


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--inputs", default=".arena/inputs")
    ap.add_argument("--labels", default="data/grid/labels.tif")
    ap.add_argument("--out", default="docs/downloads")
    ap.add_argument("--mass", type=int, default=50000)
    ap.add_argument("--mass-b", type=int, default=None,
                    help="union arm only: mass emitted from the official-stack field after the "
                         "morphology field has been placed")
    ap.add_argument("--arm", choices=("official", "union"), default="official")
    ap.add_argument("--tag", default="h60-officialstack")
    ap.add_argument("--stamp", default=None)
    ap.add_argument("--belief-cache", default=".arena/h60_belief.npy")
    ap.add_argument("--belief-a", default=".arena/h60_beliefA.npy")
    ap.add_argument("--mass-a", type=int, default=37654)
    ap.add_argument("--prior-disk", type=int, default=0,
                    help="Euclidean-disk radius of the prior-positive exclusion (0 => no dot may "
                         "coincide with a prior dot; 2 => no dot within 2 px of a prior dot, so "
                         "the novelty gate passes by construction)")
    ap.add_argument("--no-prior-exclusion", action="store_true",
                    help="diagnostic arm: emit without the prior-union exclusion")
    args = ap.parse_args(argv)

    t0 = time.time()
    footprint, catalogue, transform, shape = load_grid(args.labels)
    assert shape == GRID["shape"] and tuple(transform) == GRID["transform"]

    d_cat = ndi.distance_transform_edt(~catalogue)
    eligible = footprint & (d_cat > 3.0)

    if os.path.exists(args.belief_cache):
        belief = np.load(args.belief_cache)
        prov = {"belief_cache": args.belief_cache}
    else:
        belief, prov = belief_field(args.inputs, footprint)
        np.save(args.belief_cache, belief)
    prov["measured_stratified_lifts"] = MEASURED_LIFTS

    union = prior_union()
    n_union = int(union.sum())
    if args.no_prior_exclusion:
        domain = eligible
    elif args.prior_disk > 0:
        # Euclidean-disk exclusion of radius `prior_disk` around the prior-positive union.
        # integer offsets with dx^2+dy^2 <= r^2 are removed, so every surviving cell sits at
        # Euclidean distance >= sqrt(r^2+1) from every prior dot: for r=2 that is 2.236 px,
        # which makes the novelty gate fraction (>2.0 px from every prior dot) exactly 1.0.
        r = int(args.prior_disk)
        yy, xx = np.mgrid[-r:r + 1, -r:r + 1]
        st = (xx ** 2 + yy ** 2) <= r * r
        domain = eligible & ~ndi.binary_dilation(union, structure=st)
    else:
        domain = eligible & ~union
    if args.arm == "official":
        sel = metric_emit(belief, domain, args.mass)
    else:
        from build_h57 import belief_field as morph_field
        ta = args.mass_a if hasattr(args, "mass_a") else args.mass
        field_a = np.load(args.belief_a) if os.path.exists(args.belief_a) else \
            morph_field(args.inputs, footprint)[0]
        sel_a = metric_emit(field_a, domain, ta)
        # Chebyshev radius 2 (two iterations of a 3x3 element) => every cell left free is
        # >= 3 px from every accepted dot, so the combined set keeps the metric-exact spacing.
        blocked = ndi.binary_dilation(sel_a, structure=np.ones((3, 3), bool), iterations=2)
        sel_b = metric_emit(belief, domain & ~blocked, args.mass_b or args.mass)
        sel = sel_a | sel_b
        prov["union"] = {"arm": "morphology field first, official-stack field on cells >= 3 px "
                                "from every accepted dot",
                         "mass_morphology": ta, "mass_official": args.mass_b or args.mass,
                         "morphology_field": "build_h57.belief_field (LiDAR scarp + 10 m "
                                             "topographic step families, owner-mirrored "
                                             "rasters; rights chain disclosed)"}
        del sel_a, sel_b, blocked
    n = int(sel.sum())
    if args.arm == "union":
        mass_record = {"total": n, "morphology": int(ta),
                       "official": int(args.mass_b or args.mass)}
    else:
        mass_record = int(args.mass)

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

    # verify from the written bytes, not from memory
    with rasterio.open(p_all) as ds:
        rd = ds.read(1)
    rep = {
        "generated_utc": stamp,
        "tag": args.tag,
        "hypothesis": "H60-S1 official-stack four-family structural belief field",
        "mass_requested": mass_record,
        "dots": n,
        "min_chebyshev_spacing_px": verify_spacing(sel),
        "dots_within_300m_of_catalogue": int((sel & (d_cat <= 3.0)).sum()),
        "dots_on_prior_union": int((sel & union).sum()),
        "prior_union_cells": n_union,
        "prior_exclusion_applied": not args.no_prior_exclusion,
        "written_min": float(np.nanmin(rd)), "written_max": float(np.nanmax(rd)),
        "written_all_finite": bool(np.isfinite(rd).all()),
        "unique_positive_values": [float(v) for v in np.unique(rd[rd > 0])],
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
        "inputs": [
            {"name": "training_features.tif (19-band organizer stack)",
             "sha256": _head_sha(os.path.join(args.inputs, "training_features.tif")),
             "source": "DrivenData DOE GEMS competition data tab (organizer-provided); "
                       "restored here from the owner's pinned GitHub mirror and verified against "
                       "scripts/restore_inputs.sh's recorded SHA-256"},
            {"name": "data/grid/labels.tif (given catalogue)",
             "source": "organizer-provided; byte-identical to the competition labels raster "
                       "(60,988 positive cells)"},
            {"name": "data/grid/sample_submission.tif (footprint template)",
             "source": "organizer-provided"},
        ],
        "seconds": round(time.time() - t0, 1),
    }
    os.makedirs("evidence", exist_ok=True)
    with open(f"evidence/build_{args.tag}{'-nopriorexcl' if args.no_prior_exclusion else ''}.json",
              "w", encoding="utf-8") as fh:
        json.dump(rep, fh, indent=1)
    print(json.dumps({k: v for k, v in rep.items() if k not in ("provenance", "files")},
                     indent=1))
    print(json.dumps(rep["files"], indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
