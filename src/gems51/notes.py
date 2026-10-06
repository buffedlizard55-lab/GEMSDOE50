"""Evidence-class labels, so no claim in this package is stronger than its source."""

PUBLISHED_3D = "published-3D"          # taken unchanged from the cited paper
ADAPTED_2D = "adapted-2D-unverified"   # published 3-D rule reduced to epicentres
OWN = "own-adaptation-unverified"      # this project's own invention
MEASURED = "measured-here"             # computed from pinned bytes in this session

OWN_WORK = {
    "h_err_model": (
        "The horizontal-uncertainty model in :mod:`gems51.uncertainty` "
        "(log10(h_err_m) ~ log10(nst) + log10(gap) + depth + mag, calibrated on the ComCat "
        "events of this footprint that publish their own horizontalError) is this project's own "
        "construction. It is NOT part of Ouillon/Sornette/Ducorbier or Wang et al. and it is "
        "carried as 'own-adaptation-unverified' wherever it is used."
    ),
}

CITATIONS = {
    "ouillon2008": (
        "Ouillon, G., Ducorbier, C., Sornette, D. (2008). Automatic reconstruction of fault "
        "networks from seismicity catalogs: three-dimensional optimal anisotropic dynamic "
        "clustering. JGR 113, B01306. doi:10.1029/2007JB005032"
    ),
    "ouillon2011": (
        "Ouillon, G., Sornette, D. (2011). Segmentation of fault networks determined from "
        "spatial clustering of earthquakes. JGR 116, B02306. doi:10.1029/2010JB007752"
    ),
    "wang2013": (
        "Wang, Y., Ouillon, G., Woessner, J., Sornette, D., Husen, S. (2013). Automatic "
        "reconstruction of fault networks from seismicity catalogs including location "
        "uncertainty. JGR Solid Earth 118, 5956-5975. doi:10.1002/2013JB010164 "
        "(preprint arXiv:1304.6912)"
    ),
    "competition": (
        "DrivenData/DOE GEMS Prize Challenge #306 problem description and evaluation page "
        "(round structure, inputs, submission contract, distance-weighted Tversky metric and "
        "its worked example) https://www.drivendata.org/competitions/306/competition-doe-gems/"
    ),
    "sgmc": (
        "USGS State Geologic Map Compilation (SGMC) fault inventory; USGS data are public "
        "domain (https://www.usgs.gov/information-policies-and-instructions/copyrights-and-credits)"
    ),
    "scarp3dep": (
        "3DEP/USGS lidar-derived scarp and topographic descriptors distributed with the "
        "competition; USGS data are public domain"
    ),
    "comcat": (
        "USGS ANSS Comprehensive Earthquake Catalog (ComCat), FDSN event service "
        "https://earthquake.usgs.gov/fdsnws/event/1/ - USGS data are public domain "
        "(https://www.usgs.gov/information-policies-and-instructions/copyrights-and-credits)"
    ),
}
