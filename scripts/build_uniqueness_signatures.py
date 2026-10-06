#!/usr/bin/env python3
"""Freeze a compact signature of every prior artifact on this grid.

The full prior-artifact corpus lives only on the development machine (it is several
hundred MB of GeoTIFFs).  To let the uniqueness gate run on a bare CI runner, each
artifact is reduced to a 32x-downsampled occupancy bitmask (block-max), its sha256 and
its dot count.  A 32x mask cannot prove fine-scale novelty, but it *does* catch the
failure that matters — shipping a copy, or a near-copy, of an earlier file — because
any artifact that reproduces an earlier support will overlap block-for-block.
"""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

import numpy as np
import rasterio

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from gems50 import grid  # noqa: E402

sys.path.insert(0, str(ROOT / "scripts"))
from check_submission import CORPUS_DIRS, MAX_POSITIVE_FRACTION  # noqa: E402

FACTORS = (8, 32)


def coarse(mask: np.ndarray, factor: int = 8) -> np.ndarray:
    h, w = mask.shape
    h2, w2 = h // factor * factor, w // factor * factor
    blocks = mask[:h2, :w2].reshape(h2 // factor, factor, w2 // factor, factor)
    return blocks.any(axis=(1, 3))


def main() -> int:
    out = ROOT / "registry" / "prior_artifact_signatures.npz"
    names, shas, counts, masks = [], [], [], []
    for d in CORPUS_DIRS:
        if not d.exists():
            continue
        for f in sorted(d.glob("*.tif")):
            try:
                with rasterio.open(f) as s:
                    if (s.height, s.width) != grid.SHAPE:
                        continue
                    a = s.read(1)
                pos = np.isfinite(a) & (a > 0)
                if pos.sum() > MAX_POSITIVE_FRACTION * a.size:
                    continue
                names.append(f.name)
                shas.append(hashlib.sha256(f.read_bytes()).hexdigest())
                counts.append(int(pos.sum()))
                masks.append([np.packbits(coarse(pos, f)) for f in FACTORS])
            except Exception as exc:  # noqa: BLE001
                print(f"  skipped {f.name}: {exc}")
    if not names:
        print("no artifacts found — run this where the corpus exists")
        return 1
    cshapes = [coarse(np.ones(grid.SHAPE, bool), f).shape for f in FACTORS]
    payload = dict(names=np.array(names), sha256=np.array(shas), counts=np.array(counts),
                   factors=np.array(FACTORS), grid_shape=np.array(grid.SHAPE),
                   coarse_shapes=np.array(cshapes))
    for j, f in enumerate(FACTORS):
        payload[f"masks_block{f}"] = np.stack([m[j] for m in masks])
    np.savez_compressed(out, **payload)
    print(f"wrote {out} ({out.stat().st_size:,} B): {len(names)} artifacts at "
          f"blocks {FACTORS}, coarse shapes {[list(c) for c in cshapes]}")
    (ROOT / "registry" / "prior_artifact_signatures.json").write_text(json.dumps(
        {"artifacts": [{"file": n, "sha256": s, "dots": c} for n, s, c in zip(names, shas, counts)],
         "downsample_blocks": list(FACTORS)}, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
