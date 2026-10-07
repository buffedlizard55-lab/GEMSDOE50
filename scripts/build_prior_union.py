#!/usr/bin/env python3
"""Build a compact union of every hash-verified prior submission's positive pixels.

The full corpus remains scratch-only. The packed union is committed because final H55 placement
uses prior artifacts only as a negative originality mask; it never copies a prior positive pixel.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
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
    "docs/downloads/gems52-union-h51-h52a-offcat-44828-20261007T021528Z-990213fd-allfinite.tif",
    "docs/downloads/gems52-union-h51-h52a-offcat-44828-20261007T021528Z-990213fd-nan.tif",
    "docs/downloads/gems52a-scarpdrainage-offcat-10000-20261007T021452Z-5c377a13-allfinite.tif",
    "docs/downloads/gems52a-scarpdrainage-offcat-10000-20261007T021452Z-5c377a13-nan.tif",
    "docs/downloads/gemsdoe50-h53-tmiconj-20261007T0345Z-allfinite.tif",
    "docs/downloads/gemsdoe50-h53-tmiconj-20261007T0345Z.tif",
    # Byte-identical second copies merged under downloads/ by PR #14. Keep both
    # source assertions in the receipt; SHA-256 deduplication ensures each
    # unique prediction contributes to the union exactly once.
    "downloads/gemsdoe50-h53-tmiconj-20261007T0345Z-allfinite.tif",
    "downloads/gemsdoe50-h53-tmiconj-20261007T0345Z.tif",
)
MAX_POSITIVE_FRACTION = 0.05


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _positive_count(path: Path) -> int:
    with rasterio.open(path) as dataset:
        values = dataset.read(1)
    return int((np.isfinite(values) & (values > 0)).sum())


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--corpus", default=".arena/prior_corpus")
    parser.add_argument("--registry", default="registry/prior_artifact_signatures.json")
    parser.add_argument("--output", default="registry/prior_positive_union.npz")
    parser.add_argument(
        "--receipt",
        default="evidence/results/h55-prior-corpus-receipt-20261007.json",
    )
    args = parser.parse_args()

    corpus = ROOT / args.corpus
    registry_path = ROOT / args.registry
    receipt_path = ROOT / args.receipt
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
    positive_mask_hashes: list[str] = []
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
        positive_mask_hashes.append(
            hashlib.sha256(np.packbits(positive.ravel()).tobytes()).hexdigest()
        )
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
        positive_mask_sha256=np.asarray(positive_mask_hashes),
        source_kind=np.asarray(kinds),
        positive_counts=np.asarray(counts, dtype=np.int64),
        registry_sha256=np.asarray(_sha256(registry_path)),
        registry_entries=np.asarray(len(registry["artifacts"]), dtype=np.int64),
        local_prior_entries=np.asarray(len(LOCAL_PRIORS), dtype=np.int64),
        all_source_entries=np.asarray(len(entries), dtype=np.int64),
        positive_cells=np.asarray(int(union.sum()), dtype=np.int64),
    )

    previous_receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    registered_receipts = [
        item for item in previous_receipt["entries"] if item["source_kind"] == "registered-sibling"
    ]
    if len(registered_receipts) != len(registry["artifacts"]):
        raise ValueError("receipt does not preserve every registered sibling assertion")

    mask_hash_by_file_hash = dict(zip(hashes, positive_mask_hashes, strict=True))
    receipt_entries = registered_receipts.copy()
    for relative in LOCAL_PRIORS:
        path = ROOT / relative
        digest = _sha256(path)
        receipt_entries.append(
            {
                "bytes": path.stat().st_size,
                "expected_sha256": digest,
                "file": path.name,
                "github_blob_sha1": None,
                "github_url": (
                    f"https://github.com/buffedlizard55-lab/GEMSDOE50/blob/main/{relative}"
                ),
                "positive_cells_registry": _positive_count(path),
                "positive_mask_sha256": mask_hash_by_file_hash[digest],
                "source_kind": "local-prior",
                "source_path": relative,
                "source_repo": "buffedlizard55-lab/GEMSDOE50",
                "verified": True,
                "verified_sha256": digest,
            }
        )
    for item in receipt_entries:
        item["positive_mask_sha256"] = mask_hash_by_file_hash[item["verified_sha256"]]

    byte_groups: dict[str, set[str]] = {}
    prediction_groups: dict[str, set[str]] = {}
    for item in receipt_entries:
        byte_groups.setdefault(item["verified_sha256"], set()).add(item["source_path"])
        prediction_groups.setdefault(item["positive_mask_sha256"], set()).add(item["source_path"])
    identical = [
        {"sha256": digest, "source_paths": sorted(paths)}
        for digest, paths in byte_groups.items()
        if len(paths) > 1
    ]
    equivalent = [
        {"positive_mask_sha256": digest, "source_paths": sorted(paths)}
        for digest, paths in prediction_groups.items()
        if len(paths) > 1
    ]
    receipt = {
        "all_sha256_verified": True,
        "all_source_assertions": len(receipt_entries),
        "byte_identical_groups": identical,
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "entries": receipt_entries,
        "full_resolution_comparison_filenames": len({item["file"] for item in receipt_entries}),
        "local_prior_entries": len(LOCAL_PRIORS),
        "note": (
            "The sibling registry and every in-repository prior TIFF are inventoried. "
            "Byte-identical copies are retained as source assertions but SHA-256 "
            "deduplicated for union construction; finite/NaN twins with equivalent "
            "positive support are identified by positive-mask hashes. The scratch "
            "corpus bytes are not committed."
        ),
        "prediction_equivalent_groups": equivalent,
        "registered_sibling_entries": len(registry["artifacts"]),
        "registry_source": str(registry_path.relative_to(ROOT)),
        "schema": "gemsdoe50.h55-prior-corpus-receipt.v3",
        "unique_filenames": len({item["file"] for item in receipt_entries}),
        "unique_positive_masks": len(prediction_groups),
        "unique_sha256": len(byte_groups),
        "unique_source_paths": len({item["source_path"] for item in receipt_entries}),
    }
    receipt_path.write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")

    print(
        f"wrote {output.relative_to(ROOT)}: {len(entries)} assertions, "
        f"{len(unique)} unique file hashes, {int(union.sum()):,} union cells, "
        f"{output.stat().st_size:,} bytes"
    )


if __name__ == "__main__":
    main()
