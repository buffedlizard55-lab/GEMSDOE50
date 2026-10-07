#!/usr/bin/env bash
# Fetch hash-pinned comparison inputs from two public sibling-repository snapshots.
# These GitHub mirrors are retrieval aids, not official provenance; official source binaries
# still need byte-for-byte comparison before any submission slot is authorized.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PUBLIC_DIR="${1:-$ROOT/.arena/public-inputs}"
REVIEW_DIR="${2:-$ROOT/.arena/review}"
mkdir -p "$PUBLIC_DIR" "$REVIEW_DIR"

GEMSDOE24_COMMIT="07345ea0604953d7efb858d9cfbc21e20c7aca0b"
GEMSDOE32_COMMIT="b983924b57781edd29b8e249c4923bf33d9902f6"

fetch_raw() {
  local repo="$1" ref="$2" remote_path="$3" output="$4" expected="$5"
  local tmp="${output}.partial"
  gh api -H 'Accept: application/vnd.github.raw' \
    "repos/${repo}/contents/${remote_path}?ref=${ref}" > "$tmp"
  local got
  got="$(sha256sum "$tmp" | awk '{print $1}')"
  if [[ "$got" != "$expected" ]]; then
    rm -f "$tmp"
    printf 'SHA-256 mismatch for %s/%s@%s: got %s expected %s\n' \
      "$repo" "$remote_path" "$ref" "$got" "$expected" >&2
    return 1
  fi
  mv "$tmp" "$output"
  printf '%s  %s\n' "$got" "$output"
}

fetch_raw buffedlizard55-lab/GEMSDOE24 "$GEMSDOE24_COMMIT" \
  data/external/2m_temperature_probe_INGENIOUS_regional_data.zip \
  "$PUBLIC_DIR/2m_temperature_probe_INGENIOUS_regional_data.zip" \
  1301f70d230058e616ea5d34d1c7a32fabf7d49198172f376c59c89bd652eca3
fetch_raw buffedlizard55-lab/GEMSDOE24 "$GEMSDOE24_COMMIT" \
  data/external/geodawn_extensions_u8.tif \
  "$PUBLIC_DIR/geodawn_extensions_u8.tif" \
  a35a9c6d2a14786f4dab85481ee59769213072f5dab5b2535ea82ae4d9bb7d9b
fetch_raw buffedlizard55-lab/GEMSDOE32 "$GEMSDOE32_COMMIT" \
  docs/downloads/gemsdoe32-h33-h33-2-b2-20261004T220000Z-e5eb6e7e-nan.tif \
  "$REVIEW_DIR/gemsdoe32-h33-h33-2-b2-nan.tif" \
  baeae3219bba6a19bc8cfe79224e28555c50184b7c1ca65c2a822f54807c77dd
fetch_raw buffedlizard55-lab/GEMSDOE32 "$GEMSDOE32_COMMIT" \
  docs/downloads/gemsdoe32-h33-h33-2-b2-20261004T220000Z-e5eb6e7e-audit.json \
  "$REVIEW_DIR/gemsdoe32-h33-h33-2-b2-audit.json" \
  e4db14f2e369b1db37870d8d1a31035f730512309a88810d99ff705782e28212

cat <<EOF
Retrieved only pinned public mirror assets. These hashes establish sibling-mirror identity, not
identity with the official GDR/USGS source binaries. See docs/research/h53-hypotheses-20261007.md
and docs/research/h53-preregistration-20261007.md before using or sharing any derivative.
EOF
