"""GEMSDOE50 H51: corroborated seismicity-plane lineament detection.

New evidence line for the DOE GEMS Prize (DrivenData #306), built 2026-10-06.

Distinct from the repository's earlier work
-------------------------------------------
* ``gems50`` (this repository's earlier package) ran a **space-only** 2-D
  triangle-area decluster, an epicentral anisotropic-clustering lineation, a Hough
  transform and a snap onto the 3DEP scarp ridge, and emitted an off-catalogue
  corridor file ``gems50-seislin-44709``.
* H51 instead (i) tests the 2-D **triangle-area** adaptation against a 3-D
  **space-time tetrahedron volume** with an empirical surrogate null, (ii) carries each
  event's own ``horizontalError`` through the decluster, the covariance fit *and* the
  corridor width, (iii) removes documented induced/anthropogenic sources before any
  geometry is fitted, (iv) requires multi-year recurrence, and (v) compares the resulting
  corridor field against independent topographic and radiometric lineament families on two
  instruments before anything is emitted.
* Measured outcome of that comparison, 2026-10-06: the seismicity family is **level with a
  matched random control** on the off-catalogue instrument and adds nothing on the Monte
  Cristo instrument, so the shipped build gives it no mass and emits a corroborated
  topographic + radiometric field instead.  The corridor geometry is still published, with
  its own instruments, as the recorded negative result of the H51-B hypothesis.
* Every part of that is flagged in :mod:`gems51.notes` as either published method,
  published method adapted to 2-D, or this project's own unverified adaptation.
"""
__all__ = ["emit", "grid", "instruments", "notes", "seisfield", "structfield",
           "uncertainty"]
