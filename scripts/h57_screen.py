"""H57 channel screen — which evidence channels carry information about faults
the given catalogue does not contain?

Instrument
----------
For a frame with truth mask ``T`` and eligible domain ``D`` the metric's own
local credit field is

    K(x) = max_{g in T} clip(1 - d(x, g) / 3, 0)

(the official 300 m triangular kernel, 3 px at 100 m). For an emitter that
places dots at least 3 px apart, the metric's weighted true-positive count is
``A = sum_{x in S} K(x)`` and its false-positive count is ``|S| - A``, so

    c_per_dot(S) = A / |S|

is exactly the numerator contribution per dot. The exact score is

    DTI = T / (0.2 T + 0.2 F + 0.8 G),  T = min(A, G),  F = |S| - A.

A uniformly random emitter earns ``mean(K)`` per dot, so the scale-free
statistic is ``lift = c_per_dot / mean(K over D)``, comparable across frames with
different truth density.

Why ``c_per_dot`` and not DTI
-----------------------------
The metric's marginal-inclusion rule (derived in ``docs/research/score-model.md``)
says a dot pays for itself while its expected new credit exceeds
``0.2 s (1 - k) / (1 - 0.2 s)``; at ``s = 0.3774`` that is ``0.0816 (1 - k)``.
For a dot 1.5 px from truth (``k = 0.5``) the required hit probability is about
**8.2 %**, versus a uniform baseline of a few percent. Resolving a threshold
that low needs a statistic measured on the metric's own kernel weight, which is
``c_per_dot``; raw "off-catalogue DTI" also carries the frame's ``0.8 G`` term
and so is not comparable between frames.

Usage
-----
    python scripts/h57_screen.py --inputs .arena/inputs --out evidence/h57_screen.json
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time

import numpy as np
from scipy import ndimage as ndi

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from h57_frames import build_frames, load_grid  # noqa: E402

DEFAULT_MASSES = (15000, 30000, 60000, 120000)


def nan_fill(a: np.ndarray) -> "tuple[np.ndarray, np.ndarray, float]":
    """Return (filled array, finite mask, fill value).

    ``scipy.ndimage.uniform_filter`` is a running-sum implementation: a single
    NaN contaminates the remainder of its row and every row below it. The
    competition feature cube carries a -3.4028235e38 sentinel outside the study
    footprint (and 3,061 stray sentinel pixels inside it), so every neighbourhood
    transform must be NaN-safe or it silently returns an all-NaN band. Verified
    in `tests/test_h57_screen.py::test_uniform_filter_nan_hazard`.
    """
    finite = np.isfinite(a)
    if finite.all():
        return a, finite, 0.0
    fill = float(np.nanmean(a)) if finite.any() else 0.0
    if not np.isfinite(fill):
        fill = 0.0
    return np.where(finite, a, fill).astype(np.float32), finite, fill


def _box9(a: np.ndarray) -> np.ndarray:
    b, finite, _ = nan_fill(a)
    return np.where(finite, ndi.uniform_filter(b, size=9, mode="nearest"), np.nan)


def _res9(a: np.ndarray) -> np.ndarray:
    """Local residual: value minus its 9 x 9 box mean (repository convention,
    `docs/research/h52-hypotheses.md`). NaN-safe."""
    b, finite, _ = nan_fill(a)
    return np.where(finite, a - ndi.uniform_filter(b, size=9, mode="nearest"), np.nan)


def _gradmag(a: np.ndarray) -> np.ndarray:
    b, finite, _ = nan_fill(a)
    gx = ndi.sobel(b, axis=1, mode="nearest")
    gy = ndi.sobel(b, axis=0, mode="nearest")
    return np.where(finite, np.hypot(gx, gy), np.nan)


def _ring_kernel(r: int) -> np.ndarray:
    k = np.zeros((2 * r + 1, 2 * r + 1), dtype=np.float32)
    k[r, r] = 1.0
    k += -np.ones_like(k) / (k.size - 1)
    return k


def _ridge(a: np.ndarray, r: int = 2) -> np.ndarray:
    b, finite, _ = nan_fill(a)
    return np.where(finite, np.maximum(ndi.convolve(b, _ring_kernel(r), mode="nearest"), 0.0),
                    np.nan)


TRANSFORMS = {
    "raw": lambda a: a,
    "res9": _res9,
    "grad": _gradmag,
    "ridge2": lambda a: _ridge(a, 2),
    "ridge4": lambda a: _ridge(a, 4),
}


class Rasters:
    """Lazy access to the hash-pinned input rasters."""

    FILES = {
        "tf": ("training_features.tif", 19),
        "lidar": ("lidar_scarp_features_u8.tif", 12),
        "topo": ("topo_u8.tif", 9),
        "rad": ("radiometric_u8.tif", 7),
        "grad": ("geodawn_rad_u8.tif", 4),
        "gext": ("geodawn_extensions_u8.tif", 4),
    }

    def __init__(self, inputs: str):
        self.inputs = inputs
        self._handles = {}
        self._descs = {}

    def _path(self, key):
        return os.path.join(self.inputs, self.FILES[key][0])

    def descriptions(self, key):
        if key not in self._descs:
            import rasterio

            with rasterio.open(self._path(key)) as ds:
                self._descs[key] = [
                    (d.split(" - ")[0].strip() if d else f"band{i}")
                    for i, d in enumerate(ds.descriptions, 1)
                ]
        return self._descs[key]

    def band(self, key, idx):
        import rasterio

        path = self._path(key)
        h = self._handles.get(path)
        if h is None:
            h = self._handles[path] = rasterio.open(path)
        a = h.read(idx).astype(np.float32)
        a[a < -1e30] = np.nan  # -3.4028235e38 nodata sentinel in the feature cube
        return a


def channels(rasters: Rasters, transforms, keys=None):
    """Yield (name, band array). Caller consumes immediately and drops it."""
    for key in (keys or rasters.FILES):
        for i, d in enumerate(rasters.descriptions(key), start=1):
            raw = rasters.band(key, i)
            for tname in transforms:
                name = f"{tname}::{key}.{d}"
                arr = raw if tname == "raw" else TRANSFORMS[tname](raw)
                yield name, np.asarray(arr, dtype=np.float32)


def _top_within(arr, domain, n_target):
    c = np.where(domain & np.isfinite(arr), arr, -np.inf)
    flat = c.ravel()
    n = min(n_target, int(np.isfinite(flat).sum()))
    if n <= 0:
        return np.zeros(domain.shape, dtype=bool)
    idx = np.argpartition(flat, -n)[-n:]
    out = np.zeros(flat.size, dtype=bool)
    out[idx] = True
    return out.reshape(domain.shape)


def _enrichment(arr, truth, domain):
    v = np.where(np.isfinite(arr), arr, np.nan)
    with np.errstate(invalid="ignore", divide="ignore"):
        t = np.nanmean(v[truth]) if truth.any() else np.nan
        d = np.nanmean(v[domain])
    return float(t / d) if np.isfinite(d) and d != 0.0 and np.isfinite(t) else float("nan")


def measure(channel, frames, masses):
    """Per-fold, per-mass exact credit counts for one channel."""
    out = {}
    for fname, fr in frames.items():
        row = {"truth_px": fr.n_truth, "domain_px": fr.domain_px,
               "base_c_per_dot": fr.base_c_per_dot,
               "enrichment": _enrichment(channel, fr.truth, fr.domain)}
        for m in masses:
            sel = _top_within(channel, fr.domain, m)
            n = int(sel.sum())
            if n == 0:
                row[f"m{m}"] = None
                continue
            credit = float(fr.K[sel].sum())
            row[f"m{m}"] = {"n_dots": n, "credit": credit}
        out[fname] = row
    return out


def pool(row, prefix="F2_cat_"):
    keys = [k for k in row if k.startswith(prefix)]
    base = float(np.mean([row[k]["base_c_per_dot"] for k in keys]))
    out = {"base_c_per_dot": base,
           "enrichment": float(np.nanmean([row[k]["enrichment"] for k in keys])),
           "folds": len(keys)}
    masses = sorted({int(k[1:]) for k in row[keys[0]] if k.startswith("m")})
    for m in masses:
        c = n = g = 0.0
        for k in keys:
            s = row[k].get(f"m{m}")
            if not s:
                continue
            c += s["credit"]
            n += s["n_dots"]
            g += row[k]["truth_px"]
        if n == 0:
            continue
        t = min(c, g)
        d = 0.2 * t + 0.2 * (n - c) + 0.8 * g
        out[f"m{m}"] = {"n_dots": n, "c_per_dot": c / n, "lift": (c / n) / base if base else np.nan,
                        "coverage": t / g, "dti": t / d if d > 0 else 0.0}
    return out


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--inputs", default=".arena/inputs")
    ap.add_argument("--labels", default="data/grid/labels.tif")
    ap.add_argument("--sgmc", default="data/external/derived_sgmc_faults_100m_u8.tif")
    ap.add_argument("--out", default="evidence/h57_screen.json")
    ap.add_argument("--transforms", default="raw,res9")
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--keys", default="")
    ap.add_argument("--no-incumbent", action="store_true")
    ap.add_argument("--masses", default=",".join(str(m) for m in DEFAULT_MASSES))
    args = ap.parse_args(argv)

    transforms = [t for t in args.transforms.split(",") if t]
    masses = [int(m) for m in args.masses.split(",") if m]
    import rasterio

    footprint, catalogue, transform, shape = load_grid(args.labels)
    with rasterio.open(args.sgmc) as ds:
        sgmc = ds.read(1) == 1
    with rasterio.open(os.path.join(args.inputs, "lidar_scarp_features_u8.tif")) as ds:
        valid = ds.read(12) > 0

    frames_all = build_frames(footprint, catalogue, sgmc, valid)
    frames = {k: v for k, v in frames_all.items() if k.startswith("F2_")}

    rast = Rasters(args.inputs)
    rows, t0 = [], time.time()
    keys = [k for k in args.keys.split(",") if k] or None
    for i, (name, arr) in enumerate(channels(rast, transforms, keys)):
        if args.limit and i >= args.limit:
            break
        rows.append({"channel": name, **measure(arr, frames, masses)})
        del arr
        if i % 15 == 0:
            print(f"  [{i:3d}] {name}  ({time.time() - t0:.0f}s)", flush=True)

    if args.no_incumbent:
        rows_out = rows
        _dump(rows_out, args, frames_all, masses, transforms, t0)
        return 0

    # incumbent: the LiDAR scarp rank-mean family shipped by H52/H56
    lid = {d: i for i, d in enumerate(rast.descriptions("lidar"), 1)}
    parts = [_rank(rast.band("lidar", lid[b]), footprint)
             for b in ("ex_max", "step_max", "lapneg_max", "downface_max", "relief")]
    parts.append(_rank(_res9(rast.band("lidar", lid["downface_max"])), footprint))
    parts.append(_rank(_res9(rast.band("lidar", lid["upface_max"])), footprint))
    inc = np.nanmean(np.stack(parts), axis=0).astype(np.float32)
    rows.append({"channel": "INCUMBENT_lidar_scarp_rankmean",
                 **measure(inc, frames, masses)})

    _dump(rows, args, frames_all, masses, transforms, t0)
    print_table(rows, masses[1] if len(masses) > 1 else masses[0])
    return 0


def _dump(rows, args, frames_all, masses, transforms, t0):
    rep = {
        "generated_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "frames": {k: v.detail for k, v in frames_all.items()},
        "masses": masses,
        "transforms": transforms,
        "n_channels": len(rows),
        "rows": rows,
    }
    os.makedirs(os.path.dirname(args.out) or ".", exist_ok=True)
    with open(args.out, "w") as fh:
        json.dump(rep, fh, indent=1)
    print(f"\nscreen: {len(rows)} channels in {time.time() - t0:.0f}s -> {args.out}")


def _rank(a, mask):
    a = np.where(np.isfinite(a), a, np.nan)
    out = np.full(a.shape, np.nan, dtype=np.float32)
    v = a[mask]
    order = np.argsort(v)
    r = np.empty(v.size, dtype=np.float32)
    r[order] = np.arange(v.size, dtype=np.float32)
    out[mask] = r / max(v.size - 1, 1)
    return out


def print_table(rows, mass):
    table = []
    for r in rows:
        p = pool(r)
        s = p.get(f"m{mass}")
        if s is None:
            continue
        table.append((s["lift"], r["channel"], p, s))
    print(f"\n{'channel':40s} {'base':>7s} {'c/dot':>7s} {'lift':>6s} "
          f"{'cov':>6s} {'DTI':>7s}   (mass {mass})")
    for lift, ch, p, s in sorted(table, reverse=True)[:35]:
        print(f"{ch[:40]:40s} {p['base_c_per_dot']:7.4f} {s['c_per_dot']:7.4f} "
              f"{s['lift']:6.3f} {s['coverage']:6.3f} {s['dti']:7.4f}")


if __name__ == "__main__":
    raise SystemExit(main())
