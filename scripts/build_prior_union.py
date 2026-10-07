#!/usr/bin/env python3
"""Build a compact union of every hash-verified prior submission's positive pixels.

The full corpus remains scratch-only. The packed union is committed because final H55 placement
uses prior artifacts only as a negative originality mask; it never copies a prior positive pixel.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
import rasterio

ROOT = Path(__file__).resolve().parents[1]
LOCAL_PRIORS = (
    "docs/downloads/gems50-seislin-44709-20261006T2041Z-79e260ae.tif",
    "docs/downloads/gems51-scarpradio-offcat-35000-20261006-ecf058ea-allfinite.tif",
    "docs/downloads/gems51-scarpradio-offcat-35000-20261006-ecf058ea-nan.tif",
    "docs/downloads/gemsdoe50-h51-corridor-consensus-mix-20261007T0200Z-allfinite.tif",
    "docs/downloads/gemsdoe50-h51-corridor-consensus-mix-20261007T0200Z.tif",
)
MAX_POSITIVE_FRACTION = 0.05


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--corpus", default=".arena/prior_corpus")
    parser.add_argument("--registry", default="registry/prior_artifact_signatures.json")
    parser.add_argument("--output", default="registry/prior_positive_union.npz")
    args = parser.parse_args()

    corpus = ROOT / args.corpus
    registry_path = ROOT / args.registry
    registry = json.loads(registry_path.read_text(encoding="utf-8"))
    entries: list[tuple[str, Path, str, str]] = []
    for artifact in registry["artifacts"]:
        path = corpus / artifact["file"]
        if not path.is_file():
            raise FileNotFoundError(path)
        expected = str(artifact["sha256"])
        actual = _sha256(path)
        if actual != expected:
            raise ValueError(f"prior SHA-256 mismatch: {path}: {actual} != {expected}")
        entries.append((artifact["file"], path, actual, "registered-sibling"))
    for relative in LOCAL_PRIORS:
        path = ROOT / relative
        if not path.is_file():
            raise FileNotFoundError(path)
        entries.append((path.name, path, _sha256(path), "local-prior"))

    union: np.ndarray | None = None
    shape: tuple[int, int] | None = None
    unique: dict[str, tuple[str, Path, str, str]] = {}
    for entry in entries:
        unique.setdefault(entry[2], entry)
    names: list[str] = []
    hashes: list[str] = []
    kinds: list[str] = []
    counts: list[int] = []
    for name, path, digest, kind in unique.values():
        with rasterio.open(path) as ds:
            if ds.count != 1:
                raise ValueError(f"prior artifact is not single-band: {path}")
            if shape is None:
                shape = ds.shape
                union = np.zeros(shape, dtype=bool)
            elif ds.shape != shape:
                raise ValueError(f"prior artifact shape mismatch: {path}")
            values = ds.read(1)
        positive = np.isfinite(values) & (values > 0)
        if positive.mean() > MAX_POSITIVE_FRACTION:
            raise ValueError(f"prior artifact is not sparse enough to be a submission: {path}")
        assert union is not None
        union |= positive
        names.append(name)
        hashes.append(digest)
        kinds.append(kind)
        counts.append(int(positive.sum()))
    assert union is not None and shape is not None

    output = ROOT / args.output
    np.savez_compressed(
        output,
        packed=np.packbits(union.ravel()),
        shape=np.asarray(shape, dtype=np.int32),
        names=np.asarray(names),
        sha256=np.asarray(hashes),
        source_kind=np.asarray(kinds),
        positive_counts=np.asarray(counts, dtype=np.int64),
        registry_sha256=np.asarray(_sha256(registry_path)),
        registry_entries=np.asarray(len(registry["artifacts"]), dtype=np.int64),
        local_prior_entries=np.asarray(len(LOCAL_PRIORS), dtype=np.int64),
        all_source_entries=np.asarray(len(entries), dtype=np.int64),
        positive_cells=np.asarray(int(union.sum()), dtype=np.int64),
    )
    print(
        f"wrote {output.relative_to(ROOT)}: {len(entries)} assertions, "
        f"{len(unique)} unique file hashes, {int(union.sum()):,} union cells, "
        f"{output.stat().st_size:,} bytes"
    )


if __name__ == "__main__":
    main()
