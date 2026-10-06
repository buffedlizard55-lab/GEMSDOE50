#!/usr/bin/env python3
"""Assemble the evidence layers and the fused belief field.

Components (each label-free — none of them reads the fault catalogue):

  struct   multi-physics lineament consensus: a Hessian line response at two scales
           on eight official bands, multiplied by the second-order orientation order
           parameter across the physics, so a pixel scores only if independent fields
           agree that a line exists *and which way it runs*.
  scarp    LiDAR scarp lineament chain: the 12-channel 1 m-DEM-derived scarp
           descriptor stack, decoded per its documented sqrt encoding, combined into
           a scarp-dipole score, skeletonised and chained with a 16-direction
           collinearity vote.  Roads/channels/terrace risers are the known
           confounders; the coherence channel and the dipole (face) requirement are
           what suppress them.
  seis     legacy seismicity-lineament corridors from a mixed-network ComCat extract
           (src/gems50/seis.py). Not new, not an H50-S1 input, and not cleared for
           external competition use until contributor rights are reviewed.
  cont     along-strike continuation of mapped traces: fault systems continue beyond
           their mapped terminations, which is where "new geometry of an existing
           system" lives.

Outputs go to /tmp/gems50 (scratch), never into the repository.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import rasterio

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from gems50 import grid, lineaments, seis  # noqa: E402

WORK = Path("/tmp/gems50")
FEATURES = Path("/tmp/gems_work/training_features.tif")
EXT = Path("/tmp/gems_work/external")
LABELS = Path("/tmp/gems_work/labels.tif")
CAT = Path("data/external/usgs_comcat_earthquakes.csv")

#: band order of the owner-derived scarp descriptor stack (from its own receipt:
#: docs/research/geothermal-vents-knowledge.md in GEMSDOE30 and the GEMSDOE24 metadata)
SCARP_BANDS = ["ex_max", "ex_mean", "step_max", "lapneg_max", "lappos_max",
               "downface_max", "upface_max", "cross_max", "relief", "coh100",
               "strike", "valid"]
#: channels documented as xmax-quantised: value = ((clip(q-1,0,254)/254))**2
SCARP_SQRT_BANDS = {"ex_max", "step_max", "lapneg_max", "lappos_max",
                    "downface_max", "upface_max", "cross_max"}


def load_footprint() -> np.ndarray:
    fp = WORK / "footprint.npy"
    if fp.exists():
        return np.load(fp)
    with rasterio.open("/tmp/gems_work/sample_submission.tif") as s:
        a = np.isfinite(s.read(1))
    np.save(fp, a)
    return a


def band(name: str, footprint: np.ndarray) -> np.ndarray:
    """Read one official band as float32 with the sentinel removed."""
    idx = [k for k, (n, _d) in grid.BANDS.items() if n == name]
    assert len(idx) == 1, f"unknown band {name}"
    with rasterio.open(FEATURES) as s:
        a = s.read(idx[0]).astype(np.float32)
    a[a < -1e37] = np.nan
    return a


def component_struct(footprint: np.ndarray, cache: Path) -> np.ndarray:
    out = cache / "comp_struct.npy"
    if out.exists():
        return np.load(out)
    physics = ["tmi", "rtp", "mag_anom", "iso_grav_anom", "cond_surf",
               "depth_to_base_surf", "det_elev", "tilt_angle"]
    responses, angles = [], []
    for name in physics:
        a = band(name, footprint)
        v = np.isfinite(a) & footprint
        a = np.nan_to_num(a, nan=0.0)
        r, ang = lineaments.line_response(a, v)
        r = lineaments.normalize(r, v, 60.0, 99.5)
        responses.append(r)
        angles.append(ang)
        print(f"  struct: {name} line response p99 {np.percentile(r[v], 99):.3f}")
    cons = lineaments.cross_physics_consensus(responses, angles, radius=5)
    cons = lineaments.normalize(cons, footprint, 50.0, 99.9)
    np.save(out, cons.astype(np.float32))
    del responses, angles
    return cons


def component_scarp(footprint: np.ndarray, cache: Path) -> np.ndarray:
    out = cache / "comp_scarp.npy"
    if out.exists():
        return np.load(out)
    with rasterio.open(EXT / "lidar_scarp_features_u8.tif") as s:
        raw = s.read().astype(np.float32)          # (12, H, W)
    chans = {}
    for i, name in enumerate(SCARP_BANDS):
        v = raw[i]
        if name in SCARP_SQRT_BANDS:
            v = (np.clip(v - 1.0, 0.0, 254.0) / 254.0) ** 2
        else:
            v = np.clip(v / 255.0, 0.0, 1.0)
        chans[name] = v
    valid = chans["valid"] > 0
    step = chans["step_max"]
    face = np.maximum(chans["upface_max"], chans["downface_max"])
    coh = chans["coh100"]
    dipole = np.sqrt(np.maximum(step * face, 0.0))
    scarp = dipole * np.sqrt(np.maximum(coh * valid, 0.0))
    print(f"  scarp: valid {valid.mean()*100:.1f} % of raster, "
          f"step p99 {np.percentile(step[valid], 99):.4f}, "
          f"scarp>0 on {100*(scarp>0).mean():.2f} % of raster")
    # chain vote: collinear continuations only
    for thr_pct in (98.0,):
        thr = np.percentile(scarp[valid], thr_pct)
        mask = (scarp >= thr) & valid
        vote = lineaments.chain_vote(mask, length_px=9, n_dirs=16, weights=scarp)
        print(f"  scarp: threshold p{thr_pct} -> {int(mask.sum())} px, "
              f"chained mean {vote[mask].mean():.3f}")
    vote = lineaments.normalize(vote, valid, 50.0, 99.5)
    np.save(out, vote.astype(np.float32))
    return vote


def component_seis(footprint: np.ndarray, cache: Path) -> tuple:
    out = cache / "comp_seis.npy"
    meta_out = cache / "seis_clusters.json"
    if out.exists():
        return np.load(out), json.loads(meta_out.read_text())
    events = seis.read_comcat(CAT, depth_max_km=30.0, mag_min=2.0)
    events = events.subset(seis.inside_footprint(events))
    cs = seis.correlation_scale(events, k=1, n_rand=10)
    print(f"  seis: {len(events)} events, r_c {cs['r_c_km']:.2f} km, "
          f"clustered {cs['clustered_fraction']*100:.1f} %")
    lab = seis.dbscan_labels(events, eps_km=5.0, min_samples=6)
    cl = seis.cluster_inertia(events, lab, min_events=8)
    lin = [c for c in cl if np.isfinite(c.elongation) and c.elongation >= 4.0
           and c.length_km >= 1.0]
    axis = seis.corridor_raster(lin, half_width_px=1.5)
    spread = lineaments.normalize(axis, footprint, 50.0, 99.9)
    meta = dict(n_events=len(events), r_c_km=cs["r_c_km"],
                clustered_fraction=cs["clustered_fraction"],
                n_clusters=len(cl), n_linear=len(lin),
                corridor_px=int((axis > 0).sum()),
                clusters=[dict(n=c.n, length_km=c.length_km, elongation=float(c.elongation),
                               lon=c.centroid_lonlat[0], lat=c.centroid_lonlat[1],
                               axis_deg=c.axis_angle_deg, sigma_km=c.sigma_km) for c in lin])
    np.save(out, spread.astype(np.float32))
    meta_out.write_text(json.dumps(meta, indent=1))
    return spread, meta


def component_cont(footprint: np.ndarray, cache: Path) -> np.ndarray:
    """Along-strike continuation of mapped traces (geometry only, no label learning).

    The catalogue is used *as geometry*: every mapped trace endpoint is extended
    along its local strike for a fixed distance, because fault systems continue
    beyond their mapped terminations.
    """
    out = cache / "comp_cont.npy"
    if out.exists():
        return np.load(out)
    from scipy.ndimage import binary_dilation, distance_transform_edt

    with rasterio.open(LABELS) as s:
        cat = (s.read(1) == 1)
    cont = np.zeros(cat.shape, dtype=np.float32)
    # local strike of the catalogue: structure tensor of a blurred catalogue
    from scipy.ndimage import gaussian_filter

    b = gaussian_filter(cat.astype(np.float32), 6.0)
    gy, gx = np.gradient(b)
    gxx = gaussian_filter(gx * gx, 6.0)
    gyy = gaussian_filter(gy * gy, 6.0)
    gxy = gaussian_filter(gx * gy, 6.0)
    theta = 0.5 * np.arctan2(2 * gxy, gxx - gyy)     # orientation of the structure
    # extend each trace pixel along the local strike direction
    H, W = cat.shape
    idx = np.argwhere(cat)
    for step in range(3, 31, 3):
        dr = np.round(step * np.sin(theta[tuple(idx.T)])).astype(int)
        dc = np.round(step * np.cos(theta[tuple(idx.T)])).astype(int)
        for sign in (+1, -1):
            rr = np.clip(idx[:, 0] + sign * dr, 0, H - 1)
            cc = np.clip(idx[:, 1] + sign * dc, 0, W - 1)
            cont[rr, cc] = np.maximum(cont[rr, cc], 1.0 - step / 40.0)
    # only keep the continuation *outside* the mapped traces
    cont[binary_dilation(cat, np.ones((3, 3), bool))] = 0.0
    d = distance_transform_edt(~cat)
    cont *= np.clip(1.0 - (d - 2.0) / 30.0, 0.0, 1.0)
    np.save(out, cont.astype(np.float32))
    return cont


def main() -> int:
    WORK.mkdir(parents=True, exist_ok=True)
    (WORK / "cache").mkdir(exist_ok=True)
    cache = WORK / "cache"
    fp = load_footprint()
    print(f"footprint {fp.sum():,} px")

    print("== struct ==")
    struct = component_struct(fp, cache)
    print("== scarp ==")
    scarp = component_scarp(fp, cache)
    print("== seis ==")
    seis_c, seis_meta = component_seis(fp, cache)
    print("== continuation ==")
    cont = component_cont(fp, cache)

    for name, arr in (("struct", struct), ("scarp", scarp), ("seis", seis_c), ("cont", cont)):
        v = arr[fp]
        print(f"{name:10s} max {v.max():.4f} mean {v.mean():.5f} "
              f"frac>0.05 {np.mean(v > 0.05)*100:.3f} %")

    stats = {name: dict(max=float(arr[fp].max()), mean=float(arr[fp].mean()),
                        frac_gt_005=float(np.mean(arr[fp] > 0.05)),
                        nonzero_px=int((arr > 0).sum()))
             for name, arr in (("struct", struct), ("scarp", scarp),
                               ("seis", seis_c), ("cont", cont))}
    stats["seis_meta"] = seis_meta
    (WORK / "component_stats.json").write_text(json.dumps(stats, indent=1))
    print(json.dumps({k: v for k, v in stats.items() if k != "seis_meta"}, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
