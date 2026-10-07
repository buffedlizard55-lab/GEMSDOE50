#!/usr/bin/env python3
"""ARCHIVED inventory checker; it does not authorize restoring or using these legacy files.

H50-S1 does not consume mixed-network ComCat or third-party derived scarp/radiometric rasters.
Their source-specific rights or derived-file reuse terms are unresolved. This utility only
checks legacy byte hashes; a hash match is not a license, provenance, or scientific approval.
"""
from __future__ import annotations

import hashlib
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
EXT = REPO / "data" / "external"

EXPECTED = {
    "usgs_comcat_earthquakes.csv.gz": None,  # hash recorded in registry/sources.json
    "derived_sgmc_faults_100m_u8.tif": "26d142c4c93282cd94f6950ab96f22aeff59fbbea523d43d662e76fa1b161b5c",
    "lidar_scarp_features_u8.tif": "d580bb8bdcdb941e32fefb8b38044bc5bf04e199bf2e83498c3576e6fc465568",
    "geodawn_rad_u8.tif": "c22420f75999030d7cc65c9e31e50d232ea6158423bca051613a18a8b20ba682",
}

RESTORE = {
    name: "Not approved for H50-S1; do not restore until source-specific rights and provenance are resolved."
    for name in EXPECTED
}


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def main() -> int:
    missing, bad = [], []
    for name, expected in EXPECTED.items():
        p = EXT / name
        if not p.exists():
            missing.append(name)
            continue
        if expected is not None:
            got = sha256(p)
            if got != expected:
                bad.append((name, got, expected))
        print(f"  ok      {name:36s} {p.stat().st_size:>12,d} B")
    for name, got, expected in bad:
        print(f"  BAD     {name}\n            got      {got}\n            expected {expected}")
    for name in missing:
        print(f"  MISSING {name}\n            {RESTORE.get(name, 'see registry/sources.json')}")
    if bad or missing:
        print("\nLegacy inventory is incomplete or mismatched; no H50-S1 build is authorized.")
        return 1
    print("\nLegacy bytes match their pins only; rights, source provenance, and H50-S1 use are not approved.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
