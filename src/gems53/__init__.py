"""H53 - score-calibrated emission for the DOE GEMS Prize.

Modules
-------
:mod:`gems53.truthmodel`
    The official distance-weighted Tversky index written as an optimisation objective over a
    *weighted* (probabilistic) truth set, plus the exact binary-truth reference used to verify it.
:mod:`gems53.field`
    Label-free belief field: 3DEP/LiDAR scarp + GeoDAWN radiometric structure-tensor families,
    a directional line-integral "fault-likeness" term, geothermal-manifestation anchoring and
    road/mining-claim suppression.
:mod:`gems53.emitter`
    Expected-DTI greedy emitter: no hand-set mass, no hand-set spacing; both are solved for.
"""
from .field import DOMAIN, build_field, load_inputs
from .truthmodel import TruthModel, dti_exact, dti_weighted, support_coverage
from .emitter import emit_expected_dti

__all__ = [
    "DOMAIN", "build_field", "load_inputs", "TruthModel", "dti_exact", "dti_weighted",
    "support_coverage", "emit_expected_dti",
]
