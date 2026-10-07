#!/usr/bin/env bash
set -euo pipefail

OUT_DIR="${1:-.arena/run/inputs}"
mkdir -p "$OUT_DIR"

# Public file mirrors of the competition's downloadable training rasters.
# The SHA-256 pins were recorded from the source bridge manifest; matching them
# verifies bytes, but does not independently authenticate the mirror's origin.
LABEL_SOURCE='https://www.dropbox.com/scl/fi/t7fyt03qdh9egyme0itwo/existing_faults.tif?rlkey=yiao96uluqdkipf0h5vju71jf&dl=1'
TEMPLATE_SOURCE='https://www.dropbox.com/scl/fi/6rgvnuady818ol8yqgis4/example_submission.tif?rlkey=kbykilvau066xuogoosbf4cq8&dl=1'
CATALOG_SOURCE='https://zenodo.org/api/records/11167510/files/nvreloc_catalog_newmag.txt/content'

curl --fail --location --retry 3 --retry-all-errors --connect-timeout 30 "$LABEL_SOURCE" -o "$OUT_DIR/existing_faults.tif"
curl --fail --location --retry 3 --retry-all-errors --connect-timeout 30 "$TEMPLATE_SOURCE" -o "$OUT_DIR/example_submission.tif"
curl --fail --location --retry 3 --retry-all-errors --connect-timeout 30 "$CATALOG_SOURCE" -o "$OUT_DIR/nvreloc_catalog_newmag.txt"

printf '%s  %s\n' \
  '7ba308ccdc4418b31a178f4f1ef21aaa6e152e4028f2f6f64b01f7eb25ae4093' "$OUT_DIR/existing_faults.tif" \
  '2176d08e485aa2cd2860ce8df539db4faf4d76163b38a4dd8c30a40454d35cbc' "$OUT_DIR/example_submission.tif" | sha256sum --check --status

catalog_bytes="$(wc -c < "$OUT_DIR/nvreloc_catalog_newmag.txt" | tr -d ' ')"
catalog_md5="$(md5sum "$OUT_DIR/nvreloc_catalog_newmag.txt" | cut -d ' ' -f 1)"
if [[ "$catalog_bytes" != '13833354' ]]; then
  echo "Unexpected Nevada catalog size: $catalog_bytes bytes (expected 13833354)" >&2
  exit 1
fi
if [[ "$catalog_md5" != '38fa663f473378b61c74b597c53c416b' ]]; then
  echo "Nevada catalog MD5 mismatch: $catalog_md5" >&2
  exit 1
fi
sha256sum "$OUT_DIR/nvreloc_catalog_newmag.txt" > "$OUT_DIR/catalog.sha256"
printf 'catalog_bytes=%s\ncatalog_md5=%s\ncatalog_sha256=%s\n' \
  "$catalog_bytes" "$catalog_md5" "$(cut -d ' ' -f 1 "$OUT_DIR/catalog.sha256")" \
  | tee "$OUT_DIR/catalog-checks.txt"

PYTHON_BIN="${PYTHON:-python}"
"$PYTHON_BIN" scripts/download_3dep_dem.py \
  --template "$OUT_DIR/example_submission.tif" \
  --output "$OUT_DIR/3dep_dem_100m.tif"

echo "Verified pinned contest rasters, the CC BY 4.0 Nevada catalog, and a grid-matched USGS 3DEP DEM in $OUT_DIR"
