#!/usr/bin/env python3
"""Request a grid-exact, 100 m DEM from the official USGS 3DEP image service."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

import numpy as np
import rasterio

IMAGE_SERVER = "https://elevation.nationalmap.gov/arcgis/rest/services/3DEPElevation/ImageServer"
LICENSE_URL = "https://data.usgs.gov/datacatalog/data/USGS:77ae0551-c61e-4979-aedd-d797abdcde0e"
USER_AGENT = "GEMSDOE50 research workflow (reproducible terrain-intersection control)"


def sha256_file(path: str | Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _read_url(url: str, *, timeout: int = 180) -> tuple[bytes, str]:
    request = Request(url, headers={"User-Agent": USER_AGENT, "Accept": "image/tiff,application/json,*/*"})
    last_error: Exception | None = None
    for attempt in range(4):
        try:
            with urlopen(request, timeout=timeout) as response:
                content = response.read()
                content_type = response.headers.get("Content-Type", "unknown")
                return content, content_type
        except (HTTPError, URLError, TimeoutError, OSError) as exc:
            last_error = exc
            if attempt == 3:
                break
            time.sleep(2**attempt)
    raise RuntimeError(f"USGS 3DEP request failed after retries: {last_error}")


def build_export_url(template_path: str | Path) -> tuple[str, dict[str, Any]]:
    """Return the official exportImage URL and exact requested grid metadata."""
    with rasterio.open(template_path) as template:
        if template.count != 1:
            raise ValueError("submission template must have exactly one band")
        if template.crs is None or template.crs.to_epsg() != 32611:
            raise ValueError("3DEP request template must use EPSG:32611")
        transform = template.transform
        pixel_x = abs(float(transform.a))
        pixel_y = abs(float(transform.e))
        if not np.isclose(pixel_x, 100.0) or not np.isclose(pixel_y, 100.0):
            raise ValueError(f"expected 100 m square cells, got {pixel_x} x {pixel_y} m")
        if abs(transform.b) > 1e-9 or abs(transform.d) > 1e-9:
            raise ValueError("template must be a north-up raster")
        bounds = template.bounds
        width, height = template.width, template.height
        params = {
            "bbox": ",".join(f"{v:.12f}" for v in (bounds.left, bounds.bottom, bounds.right, bounds.top)),
            "bboxSR": "32611",
            "size": f"{width},{height}",
            "imageSR": "32611",
            "format": "tiff",
            "pixelType": "F32",
            "noData": "-9999",
            "noDataInterpretation": "esriNoDataMatchAny",
            "interpolation": "RSP_BilinearInterpolation",
            "returnSquarePixels": "true",
            "f": "image",
        }
        grid = {
            "width": width,
            "height": height,
            "crs": template.crs.to_string(),
            "transform": list(transform),
            "bounds": [float(bounds.left), float(bounds.bottom), float(bounds.right), float(bounds.top)],
            "pixel_size_m": [pixel_x, pixel_y],
        }
    return f"{IMAGE_SERVER}/exportImage?{urlencode(params)}", {"params": params, "grid": grid}


def download_dem(template_path: str | Path, output_path: str | Path) -> dict[str, Any]:
    template_path = Path(template_path)
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    request_url, request_metadata = build_export_url(template_path)

    service_payload, _ = _read_url(f"{IMAGE_SERVER}?f=pjson", timeout=60)
    try:
        service_metadata = json.loads(service_payload.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise RuntimeError("USGS image service metadata response is not valid JSON") from exc
    if service_metadata.get("serviceDataType") != "esriImageServiceDataTypeElevation":
        raise RuntimeError("USGS endpoint did not report an elevation image service")

    image_bytes, response_type = _read_url(request_url)
    if len(image_bytes) < 8 or image_bytes.lstrip().startswith(b"{"):
        preview = image_bytes[:500].decode("utf-8", errors="replace")
        raise RuntimeError(f"3DEP export did not return a TIFF image: {preview}")

    temporary_path = output_path.with_suffix(output_path.suffix + ".partial")
    temporary_path.write_bytes(image_bytes)
    try:
        with rasterio.open(template_path) as template, rasterio.open(temporary_path) as dem:
            attrs = ("width", "height", "count", "crs", "transform")
            mismatches = [
                f"{attr}: template={getattr(template, attr)!r}, dem={getattr(dem, attr)!r}"
                for attr in attrs
                if getattr(template, attr) != getattr(dem, attr)
            ]
            if mismatches:
                raise ValueError("exported DEM grid mismatch: " + "; ".join(mismatches))
            if dem.count != 1 or dem.dtypes != ("float32",):
                raise ValueError(f"expected one float32 DEM band, got {dem.count} {dem.dtypes}")
            raw = dem.read(1, masked=True)
            values = np.asarray(raw.filled(np.nan), dtype=np.float64)
            valid = np.isfinite(values) & ~np.ma.getmaskarray(raw)
            if not np.any(valid):
                raise ValueError("USGS export contains no valid elevation pixels")
            dem_stats = {
                "valid_pixels": int(np.count_nonzero(valid)),
                "nodata_pixels": int(values.size - np.count_nonzero(valid)),
                "minimum_elevation_m": float(np.min(values[valid])),
                "maximum_elevation_m": float(np.max(values[valid])),
                "mean_elevation_m": float(np.mean(values[valid], dtype=np.float64)),
                "nodata_value": dem.nodata,
                "dtype": dem.dtypes[0],
                "crs": dem.crs.to_string() if dem.crs else None,
                "transform": list(dem.transform),
                "bounds": [float(v) for v in dem.bounds],
            }
        os.replace(temporary_path, output_path)
    except Exception:
        temporary_path.unlink(missing_ok=True)
        raise

    metadata = {
        "source": "USGS National Map 3DEP dynamic elevation image service",
        "service_url": IMAGE_SERVER,
        "request_url": request_url,
        "request_params": request_metadata["params"],
        "requested_grid": request_metadata["grid"],
        "service_description": service_metadata.get("serviceDescription"),
        "service_copyright": service_metadata.get("copyrightText"),
        "service_snapshot_note": "See the saved service description for the service's published-data date; the mosaic may be refreshed later.",
        "license": "Public domain; USGS Data Catalog states all 3DEP products are public domain.",
        "license_source": LICENSE_URL,
        "acquired_utc": datetime.now(timezone.utc).isoformat(),
        "response_content_type": response_type,
        "response_bytes": output_path.stat().st_size,
        "sha256": sha256_file(output_path),
        "dem_statistics": dem_stats,
        "vertical_datum_caveat": (
            "The dynamic service catalog exposes a VerticalDatum field for source items, but this export does not establish "
            "a single datum for every pixel. The Nevada catalog reports depth relative to mean sea level. No local datum "
            "transformation has been applied; the experiment uses a zero-offset approximation and is not slot-eligible."
        ),
    }
    metadata_path = output_path.with_suffix(".json")
    metadata_path.write_text(json.dumps(metadata, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return metadata


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--template", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    metadata = download_dem(args.template, args.output)
    print(json.dumps(metadata, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
