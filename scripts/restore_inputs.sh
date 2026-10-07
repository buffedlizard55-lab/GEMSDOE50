#!/usr/bin/env bash
# Rebuild a complete, hash-pinned input set for scripts/build_h52.py.
#
# Why this exists: the official competition rasters are login-gated at
# drivendata.org, and this sandbox's egress allow-list reaches only PyPI and
# GitHub.  The large inputs are therefore restored from public *transport*
# copies that live inside the owner's sibling repositories, and every restored
# byte is checked against the SHA-256 that this repository recorded when the
# same files were first used (see registry/sources.json and the H51 build
# receipt).  A hash match proves the transport copies are byte-identical to the
# files this project has been building on; it does not independently
# authenticate them as organizer originals — see README "Inherited provenance
# caveat".
#
# Usage:  scripts/restore_inputs.sh [OUT_DIR]        (default .arena/inputs)
#
# After it succeeds, `scripts/build_h52.py --inputs "$OUT_DIR"` is fully
# reproducible offline.
set -euo pipefail

OUT_DIR="${1:-.arena/inputs}"
OWNER="buffedlizard55-lab"
mkdir -p "$OUT_DIR"

# path_in_repo <owner/repo> <repo path> <destination>
fetch_raw() {
  local repo="$1" path="$2" dest="$3"
  echo "  fetch  $repo/$path"
  gh api -H "Accept: application/vnd.github.raw" "repos/$repo/contents/$path" > "$dest"
}

echo "[1/4] competition grid rasters from this repository (already hash-pinned)"
cp -f data/grid/labels.tif "$OUT_DIR/existing_faults.tif"
cp -f data/grid/sample_submission.tif "$OUT_DIR/example_submission.tif"

echo "[2/4] 19-band feature cube (split into five parts upstream) + quantised derivatives"
for i in 000 001 002 003 004; do
  fetch_raw "$OWNER/5GEMSDOE" "data/bridge/gems-geodawn-numerical-features.tif.part-$i" "$OUT_DIR/tf.part-$i"
done
cat "$OUT_DIR"/tf.part-000 "$OUT_DIR"/tf.part-001 "$OUT_DIR"/tf.part-002 \
    "$OUT_DIR"/tf.part-003 "$OUT_DIR"/tf.part-004 > "$OUT_DIR/training_features.tif"
rm -f "$OUT_DIR"/tf.part-*
fetch_raw "$OWNER/5GEMSDOE" "data/aux_bridge/topo/topo_u8.tif.part-000" "$OUT_DIR/topo_u8.tif"
fetch_raw "$OWNER/5GEMSDOE" "data/aux_bridge/radiometric/radiometric_u8.tif.part-000" "$OUT_DIR/radiometric_u8.tif"

echo "[3/4] USGS 3DEP scarp descriptors and GeoDAWN radiometric mosaics"
fetch_raw "$OWNER/7GEMSDOE" "external/dem/lidar_scarp_features_u8.tif" "$OUT_DIR/lidar_scarp_features_u8.tif"
fetch_raw "$OWNER/7GEMSDOE" "external/geodawn_rad/geodawn_rad_u8.tif" "$OUT_DIR/geodawn_rad_u8.tif"
fetch_raw "$OWNER/7GEMSDOE" "external/geodawn_extensions/geodawn_extensions_u8.tif" "$OUT_DIR/geodawn_extensions_u8.tif"

echo "[4/4] verifying SHA-256 of every restored file"
sha256sum --check --status <<EOF || { echo "MISMATCH: an input does not match the pinned hash" >&2; exit 1; }
4371c82e3b8339b807bdffcf4ef59a225520fe2988d521be208ae33743123bc5  $OUT_DIR/training_features.tif
a6398d9950965dec6aae6ccecdaa6ced48645d133eab222cbdd11def9bdabfa4  $OUT_DIR/topo_u8.tif
6cb051f70f941fd78028fe66a9f71e87204fcd8d9a85903df0b94993bad1ec4d  $OUT_DIR/radiometric_u8.tif
d580bb8bdcdb941e32fefb8b38044bc5bf04e199bf2e83498c3576e6fc465568  $OUT_DIR/lidar_scarp_features_u8.tif
c22420f75999030d7cc65c9e31e50d232ea6158423bca051613a18a8b20ba682  $OUT_DIR/geodawn_rad_u8.tif
a35a9c6d2a14786f4dab85481ee59769213072f5dab5b2535ea82ae4d9bb7d9b  $OUT_DIR/geodawn_extensions_u8.tif
2176d08e485aa2cd2860ce8df539db4faf4d76163b38a4dd8c30a40454d35cbc  $OUT_DIR/example_submission.tif
7ba308ccdc4418b31a178f4f1ef21aaa6e152e4028f2f6f64b01f7eb25ae4093  $OUT_DIR/existing_faults.tif
EOF
sha256sum "$OUT_DIR"/*.tif | sort -k2 > "$OUT_DIR/restore_sha256.txt"
echo "OK: 8 inputs restored and hash-verified in $OUT_DIR"
