#!/usr/bin/env python3
"""H61 merge-time adjudication: which file on ``main`` should the site recommend?

While H61 was in flight, two sessions merged new candidates to ``main`` (the
sibling's H59 sharpened-scarp scatter and the H60 union arm). ``main`` ended up
inconsistent: the H60 receipt (``evidence/h60_gate_decision.json``) records
``recommended_artifact = main H59 sharpened-scarp-scatter-90k`` while the pages
still led with H57. This script settles it with committed evidence:

1. **Eligibility (charter item 2, "never copy prior prediction pixels").** A file
   is eligible only if none of its dots lies on the frozen 61-artifact prior
   union (``registry/prior_positive_union.npz``). Also recorded: dots on or
   within 300 m of the supplied catalogue.
2. **Ranking instrument 1: the repository's frozen gate** (``validate_h56.py
   --truth-mode sgmc_off``), copied from the H60 receipt with its path.
3. **Ranking instrument 2: H61 frame A** (this session's vectorised scorer, the
   same truth and macrofold cores; false positives charged on every dot), with
   fold-by-fold results and paired 16-subtile bootstraps against H57 and
   against the recommended file.

The recommended file is the eligible file ranked first by the frozen gate; the
frame-A ranking is reported next to it and any disagreement is flagged.
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
sys.path.insert(0, str(REPO / "scripts"))

import build_h61 as B

from gemsdoe50.common import sha256_file
from gemsdoe50.holdout import build_spatial_blocks, load_split_spec

DL = "docs/downloads/"
CANDIDATES = {
    "H57-scarpstep-80000": {
        "tif": DL + "gemsdoe50-h57-scarpstep-80000-20261007T1830Z-allfinite.tif",
        "zip": DL + "gemsdoe50-h57-scarpstep-80000-20261007T1830Z-allfinite.zip",
        "nan": DL + "gemsdoe50-h57-scarpstep-80000-20261007T1830Z.tif",
        "entry_name": "GEMSDOE50-H57-SCARPSTEP",
        "gate_key": "H57-scarpstep-80000",
        "uses_comcat": False,
    },
    "H59-sharpened-scarp-scatter-90k": {
        "tif": DL + "gemsdoe50-h59-sharpened-scarp-scatter-90k-20261007T171954Z-allfinite.tif",
        "zip": DL + "gemsdoe50-h59-sharpened-scarp-scatter-90k-20261007T171954Z-allfinite.zip",
        "nan": DL + "gemsdoe50-h59-sharpened-scarp-scatter-90k-20261007T171954Z-nan.tif",
        "entry_name": "GEMSDOE50-H59-SHARPENED-SCARP-SCATTER-90K",
        "gate_key": "cross_session_competitor",
        "uses_comcat": False,
    },
    "H60-union-d0-75308": {
        "tif": DL + "gemsdoe50-h60-union-d0-75308-20261007T2250Z-allfinite.tif",
        "zip": DL + "gemsdoe50-h60-union-d0-75308-20261007T2250Z-allfinite.zip",
        "nan": DL + "gemsdoe50-h60-union-d0-75308-20261007T2250Z.tif",
        "entry_name": "GEMSDOE50-H60-UNION-75308",
        "gate_key": "H60-union-d0-75308",
        "uses_comcat": False,
    },
    "H60-officialstack-50000": {
        "tif": DL + "gemsdoe50-h60-officialstack-50000-20261007T2100Z-allfinite.tif",
        "zip": None,
        "nan": None,
        "entry_name": None,
        "gate_key": "official_stack_arm",
        "uses_comcat": False,
    },
    "H60-KDE-seiscombined-55000": {
        "tif": DL + "gemsdoe50-h60-combined-55000-20261007T212217Z-allfinite.tif",
        "zip": DL + "gemsdoe50-h60-combined-55000-20261007T212217Z-allfinite.zip",
        "nan": DL + "gemsdoe50-h60-combined-55000-20261007T212217Z-nan.tif",
        "entry_name": "GEMSDOE50-H60-SEISCOMBINED-55000",
        "gate_key": None,
        "uses_comcat": True,
    },
    "H60-KDE-targeted-40000": {
        "tif": DL + "gemsdoe50-h60-targeted-40000-20261007T212429Z-allfinite.tif",
        "zip": DL + "gemsdoe50-h60-targeted-40000-20261007T212429Z-allfinite.zip",
        "nan": DL + "gemsdoe50-h60-targeted-40000-20261007T212429Z-nan.tif",
        "entry_name": None,
        "gate_key": None,
        "uses_comcat": True,
    },
    "H59-topo-lineament-scatter-180k": {
        "tif": DL + "gemsdoe50-h59-topo-lineament-scatter-180k-20261007T170212Z-allfinite.tif",
        "zip": None,
        "nan": None,
        "entry_name": None,
        "gate_key": None,
        "uses_comcat": False,
    },
}
# Corrected short note for the recommended file: the sibling's published note cites the
# retracted transfer model ("operating point at 0.45"), so it is not reused verbatim.
NOTES = {
    "H59-sharpened-scarp-scatter-90k": (
        "GEMSDOE50 H59 rev2: blue-noise scatter, 90,000 dots on a 3-px lattice, sampling a sharpened "
        "rank-mean of the official band-19 slope-edge map and USGS 3DEP LiDAR scarp descriptors; no dot "
        "on a supplied-catalogue pixel or any prior-artifact pixel. Research model; no organizer score."
    ),
    "H57-scarpstep-80000": (
        "H57 stratified LiDAR-scarp + topographic-step dot emitter; every dot is >=300 m from the given "
        "catalogue and >=300 m from every other dot; research model, not organizer-scored."
    ),
    "H60-union-d0-75308": (
        "GEMSDOE50 H60 union: official-stack + LiDAR/topographic-step belief, 75,308 dots, >=300 m from the "
        "given catalogue, no prior-artifact pixel. Research model; no organizer score."
    ),
}


def _gate(receipt: dict, key: str | None) -> dict | None:
    if key is None:
        return None
    if key in receipt.get("candidates", {}):
        c = receipt["candidates"][key]
    else:
        c = receipt.get(key)
    if not isinstance(c, dict):
        return None
    return {k: c.get(k) for k in ("frozen_gate_pooled_dti", "frozen_gate_uniform", "frozen_gate_paired_ci95",
                                  "frozen_gate_folds_positive", "F1_pooled_dti")}


def main() -> int:
    t0 = time.time()
    receipt_path = REPO / "evidence/h60_gate_decision.json"
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    with rasterio.open(REPO / "data/grid/sample_submission.tif") as ds:
        valid = np.isfinite(ds.read(1))
        shape = ds.shape
    with rasterio.open(REPO / "data/grid/labels.tif") as ds:
        cat = ds.read(1) == 1
    dcat = ndimage.distance_transform_edt(~cat)
    domain = valid & (dcat > 3.0)
    with rasterio.open(REPO / "data/external/derived_sgmc_faults_100m_u8.tif") as ds:
        truth = domain & (ds.read(1) > 0)
    with np.load(REPO / "registry/prior_positive_union.npz", allow_pickle=False) as z:
        prior = np.unpackbits(z["packed"])[: shape[0] * shape[1]].astype(bool).reshape(shape)
    sc = B.FastScorer(truth)
    blocks, _ = build_spatial_blocks(valid, cat, load_split_spec(REPO / "evidence/holdout-v1.json"))
    cores, tiles = {}, []
    for b in blocks:
        r0, r1, c0, c1 = map(int, b.metadata["core_bounds"])
        m = np.zeros(shape, dtype=bool)
        m[r0:r1, c0:c1] = True
        cores[b.block_id] = m
        for tid, tr, tc, _e, _c in b.subtile_masks:
            t = np.zeros(shape, dtype=bool)
            t[tr[0]:tr[1], tc[0]:tc[1]] = True
            tiles.append((tid, t))
    all_cores = np.zeros(shape, dtype=bool)
    for m in cores.values():
        all_cores |= m

    rows: dict[str, dict] = {}
    subt: dict[str, list[float]] = {}
    for name, c in CANDIDATES.items():
        path = REPO / c["tif"]
        pred = B._read_positive(str(path))
        best = sc.best(pred)
        full = sc.components(pred, best, None, valid)
        core = sc.components(pred, best, all_cores, valid & all_cores)
        folds = {k: sc.components(pred, best, m, valid & m)["score"] for k, m in cores.items()}
        subt[name] = [sc.components(pred, best, t, valid & t)["score"] for _tid, t in tiles]
        rows[name] = {
            "artifact": c["tif"],
            "sha256": sha256_file(path),
            "bytes": path.stat().st_size,
            "dots": int(pred.sum()),
            "dots_on_prior_union": int((pred & prior).sum()),
            "dots_on_catalogue_pixels": int((pred & cat).sum()),
            "dots_within_300m_of_catalogue": int((pred & valid & (dcat <= 3.0)).sum()),
            "uses_comcat": c["uses_comcat"],
            "frame_a_full_pooled": full["score"],
            "frame_a_core_pooled": core["score"],
            "frame_a_credit_per_dot": full["credit_per_dot"],
            "frame_a_folds": folds,
            "frozen_gate": _gate(receipt, c["gate_key"]),
        }
        rows[name]["eligible_charter_item_2"] = rows[name]["dots_on_prior_union"] == 0
        rows[name]["eligible_rights"] = not c["uses_comcat"]
        print(f"[{time.time()-t0:5.1f}s] {name:<34} N={rows[name]['dots']:>7,} prior-reuse={rows[name]['dots_on_prior_union']:>6,} "
              f"full {full['score']:.4f} core {core['score']:.4f}", flush=True)

    def gate_val(n: str) -> float:
        g = rows[n]["frozen_gate"]
        return g["frozen_gate_pooled_dti"] if g and g.get("frozen_gate_pooled_dti") is not None else -1.0

    eligible = [n for n in rows if rows[n]["eligible_charter_item_2"] and rows[n]["eligible_rights"]
                and CANDIDATES[n]["entry_name"]]
    by_gate = sorted(eligible, key=gate_val, reverse=True)
    by_frame_a = sorted(eligible, key=lambda n: rows[n]["frame_a_core_pooled"], reverse=True)
    rec = by_gate[0]
    for n, row in rows.items():
        for ref in ("H57-scarpstep-80000", rec):
            if n == ref:
                continue
            d = [a - b for a, b in zip(subt[n], subt[ref])]
            row[f"bootstrap_vs_{ref}"] = B._bootstrap(d)
            row[f"fold_wins_vs_{ref}"] = sum(
                1 for k in cores if row["frame_a_folds"][k] > rows[ref]["frame_a_folds"][k]
            )
    c = CANDIDATES[rec]
    out = {
        "schema": "gemsdoe50.h61-candidates.v1",
        "generated_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "frozen_gate_source": str(receipt_path.relative_to(REPO)),
        "rules": {
            "eligibility": ("zero dots on registry/prior_positive_union.npz (charter item 2: never copy prior "
                            "prediction pixels) and no ComCat-derived input (contributor rights unresolved; charter item 13)"),
            "ranking": "frozen gate pooled DTI (validate_h56.py --truth-mode sgmc_off, as recorded in the H60 receipt); H61 frame A reported alongside",
        },
        "candidates": rows,
        "eligible_ranked_by_frozen_gate": by_gate,
        "eligible_ranked_by_frame_a_core": by_frame_a,
        "instruments_agree_on_first": by_gate[0] == by_frame_a[0],
        "recommended": {
            "name": rec,
            "artifact": c["tif"],
            "sha256": rows[rec]["sha256"],
            "bytes": rows[rec]["bytes"],
            "zip": c["zip"],
            "zip_sha256": sha256_file(REPO / c["zip"]) if c["zip"] else None,
            "nan_twin": c["nan"],
            "dots": rows[rec]["dots"],
            "entry_name": c["entry_name"],
            "note": NOTES[rec],
            "note_chars": len(NOTES[rec]),
        },
        "flags": [
            "H57 reuses prior prediction pixels and is therefore not eligible as the recommendation under charter item 2.",
            "The sibling's published portal note cites the retracted transfer model (hidden operating point 0.45); a corrected note is used here.",
            "The two H60-KDE files (PR #28) are ComCat-derived (rights unresolved), report their own off-catalogue DTI as 0.0744, and quote a 'modelled hidden DTI 0.54' from the retracted transfer model; they carry no frozen-gate receipt.",
            "The recommended file places some dots within 300 m of the supplied catalogue (1-px buffer, per the sibling's reading of staff rulings); the GEMSDOE32 B2 result suggests such dots may cost false-positive weight on the hidden labels.",
        ],
    }
    (REPO / "evidence/h61_candidates.json").write_text(json.dumps(out, indent=1) + "\n", encoding="utf-8")
    print(f"recommended: {rec}; gate order {by_gate}; frame-A order {by_frame_a}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
