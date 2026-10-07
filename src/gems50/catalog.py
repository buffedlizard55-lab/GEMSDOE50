"""Legacy loader for a mixed-source export from the USGS-hosted ComCat service.

This module belongs to prior GEMSDOE50 experiments and is not used by H50-S1. A request to
the USGS ComCat service does not establish that every preferred contributor's record is a
USGS work or public domain. ComCat documents ``net`` as the preferred contributor and
``sources`` as contributing networks; source-specific rights and challenge/sponsor-sharing
terms for the inherited mixed-network extract remain unresolved. See
``docs/research/data-rights-audit-20261006.md`` before any reuse.

The legacy code stores ``horizontalError`` under a kilometre-oriented variable name and
uses it as an uncertainty value. The field's unit and statistical interpretation were not
verified for each network. It must not be described as 1-sigma or used as a calibrated
location uncertainty without source-specific documentation. H50-S1 does not load this
extract or use ``horizontalError``.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd
from pyproj import Transformer

REPO = Path(__file__).resolve().parents[2]
DEFAULT_CATALOG = REPO / "data" / "external" / "usgs_comcat_earthquakes.csv.gz"

#: The competition grid, EPSG:32611 (see :mod:`gems50.grid`).
FOOTPRINT = dict(left=243350.0, bottom=4135550.0, right=572550.0, top=4508550.0)

#: Event types that are *not* tectonic earthquakes.  ComCat labels them explicitly.
ANTHROPOGENIC = {
    "quarry blast",
    "explosion",
    "mining explosion",
    "chemical explosion",
    "nuclear explosion",
    "mine collapse",
    "quarry",
    "acoustic noise",
    "sonic boom",
    "rockslide",
    "other event",
    "not reported",
}

_TO_UTM = Transformer.from_crs("EPSG:4326", "EPSG:32611", always_xy=True)


@dataclass
class Catalog:
    """A catalogue ready for spatial analysis, with its QC record."""

    frame: pd.DataFrame  # legacy columns; h_err_km is a raw field under an unverified unit/meaning assumption
    qc: dict

    def __len__(self) -> int:
        return len(self.frame)

    @property
    def xy(self) -> np.ndarray:
        return self.frame[["x", "y"]].to_numpy(dtype=np.float64)

    @property
    def mag(self) -> np.ndarray:
        return self.frame["mag"].to_numpy(dtype=np.float64)

    @property
    def h_err(self) -> np.ndarray:
        """Legacy numeric error-field values; units and sigma semantics are unverified."""
        return self.frame["h_err_km"].to_numpy(dtype=np.float64)

    @property
    def time(self) -> np.ndarray:
        return self.frame["time"].to_numpy()

    @property
    def t_years(self) -> np.ndarray:
        """Decimal years since 1970-01-01 (input to the nearest-neighbour test)."""
        return self.frame["t_years"].to_numpy(dtype=np.float64)


def load_csv(path: str | Path = DEFAULT_CATALOG) -> pd.DataFrame:
    """Read a ComCat CSV/CSV.GZ into a DataFrame without touching any value."""
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(
            f"{p} not found.  Run scripts/fetch_earthquake_catalog.py on a machine with "
            "internet access (GitHub Actions runner) or point --catalog at a local copy."
        )
    return pd.read_csv(p, low_memory=False)


def project(df: pd.DataFrame) -> pd.DataFrame:
    """Add EPSG:32611 easting/northing columns (catalogue coords are WGS84 lon/lat)."""
    x, y = _TO_UTM.transform(df["longitude"].to_numpy(), df["latitude"].to_numpy())
    out = df.copy()
    out["x"] = np.asarray(x, dtype=np.float64)
    out["y"] = np.asarray(y, dtype=np.float64)
    return out


def in_footprint(df: pd.DataFrame) -> np.ndarray:
    (x, y) = df["x"].to_numpy(), df["y"].to_numpy()
    return (
        (x >= FOOTPRINT["left"])
        & (x <= FOOTPRINT["right"])
        & (y >= FOOTPRINT["bottom"])
        & (y <= FOOTPRINT["top"])
    )


def magnitude_of_completeness(mag: np.ndarray, bin_width: float = 0.1) -> float:
    """Maximum-curvature estimate of Mc (+0.2 correction; Woessner & Wiemer 2005).

    Woessner, J. and Wiemer, S. (2005), "Assessing the quality of earthquake catalogues:
    Estimating the magnitude of completeness and its uncertainty", BSSA 95(2), 684-698,
    doi:10.1785/0120040007.  The +0.2 correction is that paper's own recommendation for
    the maximum-curvature method with a 0.1 magnitude bin.
    """
    if np.ptp(mag) <= bin_width:
        return float(np.min(mag))
    edges = np.arange(np.floor(np.min(mag) / bin_width) * bin_width,
                      np.ceil(np.max(mag) / bin_width) * bin_width + bin_width,
                      bin_width)
    hist, edges = np.histogram(mag, bins=edges)
    mc = edges[int(np.argmax(hist))] + bin_width / 2.0 + 0.2
    return float(mc)


def completeness_by_epoch(df: pd.DataFrame, epochs: list[int]) -> dict[int, float]:
    """Mc per epoch, computed on the catalogue inside the footprint."""
    years = pd.to_datetime(df["time"], format="mixed", utc=True).dt.year.to_numpy()
    out = {}
    for start in epochs:
        sel = years >= start
        if sel.sum() > 200:
            out[start] = magnitude_of_completeness(df.loc[sel, "mag"].to_numpy())
    return out


def build_catalog(
    path: str | Path = DEFAULT_CATALOG,
    min_magnitude: float = 1.5,
    max_depth_km: float = 20.0,
    start_year: int = 1970,
    tectonic_only: bool = True,
    default_h_err_km: float | None = None,
) -> Catalog:
    """Legacy QC pipeline. Not approved for H50-S1 or use as uncertainty-aware analysis.

    ``default_h_err_km`` is a historical compatibility parameter. The input extract's
    ``horizontalError`` units/statistical interpretation are not verified; the fallback and
    output column name must not be read as calibrated uncertainty. The H50-S1 workflow does
    not call this function.
    """
    raw = load_csv(path)
    df = project(raw)
    qc: dict = {
        "source_rows": int(len(df)),
        "source_file": str(path),
        "footprint": dict(FOOTPRINT),
    }
    df = df[in_footprint(df)]
    qc["inside_footprint"] = int(len(df))

    if "type" in df:
        counts = df["type"].fillna("unknown").value_counts().to_dict()
        qc["types_inside"] = {str(k): int(v) for k, v in counts.items()}
        if tectonic_only:
            df = df[~df["type"].fillna("unknown").isin(ANTHROPOGENIC)]
            qc["after_type_filter"] = int(len(df))

    if min_magnitude is not None:
        df = df[df["mag"].notna() & (df["mag"] >= min_magnitude)]
        qc["min_magnitude"] = float(min_magnitude)
        qc["after_magnitude_filter"] = int(len(df))

    if max_depth_km is not None:
        df = df[df["depth"].notna() & (df["depth"] <= max_depth_km)]
        qc["max_depth_km"] = float(max_depth_km)
        qc["after_depth_filter"] = int(len(df))

    df = df.copy()
    # tz-naive UTC datetime64 keeps numpy arithmetic simple and lossless
    df["time"] = pd.to_datetime(df["time"], format="mixed", utc=True).dt.tz_convert("UTC").dt.tz_localize(None)
    if start_year is not None:
        df = df[df["time"].dt.year >= start_year]
        qc["start_year"] = int(start_year)
    qc["after_time_filter"] = int(len(df))

    err = pd.to_numeric(df.get("horizontalError"), errors="coerce")
    if default_h_err_km is None:
        default_h_err_km = float(np.nanmedian(err)) if err.notna().any() else 1.0
        qc["h_err_fallback_km"] = default_h_err_km
        qc["h_err_source"] = "median of the catalogue's own horizontalError"
    df["h_err_km"] = err.fillna(default_h_err_km).clip(lower=0.05, upper=25.0)
    qc["h_err_median_km"] = float(df["h_err_km"].median())
    qc["h_err_p90_km"] = float(df["h_err_km"].quantile(0.9))

    # decimal years since the Unix epoch reference used by the declustering test
    epoch = pd.Timestamp("1970-01-01")
    df["t_years"] = (df["time"] - epoch).dt.total_seconds() / (365.25 * 86400.0)

    keep = ["time", "t_years", "x", "y", "depth", "mag", "h_err_km", "net", "id"]
    df = df[[c for c in keep if c in df.columns]].reset_index(drop=True)
    qc["events_kept"] = int(len(df))
    if len(df):
        qc["mag_max"] = float(df["mag"].max())
        qc["time_first"] = str(df["time"].min())
        qc["time_last"] = str(df["time"].max())
    return Catalog(frame=df, qc=qc)
