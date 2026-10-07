#!/usr/bin/env python3
"""H61 post-hoc sensitivity (exploratory; NOT used for any decision).

The frozen H61-S screens kept only 31 lineations, so a negative result could be
an artifact of over-screening. This script relaxes the screens one at a time and
re-measures the two quantities that carry the conclusion:

* the **stratified corridor enrichment** — mean metric credit K inside vs outside
  the corridors within H57-belief deciles (ratio > 1 means the corridors add
  information beyond scarp strength);
* the **mean K at the snapped corridor dots** vs the uniform base rate.

Variants: frozen; no triangle screen; no declustering and no triangle screen;
lenient lineation rules (H58-S1-like: elongation >= 2, length >= 0.5 km,
no thickness rule). The frozen decision in ``evidence/h61_build.json`` is not
changed by anything here.
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import numpy as np
import rasterio
from scipy import ndimage

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "src"))
from gemsdoe50 import h61


def main() -> int:
    t0 = time.time()
    with rasterio.open(REPO / "data/grid/sample_submission.tif") as ds:
        valid = np.isfinite(ds.read(1))
        transform = ds.transform
        shape = ds.shape
    with rasterio.open(REPO / "data/grid/labels.tif") as ds:
        catalogue = ds.read(1) == 1
    domain = valid & (ndimage.distance_transform_edt(~catalogue) > 3.0)
    with rasterio.open(REPO / "data/external/derived_sgmc_faults_100m_u8.tif") as ds:
        truth = domain & (ds.read(1) > 0)
    belief = np.load(REPO / ".arena/cache/h57_belief.npy")
    k_field = h61.kernel_credit_field(truth)
    base_rate = float(k_field[domain].mean())

    events, _ = h61.load_events(REPO / "data/external/usgs_comcat_earthquakes.csv.gz",
                                REPO / "data/grid/sample_submission.tif")
    keep_zbz, _ = h61.zbz_decluster(events)
    bg = events.subset(keep_zbz)
    keep_tri, _ = h61.triangle_keep(np.column_stack([bg.x, bg.y]))

    variants = {
        "frozen": bg.subset(keep_tri),
        "no_triangle": bg,
        "no_decluster_no_triangle": events,
    }
    out = {"base_rate_meanK_domain": base_rate, "variants": {}}
    saved = (h61.LIN_THICKNESS_FACTOR, h61.LIN_MIN_HALF_KM, h61.LIN_MIN_ELONGATION)
    runs = [(name, ev, False) for name, ev in variants.items()] + [("lenient_rules_no_triangle", bg, True)]
    for name, ev, lenient in runs:
        if lenient:
            h61.LIN_THICKNESS_FACTOR, h61.LIN_MIN_HALF_KM, h61.LIN_MIN_ELONGATION = 1e9, 0.5, 2.0
        lins, lr = h61.neighbourhood_lineations(ev)
        h61.LIN_THICKNESS_FACTOR, h61.LIN_MIN_HALF_KM, h61.LIN_MIN_ELONGATION = saved
        cors = h61.corridor_geometry(lins)
        union = h61.corridor_union(cors, shape, transform)
        enr = h61.stratified_corridor_enrichment(k_field, belief, union, domain)
        cand = h61.snap_corridor_dots(cors, belief, domain, transform)
        acc = h61.greedy_spaced(cand["rows"], cand["cols"], cand["vals"], shape, max_dots=10**7)
        kk = k_field[cand["rows"][acc], cand["cols"][acc]] if acc.size else np.zeros(0)
        kinds = cand["kind"][acc] if acc.size else np.zeros(0, dtype=np.int8)
        out["variants"][name] = {
            "events": len(ev),
            "lineations": len(lins),
            "corridor_union_cells_in_domain": int((union & domain).sum()),
            "snapped_dots": int(acc.size),
            "meanK_at_dots": float(kk.mean()) if kk.size else None,
            "meanK_at_dots_by_kind": {n: (float(kk[kinds == i].mean()) if (kinds == i).any() else None)
                                      for i, n in enumerate(h61.KIND_NAMES)},
            "enrichment_median_ratio": enr["median_ratio"],
            "enrichment_strata_gt_1": enr["strata_with_ratio_gt_1"],
            "enrichment_top3": enr["top3_strata_ratio"],
            "lineation_report": lr,
        }
        v = out["variants"][name]
        print(f"[{time.time()-t0:5.1f}s] {name:<28} events {v['events']:>6,} lineations {v['lineations']:>5} "
              f"dots {v['snapped_dots']:>6,} meanK {v['meanK_at_dots']} (base {base_rate:.4f}) "
              f"enrichment median {v['enrichment_median_ratio']:.3f} strata>1 {v['enrichment_strata_gt_1']}/10",
              flush=True)
    out["note"] = ("Exploratory and post-hoc: relaxations chosen after seeing the frozen result. "
                   "Snapped dots here use the off-catalogue domain without the uniqueness exclusions, "
                   "so they are an upper bound on what the seismic corridors can place.")
    (REPO / "evidence/h61_sensitivity.json").write_text(json.dumps(out, indent=1) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
