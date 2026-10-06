"""Verified facts about the official competition grid (measured from the bytes).

Every number here was read from the hash-pinned mirror of the official file, whose
sha256 is recorded in registry/data_manifest.json.  These are the constants the rest
of the pipeline asserts, so that a silently swapped grid cannot enter a submission.
"""

from __future__ import annotations

CRS = "EPSG:32611"
PIXEL_M = 100.0
SHAPE = (3730, 3292)                     # (rows, cols)
TRANSFORM = (100.0, 0.0, 243350.0, 0.0, -100.0, 4508550.0)
BOUNDS = (243350.0, 4135550.0, 572550.0, 4508550.0)  # left, bottom, right, top

#: number of pixels that are finite in the provided sample submission == the
#: scored footprint (measured: 5,167,373 of 3730*3292 = 12,279,160)
FOOTPRINT_PX = 5_167_373

#: number of catalogue fault pixels in labels.tif (measured: value == 1)
CATALOGUE_PX = 60_988

#: official nodata sentinel of training_features.tif
NODATA = -3.4028234663852886e38

#: band index (1-based, as written by gdalinfo/rasterio) -> official description
BANDS = {
    1: ("mag_anom", "Magnetic anomaly - deviation from expected Earth's magnetic field"),
    2: ("rtp", "Reduced to pole magnetic data - magnetic anomaly corrected for latitude effects"),
    3: ("tmi_hg", "Total magnetic intensity horizontal gradient - rate of change in horizontal direction"),
    4: ("geodetic_2nd_invariant", "Geodetic second invariant - measure of strain rate tensor magnitude"),
    5: ("iso_grav_anom_slope", "Isostatic gravity anomaly slope - gradient of gravity after isostatic correction"),
    6: ("tilt_angle", "Tilt angle or total curvature - magnetic field derivative for edge detection"),
    7: ("geodetic_shear_rate", "Geodetic shear rate - measure of rate of angular deformation from GPS/InSAR"),
    8: ("geodetic_dilatation_rate", "Geodetic dilatation rate - measure of volumetric strain (expansion/contraction)"),
    9: ("tmi_vg", "Total magnetic intensity vertical gradient - rate of change in vertical direction"),
    10: ("deq_n100a15", "Distance to earthquake (n=100km radius, a=15 deg azimuth parameters)"),
    11: ("iso_grav_anom_vg", "Isostatic gravity anomaly vertical gradient - vertical rate of change"),
    12: ("det_elev", "Detrended elevation - topography with regional trends removed"),
    13: ("iso_grav_anom", "Isostatic gravity anomaly - gravity after compensating for topographic mass"),
    14: ("tmi", "Total magnetic intensity - total strength of magnetic field"),
    15: ("depth_to_base_surf", "Depth to basement surface - thickness of sedimentary cover"),
    16: ("ieq_n100a15", "Earthquake intensity or density (n=100km radius, a=15 deg parameters)"),
    17: ("cond_surf", "Conductivity surface - electrical conductivity of subsurface"),
    18: ("iso_grav_anom_hg", "Isostatic gravity anomaly horizontal gradient - horizontal rate of change"),
    19: ("det_elev_slope", "Detrended elevation slope - gradient of elevation after detrending"),
}
