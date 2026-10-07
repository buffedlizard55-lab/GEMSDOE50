"""Build the H57 feature cube on the official competition grid.

Outputs (all under the directory given by ``--out``):

  features.npy      float32 memmap, shape (H, W, F), one column per feature
  feature_names.json
  footprint.npy     bool, True inside the supplied study footprint
  aux_seis.npy      float32, the seismicity corridor field at 3 px half-width

Everything is read from the local input staging directory; no network access is
performed by this script.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from gems57 import features as F  # noqa: E402
from gems57 import seis as S  # noqa: E402

# ---------------------------------------------------------------- frozen lists
# Lineament transforms of the official stack.  Chosen for physical reason, frozen
# before any scoring: horizontal/vertical derivatives of the potential fields are
# classical fault-edge detectors; detrended elevation carries the topographic
# expression of young faults; conductivity/depth-to-basement carry basin margins.
GRAD_BANDS = [3, 9, 11, 12, 18, 19]
SALIENCY_BANDS = {2: [9, 11, 12, 17, 19], 4: [12, 19]}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--inputs", default=".arena/inputs")
    ap.add_argument("--grid", default="data/grid")
    ap.add_argument("--out", default=".arena/h57")
    args = ap.parse_args()

    inp = Path(args.inputs)
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)

    official = inp / "gems-geodawn-numerical-features.tif"
    lidar = inp / "lidar_scarp_features_u8.tif"
    scarp3m = inp / "h52_scarp3m_100m.tif"
    rad = inp / "geodawn_rad_u8.tif"

    for p in (official, lidar, scarp3m, rad, Path(args.grid) / "labels.tif"):
        F.assert_grid(p)
    print("grid assertions passed for all inputs")

    import rasterio

    with rasterio.open(Path(args.grid) / "labels.tif") as src:
        labels = src.read(1)
    footprint = labels != -1
    np.save(out / "footprint.npy", footprint)
    print("footprint cells:", int(footprint.sum()))

    # ---- seismicity corridor ------------------------------------------------
    from pyproj import Transformer

    tf = Transformer.from_crs("EPSG:4326", "EPSG:32611", always_xy=True)
    cat = S.load_trugman("data/external/nvreloc_catalog_newmag.txt.gz", tf)
    with rasterio.open(Path(args.grid) / "labels.tif") as src:
        transform = src.transform
        shape = (src.height, src.width)
    left, top = transform.c, transform.f
    cx = (cat.x - left) / 100.0
    cy = (top - cat.y) / 100.0
    inside = (cx >= 0) & (cx < shape[1]) & (cy >= 0) & (cy < shape[0]) & (cat.z >= 0.0)
    cat = S.Catalog(cat.x[inside], cat.y[inside], cat.z[inside], cat.mag[inside], cat.t[inside])
    print("catalogue events in footprint with depth>=0:", len(cat.x))
    thin = S.space_time_thin(cat)
    print("after 250 m x 90 d thinning:", len(thin.x))
    x, y, ang, hl = S.lineation_corridors(thin)
    print("accepted linear neighbourhoods:", len(x))
    axis_mask, corridor = S.corridor_raster(x, y, ang, hl, shape=shape, transform=transform)
    np.save(out / "aux_seis.npy", corridor)

    # distance to nearest event and 10 km event count
    from scipy import ndimage
    from scipy.spatial import cKDTree

    ev = np.zeros(shape, dtype=bool)
    ci = np.clip(np.rint(cx[inside]).astype(np.int64), 0, shape[1] - 1)
    ri = np.clip(np.rint(cy[inside]).astype(np.int64), 0, shape[0] - 1)
    ev[ri, ci] = True
    dist_ev = ndimage.distance_transform_edt(~ev).astype(np.float32)
    pts = np.column_stack([ri, ci]).astype(np.float64)
    tree = cKDTree(pts)
    grid_r, grid_c = np.mgrid[0 : shape[0] : 10, 0 : shape[1] : 10]
    q = np.column_stack([grid_r.ravel(), grid_c.ravel()]).astype(np.float64)
    cnt = np.asarray(tree.query_ball_point(q, r=100.0, return_length=True), dtype=np.float32)
    count_full = np.zeros(shape, dtype=np.float32)
    count_full[::10, ::10] = cnt.reshape(grid_r.shape)
    count_full = ndimage.gaussian_filter(count_full, 3.0).astype(np.float32)

    # ---- assemble -----------------------------------------------------------
    names: list[str] = []
    cols: list[np.ndarray] = []

    def add(name: str, arr: np.ndarray) -> None:
        a = np.asarray(arr, dtype=np.float32)
        if a.shape != shape:
            raise ValueError(f"{name}: shape {a.shape} != {shape}")
        names.append(name)
        cols.append(a)

    print("loading official stack ...")
    off = F.read_bands(official)
    band_desc = []
    with rasterio.open(official) as src:
        for i in range(1, src.count + 1):
            band_desc.append(src.tags(i).get("description", f"band{i}"))
    for i in range(off.shape[0]):
        add(f"o{i + 1:02d}_raw", off[i])

    print("lineament transforms of the official stack ...")
    for b in GRAD_BANDS:
        add(f"o{b:02d}_gradmag", F.grad_magnitude(off[b - 1]))
    for sigma, bands_ in SALIENCY_BANDS.items():
        for b in bands_:
            add(f"o{b:02d}_sal_s{sigma}", F.structure_tensor_saliency(off[b - 1], sigma))
    del off

    print("lidar scarp stack ...")
    lid = F.read_bands(lidar)
    for i in range(lid.shape[0]):
        add(f"lidar{i + 1:02d}", lid[i] / 255.0)
    lid_rank = F.rank_normalise(lid.max(axis=0), footprint)
    add("lidar_rankmean", lid_rank)
    add("lidar_rankmean_sal_s2", F.structure_tensor_saliency(np.nan_to_num(lid_rank, nan=0.0), 2.0))
    del lid, lid_rank

    print("3 m DEM scarp stack ...")
    s3 = F.read_bands(scarp3m)
    for i in range(s3.shape[0]):
        add(f"scarp3m{i + 1:02d}", s3[i])
    del s3

    print("radiometric stack ...")
    rd = F.read_bands(rad)
    for i in range(rd.shape[0]):
        add(f"rad{i + 1:02d}", rd[i] / 255.0)
    del rd

    print("seismicity ...")
    add("seis_corridor3", corridor)
    add("seis_corridor_log1p", np.log1p(corridor * 10.0))
    add("seis_dist_to_event", dist_ev)
    add("seis_count10km_log", np.log1p(count_full))

    cube = np.lib.format.open_memmap(
        out / "features.npy", mode="w+", dtype=np.float32, shape=(shape[0], shape[1], len(names))
    )
    chunk = 256
    for r0 in range(0, shape[0], chunk):
        r1 = min(r0 + chunk, shape[0])
        block = np.stack([c[r0:r1] for c in cols], axis=-1)
        cube[r0:r1] = block
    cube.flush()

    meta = {
        "shape": list(shape),
        "n_features": len(names),
        "names": names,
        "official_band_descriptions": band_desc,
        "grad_bands": GRAD_BANDS,
        "saliency_bands": {str(k): v for k, v in SALIENCY_BANDS.items()},
    }
    (out / "feature_names.json").write_text(json.dumps(meta, indent=1))
    print(f"wrote {out/'features.npy'} with {len(names)} features")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
