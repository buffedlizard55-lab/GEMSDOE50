#!/usr/bin/env python3
"""Legacy fetcher for the USGS-hosted, mixed-network ComCat export.

This was used by the legacy 2-D seismicity-lineament research. The ComCat API is
official, but source-specific contributor rights and competition shareability for
a mixed-network export are unresolved. The data are not cleared for external
competition use and are not an H50-S1 input. This fetcher is retained only for
audit; downloading does not confer redistribution rights.
"""

from __future__ import annotations

import argparse
import csv
import io
import json
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

FDSN = "https://earthquake.usgs.gov/fdsnws/event/1/query"

# Footprint of the competition grid (EPSG:32611, 100 m):
#   left 243350, bottom 4135550, right 572550, top 4508550
# -> WGS84 bounding box, padded outward by 0.06 deg (~6 km) so that events whose
#    *location uncertainty ellipse* touches the footprint are not lost.
BBOX = dict(minlatitude=37.27, maxlatitude=40.79, minlongitude=-120.10, maxlongitude=-116.08)

CSV_COLUMNS = [
    "time", "latitude", "longitude", "depth", "mag", "magType", "nst", "gap",
    "dmin", "rms", "net", "id", "updated", "place", "type", "horizontalError",
    "depthError", "magError", "magNst", "status", "locationSource", "magSource",
]


def query(params: dict, retries: int = 5, timeout: int = 180) -> str:
    url = FDSN + "?" + urllib.parse.urlencode(params)
    last = None
    for attempt in range(retries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "gemsdoe50-catalog-fetch/1.0"})
            with urllib.request.urlopen(req, timeout=timeout) as fh:
                return fh.read().decode("utf-8", "replace")
        except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError) as exc:
            last = exc
            print(f"    retry {attempt + 1}/{retries} after {exc}", flush=True)
            time.sleep(5 * (attempt + 1))
    raise RuntimeError(f"FDSN query failed: {url} :: {last}")


def fetch_band(lo: float, hi: float, t0: str, t1: str) -> list[dict]:
    """Fetch one magnitude band over one time window, paginating on offset."""
    rows: list[dict] = []
    offset = 1
    while True:
        params = dict(
            format="csv",
            starttime=t0,
            endtime=t1,
            minmagnitude=lo,
            maxmagnitude=hi,
            orderby="time-asc",
            limit=20000,
            offset=offset,
            **BBOX,
        )
        txt = query(params)
        body = txt.strip()
        if not body or body.startswith("Error"):
            if body and not body.startswith("time,"):
                print(f"    service said: {body[:200]}", flush=True)
            break
        reader = csv.reader(io.StringIO(txt))
        header = next(reader)
        n = 0
        for raw in reader:
            if not raw or len(raw) < len(header):
                continue
            rows.append(dict(zip(header, raw)))
            n += 1
        print(f"    M[{lo},{hi}) {t0[:10]}..{t1[:10]} offset={offset}: +{n} rows", flush=True)
        if n < 20000:
            break
        offset += 20000
        time.sleep(1)
    return rows


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="data/external")
    ap.add_argument("--start", default="1970-01-01")
    ap.add_argument("--min-magnitude", type=float, default=1.0)
    ap.add_argument("--m2-start", default="1900-01-01")
    ap.add_argument("--m2-min-magnitude", type=float, default=4.0)
    args = ap.parse_args()

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S")
    years = list(range(int(args.start[:4]), int(now[:4]) + 1))

    all_rows: list[dict] = []

    # Band 1: the dense, recent, well-located catalogue (M >= 1.0).
    print("== dense band ==", flush=True)
    for y in years:
        t0 = f"{y}-01-01T00:00:00"
        t1 = f"{y + 1}-01-01T00:00:00" if y < int(now[:4]) else now
        all_rows += fetch_band(args.min_magnitude, 10.0, t0, t1)

    # Band 2: the long historical record of larger events (M >= 4.0, 1900->).
    print("== historical band ==", flush=True)
    have = {r["id"] for r in all_rows}
    for y in range(int(args.m2_start[:4]), int(args.start[:4])):
        t0, t1 = f"{y}-01-01T00:00:00", f"{y + 1}-01-01T00:00:00"
        for r in fetch_band(args.m2_min_magnitude, 10.0, t0, t1):
            if r["id"] not in have:
                all_rows.append(r)
                have.add(r["id"])

    # Normalise to a stable column set, de-duplicate by event id.
    dedup: dict[str, dict] = {}
    for r in all_rows:
        dedup[r["id"]] = {c: r.get(c, "") for c in CSV_COLUMNS}
    rows = sorted(dedup.values(), key=lambda r: r["time"])

    csv_path = out / "usgs_comcat_earthquakes.csv"
    with csv_path.open("w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=CSV_COLUMNS)
        w.writeheader()
        w.writerows(rows)

    types: dict[str, int] = {}
    nets: dict[str, int] = {}
    for r in rows:
        types[r["type"]] = types.get(r["type"], 0) + 1
        nets[r["net"]] = nets.get(r["net"], 0) + 1
    summary = {
        "source": FDSN,
        "product": "ANSS Comprehensive Earthquake Catalog (ComCat)",
        "query_bbox": BBOX,
        "fetched_utc": now,
        "rows": len(rows),
        "first": rows[0]["time"] if rows else None,
        "last": rows[-1]["time"] if rows else None,
        "event_types": dict(sorted(types.items(), key=lambda kv: -kv[1])),
        "networks": dict(sorted(nets.items(), key=lambda kv: -kv[1])[:15]),
        "notes": [
            "Mixed-network ComCat export: contributor-specific rights and competition shareability "
            "are unresolved. General USGS public-domain guidance does not clear each contribution; "
            "do not reuse this extract externally before source-specific review.",
            "Rows with type in {explosion, quarry blast, mining explosion, anthropogenic event} are "
            "flagged, not silently deleted: the analysis removes them explicitly.",
            "horizontalError is an optional scalar record field; it does not supply a full event-location "
            "covariance. Legacy H50-B weighting/imputation is not a reproduction of an uncertainty-aware "
            "3-D clustering method.",
        ],
    }
    (out / "usgs_comcat_earthquakes.summary.json").write_text(json.dumps(summary, indent=1))
    print(json.dumps(summary, indent=1), flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
