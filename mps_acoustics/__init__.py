"""MPS parabolic-equation solver for ocean acoustic propagation (walking skeleton).

Module map (see docs/plans/2026-06-19-001-feat-mps-pe-ocean-acoustics-plan.md):

- environment  U2  Munk profile, seabed, full vertical domain, geometry, grid sizing
- pe_reference U3  pyram TL + pykrak cross-check on a reconciled grid; shared TL fn
- mps_field    U4  QTT encoding of the depth field; TL extraction
- propagator   U5  split-step refraction + diffraction MPOs, march, state-chi + MPO-bond
- validation   U6  masking, error metrics, pre-registered bar, joint gate, advantage-axis
- experiment   U7  wire MPS-PE vs reference on Munk, report accuracy-vs-chi

The core scientific bet: ocean acoustic fields may stay low bond dimension (χ),
making them cheap to compress. v1 tests this on the maximally-favorable
range-independent Munk case and can only *falsify* the bet, not confirm it.
"""

__version__ = "0.1.0"
