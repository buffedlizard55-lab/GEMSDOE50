#!/usr/bin/env python3
"""Verify the external data the build depends on, and say exactly what to do if it is missing.

Nothing is downloaded here: DrivenData is login-gated and the official USGS sources are large.
This script only *verifies* and *explains*, so that a missing file can never turn into a silently
different submission.
"""
from __future__ import annotations

import hashlib
import sys
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
    "lidar_scarp_features_u8.tif":
        "copy from buffedlizard55-lab/GEMSDOE24 data/external/ (byte-identical), or rebuild from "
        "the official USGS 3DEP 1 m tiles listed at https://apps.nationalmap.gov/downloader/",
    "geodawn_rad_u8.tif":
        "copy from buffedlizard55-lab/GEMSDOE24 data/external/, or re-fetch from "
        "https://doi.org/10.5066/P93LGLVQ (ScienceBase 657e1d85d34e23d3533209f7), archives "
        "22103_area1_tiffs.zip / 22103_area2_tiffs.zip",
    "usgs_comcat_earthquakes.csv.gz":
        "fetch with the FDSN event service query recorded in registry/sources.json, then gzip",
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
        print("\nThe build is refused until the hashes match; a different file would be a different submission.")
        return 1
    print("\nall external data present and hash-verified")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
