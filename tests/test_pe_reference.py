"""U3 tests -- reference TL: pyram cross-checked by pykrak on a reconciled grid.

Covers R3 (shared TL function), R4 (grid reconciliation), R10 (pyram-vs-pykrak
agreement). The heavy pyram/pykrak runs are computed once in module-scoped
fixtures and reused; the pure-array tests need no solver.
"""

from __future__ import annotations

from dataclasses import replace

import numpy as np
import pytest

from mps_acoustics.environment import OceanEnvironment
from mps_acoustics.pe_reference import (
    _PYKRAK_TL_OFFSET_DB,
    amplitude_mask,
    pyram_reference,
    reference_tl,
    references_agree,
    transmission_loss,
)

# Canonical range-independent Munk benchmark, kept fixed so the cross-check
# numbers are reproducible. Nz = 2^11 over water + absorbing seabed.
_BASE = dict(freq=50.0, receiver_depth=800.0, range_max=100_000.0, n_sites=11)


@pytest.fixture(scope="module")
def env() -> OceanEnvironment:
    return OceanEnvironment(source_depth=1000.0, **_BASE)


@pytest.fixture(scope="module")
def bundle(env):
    """The trusted reference bundle (pyram + pykrak + agreement), computed once."""
    return reference_tl(env)


# --------------------------------------------------------------------------- #
# R3 -- shared TL function (no solver needed)
# --------------------------------------------------------------------------- #
def test_shared_tl_maps_pressure_to_hand_value():
    # TL = -20 log10|p|: |p| = 0.1 -> 20 dB, |p| = 1 -> 0 dB.
    assert transmission_loss(0.1 + 0j) == pytest.approx(20.0, abs=1e-9)
    assert transmission_loss(1.0 + 0j) == pytest.approx(0.0, abs=1e-9)
    # Phase does not affect TL (magnitude only).
    assert transmission_loss(0.1j) == pytest.approx(20.0, abs=1e-9)


def test_shared_tl_round_trips_amplitude():
    amp = np.array([1.0, 0.5, 0.01, 1e-4])
    tl = transmission_loss(amp.astype(complex))
    assert np.allclose(10.0 ** (-tl / 20.0), amp, rtol=1e-9)


def test_shared_tl_applies_cylindrical_spreading():
    # ranges= adds the +10 log10(r) term (PE pressure excludes 1/sqrt(r)).
    p = np.full(3, 0.1 + 0j)
    r = np.array([1.0, 10.0, 100.0])
    tl = transmission_loss(p, ranges=r)
    assert np.allclose(tl, 20.0 + 10.0 * np.log10(r))


def test_shared_tl_reproduces_pyram_tl_grid():
    """The shared function reconstructs pyram's own TL Grid from its CP Grid.

    This is the "normalized identically" guarantee (R3): the reference path's TL
    is exactly what transmission_loss() computes from the complex pressure.
    """
    from pyram.PyRAM import PyRAM

    dz = 4.0
    z_ss = np.arange(0.0, 200.0 + dz, dz)
    cw = np.full_like(z_ss, 1500.0)[:, None]
    pr = PyRAM(
        50.0, 36.0, 36.0,
        z_ss, np.array([0.0]), cw,
        np.array([0.0]), np.array([0.0]),
        np.array([[1800.0]]), np.array([[1.8]]), np.array([[0.5]]),
        np.array([[0.0, 200.0]]),
        dz=dz, zmplt=200.0, rmax=5000.0,
    )
    res = pr.run()
    cpg, tlg, vr = res["CP Grid"], res["TL Grid"], res["Ranges"]
    reconstructed = transmission_loss(cpg, ranges=vr)  # vr broadcasts across columns
    assert np.nanmax(np.abs(reconstructed - tlg)) < 1e-9


