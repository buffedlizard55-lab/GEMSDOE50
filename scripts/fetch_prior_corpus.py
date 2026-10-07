#!/usr/bin/env python3
"""Rebuild the full prior-submission corpus for the uniqueness gate (H59).

Two sources, both fetched through the authenticated GitHub API (``gh api``),
which is the only route this sandbox has to the owner's sibling repositories:

1. **Pinned entries** — every ``registered-sibling`` row of
   ``evidence/results/h55-prior-corpus-receipt-20261007.json``.  Each download
   is checked against the SHA-256 recorded there; a mismatch aborts the run.
2. **Discovery sweep** — every public ``buffedlizard55-lab`` repository whose
   name contains ``GEMSDOE`` is listed, its default-branch git tree is walked,
   and every ``*.tif`` / ``*.tiff`` blob smaller than ``--max-bytes`` that is not
   already pinned (by git blob SHA-1) is downloaded and recorded with its own
   SHA-256.  This catches sibling repositories created after the H55 receipt
   (e.g. GEMSDOE47-54), so the gate runs against *all* prior submissions that
   are physically retrievable, not only the ones known on 2026-10-07 morning.

The bytes are written under ``--out`` (default ``.arena/prior_corpus``, which is
git-ignored scratch); the receipt with every hash is written to ``--receipt``
and is committed.  Continuous rasters and files on other grids are *not*
filtered here — the comparison step decides what counts as a submission-like
binary/probability artifact.
"""
from __future__ import annotations

import argparse
import base64
import hashlib
import json
import subprocess
import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
OWNER = "buffedlizard55-lab"
RECEIPT_IN = REPO / "evidence/results/h55-prior-corpus-receipt-20261007.json"


def gh_json(path: str) -> object:
    out = subprocess.run(["gh", "api", path], check=True, capture_output=True, text=True)
    return json.loads(out.stdout)


def gh_raw(repo: str, path: str, ref: str | None = None) -> bytes:
    url = f"repos/{repo}/contents/{path}" + (f"?ref={ref}" if ref else "")
    out = subprocess.run(
        ["gh", "api", "-H", "Accept: application/vnd.github.raw", url],
        check=True,
        capture_output=True,
    )
    return out.stdout


def gh_blob(repo: str, blob_sha: str) -> bytes:
    data = gh_json(f"repos/{repo}/git/blobs/{blob_sha}")
    if data.get("encoding") != "base64":  # type: ignore[union-attr]
        raise ValueError(f"unexpected blob encoding for {repo}@{blob_sha}")
    return base64.b64decode(data["content"])  # type: ignore[index]


def sha256_bytes(blob: bytes) -> str:
    return hashlib.sha256(blob).hexdigest()


def list_gemsdoe_repos() -> list[dict]:
    repos: list[dict] = []
    page = 1
    while True:
        batch = gh_json(f"users/{OWNER}/repos?per_page=100&page={page}&type=owner")
        if not batch:
            break
        repos.extend(batch)  # type: ignore[arg-type]
        page += 1
        if page > 10:
            break
    return sorted(
        (r for r in repos if "GEMSDOE" in r["name"].upper()), key=lambda r: r["name"]
    )


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", default=".arena/prior_corpus")
    ap.add_argument("--receipt", default="evidence/h59_prior_corpus_receipt.json")
    ap.add_argument("--max-bytes", type=int, default=8_000_000)
    ap.add_argument("--skip-discovery", action="store_true")
    args = ap.parse_args()

    out_dir = REPO / args.out
    out_dir.mkdir(parents=True, exist_ok=True)
    pinned = json.loads(RECEIPT_IN.read_text(encoding="utf-8"))["entries"]
    records: list[dict] = []
    seen_blobs: set[str] = set()
    seen_sha: set[str] = set()
    t0 = time.time()

    for entry in pinned:
        if entry.get("source_kind") != "registered-sibling":
            continue
        repo = entry["source_repo"]
        dest = out_dir / entry["file"]
        if dest.exists() and sha256_bytes(dest.read_bytes()) == entry["expected_sha256"]:
            blob = dest.read_bytes()
        else:
            blob = gh_raw(repo, entry["source_path"])
            dest.write_bytes(blob)
        digest = sha256_bytes(blob)
        if digest != entry["expected_sha256"]:
            print(f"HASH MISMATCH {repo}/{entry['source_path']}: {digest}", file=sys.stderr)
            return 1
        if entry.get("github_blob_sha1"):
            seen_blobs.add(entry["github_blob_sha1"])
        seen_sha.add(digest)
        records.append(
            {
                "file": entry["file"],
                "repo": repo,
                "path": entry["source_path"],
                "sha256": digest,
                "bytes": len(blob),
                "origin": "pinned-h55-receipt",
                "hash_verified_against_pin": True,
            }
        )
    print(f"[{time.time()-t0:6.1f}s] pinned entries verified: {len(records)}", flush=True)

    discovered = 0
    repo_rows: list[dict] = []
    if not args.skip_discovery:
        for r in list_gemsdoe_repos():
            name = r["name"]
            full = f"{OWNER}/{name}"
            if name == "GEMSDOE50":
                continue  # this repository's own artifacts are compared from the working tree
            branch = r.get("default_branch") or "main"
            try:
                tree = gh_json(f"repos/{full}/git/trees/{branch}?recursive=1")
            except subprocess.CalledProcessError:
                repo_rows.append({"repo": full, "status": "tree-unavailable"})
                continue
            tifs = [
                t
                for t in tree.get("tree", [])  # type: ignore[union-attr]
                if t.get("type") == "blob"
                and t["path"].lower().endswith((".tif", ".tiff"))
                and int(t.get("size", 0)) <= args.max_bytes
            ]
            new = 0
            for t in tifs:
                if t["sha"] in seen_blobs:
                    continue
                try:
                    blob = gh_blob(full, t["sha"])
                except (subprocess.CalledProcessError, ValueError):
                    continue
                digest = sha256_bytes(blob)
                seen_blobs.add(t["sha"])
                if digest in seen_sha:
                    continue
                seen_sha.add(digest)
                safe = f"{name}__{t['path'].replace('/', '__')}"
                (out_dir / safe).write_bytes(blob)
                records.append(
                    {
                        "file": safe,
                        "repo": full,
                        "path": t["path"],
                        "git_blob_sha1": t["sha"],
                        "sha256": digest,
                        "bytes": len(blob),
                        "origin": "discovery-sweep",
                        "hash_verified_against_pin": False,
                    }
                )
                new += 1
                discovered += 1
            repo_rows.append(
                {"repo": full, "branch": branch, "tif_blobs": len(tifs), "new_files": new}
            )
            print(f"[{time.time()-t0:6.1f}s] {full}: {len(tifs)} tif blobs, {new} new", flush=True)

    receipt = {
        "schema": "gemsdoe50.h59-prior-corpus.v1",
        "created_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "pinned_source": str(RECEIPT_IN.relative_to(REPO)),
        "pinned_verified": sum(1 for x in records if x["origin"] == "pinned-h55-receipt"),
        "discovered_new_files": discovered,
        "repos_swept": repo_rows,
        "max_bytes": args.max_bytes,
        "note": (
            "Bytes are scratch (git-ignored). Pinned rows are verified against the committed "
            "H55 receipt; discovery rows record the SHA-256 measured at download time."
        ),
        "files": records,
    }
    dest = REPO / args.receipt
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(json.dumps(receipt, indent=1, sort_keys=True) + "\n", encoding="utf-8")
    print(f"[{time.time()-t0:6.1f}s] receipt: {dest} ({len(records)} files)", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
