#!/usr/bin/env python3
"""Build (and cache) the H53 label-free belief field, then report its anatomy.

Usage:  python3 scripts/h53_field.py [--out /home/user/.arena/run/h53_field.npz]
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from gems53 import field as F                                     # noqa: E402
from gems53.gridio import catalogue_distance, footprint, labels   # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="/home/user/.arena/run/h53_field.npz")
    ap.add_argument("--report", default=str(ROOT / "evidence/h53_field.json"))
    ap.add_argument("--buffer-px", type=float, default=2.0)
    args = ap.parse_args()
    t0 = time.time()
    inp = F.load_inputs()
    built = F.build_field(inp, buffer_px=args.buffer_px)
    belief = built["belief"].astype(np.float32)
    domain = built["domain"]
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(args.out, belief=belief, domain=domain.astype(np.uint8),
                        scarp=built["scarp"], radiometric=built["radiometric"])
    b = belief[domain]
    rep = {
        "built_utc": __import__("datetime").datetime.now(__import__("datetime").timezone.utc)
        .isoformat(timespec="seconds"),
        "seconds": round(time.time() - t0, 1),
        "inputs": {k: v for k, v in inp.notes.items() if isinstance(v, dict)},
        "components": built["details"],
        "buffer_px": args.buffer_px,
        "domain_cells": int(domain.sum()),
        "belief_stats": {"nonzero_in_domain": int((b > 0).sum()),
                         "p50": float(np.percentile(b, 50)) if b.size else 0.0,
                         "p90": float(np.percentile(b, 90)) if b.size else 0.0,
                         "p99": float(np.percentile(b, 99)) if b.size else 0.0,
                         "max": float(b.max()) if b.size else 0.0},
        "top1pct_area_px": int((belief >= np.percentile(belief[domain], 99.0)).sum()),
        "grid": {"height": int(belief.shape[0]), "width": int(belief.shape[1]),
                 "footprint_px": int(footprint().sum()), "catalogue_px": int(labels().sum()),
                 "catalogue_distance_min_in_domain": float(catalogue_distance()[domain].min())},
    }
    Path(args.report).parent.mkdir(parents=True, exist_ok=True)
    Path(args.report).write_text(json.dumps(rep, indent=1))
    print(json.dumps(rep, indent=1)[:2600])
    print(f"cached -> {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
