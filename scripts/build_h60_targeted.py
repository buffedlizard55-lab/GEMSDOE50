#!/usr/bin/env python3
"""Build H60-TARGETED: High-precision seismicity lineation at low mass.

Key insight: At lower masses, credit-per-dot matters more than coverage.
This variant uses:
- Very selective lineation criteria (only the strongest, most linear clusters)
- Aggressive sharpening (^16) to concentrate on peak features
- Lower mass (25,000-35,000 dots) for higher credit per dot
- Direct distance-weighted belief (no distance-to-faults blend)
"""
from __future__ import annotations
import argparse, hashlib, json, subprocess, time, zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
import numpy as np
import pandas as pd
import rasterio
from scipy import ndimage
from scipy.spatial import cKDTree
from pyproj import Transformer

REPO = Path(__file__).resolve().parents[1]
import sys
sys.path.insert(0, str(REPO / "src"))
from gemsdoe50 import h56
from gemsdoe50.common import jsonable, sha256_file
from gemsdoe50.metric import distance_weighted_tversky

R_PX = 3.0; ALPHA = 0.2; BETA = 0.8
MIN_MAG = 2.0  # higher magnitude for stronger signals
MAX_DEPTH_KM = 20.0  # shallower for surface-relevant events
MAX_H_ERR = 5.0  # tighter location quality
ANTHRO_BUF = 3_000.0
TRI_Q = 0.90; TRI_SEED = 20_261_007
LIN_K = 8; LIN_MIN_EV = 8; LIN_MIN_ELONG = 4.0; LIN_MIN_S1 = 1200.0
EMIT_SEED = 603_007
MASSES = (15_000, 20_000, 25_000, 30_000, 35_000, 40_000)
G_HIDDEN = 12_226; TRANSFER = 2.0

def _sha(p):
    d = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1<<20), b""): d.update(b)
    return d.hexdigest()

def _git():
    try: return subprocess.check_output(["git","rev-parse","HEAD"], text=True, stderr=subprocess.DEVNULL).strip()
    except: return None

def _wjson(p, v):
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(jsonable(v), indent=2, sort_keys=True, allow_nan=False)+"\n")

