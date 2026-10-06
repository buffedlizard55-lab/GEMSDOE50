"""GEMSDOE50 — a seismicity-lineation fault-discovery system for the DOE GEMS Prize.

The package is deliberately small and auditable.  Every physical or statistical claim
made by the shipped site is produced by code that lives here and is covered by a test
in ``tests/``.

Modules
-------
grid         : the competition grid (EPSG:32611, 100 m, 3292 x 3730) and its valid mask
metric       : the official distance-weighted Tversky index and its algebra
catalog      : loading / quality-control of the official USGS ComCat catalogue
decluster    : separation of clustered events from uncorrelated background
lineation    : 2-D anisotropic (OADC-style) lineation extraction + location uncertainty
emission     : converting a credit field into a legal submission raster
validate     : spatially blocked holdouts and matched-mass control experiments
uniqueness   : the gate that proves a candidate is not a prior submission
"""

__all__ = [
    "grid",
    "metric",
    "catalog",
    "decluster",
    "lineation",
    "emission",
    "validate",
    "uniqueness",
]

__version__ = "1.0.0"