# --------------------------------------------------------------------------- #
# R5 precursor -- amplitude mask is reference-only (no solver needed)
# --------------------------------------------------------------------------- #
def test_amplitude_mask_is_peak_relative_and_reference_only():
    # Loud bin (low TL) is in the mask; quiet bin (high TL) is out.
    tl = np.array([[60.0, 80.0, 95.0]])  # peak amplitude at the 60 dB bin
    mask = amplitude_mask(tl, db_below_peak=25.0)
    assert mask.tolist() == [[True, True, False]]  # within 25 dB of the 60 dB floor
    # The mask ignores any field-under-test: it is a pure function of tl.
    assert np.array_equal(mask, amplitude_mask(tl, 25.0))


# --------------------------------------------------------------------------- #
# R4 -- grid reconciliation
# --------------------------------------------------------------------------- #
def test_reference_axes_coincide_with_canonical_grid(env, bundle):
    canonical = env.depth_grid()
    nz = canonical.size
    assert nz & (nz - 1) == 0  # power of two (QTT requirement)
    # pyram and pykrak land on identical axes == the U2 canonical depth axis.
    assert np.array_equal(bundle.pyram.depth, canonical)
    assert np.array_equal(bundle.pykrak.depth, canonical)
    assert np.array_equal(bundle.pyram.ranges, bundle.pykrak.ranges)
    assert bundle.pyram.tl.shape == bundle.pykrak.tl.shape == (nz, bundle.pyram.ranges.size)


# --------------------------------------------------------------------------- #
# R10 -- pyram cross-checked by pykrak
# --------------------------------------------------------------------------- #
def test_pyram_and_pykrak_agree_on_munk(bundle):
    result = bundle.agreement
    assert bundle.trustworthy is True
    assert result.agree is True
    assert result.median_db <= result.tol_db
    assert result.n_masked > 0


def test_mismatched_environment_fails_agreement(env, bundle):
    """A near-surface source produces a structurally different field that the
    cross-check rejects against the original (ducted-source) reference."""
    mismatched = pyram_reference(replace(env, source_depth=100.0))
    result = references_agree(mismatched, bundle.pykrak)
    assert result.agree is False
    assert result.median_db > result.tol_db


def test_dropping_normalization_convention_fails_agreement(bundle):
    """If pykrak's 1/(4*pi) reference convention were left uncorrected, the
    cross-check would fail by ~22 dB -- the gate is not vacuously passing."""
    miscalibrated = replace(bundle.pykrak, tl=bundle.pykrak.tl + _PYKRAK_TL_OFFSET_DB)
    assert references_agree(bundle.pyram, miscalibrated).agree is False


def test_agreement_requires_matching_grids(bundle):
    smaller = replace(bundle.pykrak, tl=bundle.pykrak.tl[:, :-1])
    with pytest.raises(ValueError):
        references_agree(bundle.pyram, smaller)


# --------------------------------------------------------------------------- #
# Physics sanity + determinism
# --------------------------------------------------------------------------- #
def test_reference_shows_convergence_zone_structure(env, bundle):
    """Deep-water Munk TL re-focuses periodically (convergence zones); the field
    is not a monotonic decay. Detect a re-convergence in the smoothed receiver
    curve beyond the near field."""
    pyram = bundle.pyram
    zi = int(np.argmin(np.abs(pyram.depth - env.receiver_depth)))
    curve = pyram.tl[zi]
    dr = pyram.ranges[1] - pyram.ranges[0]
    win = max(3, int(5000.0 / dr))  # ~5 km smoothing
    smoothed = np.convolve(curve, np.ones(win) / win, mode="valid")
    far = smoothed[int(20000.0 / dr):]  # skip the near field
    running_max = np.maximum.accumulate(far)
    drawdown = float(np.max(running_max - far))  # largest re-convergence dip
    assert np.any(np.diff(far) < 0)  # non-monotonic
    assert drawdown > 8.0  # a real convergence-zone re-focus (observed ~21 dB)


def test_reference_is_deterministic(env, bundle):
    rerun = pyram_reference(env)
    assert np.array_equal(rerun.tl, bundle.pyram.tl)
    assert np.array_equal(rerun.ranges, bundle.pyram.ranges)