def run(args):
    t0 = time.time()
    comcat = Path(args.comcat); tpl = Path(args.template)
    lp = Path(args.labels); sgmc_p = Path(args.sgmc); out = Path(args.out)
    for p in [comcat, tpl, lp, sgmc_p]: assert p.exists(), f"Missing: {p}"
    
    with rasterio.open(tpl) as ds:
        shape = ds.shape; valid = np.isfinite(ds.read(1)); tf = ds.transform
    with rasterio.open(lp) as ds: labels = ds.read(1)
    cat = labels == 1
    kd = ndimage.distance_transform_edt(~cat, sampling=(100, 100))
    domain = valid & (kd > 300.0)
    with rasterio.open(sgmc_p) as ds: sg = ds.read(1)
    truth = domain & (sg > 0)
    print(f"[{time.time()-t0:.1f}s] domain={int(domain.sum()):,} truth={int(truth.sum()):,}", flush=True)

    # Load ComCat with stricter screens
    print("  Loading ComCat (M≥2.0, depth<20km)...", flush=True)
    df = pd.read_csv(comcat)
    n0 = len(df)
    nt = {"quarry blast","explosion","mining explosion","chemical explosion","nuclear explosion",
          "mine collapse","quarry","acoustic noise","sonic boom","rockslide","other event",
          "not reported","anthropogenic event"}
    if "type" in df.columns: df = df[~df["type"].astype(str).str.strip().str.lower().isin(nt)]
    df["mag"] = pd.to_numeric(df["mag"], errors="coerce")
    df = df[df["mag"] >= MIN_MAG].reset_index(drop=True)
    df["depth"] = pd.to_numeric(df["depth"], errors="coerce")
    df = df[np.isfinite(df["depth"]) & (df["depth"] < MAX_DEPTH_KM)].reset_index(drop=True)
    if "horizontalError" in df.columns:
        h = pd.to_numeric(df["horizontalError"], errors="coerce")
        df = df[~(np.isfinite(h) & (h > MAX_H_ERR))].reset_index(drop=True)

    transformer = Transformer.from_crs("EPSG:4326", "EPSG:32611", always_xy=True)
    lon = pd.to_numeric(df["longitude"], errors="coerce").to_numpy(np.float64)
    lat = pd.to_numeric(df["latitude"], errors="coerce").to_numpy(np.float64)
    x, y = transformer.transform(lon, lat)
    x, y = np.asarray(x, np.float64), np.asarray(y, np.float64)
    inv = ~tf; col_f, row_f = inv * (x, y)
    row = np.floor(row_f).astype(np.int64); col = np.floor(col_f).astype(np.int64)
    h, w = shape
    ok = (np.isfinite(lon) & np.isfinite(lat) & (row>=0) & (row<h) & (col>=0) & (col<w))
    df, x, y, row, col = df[ok].reset_index(drop=True), x[ok], y[ok], row[ok], col[ok]
    xy = np.column_stack((x, y))
    
    # Site screen
    anthro = df["type"].astype(str).str.strip().str.lower().isin({
        "explosion","quarry blast","nuclear explosion","chemical explosion",
        "mining explosion","mine collapse","quarry","acoustic noise","sonic boom","rockslide","anthropogenic event"})
    if anthro.any():
        at = cKDTree(xy[anthro]); d, _ = at.query(xy, k=1); keep = d > ANTHRO_BUF
        df, x, y, row, col, xy = df[keep].reset_index(drop=True), x[keep], y[keep], row[keep], col[keep], xy[keep]
    
    sigma_km = h56.epicentral_sigma_km(df)
    try: tdt = pd.to_datetime(df["time"], format="ISO8601", utc=True, errors="coerce")
    except: tdt = pd.to_datetime(df["time"], utc=True, errors="coerce")
    days = tdt.astype(np.int64) / (86400 * 1e9)
    n_final = len(df)
    print(f"  Events: {n0} -> {n_final} (M≥{MIN_MAG}, depth<{MAX_DEPTH_KM}km, h_err<{MAX_H_ERR}km)", flush=True)

    # Decluster
    keep, tri = h56.triangle_area_keep(xy, quantile=TRI_Q, seed=TRI_SEED)
    x, y, row, col, xy, sigma_km = x[keep], y[keep], row[keep], col[keep], xy[keep], sigma_km[keep]
    print(f"  Declustered: {int(keep.sum())} events", flush=True)

    # Lineations with strict criteria
    lin = h56.neighbourhood_lineations(xy, sigma_km*1000.0, k=LIN_K, min_events=LIN_MIN_EV,
                                        min_elongation=LIN_MIN_ELONG, min_sigma1_m=LIN_MIN_S1)
    print(f"  Strict lineations: {len(lin)}", flush=True)

    # Render
    a, e = float(tf.a), float(tf.e)
    belief = np.zeros(shape, dtype=np.float64)
    if len(lin) > 0:
        lpx = (lin.x - tf.c) / a; lpy = (lin.y - tf.f) / e
        for i in range(len(lin)):
            s1 = min(float(lin.sigma1_m[i])/abs(a), 6.0) * 2.5
            s2 = np.clip(float(lin.sigma_loc_m[i])/abs(a)*1.5, 1.0, 6.0)
            ux, uy = float(lin.ux[i]), float(lin.uy[i])
            uc, ur = ux, -uy
            n = int(np.ceil(3.5*max(s1,s2)))
            if n < 1: continue
            rr = np.arange(-n,n+1); cc = np.arange(-n,n+1)
            CC, RR = np.meshgrid(cc,rr)
            along = CC*uc + RR*ur; perp = -CC*ur + RR*uc
            g = np.exp(-0.5*((along/max(s1,1e-6))**2 + (perp/max(s2,1e-6))**2))
            g /= max(g.max(), 1e-12); g *= float(lin.weight[i])
            r0, c0 = round(lpy[i]), round(lpx[i])
            r1,r2,c1,c2 = r0-n, r0+n+1, c0-n, c0+n+1
            sr1,sr2,sc1,sc2 = max(r1,0),min(r2,h),max(c1,0),min(c2,w)
            if sr1<sr2 and sc1<sc2:
                sub = g[sr1-r1:sr2-r1, sc1-c1:sc2-c1]
                belief[sr1:sr2,sc1:sc2] = np.maximum(belief[sr1:sr2,sc1:sc2], sub)

    belief = ndimage.gaussian_filter(belief, 2.0)
    mx = float(belief.max())
    if mx > 0: belief /= mx
    belief = (belief) ** 16  # aggressive sharpening
    mx = float(belief.max())
    if mx > 0: belief /= mx
    belief[~valid] = 0.0
    print(f"  Belief: cells>0.01={int((belief>0.01).sum()):,}", flush=True)

    # Mass sweep
    print("  Mass sweep...", flush=True)
    results = {}
    for n in MASSES:
        em = h56.emit_blue_noise(belief, domain, n_target=n, min_sep_px=R_PX, seed=EMIT_SEED)
        if em.rows.size == 0: continue
        pred = np.zeros(shape, dtype=np.float32); pred[em.rows, em.cols] = 1.0
        r = distance_weighted_tversky(truth, pred)
        cpd = float(r.tp_weight) / max(r.prediction_cells, 1)
        ht = min(cpd * TRANSFER * n, G_HIDDEN)
        hdti = ht / (ALPHA * n + BETA * G_HIDDEN)
        ctrls = []
        for s in (1,2,3):
            c = h56.emit_blue_noise(np.ones(shape, dtype=np.float32), domain, n_target=n, min_sep_px=R_PX, seed=s)
            if c.rows.size > 0:
                p2 = np.zeros(shape, dtype=np.float32); p2[c.rows, c.cols] = 1.0
                ctrls.append(distance_weighted_tversky(truth, p2).score)
        ctrl = np.mean(ctrls) if ctrls else 0
        results[str(n)] = {"n":n,"dti":r.score,"cpd":cpd,"ctrl":ctrl,"lift":r.score/max(ctrl,1e-9),"hdti":hdti}
        print(f"    N={n:5d}: dti={r.score:.4f} ctrl={ctrl:.4f} lift={r.score/max(ctrl,1e-9):.2f}x cpd={cpd:.4f} model={hdti:.4f}", flush=True)
    
    best = max(results, key=lambda k: results[k]["hdti"])
    best_n = int(best)
    print(f"  Best: N={best_n}, model={results[best]['hdti']:.4f}", flush=True)

    # Emit
    em = h56.emit_blue_noise(belief, domain, n_target=best_n, min_sep_px=R_PX, seed=EMIT_SEED)
    pred = np.zeros(shape, dtype=np.float32); pred[em.rows, em.cols] = 1.0
    r = distance_weighted_tversky(truth, pred)
    print(f"  Final: {em.rows.size} dots, DTI={r.score:.4f}", flush=True)

    # Write
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    tag = f"h60-targeted-{best_n}-{ts}"
    
    def wtiff(path, zero):
        with rasterio.open(tpl) as src: prof = src.profile.copy()
        v = pred.astype(np.float32)
        if zero: v[~valid] = 0.0; nd = None
        else: v[~valid] = np.nan; nd = np.nan
        prof.update(driver="GTiff", count=1, dtype="float32", nodata=nd,
                    compress="DEFLATE", predictor=3, tiled=True, blockxsize=256, blockysize=256)
        with rasterio.open(path, "w", **prof) as dst: dst.write(v, 1)
        with rasterio.open(path) as ds:
            rr = ds.read(1); ff = rr[np.isfinite(rr)]
            assert float(ff.min()) >= 0 and float(ff.max()) <= 1
            if zero: assert np.all(np.isfinite(rr))
        return {"path":str(path),"bytes":path.stat().st_size,"sha256":_sha(path),
                "positive":int(np.count_nonzero(rr>0)),"min":float(ff.min()),"max":float(ff.max())}

    af = out / f"gemsdoe50-{tag}-allfinite.tif"
    afm = wtiff(af, True)
    nn = out / f"gemsdoe50-{tag}-nan.tif"
    nnm = wtiff(nn, False)
    zf = out / f"gemsdoe50-{tag}-allfinite.zip"
    with zipfile.ZipFile(zf, "w", zipfile.ZIP_DEFLATED) as z: z.write(af, af.name)

    # Uniqueness
    miou = 0.0
    for pf in out.glob("*.tif"):
        if pf in (af, nn): continue
        try:
            with rasterio.open(pf) as ds: pd2 = ds.read(1)
            if pd2.shape != shape: continue
            ii = np.count_nonzero((pd2>0)&(pred>0)); uu = np.count_nonzero((pd2>0)|(pred>0))
            miou = max(miou, ii/max(uu,1))
        except: continue

    rep = {
        "h":"H60-TARGETED","ts":ts,"git":_git(),
        "catalog":{"n0":n0,"n_final":n_final,"mag_min":MIN_MAG,"depth_max":MAX_DEPTH_KM},
        "emission":{"n":best_n,"emitted":em.rows.size,"seed":EMIT_SEED},
        "score":{"dti":float(r.score),"tp":float(r.tp_weight),"cpd":float(r.tp_weight)/max(em.rows.size,1)},
        "sweep":results,"transfer":{"f":TRANSFER,"G":G_HIDDEN,"model":results[best]["hdti"]},
        "uniqueness":{"max_iou":miou},
        "limits":["2-D covariance UNVERIFIED adaptation","SGMC proxy sub-unity lift expected",
                  "Transfer factor 2.0 is conservative guess for seismicity"],
    }
    _wjson(out/f"checks-{tag}.json", rep)
    print(f"\n  Written: {af}\n  SHA256: {afm['sha256']}\n  Uniqueness IoU: {miou:.4f}", flush=True)
    print(f"  Done in {time.time()-t0:.1f}s", flush=True)

if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--comcat", default=str(REPO/"data/external/usgs_comcat_earthquakes.csv.gz"))
    p.add_argument("--template", default=str(REPO/"data/grid/sample_submission.tif"))
    p.add_argument("--labels", default=str(REPO/"data/grid/labels.tif"))
    p.add_argument("--sgmc", default=str(REPO/"data/external/derived_sgmc_faults_100m_u8.tif"))
    p.add_argument("--out", default=str(REPO/"docs/downloads"))
    run(p.parse_args())