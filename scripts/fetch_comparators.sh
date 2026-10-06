#!/usr/bin/env bash
set -euo pipefail

OUT_DIR="${1:-.arena/run/prior}"
mkdir -p "$OUT_DIR"

fetch_blob() {
  local name="$1" repo="$2" path="$3" ref="$4" expected_blob="$5" expected_sha="$6"
  local dest="$OUT_DIR/$name.tif"
  local response blob_sha
  response="$(gh api "repos/buffedlizard55-lab/$repo/contents/$path?ref=$ref")"
  blob_sha="$(printf '%s' "$response" | jq -r '.sha')"
  if [[ "$blob_sha" != "$expected_blob" ]]; then
    echo "Unexpected Git blob SHA for $repo/$path: $blob_sha" >&2
    exit 1
  fi
  printf '%s' "$response" | jq -r '.content' | tr -d '\n' | base64 --decode > "$dest"
  local actual_sha
  actual_sha="$(sha256sum "$dest" | cut -d ' ' -f 1)"
  if [[ "$actual_sha" != "$expected_sha" ]]; then
    echo "Unexpected file SHA-256 for $repo/$path: $actual_sha" >&2
    exit 1
  fi
  printf '%s\t%s\t%s\t%s\n' "$name" "$repo" "$ref" "$actual_sha"
}

fetch_blob \
  'h32d' 'GEMSDOE32' \
  'docs/downloads/gemsdoe32-h32d-submodular-multipysics-46090-20261004T183200Z-4de30601-zeros.tif' \
  '51ccc787e1059dc2e440cd94863c7d2670b3b88d' \
  '45b9f47ac9c1518875b5e4b9ea92ca2fc6727fe4' \
  'f81e26d7712d1a4a9d3d5393037b09849400c3976d1ebd40e2760a586f2adc2f'

fetch_blob \
  'h47s3' 'GEMSDOE47' \
  'docs/downloads/gemsdoe47-scarp9-persistence-s2.8-d7.37-b2.tif' \
  '97c8acdf3b0aaf151cdab606da0ac15f1a8132b8' \
  '8a2a3f49e36888ca80a582d17767334343d088f0' \
  'f3f840b7880b7540ac6260b6b791ea55b2a875646c28401b01960096dc2da291'

fetch_blob \
  'h48ds' 'GEMSDOE48' \
  'docs/downloads/gemsdoe48-h48-ds-yager-conflict-20261006.tif' \
  'd064aeeec467ce5de6cf0ecd86872af6561e509f' \
  '211a4a69a4d49f12f0fe5f2265cde0c725063254' \
  'fe68ae6f57be013e26d20006551b43cd84bb5fe4a0b07d1d10ce4725c90fd16c'

fetch_blob \
  'h50prev' 'GEMSDOE50' \
  'downloads/gems50-seislin-44709-20261006T2041Z-79e260ae.tif' \
  '80d6186dee89ba0eacedd29dc0a7455c5fad4e47' \
  'd014851c5c6221bbd00c24e5c252d84ae337352c' \
  '79e260ae223d7dfd96413da28a9c6fed30107285ab843795181a5c9e5dff7262'
